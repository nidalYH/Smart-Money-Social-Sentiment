"""
Alert system models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Alert(Base):
    """Model for alerts"""
    __tablename__ = "alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Alert identification
    alert_type = Column(String(50), nullable=False, index=True)  # signal, whale_activity, sentiment_shift, etc.
    priority = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    
    # Target information
    token_address = Column(String(42), nullable=True, index=True)
    token_symbol = Column(String(20), nullable=True, index=True)
    
    # Alert content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    
    # Alert data
    timestamp = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Alert metrics
    confidence_score = Column(Float, nullable=False, default=0.0)
    impact_score = Column(Float, nullable=False, default=0.0)
    
    # Related data
    signal_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    whale_wallet_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    sentiment_score_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Alert context
    market_conditions = Column(JSON, nullable=True, default=dict)
    technical_indicators = Column(JSON, nullable=True, default=dict)
    social_metrics = Column(JSON, nullable=True, default=dict)
    
    # Delivery settings
    delivery_channels = Column(JSON, nullable=False, default=list)  # [telegram, discord, email]
    delivery_status = Column(String(20), nullable=False, default="pending")  # pending, delivered, failed
    
    # Status tracking
    is_active = Column(Boolean, nullable=False, default=True)
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # Performance tracking
    click_count = Column(Integer, nullable=False, default=0)
    action_taken = Column(String(50), nullable=True)  # buy, sell, ignore, investigate
    
    # Relationships
    deliveries = relationship("AlertDelivery", back_populates="alert")
    
    # Indexes
    __table_args__ = (
        Index('idx_alert_type_timestamp', 'alert_type', 'timestamp'),
        Index('idx_alert_priority', 'priority'),
        Index('idx_alert_delivery_status', 'delivery_status'),
        Index('idx_alert_active', 'is_active'),
        Index('idx_alert_expires', 'expires_at'),
    )


class AlertDelivery(Base):
    """Model for tracking alert deliveries"""
    __tablename__ = "alert_deliveries"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey("alerts.id"), nullable=False, index=True)
    
    # Delivery details
    channel = Column(String(50), nullable=False, index=True)  # telegram, discord, email, sms
    recipient_id = Column(String(255), nullable=False, index=True)  # user_id, chat_id, email, etc.
    
    # Delivery status
    status = Column(String(20), nullable=False, default="pending")  # pending, sent, delivered, failed
    attempted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    
    # Delivery metadata
    delivery_method = Column(String(50), nullable=True)  # push, webhook, api, etc.
    external_message_id = Column(String(255), nullable=True)  # platform-specific message ID
    
    # Performance metrics
    delivery_time_ms = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    alert = relationship("Alert", back_populates="deliveries")
    
    # Indexes
    __table_args__ = (
        Index('idx_delivery_alert_channel', 'alert_id', 'channel'),
        Index('idx_delivery_status', 'status'),
        Index('idx_delivery_attempted', 'attempted_at'),
        Index('idx_delivery_recipient', 'recipient_id'),
    )


