"""
Order and Payment models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, JSON, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum("pending", "paid", "processing", "shipped", "delivered", "cancelled", "refunded"), default="pending")
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    tax_amount = Column(DECIMAL(10, 2), default=0.00)
    shipping_amount = Column(DECIMAL(10, 2), default=0.00)
    discount_amount = Column(DECIMAL(10, 2), default=0.00)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    billing_address = Column(JSON, nullable=False)
    shipping_address = Column(JSON, nullable=False)
    notes = Column(Text)
    tracking_number = Column(String(100))
    shipped_at = Column(DateTime)
    delivered_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    buyer = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")
    payments = relationship("Payment", back_populates="order")
    messages = relationship("Message", back_populates="order")
    reviews = relationship("ProductReview", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variation_id = Column(Integer, ForeignKey("product_variations.id"))
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    product_title = Column(String(255), nullable=False)
    product_sku = Column(String(100))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    total_price = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    variation = relationship("ProductVariation", back_populates="order_items")
    seller = relationship("Seller", back_populates="order_items")
    payouts = relationship("SellerPayout", back_populates="order_item")


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    gateway = Column(Enum("stripe", "paypal", "bank_transfer"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(Enum("pending", "processing", "completed", "failed", "cancelled", "refunded"), default="pending")
    transaction_id = Column(String(255))
    gateway_response = Column(JSON)
    failure_reason = Column(Text)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="payments")


class SellerPayout(Base):
    __tablename__ = "seller_payouts"
    
    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    commission_rate = Column(DECIMAL(5, 4), nullable=False)
    commission_amount = Column(DECIMAL(10, 2), nullable=False)
    net_amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(Enum("pending", "processing", "completed", "failed"), default="pending")
    payout_method = Column(String(50))
    payout_details = Column(JSON)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    seller = relationship("Seller", back_populates="payouts")
    order = relationship("Order")
    order_item = relationship("OrderItem", back_populates="payouts")


class Coupon(Base):
    __tablename__ = "coupons"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(Enum("percentage", "fixed_amount", "free_shipping"), nullable=False)
    value = Column(DECIMAL(10, 2), nullable=False)
    minimum_amount = Column(DECIMAL(10, 2))
    maximum_discount = Column(DECIMAL(10, 2))
    usage_limit = Column(Integer)
    used_count = Column(Integer, default=0)
    user_limit = Column(Integer, default=1)  # Per user usage limit
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")

