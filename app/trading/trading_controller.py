"""
Main trading controller with automatic execution capabilities
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import json

from app.core.signal_engine import SignalEngine
from app.core.paper_trading import PaperTradingEngine, TradeRequest, OrderType
from app.core.alert_manager import AlertManager
from app.core.whale_tracker import WhaleTracker
from app.core.sentiment_analyzer import SentimentAnalyzer
from app.core.data_manager import DataManager
from app.models.signal import TradingSignal

logger = logging.getLogger(__name__)


@dataclass
class TradingConfig:
    """Trading configuration"""
    auto_trading_enabled: bool = False
    min_confidence_threshold: float = 0.7
    max_position_size_percent: float = 0.05  # 5% of portfolio per trade
    stop_loss_percent: float = 0.05  # 5% stop loss
    take_profit_multiplier: float = 2.0  # 2:1 risk/reward ratio
    max_daily_trades: int = 10
    trading_hours_start: int = 9  # 9 AM
    trading_hours_end: int = 21   # 9 PM


class TradingController:
    """Main trading controller with automatic execution"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.config = TradingConfig()
        
        # Initialize components
        self.signal_engine = SignalEngine(data_manager)
        self.paper_trading = PaperTradingEngine(data_manager)
        self.alert_manager = AlertManager(data_manager)
        self.whale_tracker = WhaleTracker(data_manager)
        self.sentiment_analyzer = SentimentAnalyzer(data_manager)
        
        # Trading state
        self.is_running = False
        self.daily_trade_count = 0
        self.last_trade_date = None
        self.active_positions = {}
        self.trade_history = []
        
        # Performance tracking
        self.performance_metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0
        }
    
    async def initialize(self):
        """Initialize all trading components"""
        logger.info("Initializing trading controller...")
        
        try:
            # Initialize all components
            await self.signal_engine.initialize()
            await self.paper_trading.initialize()
            await self.alert_manager.initialize()
            await self.whale_tracker.initialize()
            await self.sentiment_analyzer.initialize()
            
            # Load existing positions
            await self._load_active_positions()
            
            logger.info("Trading controller initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing trading controller: {e}")
            raise
    
    async def start_live_trading(self):
        """Start the live trading loop"""
        logger.info("🚀 Starting live trading system...")
        self.is_running = True
        
        try:
            while self.is_running:
                try:
                    # Check if trading hours
                    if not self._is_trading_hours():
                        await asyncio.sleep(300)  # Wait 5 minutes
                        continue
                    
                    # Reset daily trade count if new day
                    await self._reset_daily_count_if_needed()
                    
                    # Check if we've hit daily trade limit
                    if self.daily_trade_count >= self.config.max_daily_trades:
                        logger.info(f"Daily trade limit reached ({self.config.max_daily_trades})")
                        await asyncio.sleep(3600)  # Wait 1 hour
                        continue
                    
                    # 1. Generate new signals
                    signals = await self.signal_engine.generate_signals(hours_back=2)
                    
                    # 2. Process each signal
                    for signal in signals:
                        if signal.confidence >= self.config.min_confidence_threshold:
                            await self._process_signal(signal)
                    
                    # 3. Check existing positions for exits
                    await self._check_exit_conditions()
                    
                    # 4. Update performance metrics
                    await self._update_performance_metrics()
                    
                    # 5. Wait before next scan
                    await asyncio.sleep(60)  # Scan every minute
                    
                except Exception as e:
                    logger.error(f"Error in trading loop: {e}")
                    await asyncio.sleep(30)
                    
        except Exception as e:
            logger.error(f"Fatal error in live trading: {e}")
        finally:
            self.is_running = False
            logger.info("Live trading stopped")
    
    async def stop_live_trading(self):
        """Stop the live trading loop"""
        logger.info("Stopping live trading...")
        self.is_running = False
    
    async def _process_signal(self, signal: TradingSignal):
        """Process a trading signal"""
        try:
            logger.info(f"Processing signal: {signal.signal_type} for {signal.token_symbol} "
                       f"(confidence: {signal.confidence:.2f})")
            
            # Send alert
            await self._send_signal_alert(signal)
            
            # Auto-execute if enabled
            if self.config.auto_trading_enabled:
                await self._execute_signal(signal)
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    async def _execute_signal(self, signal: TradingSignal):
        """Execute a trading signal"""
        try:
            # Calculate position size
            position_size = await self._calculate_position_size(signal)
            
            if position_size <= 0:
                logger.warning(f"Position size too small for {signal.token_symbol}")
                return
            
            # Create trade request
            trade_request = TradeRequest(
                token_symbol=signal.token_symbol,
                token_address=signal.token_address,
                action=signal.action.value,
                amount=position_size,
                order_type=OrderType.MARKET,
                signal_id=signal.signal_id,
                stop_loss=signal.stop_loss_price,
                take_profit=signal.target_price
            )
            
            # Execute trade
            trade_result = await self.paper_trading.execute_trade(trade_request)
            
            if trade_result.status.value == "filled":
                # Update tracking
                self.daily_trade_count += 1
                self.trade_history.append({
                    "signal": signal,
                    "trade_result": trade_result,
                    "timestamp": datetime.utcnow()
                })
                
                # Send execution alert
                await self._send_execution_alert(signal, trade_result)
                
                # Track position
                self.active_positions[signal.token_address] = {
                    "signal": signal,
                    "trade_result": trade_result,
                    "entry_time": datetime.utcnow(),
                    "stop_loss": signal.stop_loss_price,
                    "take_profit": signal.target_price
                }
                
                logger.info(f"✅ Trade executed: {signal.action.value} {signal.token_symbol} "
                           f"at ${trade_result.filled_price:.4f}")
            else:
                logger.warning(f"❌ Trade failed: {trade_result.error_message}")
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    async def _calculate_position_size(self, signal: TradingSignal) -> float:
        """Calculate position size based on signal confidence and risk management"""
        try:
            # Get current portfolio value
            portfolio_summary = await self.paper_trading.get_portfolio_summary()
            portfolio_value = portfolio_summary.total_value
            
            # Calculate risk amount based on confidence
            base_risk = self.config.max_position_size_percent * portfolio_value
            confidence_multiplier = 0.5 + (signal.confidence * 0.5)  # 0.5x to 1.0x
            risk_amount = base_risk * confidence_multiplier
            
            # Calculate position size
            position_size = risk_amount / signal.current_price
            
            # Apply minimum and maximum limits
            min_position = 10.0  # Minimum $10 position
            max_position = portfolio_value * 0.1  # Maximum 10% of portfolio
            
            position_size = max(min_position, min(position_size, max_position))
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    async def _check_exit_conditions(self):
        """Check if any positions should be closed"""
        try:
            for token_address, position in list(self.active_positions.items()):
                # Get current price
                current_price = await self._get_current_token_price(token_address)
                if not current_price:
                    continue
                
                signal = position["signal"]
                stop_loss = position["stop_loss"]
                take_profit = position["take_profit"]
                
                # Check stop loss
                if current_price <= stop_loss:
                    await self._close_position(token_address, "STOP_LOSS", current_price)
                
                # Check take profit
                elif current_price >= take_profit:
                    await self._close_position(token_address, "TAKE_PROFIT", current_price)
                
                # Check time-based exit (24 hours max)
                elif (datetime.utcnow() - position["entry_time"]).total_seconds() > 86400:
                    await self._close_position(token_address, "TIME_EXIT", current_price)
                    
        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
    
    async def _close_position(self, token_address: str, reason: str, current_price: float):
        """Close a position"""
        try:
            if token_address not in self.active_positions:
                return
            
            position = self.active_positions[token_address]
            signal = position["signal"]
            
            # Create sell trade request
            trade_request = TradeRequest(
                token_symbol=signal.token_symbol,
                token_address=token_address,
                action="sell",
                amount=position["trade_result"].filled_amount,
                order_type=OrderType.MARKET
            )
            
            # Execute sell trade
            trade_result = await self.paper_trading.execute_trade(trade_request)
            
            if trade_result.status.value == "filled":
                # Calculate P&L
                entry_price = position["trade_result"].filled_price
                pnl = (current_price - entry_price) * trade_result.filled_amount
                pnl_percent = (current_price - entry_price) / entry_price * 100
                
                # Update performance metrics
                self.performance_metrics["total_trades"] += 1
                self.performance_metrics["total_pnl"] += pnl
                
                if pnl > 0:
                    self.performance_metrics["winning_trades"] += 1
                else:
                    self.performance_metrics["losing_trades"] += 1
                
                # Send exit alert
                await self._send_exit_alert(signal, trade_result, reason, pnl, pnl_percent)
                
                # Remove from active positions
                del self.active_positions[token_address]
                
                logger.info(f"Position closed: {signal.token_symbol} - {reason} "
                           f"(P&L: ${pnl:.2f}, {pnl_percent:.2f}%)")
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    async def _get_current_token_price(self, token_address: str) -> Optional[float]:
        """Get current token price"""
        try:
            # This would normally fetch from a price API
            # For now, return a mock price
            return 2000.0  # Mock price
        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            return None
    
    async def _send_signal_alert(self, signal: TradingSignal):
        """Send signal alert"""
        try:
            signal_data = {
                "signal_type": signal.signal_type.value,
                "token_symbol": signal.token_symbol,
                "action": signal.action.value,
                "confidence": signal.confidence,
                "current_price": signal.current_price,
                "target_price": signal.target_price,
                "stop_loss": signal.stop_loss_price,
                "reasoning": signal.reasoning,
                "timestamp": signal.timestamp.isoformat()
            }
            
            await self.alert_manager.send_signal_alert(signal_data)
            
        except Exception as e:
            logger.error(f"Error sending signal alert: {e}")
    
    async def _send_execution_alert(self, signal: TradingSignal, trade_result):
        """Send trade execution alert"""
        try:
            execution_data = {
                "signal_type": signal.signal_type.value,
                "token_symbol": signal.token_symbol,
                "action": signal.action.value,
                "amount": trade_result.filled_amount,
                "price": trade_result.filled_price,
                "fees": trade_result.fees,
                "timestamp": trade_result.timestamp.isoformat()
            }
            
            await self.alert_manager.send_trading_signal_alert(execution_data)
            
        except Exception as e:
            logger.error(f"Error sending execution alert: {e}")
    
    async def _send_exit_alert(self, signal: TradingSignal, trade_result, reason: str, 
                              pnl: float, pnl_percent: float):
        """Send position exit alert"""
        try:
            exit_data = {
                "signal_type": signal.signal_type.value,
                "token_symbol": signal.token_symbol,
                "exit_reason": reason,
                "exit_price": trade_result.filled_price,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "timestamp": trade_result.timestamp.isoformat()
            }
            
            await self.alert_manager.send_trading_signal_alert(exit_data)
            
        except Exception as e:
            logger.error(f"Error sending exit alert: {e}")
    
    async def _load_active_positions(self):
        """Load active positions from database"""
        try:
            # This would load from database
            # For now, start with empty positions
            self.active_positions = {}
            
        except Exception as e:
            logger.error(f"Error loading active positions: {e}")
    
    async def _reset_daily_count_if_needed(self):
        """Reset daily trade count if new day"""
        today = datetime.utcnow().date()
        if self.last_trade_date != today:
            self.daily_trade_count = 0
            self.last_trade_date = today
    
    def _is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        current_hour = datetime.utcnow().hour
        return self.config.trading_hours_start <= current_hour <= self.config.trading_hours_end
    
    async def _update_performance_metrics(self):
        """Update performance metrics"""
        try:
            total_trades = self.performance_metrics["total_trades"]
            if total_trades > 0:
                self.performance_metrics["win_rate"] = (
                    self.performance_metrics["winning_trades"] / total_trades * 100
                )
                
                # Calculate average win/loss
                if self.performance_metrics["winning_trades"] > 0:
                    self.performance_metrics["avg_win"] = (
                        self.performance_metrics["total_pnl"] / 
                        self.performance_metrics["winning_trades"]
                    )
                
                if self.performance_metrics["losing_trades"] > 0:
                    self.performance_metrics["avg_loss"] = (
                        self.performance_metrics["total_pnl"] / 
                        self.performance_metrics["losing_trades"]
                    )
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    async def get_trading_status(self) -> Dict[str, Any]:
        """Get current trading status"""
        try:
            portfolio_summary = await self.paper_trading.get_portfolio_summary()
            
            return {
                "is_running": self.is_running,
                "auto_trading_enabled": self.config.auto_trading_enabled,
                "daily_trade_count": self.daily_trade_count,
                "active_positions": len(self.active_positions),
                "portfolio_summary": {
                    "total_value": portfolio_summary.total_value,
                    "total_pnl": portfolio_summary.total_pnl,
                    "total_pnl_percent": portfolio_summary.total_pnl_percent,
                    "cash_balance": portfolio_summary.cash_balance
                },
                "performance_metrics": self.performance_metrics,
                "config": {
                    "min_confidence_threshold": self.config.min_confidence_threshold,
                    "max_position_size_percent": self.config.max_position_size_percent,
                    "max_daily_trades": self.config.max_daily_trades
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting trading status: {e}")
            return {}
    
    async def update_config(self, new_config: Dict[str, Any]):
        """Update trading configuration"""
        try:
            if "auto_trading_enabled" in new_config:
                self.config.auto_trading_enabled = new_config["auto_trading_enabled"]
            
            if "min_confidence_threshold" in new_config:
                self.config.min_confidence_threshold = new_config["min_confidence_threshold"]
            
            if "max_position_size_percent" in new_config:
                self.config.max_position_size_percent = new_config["max_position_size_percent"]
            
            if "max_daily_trades" in new_config:
                self.config.max_daily_trades = new_config["max_daily_trades"]
            
            logger.info(f"Trading configuration updated: {new_config}")
            
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
    
    async def execute_manual_trade(self, trade_request: TradeRequest) -> Dict[str, Any]:
        """Execute a manual trade"""
        try:
            trade_result = await self.paper_trading.execute_trade(trade_request)
            
            if trade_result.status.value == "filled":
                self.daily_trade_count += 1
                
                # Track position if it's a buy
                if trade_request.action == "buy":
                    self.active_positions[trade_request.token_address] = {
                        "trade_result": trade_result,
                        "entry_time": datetime.utcnow()
                    }
            
            return {
                "success": trade_result.status.value == "filled",
                "trade_result": trade_result,
                "error": trade_result.error_message
            }
            
        except Exception as e:
            logger.error(f"Error executing manual trade: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_trading_loop(self):
        """Start the main trading loop"""
        logger.info("Starting trading loop...")
        self.is_running = True
        
        while self.is_running:
            try:
                # Check if we're in trading hours
                if not self._is_trading_hours():
                    await asyncio.sleep(300)  # Wait 5 minutes
                    continue
                
                # Check daily trade limit
                if self.daily_trade_count >= self.config.max_daily_trades:
                    logger.info("Daily trade limit reached")
                    await asyncio.sleep(3600)  # Wait 1 hour
                    continue
                
                # Get recent high-confidence signals
                signals = await self._get_recent_signals()
                
                # Process signals
                for signal in signals:
                    if self.config.auto_trading_enabled:
                        await self._process_signal(signal)
                
                # Monitor existing positions
                await self._monitor_positions()
                
                # Wait before next iteration
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(30)
    
    def _is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        now = datetime.utcnow()
        current_hour = now.hour
        return self.config.trading_hours_start <= current_hour <= self.config.trading_hours_end
    
    async def _get_recent_signals(self) -> List[TradingSignal]:
        """Get recent high-confidence signals"""
        try:
            async with self.data_manager.get_db_session() as session:
                from sqlalchemy import select, and_, desc
                
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                stmt = select(TradingSignal).where(
                    and_(
                        TradingSignal.timestamp >= cutoff_time,
                        TradingSignal.confidence_score >= self.config.min_confidence_threshold,
                        TradingSignal.is_active == True
                    )
                ).order_by(desc(TradingSignal.confidence_score))
                
                result = await session.execute(stmt)
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"Error getting recent signals: {e}")
            return []
    
    async def _process_signal(self, signal: TradingSignal):
        """Process a trading signal"""
        try:
            # Create trade request
            trade_request = TradeRequest(
                token_symbol=signal.token_symbol,
                token_address=signal.token_address,
                action="buy" if signal.signal_type == "BUY" else "sell",
                amount=self._calculate_position_size(signal),
                order_type=OrderType.MARKET,
                price=signal.current_price,
                signal_id=signal.signal_id
            )
            
            # Execute trade
            trade_result = await self.paper_trading.execute_trade(trade_request)
            
            if trade_result.status.value == "filled":
                self.daily_trade_count += 1
                
                # Track position
                self.active_positions[signal.token_address] = {
                    "signal": signal,
                    "trade_result": trade_result,
                    "entry_time": datetime.utcnow()
                }
                
                # Send alert
                await self.alert_manager.send_trade_alert(signal, trade_result)
                
                logger.info(f"Executed trade for signal {signal.signal_id}")
            
        except Exception as e:
            logger.error(f"Error processing signal {signal.signal_id}: {e}")
    
    def _calculate_position_size(self, signal: TradingSignal) -> float:
        """Calculate position size based on signal confidence"""
        # Base position size
        base_size = 1000.0  # $1000 base position
        
        # Adjust based on confidence
        confidence_multiplier = signal.confidence_score
        adjusted_size = base_size * confidence_multiplier
        
        # Apply max position size limit
        max_size = 100000.0 * self.config.max_position_size_percent
        return min(adjusted_size, max_size)
    
    async def _monitor_positions(self):
        """Monitor existing positions for exit conditions"""
        try:
            for token_address, position_info in list(self.active_positions.items()):
                signal = position_info["signal"]
                trade_result = position_info["trade_result"]
                
                # Get current price
                current_price = await self._get_current_price(signal.token_symbol)
                
                if current_price:
                    # Check stop loss
                    stop_loss_price = signal.current_price * (1 - self.config.stop_loss_percent)
                    if current_price <= stop_loss_price:
                        await self._close_position(token_address, "stop_loss", current_price)
                        continue
                    
                    # Check take profit
                    take_profit_price = signal.current_price * (1 + self.config.take_profit_multiplier * self.config.stop_loss_percent)
                    if current_price >= take_profit_price:
                        await self._close_position(token_address, "take_profit", current_price)
                        continue
                        
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a token"""
        try:
            async with self.data_manager.get_db_session() as session:
                from sqlalchemy import select, desc
                from app.models.token import TokenPrice
                
                stmt = select(TokenPrice).where(
                    TokenPrice.token_symbol == symbol
                ).order_by(desc(TokenPrice.timestamp)).limit(1)
                
                result = await session.execute(stmt)
                price_data = result.scalar_one_or_none()
                
                return price_data.price if price_data else None
                
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    async def _close_position(self, token_address: str, reason: str, current_price: float):
        """Close a position"""
        try:
            position_info = self.active_positions.pop(token_address, None)
            if not position_info:
                return
            
            signal = position_info["signal"]
            
            # Create closing trade request
            closing_request = TradeRequest(
                token_symbol=signal.token_symbol,
                token_address=signal.token_address,
                action="sell",
                amount=position_info["trade_result"].quantity,
                order_type=OrderType.MARKET,
                price=current_price,
                signal_id=signal.signal_id
            )
            
            # Execute closing trade
            closing_result = await self.paper_trading.execute_trade(closing_request)
            
            if closing_result.status.value == "filled":
                self.daily_trade_count += 1
                logger.info(f"Closed position for {signal.token_symbol} due to {reason}")
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    async def stop_trading_loop(self):
        """Stop the trading loop"""
        logger.info("Stopping trading loop...")
        self.is_running = False