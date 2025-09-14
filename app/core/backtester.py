"""
Advanced Backtesting Engine
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class TradeType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class Trade:
    """Individual trade record"""
    symbol: str
    trade_type: TradeType
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percent: float
    fees: float
    signal_strength: float
    hold_duration: timedelta

@dataclass
class BacktestResult:
    """Backtesting results"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_percent: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    avg_trade_duration: timedelta
    best_trade: Trade
    worst_trade: Trade
    trades: List[Trade]
    equity_curve: List[float]
    monthly_returns: Dict[str, float]

class Backtester:
    """Advanced backtesting engine"""
    
    def __init__(self, initial_capital: float = 100000, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
        self.results = {}
        
    def run_backtest(self, 
                    price_data: Dict, 
                    signals: List[Dict], 
                    strategy_name: str = "default",
                    position_sizing: str = "fixed",
                    risk_per_trade: float = 0.02) -> BacktestResult:
        """Run comprehensive backtesting"""
        
        try:
            df = self._prepare_data(price_data, signals)
            if df.empty:
                return self._create_empty_result()
            
            # Initialize tracking variables
            capital = self.initial_capital
            position = 0
            position_value = 0
            trades = []
            equity_curve = [capital]
            
            # Track performance metrics
            peak_capital = capital
            max_drawdown = 0
            max_drawdown_percent = 0
            
            for i in range(1, len(df)):
                current_price = df.iloc[i]['price']
                current_signal = df.iloc[i]['signal']
                current_time = df.iloc[i]['timestamp']
                
                # Update position value
                if position > 0:
                    position_value = position * current_price
                
                # Check for exit conditions
                if position > 0 and self._should_exit(df, i, position):
                    trade = self._close_position(
                        symbol=df.iloc[i]['symbol'],
                        position=position,
                        exit_price=current_price,
                        exit_time=current_time,
                        entry_price=df.iloc[i]['entry_price'],
                        entry_time=df.iloc[i]['entry_time']
                    )
                    if trade:
                        trades.append(trade)
                        capital += trade.pnl
                        position = 0
                        position_value = 0
                
                # Check for entry conditions
                elif position == 0 and current_signal in ['BUY', 'SELL']:
                    if current_signal == 'BUY':
                        position, entry_price = self._open_position(
                            capital, current_price, position_sizing, risk_per_trade
                        )
                        if position > 0:
                            df.at[i, 'position'] = position
                            df.at[i, 'entry_price'] = entry_price
                            df.at[i, 'entry_time'] = current_time
                
                # Update capital and equity curve
                total_value = capital + position_value
                equity_curve.append(total_value)
                
                # Update drawdown tracking
                if total_value > peak_capital:
                    peak_capital = total_value
                
                current_drawdown = peak_capital - total_value
                current_drawdown_percent = (current_drawdown / peak_capital) * 100
                
                if current_drawdown > max_drawdown:
                    max_drawdown = current_drawdown
                    max_drawdown_percent = current_drawdown_percent
            
            # Close any remaining position
            if position > 0:
                trade = self._close_position(
                    symbol=df.iloc[-1]['symbol'],
                    position=position,
                    exit_price=df.iloc[-1]['price'],
                    exit_time=df.iloc[-1]['timestamp'],
                    entry_price=df.iloc[-1]['entry_price'],
                    entry_time=df.iloc[-1]['entry_time']
                )
                if trade:
                    trades.append(trade)
                    capital += trade.pnl
            
            # Calculate final results
            result = self._calculate_results(
                trades, equity_curve, self.initial_capital, capital
            )
            
            self.results[strategy_name] = result
            return result
            
        except Exception as e:
            logger.error(f"Error in backtesting: {e}")
            return self._create_empty_result()
    
    def _prepare_data(self, price_data: Dict, signals: List[Dict]) -> pd.DataFrame:
        """Prepare data for backtesting"""
        try:
            df = pd.DataFrame({
                'timestamp': price_data.get('timestamps', []),
                'price': price_data.get('prices', []),
                'volume': price_data.get('volumes', []),
                'symbol': price_data.get('symbol', 'UNKNOWN')
            })
            
            # Add signal column
            df['signal'] = 'HOLD'
            df['signal_strength'] = 0.0
            df['position'] = 0
            df['entry_price'] = 0.0
            df['entry_time'] = None
            
            # Map signals to dataframe
            for signal in signals:
                signal_time = signal.get('timestamp')
                if signal_time:
                    # Find closest timestamp
                    time_diff = abs((pd.to_datetime(df['timestamp']) - pd.to_datetime(signal_time)).dt.total_seconds())
                    closest_idx = time_diff.idxmin()
                    if time_diff.iloc[closest_idx] < 3600:  # Within 1 hour
                        df.at[closest_idx, 'signal'] = signal.get('signal_type', 'HOLD')
                        df.at[closest_idx, 'signal_strength'] = signal.get('strength', 0.0)
            
            return df
            
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return pd.DataFrame()
    
    def _should_exit(self, df: pd.DataFrame, current_idx: int, position: float) -> bool:
        """Determine if position should be exited"""
        if position == 0:
            return False
        
        # Simple exit conditions (can be enhanced)
        current_price = df.iloc[current_idx]['price']
        entry_price = df.iloc[current_idx]['entry_price']
        
        # Stop loss (5%)
        if current_price <= entry_price * 0.95:
            return True
        
        # Take profit (10%)
        if current_price >= entry_price * 1.10:
            return True
        
        # Time-based exit (7 days)
        entry_time = df.iloc[current_idx]['entry_time']
        current_time = df.iloc[current_idx]['timestamp']
        if (current_time - entry_time).days >= 7:
            return True
        
        return False
    
    def _open_position(self, capital: float, price: float, position_sizing: str, risk_per_trade: float) -> Tuple[float, float]:
        """Open a new position"""
        try:
            if position_sizing == "fixed":
                # Fixed dollar amount
                position_value = capital * 0.1  # 10% of capital
            elif position_sizing == "risk_based":
                # Risk-based position sizing
                position_value = capital * risk_per_trade
            else:
                # Percentage of capital
                position_value = capital * 0.05  # 5% of capital
            
            # Calculate quantity
            quantity = position_value / price
            
            # Apply commission
            commission_cost = position_value * self.commission
            actual_position_value = position_value - commission_cost
            quantity = actual_position_value / price
            
            return quantity, price
            
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return 0, 0
    
    def _close_position(self, symbol: str, position: float, exit_price: float, 
                       exit_time: datetime, entry_price: float, entry_time: datetime) -> Optional[Trade]:
        """Close a position and create trade record"""
        try:
            if position == 0:
                return None
            
            # Calculate P&L
            gross_pnl = position * (exit_price - entry_price)
            fees = (position * entry_price + position * exit_price) * self.commission
            net_pnl = gross_pnl - fees
            pnl_percent = (net_pnl / (position * entry_price)) * 100
            
            # Calculate hold duration
            hold_duration = exit_time - entry_time
            
            trade = Trade(
                symbol=symbol,
                trade_type=TradeType.BUY if position > 0 else TradeType.SELL,
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=abs(position),
                entry_time=entry_time,
                exit_time=exit_time,
                pnl=net_pnl,
                pnl_percent=pnl_percent,
                fees=fees,
                signal_strength=0.0,  # Would need to track this
                hold_duration=hold_duration
            )
            
            return trade
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None
    
    def _calculate_results(self, trades: List[Trade], equity_curve: List[float], 
                          initial_capital: float, final_capital: float) -> BacktestResult:
        """Calculate comprehensive backtesting results"""
        
        if not trades:
            return self._create_empty_result()
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl < 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = sum(t.pnl for t in trades)
        total_pnl_percent = ((final_capital - initial_capital) / initial_capital) * 100
        
        # Drawdown
        max_drawdown, max_drawdown_percent = self._calculate_drawdown(equity_curve)
        
        # Risk metrics
        returns = [equity_curve[i] / equity_curve[i-1] - 1 for i in range(1, len(equity_curve))]
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        sortino_ratio = self._calculate_sortino_ratio(returns)
        
        # Profit factor
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Trade duration
        avg_duration = sum(t.hold_duration for t in trades) / len(trades)
        
        # Best and worst trades
        best_trade = max(trades, key=lambda t: t.pnl) if trades else None
        worst_trade = min(trades, key=lambda t: t.pnl) if trades else None
        
        # Monthly returns
        monthly_returns = self._calculate_monthly_returns(equity_curve)
        
        return BacktestResult(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            profit_factor=profit_factor,
            avg_trade_duration=avg_duration,
            best_trade=best_trade,
            worst_trade=worst_trade,
            trades=trades,
            equity_curve=equity_curve,
            monthly_returns=monthly_returns
        )
    
    def _calculate_drawdown(self, equity_curve: List[float]) -> Tuple[float, float]:
        """Calculate maximum drawdown"""
        peak = equity_curve[0]
        max_dd = 0
        max_dd_percent = 0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = peak - value
            drawdown_percent = (drawdown / peak) * 100
            
            if drawdown > max_dd:
                max_dd = drawdown
                max_dd_percent = drawdown_percent
        
        return max_dd, max_dd_percent
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if not returns:
            return 0
        
        excess_returns = [r - risk_free_rate/252 for r in returns]  # Daily risk-free rate
        if len(excess_returns) < 2:
            return 0
        
        mean_return = np.mean(excess_returns)
        std_return = np.std(excess_returns)
        
        return (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0
    
    def _calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio"""
        if not returns:
            return 0
        
        excess_returns = [r - risk_free_rate/252 for r in returns]
        negative_returns = [r for r in excess_returns if r < 0]
        
        if not negative_returns:
            return float('inf')
        
        mean_return = np.mean(excess_returns)
        downside_deviation = np.std(negative_returns)
        
        return (mean_return / downside_deviation) * np.sqrt(252) if downside_deviation > 0 else 0
    
    def _calculate_monthly_returns(self, equity_curve: List[float]) -> Dict[str, float]:
        """Calculate monthly returns"""
        # This is a simplified version - would need proper date handling
        monthly_returns = {}
        
        if len(equity_curve) < 30:
            return monthly_returns
        
        # Calculate monthly returns (simplified)
        for i in range(30, len(equity_curve), 30):
            if i < len(equity_curve):
                monthly_return = (equity_curve[i] / equity_curve[i-30] - 1) * 100
                month_key = f"Month_{i//30}"
                monthly_returns[month_key] = monthly_return
        
        return monthly_returns
    
    def _create_empty_result(self) -> BacktestResult:
        """Create empty result for error cases"""
        return BacktestResult(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            total_pnl_percent=0.0,
            max_drawdown=0.0,
            max_drawdown_percent=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            profit_factor=0.0,
            avg_trade_duration=timedelta(0),
            best_trade=None,
            worst_trade=None,
            trades=[],
            equity_curve=[],
            monthly_returns={}
        )
    
    def compare_strategies(self, strategies: List[str]) -> Dict[str, Dict]:
        """Compare multiple strategies"""
        comparison = {}
        
        for strategy in strategies:
            if strategy in self.results:
                result = self.results[strategy]
                comparison[strategy] = {
                    'total_return': result.total_pnl_percent,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown_percent,
                    'win_rate': result.win_rate,
                    'total_trades': result.total_trades
                }
        
        return comparison
