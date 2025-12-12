"""
Order management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_active_user, require_seller
from app.models.user import User, UserRole, Seller
from app.models.product import CartItem, Product
from app.models.order import Order, OrderItem
from app.schemas.order import (
    OrderCreate, OrderResponse, OrderWithItems, OrderUpdate,
    OrderItemResponse, CheckoutRequest
)
from app.core.exceptions import NotFoundError, ValidationError
import uuid

router = APIRouter()


@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    skip: int = 0,
    limit: int = 20,
    status: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user orders"""
    query = db.query(Order).filter(Order.buyer_id == current_user.id)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders


@router.get("/{order_id}", response_model=OrderWithItems)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get order by ID"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.buyer_id == current_user.id
    ).first()
    
    if not order:
        raise NotFoundError("Order not found")
    
    return order


@router.post("/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    checkout_data: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create order from cart items"""
    # Get cart items
    cart_items = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    
    if not cart_items:
        raise ValidationError("Cart is empty")
    
    # Calculate totals
    subtotal = sum(item.price * item.quantity for item in cart_items)
    tax_amount = subtotal * 0.1  # 10% tax (should be configurable)
    shipping_amount = 0 if subtotal >= 50 else 10  # Free shipping over $50
    total_amount = subtotal + tax_amount + shipping_amount - checkout_data.discount_amount
    
    # Generate order number
    order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    # Create order
    order = Order(
        order_number=order_number,
        buyer_id=current_user.id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_amount=shipping_amount,
        discount_amount=checkout_data.discount_amount,
        total_amount=total_amount,
        billing_address=checkout_data.billing_address,
        shipping_address=checkout_data.shipping_address,
        notes=checkout_data.notes
    )
    
    db.add(order)
    db.flush()  # Get order ID
    
    # Create order items and update stock
    for cart_item in cart_items:
        # Check stock availability
        product = db.query(Product).filter(Product.id == cart_item.product_id).first()
        if not product:
            raise ValidationError(f"Product {cart_item.product_id} not found")
        
        if product.stock < cart_item.quantity:
            raise ValidationError(f"Insufficient stock for {product.title}")
        
        # Create order item
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            variation_id=cart_item.variation_id,
            seller_id=product.seller_id,
            product_title=product.title,
            product_sku=product.sku,
            quantity=cart_item.quantity,
            unit_price=cart_item.price,
            total_price=cart_item.price * cart_item.quantity
        )
        
        db.add(order_item)
        
        # Update product stock
        product.stock -= cart_item.quantity
        product.sales_count += cart_item.quantity
    
    # Clear cart
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    
    db.commit()
    db.refresh(order)
    
    return order


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_update: OrderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update order status"""
    # Check if user is admin or seller
    if current_user.role == UserRole.ADMIN:
        order = db.query(Order).filter(Order.id == order_id).first()
    elif current_user.role == UserRole.SELLER:
        # Get seller profile
        seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seller profile not found"
            )
        
        # Check if order contains seller's products
        order = db.query(Order).join(OrderItem).filter(
            Order.id == order_id,
            OrderItem.seller_id == seller.id
        ).first()
    else:
        # Regular user can only update their own orders
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.buyer_id == current_user.id
        ).first()
    
    if not order:
        raise NotFoundError("Order not found")
    
    # Update order fields
    for field, value in status_update.dict(exclude_unset=True).items():
        setattr(order, field, value)
    
    # Set timestamps for status changes
    if status_update.status == "shipped":
        order.shipped_at = datetime.utcnow()
    elif status_update.status == "delivered":
        order.delivered_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    
    return order


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel order"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.buyer_id == current_user.id
    ).first()
    
    if not order:
        raise NotFoundError("Order not found")
    
    if order.status not in ["pending", "paid"]:
        raise ValidationError("Order cannot be cancelled")
    
    # Update order status
    order.status = "cancelled"
    
    # Restore product stock
    for order_item in order.order_items:
        product = db.query(Product).filter(Product.id == order_item.product_id).first()
        if product:
            product.stock += order_item.quantity
            product.sales_count -= order_item.quantity
    
    db.commit()
    
    return {"message": "Order cancelled successfully"}


# Seller order endpoints
@router.get("/seller/orders", response_model=List[OrderResponse])
async def get_seller_orders(
    skip: int = 0,
    limit: int = 20,
    status: str = None,
    current_user: User = Depends(require_seller),
    db: Session = Depends(get_db)
):
    """Get seller orders"""
    # Get seller profile
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile not found"
        )
    
    # Get orders that contain seller's products
    query = db.query(Order).join(OrderItem).filter(OrderItem.seller_id == seller.id)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders


@router.get("/seller/orders/{order_id}", response_model=OrderWithItems)
async def get_seller_order(
    order_id: int,
    current_user: User = Depends(require_seller),
    db: Session = Depends(get_db)
):
    """Get seller order by ID"""
    # Get seller profile
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile not found"
        )
    
    # Get order that contains seller's products
    order = db.query(Order).join(OrderItem).filter(
        Order.id == order_id,
        OrderItem.seller_id == seller.id
    ).first()
    
    if not order:
        raise NotFoundError("Order not found")
    
    return order


@router.put("/seller/orders/{order_id}/fulfill")
async def fulfill_order(
    order_id: int,
    tracking_number: str = None,
    current_user: User = Depends(require_seller),
    db: Session = Depends(get_db)
):
    """Mark order as fulfilled by seller"""
    # Get seller profile
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile not found"
        )
    
    # Get order that contains seller's products
    order = db.query(Order).join(OrderItem).filter(
        Order.id == order_id,
        OrderItem.seller_id == seller.id
    ).first()
    
    if not order:
        raise NotFoundError("Order not found")
    
    if order.status not in ["paid", "processing"]:
        raise ValidationError("Order cannot be fulfilled")
    
    # Update order status
    order.status = "shipped"
    order.shipped_at = datetime.utcnow()
    
    if tracking_number:
        order.tracking_number = tracking_number
    
    db.commit()
    
    return {"message": "Order fulfilled successfully"}

