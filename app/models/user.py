"""
User and subscription models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class User(Base):
    """Model for application users"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # User identification
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    
    # User preferences
    timezone = Column(String(50), nullable=False, default="UTC")
    language = Column(String(10), nullable=False, default="en")
    currency = Column(String(10), nullable=False, default="USD")
    
    # Notification preferences
    telegram_enabled = Column(Boolean, nullable=False, default=False)
    telegram_chat_id = Column(String(255), nullable=True)
    discord_enabled = Column(Boolean, nullable=False, default=False)
    discord_webhook_url = Column(String(500), nullable=True)
    email_enabled = Column(Boolean, nullable=False, default=True)
    sms_enabled = Column(Boolean, nullable=False, default=False)
    phone_number = Column(String(20), nullable=True)
    
    # Alert preferences
    alert_frequency = Column(String(20), nullable=False, default="medium")  # low, medium, high
    min_confidence_threshold = Column(Float, nullable=False, default=0.7)
    max_alerts_per_day = Column(Integer, nullable=False, default=20)
    
    # Tracking preferences
    tracked_tokens = Column(JSON, nullable=True, default=list)
    ignored_tokens = Column(JSON, nullable=True, default=list)
    whale_wallets_of_interest = Column(JSON, nullable=True, default=list)
    
    # User metrics
    total_alerts_received = Column(Integer, nullable=False, default=0)
    total_signals_followed = Column(Integer, nullable=False, default=0)
    total_profit_loss = Column(Float, nullable=False, default=0.0)
    
    # Account status
    subscription_status = Column(String(20), nullable=False, default="free")  # free, premium, pro
    subscription_expires_at = Column(DateTime, nullable=True)
    trial_expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=True)
    
    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_active', 'is_active'),
        Index('idx_user_subscription', 'subscription_status'),
        Index('idx_user_created', 'created_at'),
    )


class UserSubscription(Base):
    """Model for user subscriptions and billing"""
    __tablename__ = "user_subscriptions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    # Subscription details
    plan_name = Column(String(50), nullable=False, index=True)  # free, premium, pro
    plan_features = Column(JSON, nullable=False, default=dict)
    
    # Billing information
    price_per_month = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="USD")
    billing_cycle = Column(String(20), nullable=False, default="monthly")  # monthly, yearly
    
    # Subscription status
    status = Column(String(20), nullable=False, default="active")  # active, cancelled, expired, suspended
    starts_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Payment information
    payment_method = Column(String(50), nullable=True)  # stripe, paypal, crypto, etc.
    payment_reference = Column(String(255), nullable=True)
    last_payment_at = Column(DateTime, nullable=True)
    next_payment_at = Column(DateTime, nullable=True)
    
    # Usage tracking
    alerts_used_this_month = Column(Integer, nullable=False, default=0)
    alerts_limit_per_month = Column(Integer, nullable=False, default=100)
    api_calls_used_this_month = Column(Integer, nullable=False, default=0)
    api_calls_limit_per_month = Column(Integer, nullable=False, default=1000)
    
    # Features enabled
    features_enabled = Column(JSON, nullable=False, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    
    # Indexes
    __table_args__ = (
        Index('idx_subscription_user', 'user_id'),
        Index('idx_subscription_status', 'status'),
        Index('idx_subscription_expires', 'expires_at'),
        Index('idx_subscription_plan', 'plan_name'),
    )


