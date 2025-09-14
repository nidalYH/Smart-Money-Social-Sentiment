"""
Paper trading system with backtesting capabilities
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.paper_trading import PaperTrade, PaperPortfolio, PaperPosition, PaperPerformance
from app.models.signal import TradingSignal
from app.models.token import Token, TokenPrice
from app.core.data_manager import DataManager

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    """Trade status enumeration"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


@dataclass
class TradeRequest:
    """Trade request data"""
    token_symbol: str
    token_address: str
    action: str  # buy/sell
    amount: float
    order_type: OrderType
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    signal_id: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class TradeResult:
    """Trade execution result"""
    trade_id: str
    status: TradeStatus
    filled_price: Optional[float]
    filled_amount: Optional[float]
    fees: float
    timestamp: datetime
    error_message: Optional[str] = None


@dataclass
class PortfolioSummary:
    """Portfolio summary data"""
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_percent: float
    cash_balance: float
    positions_count: int
    active_trades: int
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float


class PaperTradingEngine:
    """Paper trading engine with backtesting capabilities"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.is_running = False
        self.initial_cash = 100000.0  # $100k starting capital
        self.trading_fee_rate = 0.001  # 0.1% trading fee
        
    async def initialize(self):
        """Initialize paper trading engine"""
        logger.info("Initializing paper trading engine...")
        
        # Create default portfolio if it doesn't exist
        await self._ensure_default_portfolio()
        
        logger.info("Paper trading engine initialized")
    
    async def _ensure_default_portfolio(self):
        """Ensure default portfolio exists"""
        try:
            async with self.data_manager.get_db_session() as session:
                # Check if default portfolio exists
                stmt = select(PaperPortfolio).where(
                    PaperPortfolio.portfolio_name == "default"
                )
                result = await session.execute(stmt)
                portfolio = result.scalar_one_or_none()
                
                if not portfolio:
                    # Create default portfolio
                    portfolio = PaperPortfolio(
                        portfolio_id=str(uuid.uuid4()),
                        portfolio_name="default",
                        user_id=None,  # System portfolio
                        initial_cash=self.initial_cash,
                        current_cash=self.initial_cash,
                        total_value=self.initial_cash,
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    session.add(portfolio)
                    await session.commit()
                    logger.info("Created default paper trading portfolio")
                
        except Exception as e:
            logger.error(f"Error ensuring default portfolio: {e}")
    
    async def execute_trade(self, trade_request: TradeRequest) -> TradeResult:
        """Execute a paper trade"""
        try:
            # Validate trade request
            validation_result = await self._validate_trade_request(trade_request)
            if not validation_result["valid"]:
                return TradeResult(
                    trade_id=str(uuid.uuid4()),
                    status=TradeStatus.REJECTED,
                    filled_price=None,
                    filled_amount=None,
                    fees=0.0,
                    timestamp=datetime.utcnow(),
                    error_message=validation_result["error"]
                )
            
            # Get current token price
            current_price = await self._get_current_token_price(trade_request.token_address)
            if not current_price:
                return TradeResult(
                    trade_id=str(uuid.uuid4()),
                    status=TradeStatus.REJECTED,
                    filled_price=None,
                    filled_amount=None,
                    fees=0.0,
                    timestamp=datetime.utcnow(),
                    error_message="Unable to get current token price"
                )
            
            # Calculate trade values
            if trade_request.order_type == OrderType.MARKET:
                fill_price = current_price
            elif trade_request.order_type == OrderType.LIMIT:
                if trade_request.price is None:
                    return TradeResult(
                        trade_id=str(uuid.uuid4()),
                        status=TradeStatus.REJECTED,
                        filled_price=None,
                        filled_amount=None,
                        fees=0.0,
                        timestamp=datetime.utcnow(),
                        error_message="Limit price required for limit orders"
                    )
                fill_price = trade_request.price
            else:
                fill_price = current_price
            
            # Calculate trade amount in USD
            trade_value_usd = trade_request.amount * fill_price
            fees = trade_value_usd * self.trading_fee_rate
            
            # Check if we have enough cash for buy orders
            if trade_request.action == "buy":
                total_required = trade_value_usd + fees
                portfolio = await self._get_portfolio(trade_request.user_id)
                if portfolio.current_cash < total_required:
                    return TradeResult(
                        trade_id=str(uuid.uuid4()),
                        status=TradeStatus.REJECTED,
                        filled_price=None,
                        filled_amount=None,
                        fees=0.0,
                        timestamp=datetime.utcnow(),
                        error_message=f"Insufficient cash. Required: ${total_required:,.2f}, Available: ${portfolio.current_cash:,.2f}"
                    )
            
            # Check if we have enough tokens for sell orders
            if trade_request.action == "sell":
                current_position = await self._get_position(
                    trade_request.user_id, 
                    trade_request.token_address
                )
                if not current_position or current_position.amount < trade_request.amount:
                    return TradeResult(
                        trade_id=str(uuid.uuid4()),
                        status=TradeStatus.REJECTED,
                        filled_price=None,
                        filled_amount=None,
                        fees=0.0,
                        timestamp=datetime.utcnow(),
                        error_message=f"Insufficient tokens. Required: {trade_request.amount}, Available: {current_position.amount if current_position else 0}"
                    )
            
            # Execute the trade
            trade_result = await self._execute_trade_internal(
                trade_request, fill_price, fees
            )
            
            return trade_result
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return TradeResult(
                trade_id=str(uuid.uuid4()),
                status=TradeStatus.REJECTED,
                filled_price=None,
                filled_amount=None,
                fees=0.0,
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
    
    async def _validate_trade_request(self, trade_request: TradeRequest) -> Dict:
        """Validate trade request"""
        try:
            # Check if token exists
            async with self.data_manager.get_db_session() as session:
                stmt = select(Token).where(Token.address == trade_request.token_address)
                result = await session.execute(stmt)
                token = result.scalar_one_or_none()
                
                if not token:
                    return {"valid": False, "error": "Token not found"}
            
            # Validate amount
            if trade_request.amount <= 0:
                return {"valid": False, "error": "Amount must be positive"}
            
            # Validate action
            if trade_request.action not in ["buy", "sell"]:
                return {"valid": False, "error": "Action must be 'buy' or 'sell'"}
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def _get_current_token_price(self, token_address: str) -> Optional[float]:
        """Get current token price"""
        try:
            async with self.data_manager.get_db_session() as session:
                # Get latest price from database
                stmt = select(TokenPrice).where(
                    TokenPrice.token_address == token_address
                ).order_by(desc(TokenPrice.timestamp)).limit(1)
                
                result = await session.execute(stmt)
                price_data = result.scalar_one_or_none()
                
                if price_data:
                    return price_data.price_usd
                
                # Fallback to token current price
                stmt = select(Token.current_price).where(Token.address == token_address)
                result = await session.execute(stmt)
                current_price = result.scalar_one_or_none()
                
                return current_price
                
        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            return None
    
    async def _execute_trade_internal(self, trade_request: TradeRequest, 
                                     fill_price: float, fees: float) -> TradeResult:
        """Execute trade internally"""
        try:
            trade_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            # Calculate trade values
            trade_value_usd = trade_request.amount * fill_price
            
            # Create trade record
            trade = PaperTrade(
                trade_id=trade_id,
                portfolio_id=await self._get_portfolio_id(trade_request.user_id),
                token_address=trade_request.token_address,
                token_symbol=trade_request.token_symbol,
                action=trade_request.action,
                amount=trade_request.amount,
                price=fill_price,
                value_usd=trade_value_usd,
                fees=fees,
                order_type=trade_request.order_type.value,
                status=TradeStatus.FILLED.value,
                signal_id=trade_request.signal_id,
                executed_at=timestamp,
                stop_loss=trade_request.stop_loss,
                take_profit=trade_request.take_profit
            )
            
            # Update portfolio and positions
            await self._update_portfolio_and_positions(trade)
            
            # Store trade
            async with self.data_manager.get_db_session() as session:
                session.add(trade)
                await session.commit()
            
            logger.info(f"Executed {trade_request.action} trade: {trade_request.amount} {trade_request.token_symbol} at ${fill_price:.2f}")
            
            return TradeResult(
                trade_id=trade_id,
                status=TradeStatus.FILLED,
                filled_price=fill_price,
                filled_amount=trade_request.amount,
                fees=fees,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"Error executing trade internally: {e}")
            return TradeResult(
                trade_id=str(uuid.uuid4()),
                status=TradeStatus.REJECTED,
                filled_price=None,
                filled_amount=None,
                fees=0.0,
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
    
    async def _update_portfolio_and_positions(self, trade: PaperTrade):
        """Update portfolio and positions after trade"""
        try:
            async with self.data_manager.get_db_session() as session:
                # Get portfolio
                stmt = select(PaperPortfolio).where(
                    PaperPortfolio.portfolio_id == trade.portfolio_id
                )
                result = await session.execute(stmt)
                portfolio = result.scalar_one_or_none()
                
                if not portfolio:
                    raise Exception("Portfolio not found")
                
                # Update cash balance
                if trade.action == "buy":
                    portfolio.current_cash -= (trade.value_usd + trade.fees)
                else:  # sell
                    portfolio.current_cash += (trade.value_usd - trade.fees)
                
                # Update or create position
                position_stmt = select(PaperPosition).where(
                    and_(
                        PaperPosition.portfolio_id == trade.portfolio_id,
                        PaperPosition.token_address == trade.token_address
                    )
                )
                position_result = await session.execute(position_stmt)
                position = position_result.scalar_one_or_none()
                
                if not position:
                    # Create new position
                    position = PaperPosition(
                        position_id=str(uuid.uuid4()),
                        portfolio_id=trade.portfolio_id,
                        token_address=trade.token_address,
                        token_symbol=trade.token_symbol,
                        amount=0.0,
                        avg_cost=0.0,
                        total_cost=0.0,
                        current_value=0.0,
                        unrealized_pnl=0.0,
                        unrealized_pnl_percent=0.0,
                        created_at=datetime.utcnow()
                    )
                    session.add(position)
                
                # Update position
                if trade.action == "buy":
                    # Add to position
                    new_total_cost = position.total_cost + trade.value_usd + trade.fees
                    new_amount = position.amount + trade.amount
                    position.amount = new_amount
                    position.total_cost = new_total_cost
                    position.avg_cost = new_total_cost / new_amount if new_amount > 0 else 0
                else:  # sell
                    # Remove from position
                    position.amount -= trade.amount
                    if position.amount <= 0:
                        position.amount = 0
                        position.avg_cost = 0
                        position.total_cost = 0
                    else:
                        # Recalculate average cost
                        position.total_cost = position.avg_cost * position.amount
                
                # Update position current value
                current_price = await self._get_current_token_price(trade.token_address)
                if current_price:
                    position.current_value = position.amount * current_price
                    position.unrealized_pnl = position.current_value - position.total_cost
                    position.unrealized_pnl_percent = (position.unrealized_pnl / position.total_cost * 100) if position.total_cost > 0 else 0
                
                # Update portfolio total value
                await self._update_portfolio_total_value(portfolio)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating portfolio and positions: {e}")
            raise
    
    async def _update_portfolio_total_value(self, portfolio: PaperPortfolio):
        """Update portfolio total value"""
        try:
            async with self.data_manager.get_db_session() as session:
                # Get all positions for this portfolio
                stmt = select(PaperPosition).where(
                    PaperPosition.portfolio_id == portfolio.portfolio_id
                )
                result = await session.execute(stmt)
                positions = result.scalars().all()
                
                # Calculate total value
                total_positions_value = sum(pos.current_value for pos in positions)
                portfolio.total_value = portfolio.current_cash + total_positions_value
                
                # Update portfolio
                session.add(portfolio)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating portfolio total value: {e}")
    
    async def _get_portfolio(self, user_id: Optional[str]) -> PaperPortfolio:
        """Get portfolio for user"""
        try:
            async with self.data_manager.get_db_session() as session:
                if user_id:
                    stmt = select(PaperPortfolio).where(
                        and_(
                            PaperPortfolio.user_id == user_id,
                            PaperPortfolio.is_active == True
                        )
                    )
                else:
                    stmt = select(PaperPortfolio).where(
                        and_(
                            PaperPortfolio.portfolio_name == "default",
                            PaperPortfolio.is_active == True
                        )
                    )
                
                result = await session.execute(stmt)
                portfolio = result.scalar_one_or_none()
                
                if not portfolio:
                    # Create portfolio if it doesn't exist
                    portfolio = PaperPortfolio(
                        portfolio_id=str(uuid.uuid4()),
                        portfolio_name="default" if not user_id else f"user_{user_id}",
                        user_id=user_id,
                        initial_cash=self.initial_cash,
                        current_cash=self.initial_cash,
                        total_value=self.initial_cash,
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    session.add(portfolio)
                    await session.commit()
                
                return portfolio
                
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            raise
    
    async def _get_portfolio_id(self, user_id: Optional[str]) -> str:
        """Get portfolio ID for user"""
        portfolio = await self._get_portfolio(user_id)
        return portfolio.portfolio_id
    
    async def _get_position(self, user_id: Optional[str], token_address: str) -> Optional[PaperPosition]:
        """Get position for user and token"""
        try:
            portfolio_id = await self._get_portfolio_id(user_id)
            
            async with self.data_manager.get_db_session() as session:
                stmt = select(PaperPosition).where(
                    and_(
                        PaperPosition.portfolio_id == portfolio_id,
                        PaperPosition.token_address == token_address
                    )
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
                
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None
    
    async def get_portfolio_summary(self, user_id: Optional[str] = None) -> PortfolioSummary:
        """Get portfolio summary"""
        try:
            portfolio = await self._get_portfolio(user_id)
            
            # Get all positions
            async with self.data_manager.get_db_session() as session:
                stmt = select(PaperPosition).where(
                    PaperPosition.portfolio_id == portfolio.portfolio_id
                )
                result = await session.execute(stmt)
                positions = result.scalars().all()
                
                # Calculate summary
                total_positions_value = sum(pos.current_value for pos in positions)
                total_cost = sum(pos.total_cost for pos in positions)
                total_pnl = total_positions_value - total_cost
                total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0
                
                # Get daily/weekly/monthly PnL
                daily_pnl = await self._calculate_period_pnl(portfolio.portfolio_id, 1)
                weekly_pnl = await self._calculate_period_pnl(portfolio.portfolio_id, 7)
                monthly_pnl = await self._calculate_period_pnl(portfolio.portfolio_id, 30)
                
                # Count active trades
                active_trades = await self._count_active_trades(portfolio.portfolio_id)
                
                return PortfolioSummary(
                    total_value=portfolio.total_value,
                    total_cost=portfolio.initial_cash,
                    total_pnl=total_pnl,
                    total_pnl_percent=total_pnl_percent,
                    cash_balance=portfolio.current_cash,
                    positions_count=len(positions),
                    active_trades=active_trades,
                    daily_pnl=daily_pnl,
                    weekly_pnl=weekly_pnl,
                    monthly_pnl=monthly_pnl
                )
                
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return PortfolioSummary(
                total_value=0.0,
                total_cost=0.0,
                total_pnl=0.0,
                total_pnl_percent=0.0,
                cash_balance=0.0,
                positions_count=0,
                active_trades=0,
                daily_pnl=0.0,
                weekly_pnl=0.0,
                monthly_pnl=0.0
            )
    
    async def _calculate_period_pnl(self, portfolio_id: str, days: int) -> float:
        """Calculate PnL for a specific period"""
        try:
            async with self.data_manager.get_db_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(days=days)
                
                # Get trades in period
                stmt = select(PaperTrade).where(
                    and_(
                        PaperTrade.portfolio_id == portfolio_id,
                        PaperTrade.executed_at >= cutoff_time
                    )
                )
                result = await session.execute(stmt)
                trades = result.scalars().all()
                
                # Calculate PnL from trades
                pnl = 0.0
                for trade in trades:
                    if trade.action == "sell":
                        # Calculate profit/loss for sell trades
                        # This is a simplified calculation
                        pnl += trade.value_usd - trade.fees
                    else:
                        pnl -= (trade.value_usd + trade.fees)
                
                return pnl
                
        except Exception as e:
            logger.error(f"Error calculating period PnL: {e}")
            return 0.0
    
    async def _count_active_trades(self, portfolio_id: str) -> int:
        """Count active trades"""
        try:
            async with self.data_manager.get_db_session() as session:
                stmt = select(func.count(PaperTrade.trade_id)).where(
                    and_(
                        PaperTrade.portfolio_id == portfolio_id,
                        PaperTrade.status == TradeStatus.FILLED.value
                    )
                )
                result = await session.execute(stmt)
                return result.scalar() or 0
                
        except Exception as e:
            logger.error(f"Error counting active trades: {e}")
            return 0
    
    async def get_trade_history(self, user_id: Optional[str] = None, 
                               limit: int = 100) -> List[Dict]:
        """Get trade history"""
        try:
            portfolio_id = await self._get_portfolio_id(user_id)
            
            async with self.data_manager.get_db_session() as session:
                stmt = select(PaperTrade).where(
                    PaperTrade.portfolio_id == portfolio_id
                ).order_by(desc(PaperTrade.executed_at)).limit(limit)
                
                result = await session.execute(stmt)
                trades = result.scalars().all()
                
                return [
                    {
                        "trade_id": trade.trade_id,
                        "token_symbol": trade.token_symbol,
                        "action": trade.action,
                        "amount": trade.amount,
                        "price": trade.price,
                        "value_usd": trade.value_usd,
                        "fees": trade.fees,
                        "status": trade.status,
                        "executed_at": trade.executed_at.isoformat(),
                        "signal_id": trade.signal_id
                    }
                    for trade in trades
                ]
                
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
    
    async def get_positions(self, user_id: Optional[str] = None) -> List[Dict]:
        """Get current positions"""
        try:
            portfolio_id = await self._get_portfolio_id(user_id)
            
            async with self.data_manager.get_db_session() as session:
                stmt = select(PaperPosition).where(
                    and_(
                        PaperPosition.portfolio_id == portfolio_id,
                        PaperPosition.amount > 0
                    )
                )
                
                result = await session.execute(stmt)
                positions = result.scalars().all()
                
                return [
                    {
                        "token_symbol": pos.token_symbol,
                        "amount": pos.amount,
                        "avg_cost": pos.avg_cost,
                        "current_value": pos.current_value,
                        "unrealized_pnl": pos.unrealized_pnl,
                        "unrealized_pnl_percent": pos.unrealized_pnl_percent
                    }
                    for pos in positions
                ]
                
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def execute_signal_trades(self, signal: TradingSignal) -> List[TradeResult]:
        """Execute trades based on trading signals"""
        try:
            trade_results = []
            
            # Create trade request from signal
            trade_request = TradeRequest(
                token_symbol=signal.token_symbol,
                token_address=signal.token_address,
                action=signal.action,
                amount=self._calculate_trade_amount(signal),
                order_type=OrderType.MARKET,
                signal_id=signal.signal_id
            )
            
            # Execute trade
            trade_result = await self.execute_trade(trade_request)
            trade_results.append(trade_result)
            
            # Set stop loss and take profit if specified
            if signal.stop_loss_price and trade_result.status == TradeStatus.FILLED:
                stop_loss_request = TradeRequest(
                    token_symbol=signal.token_symbol,
                    token_address=signal.token_address,
                    action="sell",
                    amount=trade_request.amount,
                    order_type=OrderType.STOP_LOSS,
                    price=signal.stop_loss_price,
                    signal_id=signal.signal_id
                )
                # Note: Stop loss would be implemented as a separate order type
                # For now, we'll just log it
                logger.info(f"Stop loss set at ${signal.stop_loss_price:.2f} for {signal.token_symbol}")
            
            return trade_results
            
        except Exception as e:
            logger.error(f"Error executing signal trades: {e}")
            return []
    
    def _calculate_trade_amount(self, signal: TradingSignal) -> float:
        """Calculate trade amount based on signal and portfolio size"""
        # Simple position sizing: 5% of portfolio per trade
        portfolio_value = 100000.0  # This would be fetched from portfolio
        position_size_percent = 0.05
        trade_value = portfolio_value * position_size_percent
        return trade_value / signal.current_price
    
    async def start_auto_trading(self):
        """Start automatic trading based on signals"""
        logger.info("Starting auto trading...")
        self.is_running = True
        
        while self.is_running:
            try:
                # Get recent high-confidence signals
                async with self.data_manager.get_db_session() as session:
                    cutoff_time = datetime.utcnow() - timedelta(hours=1)
                    stmt = select(TradingSignal).where(
                        and_(
                            TradingSignal.timestamp >= cutoff_time,
                            TradingSignal.confidence_score >= 0.8,
                            TradingSignal.is_active == True
                        )
                    ).order_by(desc(TradingSignal.confidence_score))
                    
                    result = await session.execute(stmt)
                    signals = result.scalars().all()
                
                # Execute trades for signals
                for signal in signals:
                    try:
                        trade_results = await self.execute_signal_trades(signal)
                        logger.info(f"Executed {len(trade_results)} trades for signal {signal.signal_id}")
                    except Exception as e:
                        logger.error(f"Error executing trades for signal {signal.signal_id}: {e}")
                
                # Wait before next iteration
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in auto trading: {e}")
                await asyncio.sleep(60)
    
    async def stop_auto_trading(self):
        """Stop automatic trading"""
        logger.info("Stopping auto trading...")
        self.is_running = False
    
    async def start_monitoring(self):
        """Start monitoring for trading opportunities"""
        logger.info("Starting paper trading monitoring...")
        self.is_running = True
        
        while self.is_running:
            try:
                # Monitor existing positions for exit conditions
                await self._monitor_positions()
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_positions(self):
        """Monitor existing positions for stop loss/take profit"""
        try:
            async with self.data_manager.get_db_session() as session:
                # Get active positions
                stmt = select(PaperPosition).where(
                    and_(
                        PaperPosition.is_active == True,
                        PaperPosition.status == "open"
                    )
                )
                result = await session.execute(stmt)
                positions = result.scalars().all()
                
                for position in positions:
                    # Check if position should be closed
                    current_price = await self._get_current_price(position.token_symbol)
                    
                    if current_price:
                        # Check stop loss
                        if position.stop_loss_price and current_price <= position.stop_loss_price:
                            await self._close_position(position, "stop_loss", current_price)
                        
                        # Check take profit
                        elif position.take_profit_price and current_price >= position.take_profit_price:
                            await self._close_position(position, "take_profit", current_price)
                            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a token symbol"""
        try:
            async with self.data_manager.get_db_session() as session:
                stmt = select(TokenPrice).where(
                    TokenPrice.token_symbol == symbol
                ).order_by(desc(TokenPrice.timestamp)).limit(1)
                
                result = await session.execute(stmt)
                price_data = result.scalar_one_or_none()
                
                return price_data.price if price_data else None
                
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    async def _close_position(self, position: PaperPosition, reason: str, current_price: float):
        """Close a position"""
        try:
            async with self.data_manager.get_db_session() as session:
                # Create closing trade
                closing_trade = PaperTrade(
                    trade_id=str(uuid.uuid4()),
                    portfolio_id=position.portfolio_id,
                    token_symbol=position.token_symbol,
                    token_address=position.token_address,
                    trade_type="sell",
                    quantity=position.quantity,
                    price=current_price,
                    total_value=position.quantity * current_price,
                    status="filled",
                    timestamp=datetime.utcnow(),
                    signal_id=position.signal_id,
                    notes=f"Closed due to {reason}"
                )
                
                session.add(closing_trade)
                
                # Update position
                position.is_active = False
                position.status = "closed"
                position.closed_at = datetime.utcnow()
                position.closing_price = current_price
                position.closing_reason = reason
                
                await session.commit()
                
                logger.info(f"Closed position {position.position_id} due to {reason} at ${current_price:.2f}")
                
        except Exception as e:
            logger.error(f"Error closing position: {e}")
