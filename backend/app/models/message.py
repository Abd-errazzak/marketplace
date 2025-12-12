"""
Message and Notification models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"))  # Optional: tie to specific order
    content = Column(Text, nullable=False)
    message_type = Column(Enum("text", "image", "file", "system"), default="text")
    attachments = Column(JSON)  # Array of file URLs
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="messages_sent")
    to_user = relationship("User", foreign_keys=[to_user_id], back_populates="messages_received")
    order = relationship("Order", back_populates="messages")


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(100), nullable=False)  # order_created, message_received, etc.
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSON)  # Additional data
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    sent_email = Column(Boolean, default=False)
    sent_push = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notifications")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String(255))
    event_type = Column(String(100), nullable=False)  # page_view, product_view, add_to_cart, etc.
    event_data = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    referrer = Column(String(500))
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User")


class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text)
    type = Column(Enum("string", "number", "boolean", "json"), default="string")
    description = Column(Text)
    is_public = Column(Boolean, default=False)  # Can be accessed by frontend
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

