"""
Token and price data models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy import JSON
import uuid

from app.database import Base


class Token(Base):
    """Model for token information"""
    __tablename__ = "tokens"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Token identifiers
    address = Column(String(42), unique=True, nullable=False, index=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    
    # Token metadata
    decimals = Column(Integer, nullable=False, default=18)
    total_supply = Column(Float, nullable=True)
    circulating_supply = Column(Float, nullable=True)
    
    # Market data
    market_cap = Column(Float, nullable=True)
    market_cap_rank = Column(Integer, nullable=True)
    fully_diluted_valuation = Column(Float, nullable=True)
    
    # Trading data
    current_price = Column(Float, nullable=True)
    price_change_24h = Column(Float, nullable=True)
    price_change_percentage_24h = Column(Float, nullable=True)
    price_change_percentage_7d = Column(Float, nullable=True)
    price_change_percentage_30d = Column(Float, nullable=True)
    
    # Volume data
    volume_24h = Column(Float, nullable=True)
    volume_change_percentage_24h = Column(Float, nullable=True)
    
    # Additional metrics
    ath = Column(Float, nullable=True)  # All-time high
    ath_change_percentage = Column(Float, nullable=True)
    ath_date = Column(DateTime, nullable=True)
    atl = Column(Float, nullable=True)  # All-time low
    atl_change_percentage = Column(Float, nullable=True)
    atl_date = Column(DateTime, nullable=True)
    
    # Social and community data
    community_score = Column(Float, nullable=True)
    developer_score = Column(Float, nullable=True)
    liquidity_score = Column(Float, nullable=True)
    public_interest_score = Column(Float, nullable=True)
    
    # Classification
    categories = Column(JSON, nullable=True, default=list)
    platforms = Column(JSON, nullable=True, default=dict)
    
    # Status
    is_tracked = Column(Boolean, nullable=False, default=True)
    is_stablecoin = Column(Boolean, nullable=False, default=False)
    is_dex_token = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_token_symbol', 'symbol'),
        Index('idx_token_market_cap_rank', 'market_cap_rank'),
        Index('idx_token_tracked', 'is_tracked'),
        Index('idx_token_volume_24h', 'volume_24h'),
    )


class TokenPrice(Base):
    """Model for historical token prices"""
    __tablename__ = "token_prices"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token_address = Column(String(42), nullable=False, index=True)
    
    # Price data
    timestamp = Column(DateTime, nullable=False, index=True)
    price_usd = Column(Float, nullable=False)
    price_btc = Column(Float, nullable=True)
    price_eth = Column(Float, nullable=True)
    
    # Market data
    market_cap = Column(Float, nullable=True)
    volume_24h = Column(Float, nullable=True)
    market_cap_rank = Column(Integer, nullable=True)
    
    # Price changes
    price_change_1h = Column(Float, nullable=True)
    price_change_24h = Column(Float, nullable=True)
    price_change_7d = Column(Float, nullable=True)
    price_change_30d = Column(Float, nullable=True)
    
    # Technical indicators (if calculated)
    rsi_14 = Column(Float, nullable=True)
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    ema_12 = Column(Float, nullable=True)
    ema_26 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    bollinger_upper = Column(Float, nullable=True)
    bollinger_lower = Column(Float, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_price_token_timestamp', 'token_address', 'timestamp'),
        Index('idx_price_timestamp', 'timestamp'),
        Index('idx_price_token', 'token_address'),
    )


class TokenVolume(Base):
    """Model for token volume data"""
    __tablename__ = "token_volumes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token_address = Column(String(42), nullable=False, index=True)
    
    # Volume data
    timestamp = Column(DateTime, nullable=False, index=True)
    volume_24h = Column(Float, nullable=False)
    volume_change_24h = Column(Float, nullable=True)
    volume_change_percentage_24h = Column(Float, nullable=True)
    
    # Exchange volume breakdown
    volume_by_exchange = Column(JSON, nullable=True, default=dict)
    
    # Trading pairs
    top_trading_pairs = Column(JSON, nullable=True, default=list)
    
    # Volume analysis
    is_volume_spike = Column(Boolean, nullable=False, default=False)
    volume_spike_multiplier = Column(Float, nullable=True)
    avg_volume_7d = Column(Float, nullable=True)
    avg_volume_30d = Column(Float, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_volume_token_timestamp', 'token_address', 'timestamp'),
        Index('idx_volume_timestamp', 'timestamp'),
        Index('idx_volume_spike', 'is_volume_spike'),
    )


