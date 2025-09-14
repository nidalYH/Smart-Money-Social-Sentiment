"""
Trading signal models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy import JSON
import uuid

from app.database import Base


class TradingSignal(Base):
    """Model for trading signals"""
    __tablename__ = "trading_signals"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Signal identification
    signal_id = Column(String(100), unique=True, nullable=False, index=True)
    signal_type = Column(String(50), nullable=False, index=True)  # EARLY_ACCUMULATION, MOMENTUM_BUILD, etc.
    
    # Target information
    token_address = Column(String(42), nullable=False, index=True)
    token_symbol = Column(String(20), nullable=False, index=True)
    token_name = Column(String(100), nullable=False)
    
    # Signal details
    timestamp = Column(DateTime, nullable=False, index=True)
    action = Column(String(10), nullable=False, index=True)  # BUY, SELL, HOLD
    confidence_score = Column(Float, nullable=False)  # 0 to 1
    risk_score = Column(Float, nullable=False)  # 0 to 1
    
    # Price information
    current_price = Column(Float, nullable=False)
    target_price = Column(Float, nullable=True)
    stop_loss_price = Column(Float, nullable=True)
    price_change_24h = Column(Float, nullable=True)
    
    # Market context
    market_cap = Column(Float, nullable=True)
    volume_24h = Column(Float, nullable=True)
    volume_change_24h = Column(Float, nullable=True)
    
    # Signal components
    whale_activity_score = Column(Float, nullable=False, default=0.0)
    sentiment_score = Column(Float, nullable=False, default=0.0)
    technical_score = Column(Float, nullable=False, default=0.0)
    volume_score = Column(Float, nullable=False, default=0.0)
    
    # Whale data
    whale_transaction_count = Column(Integer, nullable=False, default=0)
    whale_volume_usd = Column(Float, nullable=False, default=0.0)
    whale_wallets_involved = Column(JSON, nullable=True, default=list)
    whale_accumulation_pattern = Column(JSON, nullable=True, default=dict)
    
    # Sentiment data
    sentiment_trend = Column(String(20), nullable=True)
    mention_velocity = Column(Float, nullable=False, default=0.0)
    influencer_sentiment = Column(Float, nullable=False, default=0.0)
    social_momentum = Column(Float, nullable=False, default=0.0)
    
    # Technical indicators
    rsi = Column(Float, nullable=True)
    macd_signal = Column(String(20), nullable=True)
    bollinger_position = Column(String(20), nullable=True)
    moving_average_trend = Column(String(20), nullable=True)
    
    # Signal reasoning
    reasoning = Column(Text, nullable=True)
    key_factors = Column(JSON, nullable=True, default=list)
    risk_factors = Column(JSON, nullable=True, default=list)
    
    # Performance tracking
    is_active = Column(Boolean, nullable=False, default=True)
    is_triggered = Column(Boolean, nullable=False, default=False)
    triggered_at = Column(DateTime, nullable=True)
    triggered_price = Column(Float, nullable=True)
    
    # Metadata
    created_by = Column(String(50), nullable=False, default="system")
    version = Column(String(10), nullable=False, default="1.0")
    tags = Column(JSON, nullable=True, default=list)
    
    # Indexes
    __table_args__ = (
        Index('idx_signal_type_timestamp', 'signal_type', 'timestamp'),
        Index('idx_signal_token_timestamp', 'token_address', 'timestamp'),
        Index('idx_signal_confidence', 'confidence_score'),
        Index('idx_signal_active', 'is_active'),
        Index('idx_signal_action', 'action'),
    )


class SignalPerformance(Base):
    """Model for tracking signal performance"""
    __tablename__ = "signal_performance"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id = Column(String(36), nullable=False, index=True)
    
    # Performance tracking
    timestamp = Column(DateTime, nullable=False, index=True)
    current_price = Column(Float, nullable=False)
    
    # Performance metrics
    price_change_percent = Column(Float, nullable=False, default=0.0)
    unrealized_pnl_percent = Column(Float, nullable=False, default=0.0)
    
    # Time-based metrics
    time_since_signal = Column(Integer, nullable=False, default=0)  # minutes
    max_profit_percent = Column(Float, nullable=False, default=0.0)
    max_drawdown_percent = Column(Float, nullable=False, default=0.0)
    
    # Market conditions
    market_cap = Column(Float, nullable=True)
    volume_24h = Column(Float, nullable=True)
    market_sentiment = Column(Float, nullable=True)
    
    # Status tracking
    is_stop_loss_hit = Column(Boolean, nullable=False, default=False)
    is_target_hit = Column(Boolean, nullable=False, default=False)
    is_expired = Column(Boolean, nullable=False, default=False)
    
    # Final performance (when signal closes)
    final_price = Column(Float, nullable=True)
    final_pnl_percent = Column(Float, nullable=True)
    hold_duration_hours = Column(Integer, nullable=True)
    
    # Relationships
    signal = relationship("TradingSignal", back_populates="performance_records")
    
    # Indexes
    __table_args__ = (
        Index('idx_performance_signal_timestamp', 'signal_id', 'timestamp'),
        Index('idx_performance_pnl', 'unrealized_pnl_percent'),
        Index('idx_performance_expired', 'is_expired'),
    )


