"""
Advanced Technical Analysis Engine
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TechnicalSignal:
    """Technical analysis signal"""
    symbol: str
    signal_type: str  # BUY, SELL, HOLD
    strength: float  # 0-1
    indicators: Dict[str, float]
    timestamp: datetime
    price: float
    confidence: float

class TechnicalAnalyzer:
    """Advanced technical analysis engine"""
    
    def __init__(self):
        self.indicators = {}
        self.price_data = {}
        
    def calculate_sma(self, prices: List[float], period: int) -> List[float]:
        """Simple Moving Average"""
        if len(prices) < period:
            return [0.0] * len(prices)
        
        sma = []
        for i in range(len(prices)):
            if i < period - 1:
                sma.append(0.0)
            else:
                sma.append(sum(prices[i-period+1:i+1]) / period)
        return sma
    
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Exponential Moving Average"""
        if len(prices) < period:
            return [0.0] * len(prices)
        
        multiplier = 2 / (period + 1)
        ema = [prices[0]]  # Start with first price
        
        for i in range(1, len(prices)):
            ema.append((prices[i] * multiplier) + (ema[-1] * (1 - multiplier)))
        
        return ema
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Relative Strength Index"""
        if len(prices) < period + 1:
            return [50.0] * len(prices)
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        rsi = [50.0] * period  # Initial values
        
        for i in range(period, len(prices)):
            avg_gain = sum(gains[i-period:i]) / period
            avg_loss = sum(losses[i-period:i]) / period
            
            if avg_loss == 0:
                rsi.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))
        
        return rsi
    
    def calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
        """MACD (Moving Average Convergence Divergence)"""
        ema_fast = self.calculate_ema(prices, fast)
        ema_slow = self.calculate_ema(prices, slow)
        
        macd_line = [fast_val - slow_val for fast_val, slow_val in zip(ema_fast, ema_slow)]
        signal_line = self.calculate_ema(macd_line, signal)
        histogram = [macd - signal for macd, signal in zip(macd_line, signal_line)]
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2) -> Dict[str, List[float]]:
        """Bollinger Bands"""
        sma = self.calculate_sma(prices, period)
        bands = {'upper': [], 'middle': [], 'lower': []}
        
        for i in range(len(prices)):
            if i < period - 1:
                bands['upper'].append(0.0)
                bands['middle'].append(0.0)
                bands['lower'].append(0.0)
            else:
                period_prices = prices[i-period+1:i+1]
                mean = sma[i]
                std = np.std(period_prices)
                
                bands['upper'].append(mean + (std * std_dev))
                bands['middle'].append(mean)
                bands['lower'].append(mean - (std * std_dev))
        
        return bands
    
    def calculate_stochastic(self, high: List[float], low: List[float], close: List[float], k_period: int = 14, d_period: int = 3) -> Dict[str, List[float]]:
        """Stochastic Oscillator"""
        k_percent = []
        d_percent = []
        
        for i in range(len(close)):
            if i < k_period - 1:
                k_percent.append(50.0)
            else:
                period_high = max(high[i-k_period+1:i+1])
                period_low = min(low[i-k_period+1:i+1])
                
                if period_high == period_low:
                    k_percent.append(50.0)
                else:
                    k_percent.append(((close[i] - period_low) / (period_high - period_low)) * 100)
        
        # Calculate %D (smoothed %K)
        for i in range(len(k_percent)):
            if i < d_period - 1:
                d_percent.append(50.0)
            else:
                d_percent.append(sum(k_percent[i-d_period+1:i+1]) / d_period)
        
        return {'k': k_percent, 'd': d_percent}
    
    def calculate_atr(self, high: List[float], low: List[float], close: List[float], period: int = 14) -> List[float]:
        """Average True Range"""
        tr = []
        atr = []
        
        for i in range(len(close)):
            if i == 0:
                tr.append(high[i] - low[i])
            else:
                tr1 = high[i] - low[i]
                tr2 = abs(high[i] - close[i-1])
                tr3 = abs(low[i] - close[i-1])
                tr.append(max(tr1, tr2, tr3))
        
        # Calculate ATR
        for i in range(len(tr)):
            if i < period - 1:
                atr.append(0.0)
            else:
                atr.append(sum(tr[i-period+1:i+1]) / period)
        
        return atr
    
    def calculate_volume_indicators(self, prices: List[float], volumes: List[float]) -> Dict[str, List[float]]:
        """Volume-based indicators"""
        # On-Balance Volume (OBV)
        obv = [volumes[0]]
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif prices[i] < prices[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        
        # Volume Price Trend (VPT)
        vpt = [0.0]
        for i in range(1, len(prices)):
            price_change = (prices[i] - prices[i-1]) / prices[i-1]
            vpt.append(vpt[-1] + (volumes[i] * price_change))
        
        return {'obv': obv, 'vpt': vpt}
    
    def generate_signals(self, symbol: str, price_data: Dict) -> List[TechnicalSignal]:
        """Generate technical analysis signals"""
        signals = []
        
        try:
            prices = price_data.get('prices', [])
            volumes = price_data.get('volumes', [])
            timestamps = price_data.get('timestamps', [])
            
            if len(prices) < 50:  # Need enough data
                return signals
            
            # Calculate indicators
            sma_20 = self.calculate_sma(prices, 20)
            sma_50 = self.calculate_sma(prices, 50)
            ema_12 = self.calculate_ema(prices, 12)
            ema_26 = self.calculate_ema(prices, 26)
            rsi = self.calculate_rsi(prices, 14)
            macd = self.calculate_macd(prices)
            bb = self.calculate_bollinger_bands(prices, 20, 2)
            
            # Generate signals based on multiple indicators
            current_price = prices[-1]
            current_rsi = rsi[-1]
            current_macd = macd['macd'][-1]
            current_signal = macd['signal'][-1]
            current_bb_upper = bb['upper'][-1]
            current_bb_lower = bb['lower'][-1]
            current_sma_20 = sma_20[-1]
            current_sma_50 = sma_50[-1]
            
            # RSI signals
            if current_rsi < 30:  # Oversold
                strength = (30 - current_rsi) / 30
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    signal_type="BUY",
                    strength=strength,
                    indicators={'rsi': current_rsi, 'price': current_price},
                    timestamp=datetime.utcnow(),
                    price=current_price,
                    confidence=strength * 0.8
                ))
            elif current_rsi > 70:  # Overbought
                strength = (current_rsi - 70) / 30
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    signal_type="SELL",
                    strength=strength,
                    indicators={'rsi': current_rsi, 'price': current_price},
                    timestamp=datetime.utcnow(),
                    price=current_price,
                    confidence=strength * 0.8
                ))
            
            # MACD signals
            if current_macd > current_signal and macd['macd'][-2] <= macd['signal'][-2]:
                # MACD bullish crossover
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    signal_type="BUY",
                    strength=0.7,
                    indicators={'macd': current_macd, 'signal': current_signal, 'price': current_price},
                    timestamp=datetime.utcnow(),
                    price=current_price,
                    confidence=0.7
                ))
            elif current_macd < current_signal and macd['macd'][-2] >= macd['signal'][-2]:
                # MACD bearish crossover
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    signal_type="SELL",
                    strength=0.7,
                    indicators={'macd': current_macd, 'signal': current_signal, 'price': current_price},
                    timestamp=datetime.utcnow(),
                    price=current_price,
                    confidence=0.7
                ))
            
            # Bollinger Bands signals
            if current_price < current_bb_lower:
                strength = (current_bb_lower - current_price) / current_bb_lower
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    signal_type="BUY",
                    strength=min(strength, 1.0),
                    indicators={'bb_lower': current_bb_lower, 'bb_upper': current_bb_upper, 'price': current_price},
                    timestamp=datetime.utcnow(),
                    price=current_price,
                    confidence=min(strength, 1.0) * 0.6
                ))
            elif current_price > current_bb_upper:
                strength = (current_price - current_bb_upper) / current_bb_upper
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    signal_type="SELL",
                    strength=min(strength, 1.0),
                    indicators={'bb_lower': current_bb_lower, 'bb_upper': current_bb_upper, 'price': current_price},
                    timestamp=datetime.utcnow(),
                    price=current_price,
                    confidence=min(strength, 1.0) * 0.6
                ))
            
            # Moving Average signals
            if current_sma_20 > current_sma_50 and sma_20[-2] <= sma_50[-2]:
                # Golden cross
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    signal_type="BUY",
                    strength=0.8,
                    indicators={'sma_20': current_sma_20, 'sma_50': current_sma_50, 'price': current_price},
                    timestamp=datetime.utcnow(),
                    price=current_price,
                    confidence=0.8
                ))
            elif current_sma_20 < current_sma_50 and sma_20[-2] >= sma_50[-2]:
                # Death cross
                signals.append(TechnicalSignal(
                    symbol=symbol,
                    signal_type="SELL",
                    strength=0.8,
                    indicators={'sma_20': current_sma_20, 'sma_50': current_sma_50, 'price': current_price},
                    timestamp=datetime.utcnow(),
                    price=current_price,
                    confidence=0.8
                ))
            
        except Exception as e:
            logger.error(f"Error generating technical signals for {symbol}: {e}")
        
        return signals
    
    def get_market_trend(self, prices: List[float]) -> str:
        """Determine overall market trend"""
        if len(prices) < 20:
            return "UNKNOWN"
        
        sma_20 = self.calculate_sma(prices, 20)[-1]
        sma_50 = self.calculate_sma(prices, 50)[-1] if len(prices) >= 50 else sma_20
        current_price = prices[-1]
        
        if current_price > sma_20 > sma_50:
            return "BULLISH"
        elif current_price < sma_20 < sma_50:
            return "BEARISH"
        else:
            return "SIDEWAYS"
    
    def calculate_support_resistance(self, prices: List[float], lookback: int = 20) -> Dict[str, float]:
        """Calculate support and resistance levels"""
        if len(prices) < lookback:
            return {"support": 0.0, "resistance": 0.0}
        
        recent_prices = prices[-lookback:]
        support = min(recent_prices)
        resistance = max(recent_prices)
        
        return {"support": support, "resistance": resistance}
