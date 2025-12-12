"""
Payment processing endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
import stripe
import paypalrestsdk
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_active_user, require_admin
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.order import Order, Payment, SellerPayout, Coupon
from app.schemas.order import (
    PaymentResponse, PaymentCreate, StripePaymentRequest, PayPalPaymentRequest,
    PaymentWebhook, SellerPayoutResponse, CouponResponse, CouponCreate,
    CouponUpdate, CouponValidation
)
from app.core.exceptions import NotFoundError, ValidationError, PaymentError
import json

router = APIRouter()

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Configure PayPal
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})


@router.post("/stripe/create-payment-intent", response_model=dict)
async def create_stripe_payment_intent(
    payment_request: StripePaymentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create Stripe payment intent"""
    # Get order
    order = db.query(Order).filter(
        Order.id == payment_request.order_id,
        Order.buyer_id == current_user.id
    ).first()
    
    if not order:
        raise NotFoundError("Order not found")
    
    if order.status != "pending":
        raise ValidationError("Order is not in pending status")
    
    try:
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(order.total_amount * 100),  # Convert to cents
            currency=order.currency.lower(),
            payment_method=payment_request.payment_method_id,
            confirmation_method='manual',
            confirm=True,
            return_url=payment_request.return_url,
            metadata={
                'order_id': str(order.id),
                'user_id': str(current_user.id)
            }
        )
        
        # Create payment record
        payment = Payment(
            order_id=order.id,
            gateway="stripe",
            amount=order.total_amount,
            currency=order.currency,
            status="processing",
            transaction_id=intent.id,
            gateway_response=intent
        )
        
        db.add(payment)
        db.commit()
        
        return {
            "client_secret": intent.client_secret,
            "status": intent.status,
            "payment_id": payment.id
        }
        
    except stripe.error.StripeError as e:
        raise PaymentError(f"Stripe error: {str(e)}")


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        await handle_successful_payment(payment_intent, db)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        await handle_failed_payment(payment_intent, db)
    
    return {"status": "success"}


async def handle_successful_payment(payment_intent, db: Session):
    """Handle successful payment"""
    order_id = payment_intent['metadata']['order_id']
    
    # Update order status
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        order.status = "paid"
    
    # Update payment status
    payment = db.query(Payment).filter(
        Payment.transaction_id == payment_intent['id']
    ).first()
    if payment:
        payment.status = "completed"
        payment.processed_at = datetime.utcnow()
    
    # Create seller payouts
    await create_seller_payouts(order, db)
    
    db.commit()


async def handle_failed_payment(payment_intent, db: Session):
    """Handle failed payment"""
    # Update payment status
    payment = db.query(Payment).filter(
        Payment.transaction_id == payment_intent['id']
    ).first()
    if payment:
        payment.status = "failed"
        payment.failure_reason = payment_intent.get('last_payment_error', {}).get('message', 'Payment failed')
    
    db.commit()


async def create_seller_payouts(order: Order, db: Session):
    """Create seller payouts for order items"""
    commission_rate = settings.PLATFORM_COMMISSION_RATE
    
    for order_item in order.order_items:
        commission_amount = order_item.total_price * commission_rate
        net_amount = order_item.total_price - commission_amount
        
        payout = SellerPayout(
            seller_id=order_item.seller_id,
            order_id=order.id,
            order_item_id=order_item.id,
            amount=order_item.total_price,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
            net_amount=net_amount,
            status="pending"
        )
        
        db.add(payout)


