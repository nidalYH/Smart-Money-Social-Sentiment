"""
Whale wallet and transaction models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class WhaleWallet(Base):
    """Model for tracking whale wallets"""
    __tablename__ = "whale_wallets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    address = Column(String(42), unique=True, nullable=False, index=True)
    label = Column(String(255), nullable=True)
    balance_eth = Column(Float, nullable=False, default=0.0)
    balance_usd = Column(Float, nullable=False, default=0.0)
    
    # Wallet metrics
    success_rate = Column(Float, nullable=False, default=0.0)  # Historical performance
    total_profit_loss = Column(Float, nullable=False, default=0.0)
    avg_hold_time = Column(Integer, nullable=False, default=0)  # In days
    
    # Classification
    wallet_type = Column(String(50), nullable=False, default="unknown")  # exchange, individual, fund, etc.
    is_exchange = Column(Boolean, nullable=False, default=False)
    is_contract = Column(Boolean, nullable=False, default=False)
    risk_score = Column(Float, nullable=False, default=0.0)  # 0-1, higher = more reliable
    
    # Metadata
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_activity = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    total_value_usd = Column(Float, nullable=False, default=0.0)
    
    # Relationships - Comentadas temporalmente para evitar errores de FK
    # transactions = relationship("WhaleTransaction", back_populates="whale_wallet")
    # portfolios = relationship("WhalePortfolio", back_populates="whale_wallet")
    
    # Indexes
    __table_args__ = (
        Index('idx_whale_wallet_balance', 'balance_eth'),
        Index('idx_whale_wallet_success_rate', 'success_rate'),
        Index('idx_whale_wallet_active', 'is_active'),
        Index('idx_whale_wallet_type', 'wallet_type'),
    )


class WhaleTransaction(Base):
    """Model for individual whale transactions"""
    __tablename__ = "whale_transactions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    whale_wallet_id = Column(String(36), nullable=False, index=True)
    
    # Transaction details
    tx_hash = Column(String(66), unique=True, nullable=False, index=True)
    block_number = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Token information
    token_address = Column(String(42), nullable=False, index=True)
    token_symbol = Column(String(20), nullable=False)
    token_name = Column(String(100), nullable=False)
    
    # Transaction type and amounts
    transaction_type = Column(String(20), nullable=False)  # buy, sell, transfer
    amount = Column(Float, nullable=False)
    amount_usd = Column(Float, nullable=False)
    price_per_token = Column(Float, nullable=False)
    
    # Gas and fees
    gas_price_gwei = Column(Float, nullable=False)
    gas_used = Column(Integer, nullable=False)
    gas_cost_eth = Column(Float, nullable=False)
    gas_cost_usd = Column(Float, nullable=False)
    
    # Market context
    token_price_at_tx = Column(Float, nullable=False)
    token_market_cap = Column(Float, nullable=True)
    token_volume_24h = Column(Float, nullable=True)
    
    # Analysis
    is_large_transaction = Column(Boolean, nullable=False, default=False)
    urgency_score = Column(Float, nullable=False, default=0.0)  # Based on gas price
    impact_score = Column(Float, nullable=False, default=0.0)  # Market impact potential
    
    # Relationships - Comentadas para evitar errores de FK
    # whale_wallet = relationship("WhaleWallet", back_populates="transactions")
    
    # Indexes
    __table_args__ = (
        Index('idx_whale_tx_timestamp', 'timestamp'),
        Index('idx_whale_tx_token', 'token_address'),
        Index('idx_whale_tx_type', 'transaction_type'),
        Index('idx_whale_tx_large', 'is_large_transaction'),
        Index('idx_whale_tx_wallet_timestamp', 'whale_wallet_id', 'timestamp'),
    )


class WhalePortfolio(Base):
    """Model for whale portfolio snapshots"""
    __tablename__ = "whale_portfolios"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    whale_wallet_id = Column(String(36), nullable=False, index=True)
    
    # Snapshot metadata
    snapshot_timestamp = Column(DateTime, nullable=False, index=True)
    total_value_usd = Column(Float, nullable=False)
    
    # Portfolio composition (stored as JSON)
    holdings = Column(JSON, nullable=False, default=dict)
    
    # Portfolio metrics
    diversification_score = Column(Float, nullable=False, default=0.0)
    concentration_risk = Column(Float, nullable=False, default=0.0)
    portfolio_beta = Column(Float, nullable=False, default=1.0)
    
    # Changes since last snapshot
    value_change_24h = Column(Float, nullable=False, default=0.0)
    value_change_percent_24h = Column(Float, nullable=False, default=0.0)
    new_positions = Column(JSON, nullable=True, default=list)
    closed_positions = Column(JSON, nullable=True, default=list)
    
    # Relationships
    whale_wallet = relationship("WhaleWallet", back_populates="portfolios")
    
    # Indexes
    __table_args__ = (
        Index('idx_portfolio_timestamp', 'snapshot_timestamp'),
        Index('idx_portfolio_wallet_timestamp', 'whale_wallet_id', 'snapshot_timestamp'),
        Index('idx_portfolio_value', 'total_value_usd'),
    )


