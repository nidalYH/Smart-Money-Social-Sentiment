"""
Advanced Trading Engine with ML, Technical Analysis, and Risk Management
"""
import asyncio
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

from .technical_analyzer import TechnicalAnalyzer, TechnicalSignal
from .ml_predictor import MLPredictor, MLPrediction
from .backtester import Backtester, BacktestResult
from .risk_manager import RiskManager, RiskMetrics, PositionRisk
from .notification_system import NotificationSystem, NotificationType, Priority
from .exchange_manager import ExchangeManager, OrderSide, OrderType

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"

@dataclass
class TradingSignal:
    """Enhanced trading signal combining multiple analysis methods"""
    symbol: str
    signal_type: str  # BUY, SELL, HOLD
    confidence: float  # 0-1
    technical_score: float
    ml_score: float
    whale_score: float
    sentiment_score: float
    risk_score: float
    price: float
    stop_loss: float
    take_profit: float
    position_size: float
    reasoning: str
    timestamp: datetime
    source: str

@dataclass
class TradingPerformance:
    """Trading performance metrics"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_percent: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    avg_trade_duration: timedelta
    best_trade: Dict
    worst_trade: Dict
    monthly_returns: Dict[str, float]

class AdvancedTradingEngine:
    """Advanced trading engine with ML, technical analysis, and risk management"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mode = TradingMode(config.get('trading_mode', 'paper'))
        
        # Initialize components
        self.technical_analyzer = TechnicalAnalyzer()
        self.ml_predictor = MLPredictor()
        self.backtester = Backtester(
            initial_capital=config.get('initial_capital', 100000),
            commission=config.get('commission', 0.001)
        )
        self.risk_manager = RiskManager(
            max_portfolio_risk=config.get('max_portfolio_risk', 0.02),
            max_position_risk=config.get('max_position_risk', 0.05)
        )
        self.notification_system = NotificationSystem(config.get('notifications', {}))
        self.exchange_manager = ExchangeManager(config.get('exchanges', {}))
        
        # Trading state
        self.positions = {}
        self.orders = {}
        self.performance = TradingPerformance(
            total_trades=0, winning_trades=0, losing_trades=0, win_rate=0.0,
            total_pnl=0.0, total_pnl_percent=0.0, max_drawdown=0.0,
            sharpe_ratio=0.0, sortino_ratio=0.0, profit_factor=0.0,
            avg_trade_duration=timedelta(0), best_trade={}, worst_trade={},
            monthly_returns={}
        )
        
        # Market data cache
        self.market_data = {}
        self.price_history = {}
        
        # Risk management
        self.daily_trade_count = 0
        self.last_trade_date = None
        self.max_daily_trades = config.get('max_daily_trades', 10)
        
    async def start_trading(self):
        """Start the advanced trading engine"""
        logger.info("🚀 Starting Advanced Trading Engine...")
        
        try:
            # Initialize ML models
            await self._initialize_ml_models()
            
            # Start main trading loop
            while True:
                try:
                    await self._trading_cycle()
                    await asyncio.sleep(60)  # Wait 1 minute between cycles
                    
                except Exception as e:
                    logger.error(f"Error in trading cycle: {e}")
                    await asyncio.sleep(30)
        
        except Exception as e:
            logger.error(f"Error starting trading engine: {e}")
    
    async def _trading_cycle(self):
        """Main trading cycle"""
        try:
            # 1. Update market data
            await self._update_market_data()
            
            # 2. Generate trading signals
            signals = await self._generate_trading_signals()
            
            # 3. Risk assessment
            risk_metrics = await self._assess_portfolio_risk()
            
            # 4. Process signals
            for signal in signals:
                if await self._should_execute_signal(signal, risk_metrics):
                    await self._execute_signal(signal)
            
            # 5. Monitor existing positions
            await self._monitor_positions()
            
            # 6. Update performance metrics
            await self._update_performance_metrics()
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    async def _initialize_ml_models(self):
        """Initialize machine learning models"""
        try:
            # Load historical data for training
            symbols = self.config.get('trading_symbols', ['BTCUSDT', 'ETHUSDT'])
            
            for symbol in symbols:
                # Get historical data (simplified - in practice would fetch from API)
                price_data = await self._get_historical_data(symbol, days=365)
                
                if price_data:
                    # Train ML model
                    success = self.ml_predictor.train_model(symbol, price_data)
                    if success:
                        logger.info(f"✅ ML model trained for {symbol}")
                    else:
                        logger.warning(f"⚠️ Failed to train ML model for {symbol}")
        
        except Exception as e:
            logger.error(f"Error initializing ML models: {e}")
    
    async def _update_market_data(self):
        """Update market data for all trading symbols"""
        try:
            symbols = self.config.get('trading_symbols', ['BTCUSDT', 'ETHUSDT'])
            
            for symbol in symbols:
                # Get current price data
                ticker = await self.exchange_manager.get_ticker(
                    self.config.get('primary_exchange', 'binance'), symbol
                )
                
                if ticker:
                    self.market_data[symbol] = {
                        'price': ticker.price,
                        'volume': ticker.volume,
                        'change_24h': ticker.change_24h,
                        'timestamp': ticker.timestamp
                    }
                    
                    # Update price history
                    if symbol not in self.price_history:
                        self.price_history[symbol] = []
                    
                    self.price_history[symbol].append({
                        'price': ticker.price,
                        'volume': ticker.volume,
                        'timestamp': ticker.timestamp
                    })
                    
                    # Keep only last 1000 data points
                    if len(self.price_history[symbol]) > 1000:
                        self.price_history[symbol] = self.price_history[symbol][-1000:]
        
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
    
    async def _generate_trading_signals(self) -> List[TradingSignal]:
        """Generate comprehensive trading signals"""
        signals = []
        
        try:
            symbols = self.config.get('trading_symbols', ['BTCUSDT', 'ETHUSDT'])
            
            for symbol in symbols:
                if symbol not in self.market_data:
                    continue
                
                # Get price data for analysis
                price_data = self._prepare_price_data(symbol)
                if not price_data:
                    continue
                
                # 1. Technical Analysis
                technical_signals = self.technical_analyzer.generate_signals(symbol, price_data)
                
                # 2. ML Prediction
                ml_prediction = self.ml_predictor.predict_price(symbol, price_data)
                
                # 3. Whale Analysis (simplified)
                whale_score = await self._analyze_whale_activity(symbol)
                
                # 4. Sentiment Analysis (simplified)
                sentiment_score = await self._analyze_sentiment(symbol)
                
                # 5. Combine signals
                combined_signal = self._combine_signals(
                    symbol, technical_signals, ml_prediction, whale_score, sentiment_score
                )
                
                if combined_signal:
                    signals.append(combined_signal)
        
        except Exception as e:
            logger.error(f"Error generating trading signals: {e}")
        
        return signals
    
    def _prepare_price_data(self, symbol: str) -> Dict:
        """Prepare price data for analysis"""
        try:
            if symbol not in self.price_history or len(self.price_history[symbol]) < 50:
                return None
            
            history = self.price_history[symbol]
            
            return {
                'prices': [h['price'] for h in history],
                'volumes': [h['volume'] for h in history],
                'timestamps': [h['timestamp'] for h in history],
                'symbol': symbol
            }
        
        except Exception as e:
            logger.error(f"Error preparing price data for {symbol}: {e}")
            return None
    
    def _combine_signals(self, symbol: str, technical_signals: List[TechnicalSignal], 
                        ml_prediction: Optional[MLPrediction], whale_score: float, 
                        sentiment_score: float) -> Optional[TradingSignal]:
        """Combine multiple signal sources into final trading signal"""
        try:
            if not technical_signals:
                return None
            
            # Get the strongest technical signal
            strongest_technical = max(technical_signals, key=lambda s: s.strength)
            
            # Calculate ML score
            ml_score = 0.0
            if ml_prediction:
                # Convert prediction to signal score
                current_price = self.market_data[symbol]['price']
                predicted_price = ml_prediction.predicted_price
                price_change = (predicted_price - current_price) / current_price
                
                if price_change > 0.02:  # 2% increase
                    ml_score = min(price_change * 10, 1.0)  # Scale to 0-1
                elif price_change < -0.02:  # 2% decrease
                    ml_score = min(abs(price_change) * 10, 1.0)
            
            # Calculate risk score
            risk_score = 1.0 - (whale_score * 0.3 + sentiment_score * 0.2 + ml_score * 0.5)
            
            # Calculate overall confidence
            confidence = (
                strongest_technical.strength * 0.4 +
                ml_score * 0.3 +
                whale_score * 0.2 +
                sentiment_score * 0.1
            )
            
            # Determine signal type
            if confidence > 0.7 and strongest_technical.signal_type == "BUY":
                signal_type = "BUY"
            elif confidence > 0.7 and strongest_technical.signal_type == "SELL":
                signal_type = "SELL"
            else:
                signal_type = "HOLD"
            
            if signal_type == "HOLD":
                return None
            
            # Calculate position size
            position_size = self._calculate_position_size(symbol, confidence)
            
            # Calculate stop loss and take profit
            current_price = self.market_data[symbol]['price']
            stop_loss, take_profit = self._calculate_stop_levels(
                current_price, strongest_technical.signal_type, confidence
            )
            
            # Create reasoning
            reasoning = self._create_signal_reasoning(
                strongest_technical, ml_prediction, whale_score, sentiment_score
            )
            
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                technical_score=strongest_technical.strength,
                ml_score=ml_score,
                whale_score=whale_score,
                sentiment_score=sentiment_score,
                risk_score=risk_score,
                price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=position_size,
                reasoning=reasoning,
                timestamp=datetime.utcnow(),
                source="advanced_engine"
            )
        
        except Exception as e:
            logger.error(f"Error combining signals for {symbol}: {e}")
            return None
    
    async def _analyze_whale_activity(self, symbol: str) -> float:
        """Analyze whale activity for symbol (simplified)"""
        try:
            # In practice, this would analyze actual whale transactions
            # For now, return a random score
            return np.random.uniform(0.3, 0.8)
        
        except Exception as e:
            logger.error(f"Error analyzing whale activity for {symbol}: {e}")
            return 0.5
    
    async def _analyze_sentiment(self, symbol: str) -> float:
        """Analyze market sentiment for symbol (simplified)"""
        try:
            # In practice, this would analyze social media, news, etc.
            # For now, return a random score
            return np.random.uniform(0.4, 0.9)
        
        except Exception as e:
            logger.error(f"Error analyzing sentiment for {symbol}: {e}")
            return 0.5
    
    def _calculate_position_size(self, symbol: str, confidence: float) -> float:
        """Calculate position size based on confidence and risk management"""
        try:
            portfolio_value = self.config.get('initial_capital', 100000)
            
            # Base position size (2% of portfolio)
            base_size = portfolio_value * 0.02
            
            # Adjust for confidence
            confidence_adjusted = base_size * confidence
            
            # Adjust for risk
            risk_adjusted = confidence_adjusted * (1 - self.performance.max_drawdown)
            
            # Get current price
            current_price = self.market_data[symbol]['price']
            
            # Calculate quantity
            quantity = risk_adjusted / current_price
            
            return quantity
        
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return 0
    
    def _calculate_stop_levels(self, current_price: float, signal_type: str, confidence: float) -> Tuple[float, float]:
        """Calculate stop loss and take profit levels"""
        try:
            # ATR-based stop loss (simplified)
            atr = current_price * 0.02  # 2% ATR approximation
            
            if signal_type == "BUY":
                stop_loss = current_price - (2 * atr)
                take_profit = current_price + (3 * atr * confidence)
            else:  # SELL
                stop_loss = current_price + (2 * atr)
                take_profit = current_price - (3 * atr * confidence)
            
            return stop_loss, take_profit
        
        except Exception as e:
            logger.error(f"Error calculating stop levels: {e}")
            return current_price * 0.95, current_price * 1.05
    
    def _create_signal_reasoning(self, technical_signal: TechnicalSignal, 
                               ml_prediction: Optional[MLPrediction], 
                               whale_score: float, sentiment_score: float) -> str:
        """Create human-readable reasoning for signal"""
        try:
            reasoning_parts = []
            
            # Technical analysis reasoning
            if technical_signal.strength > 0.7:
                reasoning_parts.append(f"Strong technical signal ({technical_signal.strength:.1%})")
            
            # ML prediction reasoning
            if ml_prediction and ml_prediction.confidence > 0.6:
                reasoning_parts.append(f"ML prediction confidence: {ml_prediction.confidence:.1%}")
            
            # Whale activity reasoning
            if whale_score > 0.6:
                reasoning_parts.append(f"High whale activity ({whale_score:.1%})")
            
            # Sentiment reasoning
            if sentiment_score > 0.7:
                reasoning_parts.append(f"Positive sentiment ({sentiment_score:.1%})")
            
            return "; ".join(reasoning_parts) if reasoning_parts else "Multiple factors aligned"
        
        except Exception as e:
            logger.error(f"Error creating signal reasoning: {e}")
            return "Signal generated by advanced analysis"
    
    async def _assess_portfolio_risk(self) -> RiskMetrics:
        """Assess current portfolio risk"""
        try:
            # Convert positions to risk manager format
            risk_positions = {}
            for symbol, position in self.positions.items():
                risk_positions[symbol] = {
                    'value': position.get('value', 0),
                    'exposure': position.get('exposure', 0)
                }
            
            # Get market data for risk calculation
            market_data = {}
            for symbol in self.positions.keys():
                if symbol in self.market_data:
                    market_data[symbol] = self.market_data[symbol]
            
            return self.risk_manager.assess_portfolio_risk(risk_positions, market_data)
        
        except Exception as e:
            logger.error(f"Error assessing portfolio risk: {e}")
            return self.risk_manager._create_empty_risk_metrics()
    
    async def _should_execute_signal(self, signal: TradingSignal, risk_metrics: RiskMetrics) -> bool:
        """Determine if signal should be executed based on risk management"""
        try:
            # Check confidence threshold
            if signal.confidence < 0.6:
                return False
            
            # Check daily trade limit
            today = datetime.utcnow().date()
            if self.last_trade_date != today:
                self.daily_trade_count = 0
                self.last_trade_date = today
            
            if self.daily_trade_count >= self.max_daily_trades:
                logger.info("Daily trade limit reached")
                return False
            
            # Check risk metrics
            if risk_metrics.overall_risk_score > 0.8:
                logger.info("Portfolio risk too high, skipping signal")
                return False
            
            # Check if already have position in this symbol
            if signal.symbol in self.positions:
                logger.info(f"Already have position in {signal.symbol}")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error checking if signal should execute: {e}")
            return False
    
    async def _execute_signal(self, signal: TradingSignal):
        """Execute trading signal"""
        try:
            logger.info(f"Executing {signal.signal_type} signal for {signal.symbol}")
            
            if self.mode == TradingMode.PAPER:
                await self._execute_paper_trade(signal)
            else:
                await self._execute_live_trade(signal)
            
            # Send notification
            await self.notification_system.send_trade_signal({
                'symbol': signal.symbol,
                'signal_type': signal.signal_type,
                'confidence': signal.confidence,
                'price': signal.price,
                'reasoning': signal.reasoning
            })
            
            self.daily_trade_count += 1
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    async def _execute_paper_trade(self, signal: TradingSignal):
        """Execute paper trade"""
        try:
            # Create paper trade record
            trade_id = f"paper_{int(datetime.utcnow().timestamp())}"
            
            self.positions[signal.symbol] = {
                'id': trade_id,
                'symbol': signal.symbol,
                'side': signal.signal_type,
                'quantity': signal.position_size,
                'entry_price': signal.price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'timestamp': datetime.utcnow(),
                'value': signal.position_size * signal.price
            }
            
            logger.info(f"Paper trade executed: {signal.symbol} {signal.signal_type} {signal.position_size:.4f} @ {signal.price:.4f}")
        
        except Exception as e:
            logger.error(f"Error executing paper trade: {e}")
    
    async def _execute_live_trade(self, signal: TradingSignal):
        """Execute live trade on exchange"""
        try:
            # Determine order side
            side = OrderSide.BUY if signal.signal_type == "BUY" else OrderSide.SELL
            
            # Place order
            order = await self.exchange_manager.place_order(
                exchange=self.config.get('primary_exchange', 'binance'),
                symbol=signal.symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=signal.position_size
            )
            
            if order:
                self.positions[signal.symbol] = {
                    'id': order.id,
                    'symbol': signal.symbol,
                    'side': signal.signal_type,
                    'quantity': signal.position_size,
                    'entry_price': signal.price,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'timestamp': datetime.utcnow(),
                    'value': signal.position_size * signal.price,
                    'order_id': order.id
                }
                
                logger.info(f"Live trade executed: {signal.symbol} {signal.signal_type} {signal.position_size:.4f} @ {signal.price:.4f}")
        
        except Exception as e:
            logger.error(f"Error executing live trade: {e}")
    
    async def _monitor_positions(self):
        """Monitor existing positions for exit conditions"""
        try:
            for symbol, position in list(self.positions.items()):
                current_price = self.market_data.get(symbol, {}).get('price', 0)
                
                if current_price == 0:
                    continue
                
                # Check stop loss
                if position['side'] == 'BUY' and current_price <= position['stop_loss']:
                    await self._close_position(symbol, "STOP_LOSS", current_price)
                elif position['side'] == 'SELL' and current_price >= position['stop_loss']:
                    await self._close_position(symbol, "STOP_LOSS", current_price)
                
                # Check take profit
                elif position['side'] == 'BUY' and current_price >= position['take_profit']:
                    await self._close_position(symbol, "TAKE_PROFIT", current_price)
                elif position['side'] == 'SELL' and current_price <= position['take_profit']:
                    await self._close_position(symbol, "TAKE_PROFIT", current_price)
        
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    async def _close_position(self, symbol: str, reason: str, exit_price: float):
        """Close position"""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            
            # Calculate P&L
            if position['side'] == 'BUY':
                pnl = (exit_price - position['entry_price']) * position['quantity']
            else:  # SELL
                pnl = (position['entry_price'] - exit_price) * position['quantity']
            
            # Update performance
            self.performance.total_trades += 1
            self.performance.total_pnl += pnl
            
            if pnl > 0:
                self.performance.winning_trades += 1
            else:
                self.performance.losing_trades += 1
            
            # Send notification
            await self.notification_system.send_trade_executed({
                'symbol': symbol,
                'type': position['side'],
                'quantity': position['quantity'],
                'price': exit_price,
                'pnl': pnl,
                'reason': reason
            })
            
            # Remove position
            del self.positions[symbol]
            
            logger.info(f"Position closed: {symbol} {reason} @ {exit_price:.4f} P&L: {pnl:.2f}")
        
        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")
    
    async def _update_performance_metrics(self):
        """Update trading performance metrics"""
        try:
            if self.performance.total_trades > 0:
                self.performance.win_rate = (self.performance.winning_trades / self.performance.total_trades) * 100
                
                # Calculate other metrics (simplified)
                portfolio_value = self.config.get('initial_capital', 100000)
                self.performance.total_pnl_percent = (self.performance.total_pnl / portfolio_value) * 100
                
                # Update monthly returns
                current_month = datetime.utcnow().strftime('%Y-%m')
                if current_month not in self.performance.monthly_returns:
                    self.performance.monthly_returns[current_month] = self.performance.total_pnl_percent
        
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    async def _get_historical_data(self, symbol: str, days: int) -> Optional[Dict]:
        """Get historical data for symbol (simplified)"""
        try:
            # In practice, this would fetch from exchange API
            # For now, return None to indicate no data
            return None
        
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        return {
            'total_trades': self.performance.total_trades,
            'winning_trades': self.performance.winning_trades,
            'losing_trades': self.performance.losing_trades,
            'win_rate': self.performance.win_rate,
            'total_pnl': self.performance.total_pnl,
            'total_pnl_percent': self.performance.total_pnl_percent,
            'max_drawdown': self.performance.max_drawdown,
            'sharpe_ratio': self.performance.sharpe_ratio,
            'active_positions': len(self.positions),
            'daily_trades': self.daily_trade_count,
            'positions': list(self.positions.keys())
        }