@router.post("/paypal/create-order", response_model=dict)
async def create_paypal_order(
    payment_request: PayPalPaymentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create PayPal order"""
    # Get order
    order = db.query(Order).filter(
        Order.id == payment_request.order_id,
        Order.buyer_id == current_user.id
    ).first()
    
    if not order:
        raise NotFoundError("Order not found")
    
    if order.status != "pending":
        raise ValidationError("Order is not in pending status")
    
    try:
        # Create PayPal payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": payment_request.return_url,
                "cancel_url": payment_request.cancel_url
            },
            "transactions": [{
                "amount": {
                    "total": str(order.total_amount),
                    "currency": order.currency
                },
                "description": f"Order {order.order_number}",
                "custom": str(order.id)
            }]
        })
        
        if payment.create():
            # Create payment record
            db_payment = Payment(
                order_id=order.id,
                gateway="paypal",
                amount=order.total_amount,
                currency=order.currency,
                status="processing",
                transaction_id=payment.id,
                gateway_response=payment.to_dict()
            )
            
            db.add(db_payment)
            db.commit()
            
            # Get approval URL
            approval_url = None
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    break
            
            return {
                "payment_id": payment.id,
                "approval_url": approval_url,
                "db_payment_id": db_payment.id
            }
        else:
            raise PaymentError(f"PayPal error: {payment.error}")
            
    except Exception as e:
        raise PaymentError(f"PayPal error: {str(e)}")


@router.post("/paypal/execute")
async def execute_paypal_payment(
    payment_id: str,
    payer_id: str,
    db: Session = Depends(get_db)
):
    """Execute PayPal payment"""
    try:
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            # Update payment status
            db_payment = db.query(Payment).filter(
                Payment.transaction_id == payment_id
            ).first()
            
            if db_payment:
                db_payment.status = "completed"
                db_payment.processed_at = datetime.utcnow()
                
                # Update order status
                order = db.query(Order).filter(Order.id == db_payment.order_id).first()
                if order:
                    order.status = "paid"
                
                # Create seller payouts
                await create_seller_payouts(order, db)
                
                db.commit()
            
            return {"status": "success", "payment_id": payment_id}
        else:
            raise PaymentError(f"PayPal execution failed: {payment.error}")
            
    except Exception as e:
        raise PaymentError(f"PayPal error: {str(e)}")


@router.get("/history", response_model=List[PaymentResponse])
async def get_payment_history(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user payment history"""
    payments = db.query(Payment).join(Order).filter(
        Order.buyer_id == current_user.id
    ).order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()
    
    return payments


@router.get("/payouts", response_model=List[SellerPayoutResponse])
async def get_seller_payouts(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get seller payouts"""
    if current_user.role not in [UserRole.SELLER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seller access required"
        )
    
    # Get seller profile
    from app.models.user import Seller
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile not found"
        )
    
    payouts = db.query(SellerPayout).filter(
        SellerPayout.seller_id == seller.id
    ).order_by(SellerPayout.created_at.desc()).offset(skip).limit(limit).all()
    
    return payouts


# Coupon endpoints
@router.get("/coupons", response_model=List[CouponResponse])
async def get_coupons(
    skip: int = 0,
    limit: int = 20,
    is_active: bool = True,
    db: Session = Depends(get_db)
):
    """Get active coupons"""
    coupons = db.query(Coupon).filter(
        Coupon.is_active == is_active
    ).order_by(Coupon.created_at.desc()).offset(skip).limit(limit).all()
    
    return coupons


@router.post("/coupons/validate", response_model=dict)
async def validate_coupon(
    coupon_data: CouponValidation,
    db: Session = Depends(get_db)
):
    """Validate coupon code"""
    coupon = db.query(Coupon).filter(
        Coupon.code == coupon_data.code,
        Coupon.is_active == True
    ).first()
    
    if not coupon:
        raise ValidationError("Invalid coupon code")
    
    # Check validity dates
    from datetime import datetime
    now = datetime.utcnow()
    if now < coupon.valid_from or now > coupon.valid_until:
        raise ValidationError("Coupon has expired")
    
    # Check usage limit
    if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        raise ValidationError("Coupon usage limit exceeded")
    
    # Check minimum amount
    if coupon.minimum_amount and coupon_data.order_amount < coupon.minimum_amount:
        raise ValidationError(f"Minimum order amount of ${coupon.minimum_amount} required")
    
    # Calculate discount
    if coupon.type == "percentage":
        discount_amount = coupon_data.order_amount * (coupon.value / 100)
        if coupon.maximum_discount:
            discount_amount = min(discount_amount, coupon.maximum_discount)
    elif coupon.type == "fixed_amount":
        discount_amount = coupon.value
    else:  # free_shipping
        discount_amount = 0  # Will be handled separately
    
    return {
        "valid": True,
        "discount_amount": discount_amount,
        "coupon": coupon
    }


@router.post("/coupons", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    coupon_data: CouponCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create coupon (admin only)"""
    # Check if code already exists
    existing_coupon = db.query(Coupon).filter(Coupon.code == coupon_data.code).first()
    if existing_coupon:
        raise ValidationError("Coupon code already exists")
    
    coupon = Coupon(
        **coupon_data.dict(),
        created_by=current_user.id
    )
    
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    
    return coupon


@router.put("/coupons/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: int,
    coupon_update: CouponUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update coupon (admin only)"""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise NotFoundError("Coupon not found")
    
    # Update coupon fields
    for field, value in coupon_update.dict(exclude_unset=True).items():
        setattr(coupon, field, value)
    
    db.commit()
    db.refresh(coupon)
    
    return coupon


@router.delete("/coupons/{coupon_id}")
async def delete_coupon(
    coupon_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete coupon (admin only)"""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise NotFoundError("Coupon not found")
    
    db.delete(coupon)
    db.commit()
    
    return {"message": "Coupon deleted successfully"}
