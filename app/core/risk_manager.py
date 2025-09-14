"""
Advanced Risk Management System
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class RiskMetrics:
    """Risk assessment metrics"""
    portfolio_value: float
    total_exposure: float
    max_position_size: float
    var_95: float  # Value at Risk 95%
    var_99: float  # Value at Risk 99%
    expected_shortfall: float
    sharpe_ratio: float
    max_drawdown: float
    correlation_risk: float
    concentration_risk: float
    liquidity_risk: float
    overall_risk_score: float
    risk_level: RiskLevel

@dataclass
class PositionRisk:
    """Individual position risk assessment"""
    symbol: str
    position_size: float
    position_value: float
    risk_contribution: float
    beta: float
    volatility: float
    max_loss: float
    stop_loss_price: float
    take_profit_price: float
    risk_score: float

class RiskManager:
    """Advanced risk management system"""
    
    def __init__(self, max_portfolio_risk: float = 0.02, max_position_risk: float = 0.05):
        self.max_portfolio_risk = max_portfolio_risk
        self.max_position_risk = max_position_risk
        self.positions = {}
        self.risk_history = []
        
    def assess_portfolio_risk(self, positions: Dict, market_data: Dict) -> RiskMetrics:
        """Comprehensive portfolio risk assessment"""
        try:
            portfolio_value = sum(pos.get('value', 0) for pos in positions.values())
            total_exposure = sum(pos.get('exposure', 0) for pos in positions.values())
            
            # Calculate Value at Risk
            var_95, var_99 = self._calculate_var(positions, market_data, portfolio_value)
            expected_shortfall = self._calculate_expected_shortfall(positions, market_data, portfolio_value)
            
            # Calculate risk metrics
            sharpe_ratio = self._calculate_portfolio_sharpe(positions, market_data)
            max_drawdown = self._calculate_max_drawdown(positions, market_data)
            
            # Calculate correlation and concentration risks
            correlation_risk = self._calculate_correlation_risk(positions, market_data)
            concentration_risk = self._calculate_concentration_risk(positions, portfolio_value)
            liquidity_risk = self._calculate_liquidity_risk(positions, market_data)
            
            # Calculate overall risk score
            overall_risk_score = self._calculate_overall_risk_score(
                var_95, expected_shortfall, max_drawdown, correlation_risk, 
                concentration_risk, liquidity_risk
            )
            
            # Determine risk level
            risk_level = self._determine_risk_level(overall_risk_score)
            
            # Calculate maximum position size
            max_position_size = self._calculate_max_position_size(
                portfolio_value, overall_risk_score
            )
            
            risk_metrics = RiskMetrics(
                portfolio_value=portfolio_value,
                total_exposure=total_exposure,
                max_position_size=max_position_size,
                var_95=var_95,
                var_99=var_99,
                expected_shortfall=expected_shortfall,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                correlation_risk=correlation_risk,
                concentration_risk=concentration_risk,
                liquidity_risk=liquidity_risk,
                overall_risk_score=overall_risk_score,
                risk_level=risk_level
            )
            
            self.risk_history.append({
                'timestamp': datetime.utcnow(),
                'metrics': risk_metrics
            })
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Error assessing portfolio risk: {e}")
            return self._create_empty_risk_metrics()
    
    def assess_position_risk(self, symbol: str, position: Dict, market_data: Dict) -> PositionRisk:
        """Assess risk for individual position"""
        try:
            position_size = position.get('size', 0)
            position_value = position.get('value', 0)
            current_price = market_data.get('price', 0)
            
            # Calculate position metrics
            volatility = self._calculate_volatility(symbol, market_data)
            beta = self._calculate_beta(symbol, market_data)
            
            # Calculate risk contribution
            risk_contribution = self._calculate_risk_contribution(
                position_value, volatility, beta
            )
            
            # Calculate stop loss and take profit levels
            stop_loss_price, take_profit_price = self._calculate_stop_levels(
                current_price, volatility, position.get('entry_price', current_price)
            )
            
            # Calculate maximum potential loss
            max_loss = abs(current_price - stop_loss_price) * position_size
            
            # Calculate position risk score
            risk_score = self._calculate_position_risk_score(
                volatility, beta, risk_contribution, max_loss, position_value
            )
            
            return PositionRisk(
                symbol=symbol,
                position_size=position_size,
                position_value=position_value,
                risk_contribution=risk_contribution,
                beta=beta,
                volatility=volatility,
                max_loss=max_loss,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                risk_score=risk_score
            )
            
        except Exception as e:
            logger.error(f"Error assessing position risk for {symbol}: {e}")
            return self._create_empty_position_risk(symbol)
    
    def calculate_position_size(self, symbol: str, signal_strength: float, 
                              portfolio_value: float, risk_metrics: RiskMetrics) -> float:
        """Calculate optimal position size based on risk management rules"""
        try:
            # Base position size (2% of portfolio)
            base_size = portfolio_value * 0.02
            
            # Adjust for signal strength
            signal_adjusted_size = base_size * signal_strength
            
            # Adjust for overall portfolio risk
            risk_adjusted_size = signal_adjusted_size * (1 - risk_metrics.overall_risk_score)
            
            # Apply maximum position size limit
            max_size = risk_metrics.max_position_size
            final_size = min(risk_adjusted_size, max_size)
            
            # Apply individual position risk limit
            position_risk_limit = portfolio_value * self.max_position_risk
            if final_size > position_risk_limit:
                final_size = position_risk_limit
            
            return max(final_size, 0)
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return 0
    
    def should_reduce_risk(self, risk_metrics: RiskMetrics) -> bool:
        """Determine if risk should be reduced"""
        return (
            risk_metrics.overall_risk_score > 0.7 or
            risk_metrics.max_drawdown > 0.15 or
            risk_metrics.var_95 > portfolio_value * 0.05 or
            risk_metrics.concentration_risk > 0.3
        )
    
    def get_risk_recommendations(self, risk_metrics: RiskMetrics) -> List[str]:
        """Get risk management recommendations"""
        recommendations = []
        
        if risk_metrics.overall_risk_score > 0.8:
            recommendations.append("CRITICAL: Reduce overall portfolio exposure immediately")
        
        if risk_metrics.max_drawdown > 0.2:
            recommendations.append("HIGH: Implement stricter stop-loss rules")
        
        if risk_metrics.concentration_risk > 0.4:
            recommendations.append("MEDIUM: Diversify portfolio across more assets")
        
        if risk_metrics.correlation_risk > 0.6:
            recommendations.append("MEDIUM: Reduce correlated positions")
        
        if risk_metrics.liquidity_risk > 0.5:
            recommendations.append("LOW: Consider more liquid assets")
        
        if risk_metrics.sharpe_ratio < 0.5:
            recommendations.append("LOW: Review strategy performance")
        
        return recommendations
    
    def _calculate_var(self, positions: Dict, market_data: Dict, portfolio_value: float) -> Tuple[float, float]:
        """Calculate Value at Risk"""
        try:
            # Simplified VaR calculation
            # In practice, this would use historical simulation or Monte Carlo
            
            total_volatility = 0
            for symbol, pos in positions.items():
                volatility = self._calculate_volatility(symbol, market_data)
                weight = pos.get('value', 0) / portfolio_value if portfolio_value > 0 else 0
                total_volatility += (volatility * weight) ** 2
            
            total_volatility = np.sqrt(total_volatility)
            
            # VaR calculation (simplified)
            var_95 = portfolio_value * total_volatility * 1.645  # 95% confidence
            var_99 = portfolio_value * total_volatility * 2.326  # 99% confidence
            
            return var_95, var_99
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return 0, 0
    
    def _calculate_expected_shortfall(self, positions: Dict, market_data: Dict, portfolio_value: float) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        try:
            # Simplified Expected Shortfall calculation
            var_95, _ = self._calculate_var(positions, market_data, portfolio_value)
            return var_95 * 1.2  # Typically 20% higher than VaR
            
        except Exception as e:
            logger.error(f"Error calculating Expected Shortfall: {e}")
            return 0
    
    def _calculate_portfolio_sharpe(self, positions: Dict, market_data: Dict) -> float:
        """Calculate portfolio Sharpe ratio"""
        try:
            # Simplified Sharpe ratio calculation
            # In practice, would use historical returns
            return 1.0  # Placeholder
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0
    
    def _calculate_max_drawdown(self, positions: Dict, market_data: Dict) -> float:
        """Calculate maximum drawdown"""
        try:
            # Simplified max drawdown calculation
            # In practice, would use historical equity curve
            return 0.1  # Placeholder 10%
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0
    
    def _calculate_correlation_risk(self, positions: Dict, market_data: Dict) -> float:
        """Calculate correlation risk"""
        try:
            # Simplified correlation risk calculation
            # In practice, would calculate actual correlations between positions
            return 0.3  # Placeholder
            
        except Exception as e:
            logger.error(f"Error calculating correlation risk: {e}")
            return 0
    
    def _calculate_concentration_risk(self, positions: Dict, portfolio_value: float) -> float:
        """Calculate concentration risk"""
        try:
            if not positions or portfolio_value == 0:
                return 0
            
            # Calculate Herfindahl-Hirschman Index
            weights = [pos.get('value', 0) / portfolio_value for pos in positions.values()]
            hhi = sum(w ** 2 for w in weights)
            
            # Normalize to 0-1 scale
            max_hhi = 1.0  # When all weight is in one position
            concentration_risk = hhi / max_hhi
            
            return concentration_risk
            
        except Exception as e:
            logger.error(f"Error calculating concentration risk: {e}")
            return 0
    
    def _calculate_liquidity_risk(self, positions: Dict, market_data: Dict) -> float:
        """Calculate liquidity risk"""
        try:
            # Simplified liquidity risk calculation
            # In practice, would use bid-ask spreads, volume, etc.
            return 0.2  # Placeholder
            
        except Exception as e:
            logger.error(f"Error calculating liquidity risk: {e}")
            return 0
    
    def _calculate_overall_risk_score(self, var_95: float, expected_shortfall: float, 
                                    max_drawdown: float, correlation_risk: float,
                                    concentration_risk: float, liquidity_risk: float) -> float:
        """Calculate overall risk score (0-1)"""
        try:
            # Weighted combination of risk factors
            weights = {
                'var': 0.25,
                'expected_shortfall': 0.20,
                'max_drawdown': 0.20,
                'correlation': 0.15,
                'concentration': 0.10,
                'liquidity': 0.10
            }
            
            # Normalize risk factors to 0-1 scale
            normalized_var = min(var_95 / 10000, 1.0)  # Assuming 10k is max reasonable VaR
            normalized_es = min(expected_shortfall / 12000, 1.0)
            normalized_dd = min(max_drawdown, 1.0)
            
            risk_score = (
                weights['var'] * normalized_var +
                weights['expected_shortfall'] * normalized_es +
                weights['max_drawdown'] * normalized_dd +
                weights['correlation'] * correlation_risk +
                weights['concentration'] * concentration_risk +
                weights['liquidity'] * liquidity_risk
            )
            
            return min(risk_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating overall risk score: {e}")
            return 0.5
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level based on score"""
        if risk_score >= 0.8:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            return RiskLevel.HIGH
        elif risk_score >= 0.4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_max_position_size(self, portfolio_value: float, risk_score: float) -> float:
        """Calculate maximum allowed position size"""
        base_max = portfolio_value * 0.1  # 10% of portfolio
        risk_adjusted = base_max * (1 - risk_score)
        return max(risk_adjusted, portfolio_value * 0.01)  # Minimum 1%
    
    def _calculate_volatility(self, symbol: str, market_data: Dict) -> float:
        """Calculate asset volatility"""
        try:
            # Simplified volatility calculation
            # In practice, would use historical price data
            return 0.2  # Placeholder 20% volatility
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return 0.2
    
    def _calculate_beta(self, symbol: str, market_data: Dict) -> float:
        """Calculate asset beta"""
        try:
            # Simplified beta calculation
            # In practice, would use regression against market index
            return 1.0  # Placeholder
            
        except Exception as e:
            logger.error(f"Error calculating beta for {symbol}: {e}")
            return 1.0
    
    def _calculate_risk_contribution(self, position_value: float, volatility: float, beta: float) -> float:
        """Calculate position's risk contribution"""
        return position_value * volatility * beta
    
    def _calculate_stop_levels(self, current_price: float, volatility: float, entry_price: float) -> Tuple[float, float]:
        """Calculate stop loss and take profit levels"""
        # ATR-based stop loss (simplified)
        atr = current_price * volatility
        stop_loss = current_price - (2 * atr)
        take_profit = current_price + (3 * atr)
        
        return stop_loss, take_profit
    
    def _calculate_position_risk_score(self, volatility: float, beta: float, 
                                     risk_contribution: float, max_loss: float, position_value: float) -> float:
        """Calculate individual position risk score"""
        try:
            # Weighted risk factors
            volatility_score = min(volatility * 2, 1.0)  # Scale volatility
            beta_score = min(abs(beta - 1) * 0.5, 1.0)  # Distance from market beta
            loss_score = min(max_loss / position_value, 1.0)  # Potential loss as % of position
            
            risk_score = (volatility_score * 0.4 + beta_score * 0.3 + loss_score * 0.3)
            return min(risk_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating position risk score: {e}")
            return 0.5
    
    def _create_empty_risk_metrics(self) -> RiskMetrics:
        """Create empty risk metrics for error cases"""
        return RiskMetrics(
            portfolio_value=0,
            total_exposure=0,
            max_position_size=0,
            var_95=0,
            var_99=0,
            expected_shortfall=0,
            sharpe_ratio=0,
            max_drawdown=0,
            correlation_risk=0,
            concentration_risk=0,
            liquidity_risk=0,
            overall_risk_score=0,
            risk_level=RiskLevel.LOW
        )
    
    def _create_empty_position_risk(self, symbol: str) -> PositionRisk:
        """Create empty position risk for error cases"""
        return PositionRisk(
            symbol=symbol,
            position_size=0,
            position_value=0,
            risk_contribution=0,
            beta=1.0,
            volatility=0,
            max_loss=0,
            stop_loss_price=0,
            take_profit_price=0,
            risk_score=0
        )
