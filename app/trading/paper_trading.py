"""
Advanced Paper Trading Engine with Real-time P&L Tracking
Simulates real trading with comprehensive performance analytics
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json
import uuid
from collections import defaultdict
import numpy as np
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Trading position data structure"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    entry_time: datetime
    position_type: str  # 'LONG' or 'SHORT'
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    signal_confidence: float = 0.0
    signal_id: str = ""
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


@dataclass
class Trade:
    """Completed trade record"""
    trade_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    price: float
    timestamp: datetime
    signal_confidence: float
    signal_id: str
    realized_pnl: float = 0.0
    realized_pnl_pct: float = 0.0
    hold_duration: Optional[timedelta] = None
    exit_reason: str = "MANUAL"  # 'MANUAL', 'STOP_LOSS', 'TAKE_PROFIT', 'SIGNAL'


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_value: float
    cash_balance: float
    positions_value: float
    initial_balance: float
    total_return: float
    total_return_pct: float
    daily_return_pct: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_hold_time: float  # hours
    last_updated: datetime


class PaperTradingEngine:
    """Advanced paper trading engine with real-time analytics"""

    def __init__(self, initial_balance: float = 100000.0, max_positions: int = 10):
        self.initial_balance = initial_balance
        self.cash_balance = initial_balance
        self.max_positions = max_positions

        # Trading state
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Trade] = []
        self.balance_history: List[Tuple[datetime, float]] = [(datetime.utcnow(), initial_balance)]

        # Performance tracking
        self.daily_returns: List[float] = []
        self.peak_portfolio_value = initial_balance
        self.last_portfolio_update = datetime.utcnow()

        # Risk management
        self.max_risk_per_trade = 0.03  # 3% max risk per trade
        self.max_portfolio_risk = 0.15  # 15% max portfolio risk
        self.min_confidence_threshold = 0.6

        # Price cache for performance
        self.price_cache = {}
        self.price_cache_expiry = {}

    async def execute_signal(self, signal: dict) -> dict:
        """Execute a trading signal"""
        logger.info(f"Executing signal for {signal['symbol']}: {signal['signal_type']}")

        try:
            symbol = signal['symbol']
            signal_type = signal['signal_type']
            confidence = signal.get('confidence', 0.0)
            signal_id = signal.get('signal_id', str(uuid.uuid4()))

            # Validate signal
            if confidence < self.min_confidence_threshold:
                return {
                    'success': False,
                    'reason': f'Signal confidence {confidence:.2f} below threshold {self.min_confidence_threshold}'
                }

            # Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                return {'success': False, 'reason': 'Unable to get current price'}

            # Execute based on signal type
            if signal_type in ['BUY', 'STRONG_BUY']:
                return await self._execute_buy(signal, current_price, signal_id)
            elif signal_type in ['SELL', 'STRONG_SELL']:
                return await self._execute_sell(signal, current_price, signal_id)
            else:
                return {'success': False, 'reason': f'Signal type {signal_type} not supported for execution'}

        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return {'success': False, 'reason': str(e)}

    async def _execute_buy(self, signal: dict, current_price: float, signal_id: str) -> dict:
        """Execute a buy signal"""
        symbol = signal['symbol']
        confidence = signal['confidence']

        # Check if we already have a position
        if symbol in self.positions:
            return {'success': False, 'reason': f'Already have position in {symbol}'}

        # Check maximum positions limit
        if len(self.positions) >= self.max_positions:
            return {'success': False, 'reason': f'Maximum positions ({self.max_positions}) reached'}

        # Calculate position size based on confidence and risk management
        position_size = self._calculate_position_size(confidence, current_price)

        if position_size <= 0:
            return {'success': False, 'reason': 'Position size too small or insufficient funds'}

        total_cost = position_size * current_price

        if total_cost > self.cash_balance:
            return {'success': False, 'reason': 'Insufficient cash balance'}

        # Calculate stop loss and take profit
        stop_loss = signal.get('stop_loss') or current_price * 0.95  # 5% stop loss default
        take_profit = signal.get('target_price') or current_price * (1 + confidence * 0.2)  # Dynamic TP

        # Create position
        position = Position(
            symbol=symbol,
            quantity=position_size,
            entry_price=current_price,
            current_price=current_price,
            entry_time=datetime.utcnow(),
            position_type='LONG',
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_confidence=confidence,
            signal_id=signal_id
        )

        # Update balances
        self.cash_balance -= total_cost
        self.positions[symbol] = position

        # Record trade
        trade = Trade(
            trade_id=str(uuid.uuid4()),
            symbol=symbol,
            side='BUY',
            quantity=position_size,
            price=current_price,
            timestamp=datetime.utcnow(),
            signal_confidence=confidence,
            signal_id=signal_id
        )

        self.trade_history.append(trade)

        logger.info(f"BUY executed: {symbol} x{position_size:.4f} @ ${current_price:.4f}")

        return {
            'success': True,
            'trade': asdict(trade),
            'position': asdict(position),
            'remaining_balance': self.cash_balance,
            'total_cost': total_cost
        }

    async def _execute_sell(self, signal: dict, current_price: float, signal_id: str) -> dict:
        """Execute a sell signal (close existing position)"""
        symbol = signal['symbol']

        if symbol not in self.positions:
            return {'success': False, 'reason': f'No position to sell in {symbol}'}

        return await self._close_position(symbol, current_price, "SIGNAL", signal_id)

    async def _close_position(self, symbol: str, exit_price: float, exit_reason: str = "MANUAL",
                             signal_id: str = "") -> dict:
        """Close an existing position"""
        if symbol not in self.positions:
            return {'success': False, 'reason': f'No position found for {symbol}'}

        position = self.positions[symbol]

        # Calculate P&L
        total_value = position.quantity * exit_price
        total_cost = position.quantity * position.entry_price
        realized_pnl = total_value - total_cost
        realized_pnl_pct = (realized_pnl / total_cost) * 100

        # Update cash balance
        self.cash_balance += total_value

        # Calculate hold duration
        hold_duration = datetime.utcnow() - position.entry_time

        # Record trade
        trade = Trade(
            trade_id=str(uuid.uuid4()),
            symbol=symbol,
            side='SELL',
            quantity=position.quantity,
            price=exit_price,
            timestamp=datetime.utcnow(),
            signal_confidence=position.signal_confidence,
            signal_id=signal_id or position.signal_id,
            realized_pnl=realized_pnl,
            realized_pnl_pct=realized_pnl_pct,
            hold_duration=hold_duration,
            exit_reason=exit_reason
        )

        self.trade_history.append(trade)

        # Remove position
        del self.positions[symbol]

        logger.info(f"SELL executed: {symbol} x{position.quantity:.4f} @ ${exit_price:.4f} | "
                   f"P&L: ${realized_pnl:.2f} ({realized_pnl_pct:.2f}%)")

        return {
            'success': True,
            'trade': asdict(trade),
            'realized_pnl': realized_pnl,
            'realized_pnl_pct': realized_pnl_pct,
            'hold_duration_hours': hold_duration.total_seconds() / 3600,
            'remaining_balance': self.cash_balance
        }

    def _calculate_position_size(self, confidence: float, price: float) -> float:
        """Calculate position size based on confidence and risk management"""

        # Risk amount based on confidence (1-3% of portfolio)
        base_risk_pct = 0.01  # 1% base risk
        confidence_multiplier = 1 + (confidence * 2)  # Scale up to 3% for high confidence
        risk_pct = min(base_risk_pct * confidence_multiplier, self.max_risk_per_trade)

        # Calculate risk amount
        portfolio_value = self.get_portfolio_value()
        risk_amount = portfolio_value * risk_pct

        # Don't use more than available cash
        risk_amount = min(risk_amount, self.cash_balance * 0.9)  # Leave 10% cash buffer

        # Calculate position size
        position_size = risk_amount / price

        return position_size

    async def update_positions(self) -> dict:
        """Update all positions with current prices and check exit conditions"""
        updates = []
        exit_results = []

        for symbol, position in list(self.positions.items()):
            try:
                current_price = await self._get_current_price(symbol)

                if current_price:
                    # Update position with current price
                    old_price = position.current_price
                    position.current_price = current_price

                    # Calculate unrealized P&L
                    total_cost = position.quantity * position.entry_price
                    current_value = position.quantity * current_price
                    position.unrealized_pnl = current_value - total_cost
                    position.unrealized_pnl_pct = (position.unrealized_pnl / total_cost) * 100

                    updates.append({
                        'symbol': symbol,
                        'old_price': old_price,
                        'new_price': current_price,
                        'unrealized_pnl': position.unrealized_pnl,
                        'unrealized_pnl_pct': position.unrealized_pnl_pct
                    })

                    # Check exit conditions
                    exit_result = await self._check_exit_conditions(symbol, position, current_price)
                    if exit_result:
                        exit_results.append(exit_result)

            except Exception as e:
                logger.error(f"Error updating position {symbol}: {e}")

        # Update portfolio metrics
        await self._update_portfolio_history()

        return {
            'updated_positions': updates,
            'exits_executed': exit_results,
            'total_positions': len(self.positions)
        }

    async def _check_exit_conditions(self, symbol: str, position: Position, current_price: float) -> Optional[dict]:
        """Check if position should be closed based on stop loss or take profit"""

        # Check stop loss
        if position.stop_loss and current_price <= position.stop_loss:
            logger.info(f"Stop loss triggered for {symbol}: ${current_price} <= ${position.stop_loss}")
            return await self._close_position(symbol, current_price, "STOP_LOSS")

        # Check take profit
        if position.take_profit and current_price >= position.take_profit:
            logger.info(f"Take profit triggered for {symbol}: ${current_price} >= ${position.take_profit}")
            return await self._close_position(symbol, current_price, "TAKE_PROFIT")

        return None

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price with caching"""
        now = datetime.utcnow()

        # Check cache first
        if (symbol in self.price_cache and
            symbol in self.price_cache_expiry and
            self.price_cache_expiry[symbol] > now):
            return self.price_cache[symbol]

        try:
            # Use CoinGecko free API for current prices
            coin_id_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'ADA': 'cardano',
                'SOL': 'solana',
                'MATIC': 'matic-network',
                'LINK': 'chainlink',
                'UNI': 'uniswap',
                'AVAX': 'avalanche-2',
                'DOT': 'polkadot'
            }

            coin_id = coin_id_map.get(symbol, symbol.lower())
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': coin_id, 'vs_currencies': 'usd'}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data.get(coin_id, {}).get('usd')

                        if price:
                            # Cache for 30 seconds
                            self.price_cache[symbol] = price
                            self.price_cache_expiry[symbol] = now + timedelta(seconds=30)
                            return price

        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")

        return None

    def get_portfolio_value(self) -> float:
        """Calculate current portfolio value"""
        positions_value = sum(
            pos.quantity * pos.current_price
            for pos in self.positions.values()
        )
        return self.cash_balance + positions_value

    async def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate comprehensive portfolio performance metrics"""

        # Update positions first
        await self.update_positions()

        # Basic values
        total_value = self.get_portfolio_value()
        positions_value = total_value - self.cash_balance
        total_return = total_value - self.initial_balance
        total_return_pct = (total_return / self.initial_balance) * 100

        # Unrealized P&L
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())

        # Realized P&L from completed trades
        realized_pnl = sum(trade.realized_pnl for trade in self.trade_history if trade.side == 'SELL')

        # Trade statistics
        completed_trades = [t for t in self.trade_history if t.side == 'SELL']
        total_trades = len(completed_trades)

        if total_trades > 0:
            winning_trades = len([t for t in completed_trades if t.realized_pnl > 0])
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades) * 100

            wins = [t.realized_pnl for t in completed_trades if t.realized_pnl > 0]
            losses = [abs(t.realized_pnl) for t in completed_trades if t.realized_pnl < 0]

            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            largest_win = max(wins) if wins else 0
            largest_loss = max(losses) if losses else 0

            profit_factor = sum(wins) / max(sum(losses), 1)

            # Average hold time
            hold_times = [t.hold_duration.total_seconds() / 3600 for t in completed_trades if t.hold_duration]
            avg_hold_time = np.mean(hold_times) if hold_times else 0

        else:
            winning_trades = losing_trades = win_rate = avg_win = avg_loss = 0
            largest_win = largest_loss = profit_factor = avg_hold_time = 0

        # Calculate daily return
        daily_return_pct = 0
        if len(self.balance_history) > 1:
            yesterday_value = self.balance_history[-2][1] if len(self.balance_history) > 1 else self.initial_balance
            daily_return_pct = ((total_value - yesterday_value) / yesterday_value) * 100

        # Calculate max drawdown
        max_drawdown, max_drawdown_pct = self._calculate_max_drawdown()

        # Calculate Sharpe ratio (simplified)
        sharpe_ratio = self._calculate_sharpe_ratio()

        return PortfolioMetrics(
            total_value=total_value,
            cash_balance=self.cash_balance,
            positions_value=positions_value,
            initial_balance=self.initial_balance,
            total_return=total_return,
            total_return_pct=total_return_pct,
            daily_return_pct=daily_return_pct,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            total_pnl=unrealized_pnl + realized_pnl,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_hold_time=avg_hold_time,
            last_updated=datetime.utcnow()
        )

    def _calculate_max_drawdown(self) -> Tuple[float, float]:
        """Calculate maximum drawdown"""
        if len(self.balance_history) < 2:
            return 0, 0

        values = [value for _, value in self.balance_history]
        peak = values[0]
        max_drawdown = 0
        max_drawdown_pct = 0

        for value in values[1:]:
            if value > peak:
                peak = value

            drawdown = peak - value
            drawdown_pct = (drawdown / peak) * 100

            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct

        return max_drawdown, max_drawdown_pct

    def _calculate_sharpe_ratio(self) -> float:
        """Calculate simplified Sharpe ratio"""
        if len(self.balance_history) < 2:
            return 0

        # Calculate daily returns
        values = [value for _, value in self.balance_history[-30:]]  # Last 30 data points
        if len(values) < 2:
            return 0

        returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]

        if not returns:
            return 0

        avg_return = np.mean(returns)
        std_return = np.std(returns) if len(returns) > 1 else 0

        if std_return == 0:
            return 0

        # Annualized Sharpe ratio (assuming daily data)
        sharpe = (avg_return / std_return) * np.sqrt(365)
        return sharpe

    async def _update_portfolio_history(self):
        """Update portfolio value history"""
        current_value = self.get_portfolio_value()
        current_time = datetime.utcnow()

        # Add entry if it's been more than 1 hour since last update
        if not self.balance_history or (current_time - self.balance_history[-1][0]).total_seconds() > 3600:
            self.balance_history.append((current_time, current_value))

            # Keep only last 7 days of hourly data
            cutoff_time = current_time - timedelta(days=7)
            self.balance_history = [(t, v) for t, v in self.balance_history if t >= cutoff_time]

        # Update peak value
        if current_value > self.peak_portfolio_value:
            self.peak_portfolio_value = current_value

    def get_position_summary(self) -> List[dict]:
        """Get summary of all current positions"""
        return [
            {
                'symbol': pos.symbol,
                'quantity': pos.quantity,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'unrealized_pnl': pos.unrealized_pnl,
                'unrealized_pnl_pct': pos.unrealized_pnl_pct,
                'days_held': (datetime.utcnow() - pos.entry_time).days,
                'stop_loss': pos.stop_loss,
                'take_profit': pos.take_profit,
                'signal_confidence': pos.signal_confidence
            }
            for pos in self.positions.values()
        ]

    def get_recent_trades(self, limit: int = 10) -> List[dict]:
        """Get recent trade history"""
        recent_trades = sorted(self.trade_history, key=lambda x: x.timestamp, reverse=True)[:limit]
        return [asdict(trade) for trade in recent_trades]

    async def close_all_positions(self, reason: str = "MANUAL") -> List[dict]:
        """Close all open positions"""
        results = []

        for symbol in list(self.positions.keys()):
            try:
                current_price = await self._get_current_price(symbol)
                if current_price:
                    result = await self._close_position(symbol, current_price, reason)
                    results.append(result)
            except Exception as e:
                logger.error(f"Error closing position {symbol}: {e}")
                results.append({'success': False, 'symbol': symbol, 'error': str(e)})

        return results

    def export_performance_data(self) -> dict:
        """Export all performance data for analysis"""
        return {
            'portfolio_metrics': asdict(asyncio.run(self.get_portfolio_metrics())),
            'positions': self.get_position_summary(),
            'recent_trades': self.get_recent_trades(50),
            'balance_history': [(t.isoformat(), v) for t, v in self.balance_history],
            'settings': {
                'initial_balance': self.initial_balance,
                'max_positions': self.max_positions,
                'max_risk_per_trade': self.max_risk_per_trade,
                'min_confidence_threshold': self.min_confidence_threshold
            },
            'export_timestamp': datetime.utcnow().isoformat()
        }


# Example usage and testing
async def main():
    """Example usage of the paper trading engine"""

    # Initialize paper trading
    trader = PaperTradingEngine(initial_balance=100000)

    # Example signal
    signal = {
        'symbol': 'BTC',
        'signal_type': 'BUY',
        'confidence': 0.75,
        'current_price': 45000,
        'target_price': 48000,
        'stop_loss': 42000,
        'reasoning': 'Strong whale accumulation detected with positive Reddit sentiment'
    }

    # Execute signal
    result = await trader.execute_signal(signal)
    print(f"Trade execution result: {result}")

    # Wait a bit and update positions
    await asyncio.sleep(2)
    await trader.update_positions()

    # Get portfolio metrics
    metrics = await trader.get_portfolio_metrics()
    print(f"Portfolio value: ${metrics.total_value:.2f}")
    print(f"Total return: {metrics.total_return_pct:.2f}%")
    print(f"Positions: {len(trader.positions)}")

    # Get position summary
    positions = trader.get_position_summary()
    for pos in positions:
        print(f"{pos['symbol']}: {pos['unrealized_pnl_pct']:.2f}% P&L")


if __name__ == "__main__":
    asyncio.run(main())