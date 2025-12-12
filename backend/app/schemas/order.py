"""
Order and payment schemas
"""

from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: int
    variation_id: Optional[int] = None
    seller_id: int
    product_title: str
    product_sku: Optional[str] = None
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    order_number: str
    buyer_id: int
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    currency: str
    billing_address: Dict[str, Any]
    shipping_address: Dict[str, Any]
    notes: Optional[str] = None
    tracking_number: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrderWithItems(OrderResponse):
    order_items: List[OrderItemResponse] = []


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


class CheckoutRequest(BaseModel):
    billing_address: Dict[str, Any]
    shipping_address: Dict[str, Any]
    discount_amount: Decimal = Decimal('0.00')
    notes: Optional[str] = None
    coupon_code: Optional[str] = None
    
    @validator('billing_address')
    def validate_billing_address(cls, v):
        required_fields = ['first_name', 'last_name', 'address_line_1', 'city', 'country']
        for field in required_fields:
            if field not in v or not v[field]:
                raise ValueError(f'Billing address {field} is required')
        return v
    
    @validator('shipping_address')
    def validate_shipping_address(cls, v):
        required_fields = ['first_name', 'last_name', 'address_line_1', 'city', 'country']
        for field in required_fields:
            if field not in v or not v[field]:
                raise ValueError(f'Shipping address {field} is required')
        return v


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    gateway: str
    amount: Decimal
    currency: str
    status: str
    transaction_id: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    order_id: int
    gateway: str
    amount: Decimal
    currency: str = "USD"


class StripePaymentRequest(BaseModel):
    order_id: int
    payment_method_id: str
    return_url: str


class PayPalPaymentRequest(BaseModel):
    order_id: int
    return_url: str
    cancel_url: str


class PaymentWebhook(BaseModel):
    event_type: str
    data: Dict[str, Any]
    signature: Optional[str] = None


class SellerPayoutResponse(BaseModel):
    id: int
    seller_id: int
    order_id: int
    order_item_id: int
    amount: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    net_amount: Decimal
    status: str
    payout_method: Optional[str] = None
    payout_details: Optional[Dict[str, Any]] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CouponResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    type: str
    value: Decimal
    minimum_amount: Optional[Decimal] = None
    maximum_discount: Optional[Decimal] = None
    usage_limit: Optional[int] = None
    used_count: int
    user_limit: int
    valid_from: datetime
    valid_until: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CouponCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    type: str
    value: Decimal
    minimum_amount: Optional[Decimal] = None
    maximum_discount: Optional[Decimal] = None
    usage_limit: Optional[int] = None
    user_limit: int = 1
    valid_from: datetime
    valid_until: datetime
    is_active: bool = True


class CouponUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    value: Optional[Decimal] = None
    minimum_amount: Optional[Decimal] = None
    maximum_discount: Optional[Decimal] = None
    usage_limit: Optional[int] = None
    user_limit: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None


class CouponValidation(BaseModel):
    code: str
    order_amount: Decimal


# Missing classes that are imported elsewhere
class OrderCreate(BaseModel):
    billing_address: Dict[str, Any]
    shipping_address: Dict[str, Any]
    discount_amount: Decimal = Decimal('0.00')
    notes: Optional[str] = None
    coupon_code: Optional[str] = None


class OrderOut(OrderResponse):
    pass


class PaymentOut(PaymentResponse):
    pass


class SellerPayoutCreate(BaseModel):
    seller_id: int
    order_id: int
    order_item_id: int
    amount: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    net_amount: Decimal
    payout_method: Optional[str] = None
    payout_details: Optional[Dict[str, Any]] = None


class SellerPayoutOut(SellerPayoutResponse):
    pass


class CouponOut(CouponResponse):
    pass
