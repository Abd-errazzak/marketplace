"""
Admin panel endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User, UserRole, Seller
from app.models.product import Product, Category
from app.models.order import Order, OrderItem, Payment, SellerPayout
from app.models.message import Message, Notification, AnalyticsEvent
from app.schemas.user import UserResponse, SellerResponse
from app.schemas.product import ProductResponse, CategoryResponse
from app.schemas.order import OrderResponse, PaymentResponse, SellerPayoutResponse
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics"""
    # Get date range (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # User statistics
    total_users = db.query(User).count()
    new_users = db.query(User).filter(User.created_at >= thirty_days_ago).count()
    active_sellers = db.query(Seller).filter(Seller.is_active == True).count()
    
    # Product statistics
    total_products = db.query(Product).count()
    active_products = db.query(Product).filter(Product.status == "active").count()
    pending_products = db.query(Product).filter(Product.status == "draft").count()
    
    # Order statistics
    total_orders = db.query(Order).count()
    recent_orders = db.query(Order).filter(Order.created_at >= thirty_days_ago).count()
    pending_orders = db.query(Order).filter(Order.status == "pending").count()
    
    # Revenue statistics
    total_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.status.in_(["paid", "processing", "shipped", "delivered"])
    ).scalar() or 0
    
    recent_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= thirty_days_ago,
        Order.status.in_(["paid", "processing", "shipped", "delivered"])
    ).scalar() or 0
    
    # Commission statistics
    total_commission = db.query(func.sum(SellerPayout.commission_amount)).filter(
        SellerPayout.status == "completed"
    ).scalar() or 0
    
    return {
        "users": {
            "total": total_users,
            "new_last_30_days": new_users,
            "active_sellers": active_sellers
        },
        "products": {
            "total": total_products,
            "active": active_products,
            "pending": pending_products
        },
        "orders": {
            "total": total_orders,
            "recent_last_30_days": recent_orders,
            "pending": pending_orders
        },
        "revenue": {
            "total": float(total_revenue),
            "recent_last_30_days": float(recent_revenue),
            "total_commission": float(total_commission)
        }
    }


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    role: UserRole = None,
    is_active: bool = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all users with filtering"""
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    
    return user


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activate user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    
    user.is_active = True
    db.commit()
    
    return {"message": "User activated successfully"}


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Deactivate user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    
    user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    new_role: UserRole,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user role"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    
    user.role = new_role
    db.commit()
    
    return {"message": f"User role updated to {new_role}"}


@router.get("/sellers", response_model=List[SellerResponse])
async def get_all_sellers(
    skip: int = 0,
    limit: int = 100,
    is_verified: bool = None,
    is_active: bool = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all sellers with filtering"""
    query = db.query(Seller)
    
    if is_verified is not None:
        query = query.filter(Seller.is_verified == is_verified)
    
    if is_active is not None:
        query = query.filter(Seller.is_active == is_active)
    
    sellers = query.order_by(desc(Seller.created_at)).offset(skip).limit(limit).all()
    return sellers


@router.put("/sellers/{seller_id}/verify")
async def verify_seller(
    seller_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Verify seller"""
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise NotFoundError("Seller not found")
    
    seller.is_verified = True
    db.commit()
    
    return {"message": "Seller verified successfully"}


@router.put("/sellers/{seller_id}/unverify")
async def unverify_seller(
    seller_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Unverify seller"""
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise NotFoundError("Seller not found")
    
    seller.is_verified = False
    db.commit()
    
    return {"message": "Seller unverified successfully"}


@router.get("/products", response_model=List[ProductResponse])
async def get_all_products(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    seller_id: int = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all products with filtering"""
    query = db.query(Product)
    
    if status:
        query = query.filter(Product.status == status)
    
    if seller_id:
        query = query.filter(Product.seller_id == seller_id)
    
    products = query.order_by(desc(Product.created_at)).offset(skip).limit(limit).all()
    return products


@router.put("/products/{product_id}/approve")
async def approve_product(
    product_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Approve product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundError("Product not found")
    
    product.status = "active"
    db.commit()
    
    return {"message": "Product approved successfully"}


@router.put("/products/{product_id}/reject")
async def reject_product(
    product_id: int,
    reason: str = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Reject product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundError("Product not found")
    
    product.status = "inactive"
    db.commit()
    
    return {"message": "Product rejected successfully"}


@router.get("/orders", response_model=List[OrderResponse])
async def get_all_orders(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all orders with filtering"""
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(desc(Order.created_at)).offset(skip).limit(limit).all()
    return orders


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get order by ID"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")
    
    return order


@router.get("/payments", response_model=List[PaymentResponse])
async def get_all_payments(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    gateway: str = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all payments with filtering"""
    query = db.query(Payment)
    
    if status:
        query = query.filter(Payment.status == status)
    
    if gateway:
        query = query.filter(Payment.gateway == gateway)
    
    payments = query.order_by(desc(Payment.created_at)).offset(skip).limit(limit).all()
    return payments


@router.get("/payouts", response_model=List[SellerPayoutResponse])
async def get_all_payouts(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all seller payouts with filtering"""
    query = db.query(SellerPayout)
    
    if status:
        query = query.filter(SellerPayout.status == status)
    
    payouts = query.order_by(desc(SellerPayout.created_at)).offset(skip).limit(limit).all()
    return payouts


@router.put("/payouts/{payout_id}/process")
async def process_payout(
    payout_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Process seller payout"""
    payout = db.query(SellerPayout).filter(SellerPayout.id == payout_id).first()
    if not payout:
        raise NotFoundError("Payout not found")
    
    if payout.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payout is not in pending status"
        )
    
    # TODO: Implement actual payout processing (Stripe Connect, PayPal, etc.)
    payout.status = "processing"
    payout.processed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Payout processing initiated"}


@router.get("/analytics/events")
async def get_analytics_events(
    skip: int = 0,
    limit: int = 100,
    event_type: str = None,
    days: int = 7,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get analytics events"""
    query = db.query(AnalyticsEvent)
    
    if event_type:
        query = query.filter(AnalyticsEvent.event_type == event_type)
    
    # Filter by date range
    start_date = datetime.utcnow() - timedelta(days=days)
    query = query.filter(AnalyticsEvent.created_at >= start_date)
    
    events = query.order_by(desc(AnalyticsEvent.created_at)).offset(skip).limit(limit).all()
    
    return {
        "events": events,
        "total_count": query.count()
    }


@router.get("/notifications", response_model=List[Dict[str, Any]])
async def get_notifications(
    skip: int = 0,
    limit: int = 100,
    is_read: bool = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all notifications"""
    query = db.query(Notification)
    
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    
    notifications = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()
    
    return [
        {
            "id": n.id,
            "user_id": n.user_id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at
        }
        for n in notifications
    ]


@router.get("/messages", response_model=List[Dict[str, Any]])
async def get_messages(
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all messages"""
    messages = db.query(Message).order_by(desc(Message.created_at)).offset(skip).limit(limit).all()
    
    return [
        {
            "id": m.id,
            "from_user_id": m.from_user_id,
            "to_user_id": m.to_user_id,
            "order_id": m.order_id,
            "content": m.content,
            "message_type": m.message_type,
            "is_read": m.is_read,
            "created_at": m.created_at
        }
        for m in messages
    ]



