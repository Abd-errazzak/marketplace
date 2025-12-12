"""
User and Seller models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, JSON, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.BUYER)
    avatar_url = Column(String(500))
    verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime)
    phone = Column(String(20))
    date_of_birth = Column(DateTime)
    gender = Column(Enum("male", "female", "other"))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    seller_profile = relationship("Seller", back_populates="user", uselist=False)
    addresses = relationship("UserAddress", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user")
    orders = relationship("Order", back_populates="buyer")
    messages_sent = relationship("Message", foreign_keys="Message.from_user_id", back_populates="from_user")
    messages_received = relationship("Message", foreign_keys="Message.to_user_id", back_populates="to_user")
    notifications = relationship("Notification", back_populates="user")
    reviews = relationship("ProductReview", back_populates="user")
    wishlist_items = relationship("WishlistItem", back_populates="user")


class Seller(Base):
    __tablename__ = "sellers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shop_name = Column(String(255), nullable=False)
    shop_description = Column(Text)
    shop_logo = Column(String(500))
    business_license = Column(String(100))
    tax_id = Column(String(100))
    payout_details = Column(JSON)
    rating = Column(DECIMAL(3, 2), default=0.00)
    total_sales = Column(Integer, default=0)
    total_orders = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="seller_profile")
    products = relationship("Product", back_populates="seller")
    order_items = relationship("OrderItem", back_populates="seller")
    payouts = relationship("SellerPayout", back_populates="seller")


class UserAddress(Base):
    __tablename__ = "user_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum("billing", "shipping"), nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    company = Column(String(255))
    address_line_1 = Column(String(255), nullable=False)
    address_line_2 = Column(String(255))
    city = Column(String(100), nullable=False)
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100), nullable=False)
    phone = Column(String(20))
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="addresses")

