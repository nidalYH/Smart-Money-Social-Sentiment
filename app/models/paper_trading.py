"""
Paper trading models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy import JSON
import uuid

from app.database import Base


class PaperPortfolio(Base):
    """Model for paper trading portfolio"""
    __tablename__ = "paper_portfolios"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Portfolio details
    name = Column(String(100), nullable=False)
    initial_balance = Column(Float, nullable=False, default=100000.0)
    current_balance = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    
    # Performance metrics
    total_return = Column(Float, default=0.0)
    total_return_pct = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    
    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    
    # Statistics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    positions = relationship("PaperPosition", back_populates="portfolio", cascade="all, delete-orphan")
    trades = relationship("PaperTrade", back_populates="portfolio", cascade="all, delete-orphan")
    performance_records = relationship("PaperPerformance", back_populates="portfolio", cascade="all, delete-orphan")


class PaperPosition(Base):
    """Model for paper trading positions"""
    __tablename__ = "paper_positions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String(36), ForeignKey("paper_portfolios.id"), nullable=False)
    
    # Position details
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    
    # Position management
    side = Column(String(10), nullable=False)  # LONG, SHORT
    status = Column(String(20), default="OPEN")  # OPEN, CLOSED
    
    # Risk management
    stop_loss = Column(Float)
    take_profit = Column(Float)
    
    # P&L
    unrealized_pnl = Column(Float, default=0.0)
    unrealized_pnl_pct = Column(Float, default=0.0)
    
    # Timestamps
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("PaperPortfolio", back_populates="positions")
    entry_trade = relationship("PaperTrade", foreign_keys="PaperTrade.position_id", back_populates="position", cascade="all, delete-orphan")


class PaperTrade(Base):
    """Model for paper trading transactions"""
    __tablename__ = "paper_trades"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String(36), ForeignKey("paper_portfolios.id"), nullable=False)
    position_id = Column(String(36), ForeignKey("paper_positions.id"))
    
    # Trade details
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    
    # Trade type
    trade_type = Column(String(20), default="MARKET")  # MARKET, LIMIT, STOP
    order_id = Column(String(50))
    
    # Fees and costs
    commission = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)
    
    # P&L (for closing trades)
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    
    # Signal information
    signal_id = Column(String(36))
    signal_confidence = Column(Float)
    signal_reasoning = Column(Text)
    
    # Execution details
    execution_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="FILLED")  # PENDING, FILLED, CANCELLED
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("PaperPortfolio", back_populates="trades")
    position = relationship("PaperPosition", foreign_keys=[position_id], back_populates="entry_trade")


class PaperPerformance(Base):
    """Model for paper trading performance tracking"""
    __tablename__ = "paper_performance"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String(36), ForeignKey("paper_portfolios.id"), nullable=False)
    
    # Performance snapshot
    date = Column(DateTime, default=datetime.utcnow)
    portfolio_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    positions_value = Column(Float, nullable=False)
    
    # Returns
    daily_return = Column(Float, default=0.0)
    daily_return_pct = Column(Float, default=0.0)
    total_return = Column(Float, default=0.0)
    total_return_pct = Column(Float, default=0.0)
    
    # Risk metrics
    volatility = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    
    # Trade metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    # Average metrics
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    avg_win_pct = Column(Float, default=0.0)
    avg_loss_pct = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    
    # Additional metrics
    best_trade = Column(Float, default=0.0)
    worst_trade = Column(Float, default=0.0)
    consecutive_wins = Column(Integer, default=0)
    consecutive_losses = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("PaperPortfolio", back_populates="performance_records")


# Indexes for better performance
from sqlalchemy import Index

Index('idx_paper_positions_portfolio_symbol', PaperPosition.portfolio_id, PaperPosition.symbol)
Index('idx_paper_trades_portfolio_date', PaperTrade.portfolio_id, PaperTrade.execution_time)
Index('idx_paper_performance_portfolio_date', PaperPerformance.portfolio_id, PaperPerformance.date)
