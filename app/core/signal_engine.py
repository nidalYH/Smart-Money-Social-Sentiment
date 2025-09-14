"""
Trading signal generation engine that combines whale activity and sentiment analysis
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc

from app.config import settings
from app.models.signal import TradingSignal, SignalPerformance
from app.models.whale import WhaleTransaction, WhaleWallet
from app.models.sentiment import SentimentScore
from app.models.token import Token, TokenPrice
from app.core.data_manager import DataManager

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of trading signals"""
    EARLY_ACCUMULATION = "early_accumulation"  # Whales buying, low social noise
    MOMENTUM_BUILD = "momentum_build"  # Social sentiment rising, whale positions held
    FOMO_WARNING = "fomo_warning"  # High social buzz, whales selling
    CONTRARIAN_PLAY = "contrarian_play"  # Negative sentiment, whales accumulating
    VOLUME_SPIKE = "volume_spike"  # Unusual volume with whale activity
    TECHNICAL_BREAKOUT = "technical_breakout"  # Technical indicators + whale support


class SignalAction(Enum):
    """Signal actions"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"


@dataclass
class SignalContext:
    """Context data for signal generation"""
    token_address: str
    token_symbol: str
    token_name: str
    current_price: float
    market_cap: float
    volume_24h: float
    volume_change_24h: float
    whale_activity_score: float
    sentiment_score: float
    sentiment_trend: str
    mention_velocity: float
    technical_indicators: Dict
    whale_accumulation_data: Dict
    social_momentum: float


@dataclass
class SignalResult:
    """Generated signal result"""
    signal_type: SignalType
    action: SignalAction
    confidence: float
    risk_score: float
    reasoning: str
    key_factors: List[str]
    risk_factors: List[str]
    target_price: Optional[float]
    stop_loss: Optional[float]
    context: SignalContext


class SignalEngine:
    """Main signal generation engine"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.is_running = False
        
        # Signal thresholds
        self.thresholds = {
            "whale_activity_min": 0.6,
            "sentiment_threshold": 0.5,
            "confidence_min": settings.signal_confidence_threshold,
            "volume_spike_min": 2.0,  # 2x normal volume
            "accumulation_score_min": 0.7,
            "social_momentum_min": 0.3
        }
    
    async def generate_signals(self, hours_back: int = 48) -> List[SignalResult]:
        """Generate trading signals based on whale activity and sentiment"""
        logger.info(f"Generating signals for last {hours_back} hours...")
        
        signals = []
        
        # Get active tokens with recent activity
        active_tokens = await self._get_active_tokens(hours_back)
        
        for token_address in active_tokens:
            try:
                # Build signal context
                context = await self._build_signal_context(token_address, hours_back)
                
                if context:
                    # Generate signals based on context
                    token_signals = await self._analyze_signal_patterns(context)
                    signals.extend(token_signals)
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error generating signals for {token_address}: {e}")
        
        # Sort signals by confidence
        signals.sort(key=lambda x: x.confidence, reverse=True)
        
        # Filter and store high-confidence signals
        high_confidence_signals = [s for s in signals if s.confidence >= self.thresholds["confidence_min"]]
        
        for signal in high_confidence_signals:
            await self._store_signal(signal)
        
        logger.info(f"Generated {len(signals)} signals, {len(high_confidence_signals)} high-confidence")
        return high_confidence_signals
    
    async def _get_active_tokens(self, hours_back: int) -> List[str]:
        """Get tokens with recent whale activity"""
        try:
            async with self.data_manager.get_db_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                
                # Get tokens with significant whale transactions
                stmt = select(WhaleTransaction.token_address).where(
                    and_(
                        WhaleTransaction.timestamp >= cutoff_time,
                        WhaleTransaction.amount_usd > 50000,  # > $50k transactions
                        WhaleTransaction.is_large_transaction == True
                    )
                ).distinct()
                
                result = await session.execute(stmt)
                return [row[0] for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting active tokens: {e}")
            return []
    
    async def _build_signal_context(self, token_address: str, hours_back: int) -> Optional[SignalContext]:
        """Build comprehensive context for signal generation"""
        try:
            # Get token information
            token_info = await self._get_token_info(token_address)
            if not token_info:
                return None
            
            # Get whale activity data
            whale_data = await self._get_whale_activity_data(token_address, hours_back)
            
            # Get sentiment data
            sentiment_data = await self._get_sentiment_data(token_address, hours_back)
            
            # Get technical indicators
            technical_data = await self._get_technical_indicators(token_address)
            
            # Calculate whale activity score
            whale_activity_score = self._calculate_whale_activity_score(whale_data)
            
            # Calculate social momentum
            social_momentum = self._calculate_social_momentum(sentiment_data)
            
            context = SignalContext(
                token_address=token_address,
                token_symbol=token_info["symbol"],
                token_name=token_info["name"],
                current_price=token_info["current_price"],
                market_cap=token_info["market_cap"],
                volume_24h=token_info["volume_24h"],
                volume_change_24h=token_info["volume_change_24h"],
                whale_activity_score=whale_activity_score,
                sentiment_score=sentiment_data.get("sentiment_score", 0.0),
                sentiment_trend=sentiment_data.get("trend", "stable"),
                mention_velocity=sentiment_data.get("mention_velocity", 0.0),
                technical_indicators=technical_data,
                whale_accumulation_data=whale_data,
                social_momentum=social_momentum
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Error building signal context for {token_address}: {e}")
            return None
    
    async def _get_token_info(self, token_address: str) -> Optional[Dict]:
        """Get token information from database"""
        try:
            async with self.data_manager.get_db_session() as session:
                stmt = select(Token).where(Token.address == token_address)
                result = await session.execute(stmt)
                token = result.scalar_one_or_none()
                
                if token:
                    return {
                        "symbol": token.symbol,
                        "name": token.name,
                        "current_price": token.current_price or 0.0,
                        "market_cap": token.market_cap or 0.0,
                        "volume_24h": token.volume_24h or 0.0,
                        "volume_change_24h": token.volume_change_percentage_24h or 0.0
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting token info for {token_address}: {e}")
            return None
    
    async def _get_whale_activity_data(self, token_address: str, hours_back: int) -> Dict:
        """Get whale activity data for a token"""
        try:
            async with self.data_manager.get_db_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                
                # Get whale transactions
                stmt = select(WhaleTransaction).where(
                    and_(
                        WhaleTransaction.token_address == token_address,
                        WhaleTransaction.timestamp >= cutoff_time
                    )
                ).order_by(desc(WhaleTransaction.timestamp))
                
                result = await session.execute(stmt)
                transactions = result.scalars().all()
                
                if not transactions:
                    return {"total_transactions": 0, "accumulation_score": 0.0}
                
                # Analyze whale activity
                buy_transactions = [tx for tx in transactions if tx.transaction_type == "buy"]
                sell_transactions = [tx for tx in transactions if tx.transaction_type == "sell"]
                
                total_buy_volume = sum(tx.amount_usd for tx in buy_transactions)
                total_sell_volume = sum(tx.amount_usd for tx in sell_transactions)
                net_volume = total_buy_volume - total_sell_volume
                
                # Calculate accumulation score
                accumulation_score = self._calculate_accumulation_score(transactions)
                
                # Get unique whale wallets
                unique_wallets = len(set(tx.whale_wallet_id for tx in transactions))
                
                # Calculate urgency trend
                urgency_trend = self._analyze_urgency_trend(transactions)
                
                return {
                    "total_transactions": len(transactions),
                    "buy_transactions": len(buy_transactions),
                    "sell_transactions": len(sell_transactions),
                    "total_buy_volume": total_buy_volume,
                    "total_sell_volume": total_sell_volume,
                    "net_volume": net_volume,
                    "accumulation_score": accumulation_score,
                    "unique_wallets": unique_wallets,
                    "urgency_trend": urgency_trend,
                    "transactions": transactions
                }
                
        except Exception as e:
            logger.error(f"Error getting whale activity data: {e}")
            return {"total_transactions": 0, "accumulation_score": 0.0}
    
    async def _get_sentiment_data(self, token_address: str, hours_back: int) -> Dict:
        """Get sentiment data for a token"""
        try:
            async with self.data_manager.get_db_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                
                # Get latest sentiment scores
                stmt = select(SentimentScore).where(
                    and_(
                        SentimentScore.token_address == token_address,
                        SentimentScore.timestamp >= cutoff_time
                    )
                ).order_by(desc(SentimentScore.timestamp)).limit(10)
                
                result = await session.execute(stmt)
                scores = result.scalars().all()
                
                if not scores:
                    return {"sentiment_score": 0.0, "trend": "stable", "mention_velocity": 0.0}
                
                # Calculate aggregated sentiment
                latest_score = scores[0]
                old_score = scores[-1] if len(scores) > 1 else latest_score
                
                sentiment_change = latest_score.sentiment_score - old_score.sentiment_score
                
                # Determine trend
                if sentiment_change > 0.1:
                    trend = "rising"
                elif sentiment_change < -0.1:
                    trend = "falling"
                else:
                    trend = "stable"
                
                return {
                    "sentiment_score": latest_score.sentiment_score,
                    "sentiment_confidence": latest_score.sentiment_confidence,
                    "trend": trend,
                    "mention_velocity": latest_score.mention_velocity,
                    "mention_count": latest_score.mention_count,
                    "influencer_weight": latest_score.influencer_weighted_score
                }
                
        except Exception as e:
            logger.error(f"Error getting sentiment data: {e}")
            return {"sentiment_score": 0.0, "trend": "stable", "mention_velocity": 0.0}
    
    async def _get_technical_indicators(self, token_address: str) -> Dict:
        """Get technical indicators for a token"""
        try:
            async with self.data_manager.get_db_session() as session:
                # Get latest price data with technical indicators
                stmt = select(TokenPrice).where(
                    TokenPrice.token_address == token_address
                ).order_by(desc(TokenPrice.timestamp)).limit(1)
                
                result = await session.execute(stmt)
                price_data = result.scalar_one_or_none()
                
                if price_data:
                    return {
                        "rsi": price_data.rsi_14,
                        "macd": price_data.macd,
                        "sma_20": price_data.sma_20,
                        "sma_50": price_data.sma_50,
                        "bollinger_upper": price_data.bollinger_upper,
                        "bollinger_lower": price_data.bollinger_lower,
                        "price_change_24h": price_data.price_change_24h,
                        "price_change_7d": price_data.price_change_7d
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"Error getting technical indicators: {e}")
            return {}
    
    def _calculate_whale_activity_score(self, whale_data: Dict) -> float:
        """Calculate whale activity score (0-1)"""
        if whale_data["total_transactions"] == 0:
            return 0.0
        
        # Base score from transaction volume
        volume_score = min(whale_data["total_transactions"] * 0.1, 1.0)
        
        # Accumulation bonus
        accumulation_score = whale_data.get("accumulation_score", 0.0)
        
        # Wallet diversity bonus
        wallet_diversity = min(whale_data.get("unique_wallets", 0) * 0.2, 1.0)
        
        # Net buying pressure
        net_volume = whale_data.get("net_volume", 0)
        buy_pressure_score = 0.5 if net_volume > 0 else 0.0
        
        # Urgency bonus
        urgency_bonus = 0.2 if whale_data.get("urgency_trend") == "rising" else 0.0
        
        total_score = (volume_score * 0.3 + 
                      accumulation_score * 0.3 + 
                      wallet_diversity * 0.2 + 
                      buy_pressure_score * 0.1 + 
                      urgency_bonus)
        
        return min(total_score, 1.0)
    
    def _calculate_social_momentum(self, sentiment_data: Dict) -> float:
        """Calculate social momentum score (0-1)"""
        sentiment_score = abs(sentiment_data.get("sentiment_score", 0.0))
        mention_velocity = sentiment_data.get("mention_velocity", 0.0)
        confidence = sentiment_data.get("sentiment_confidence", 0.0)
        influencer_weight = sentiment_data.get("influencer_weight", 0.0)
        
        # Normalize mention velocity (assume 10 mentions/hour is high)
        velocity_score = min(mention_velocity / 10.0, 1.0)
        
        # Combine factors
        momentum = (sentiment_score * 0.4 + 
                   velocity_score * 0.3 + 
                   confidence * 0.2 + 
                   influencer_weight * 0.1)
        
        return min(momentum, 1.0)
    
    def _calculate_accumulation_score(self, transactions: List) -> float:
        """Calculate accumulation score from transactions"""
        if not transactions:
            return 0.0
        
        buy_txs = [tx for tx in transactions if tx.transaction_type == "buy"]
        sell_txs = [tx for tx in transactions if tx.transaction_type == "sell"]
        
        if not buy_txs:
            return 0.0
        
        # Volume ratio
        buy_volume = sum(tx.amount_usd for tx in buy_txs)
        sell_volume = sum(tx.amount_usd for tx in sell_txs)
        volume_ratio = buy_volume / (sell_volume + 1)
        
        # Transaction ratio
        tx_ratio = len(buy_txs) / (len(sell_txs) + 1)
        
        # Time clustering (multiple buys close together)
        time_clustering = self._calculate_time_clustering(buy_txs)
        
        # Combine factors
        score = (min(volume_ratio / 3, 1.0) * 0.4 + 
                min(tx_ratio / 2, 1.0) * 0.3 + 
                time_clustering * 0.3)
        
        return min(score, 1.0)
    
    def _calculate_time_clustering(self, transactions: List) -> float:
        """Calculate time clustering score for transactions"""
        if len(transactions) < 2:
            return 0.0
        
        sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
        time_diffs = []
        
        for i in range(1, len(sorted_txs)):
            diff = (sorted_txs[i].timestamp - sorted_txs[i-1].timestamp).total_seconds() / 3600
            time_diffs.append(diff)
        
        # Count transactions within 6 hours
        clustered = sum(1 for diff in time_diffs if diff < 6)
        return clustered / len(time_diffs) if time_diffs else 0.0
    
    def _analyze_urgency_trend(self, transactions: List) -> str:
        """Analyze urgency trend in transactions"""
        if len(transactions) < 3:
            return "stable"
        
        sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
        mid_point = len(sorted_txs) // 2
        
        first_half_urgency = sum(tx.urgency_score for tx in sorted_txs[:mid_point]) / mid_point
        second_half_urgency = sum(tx.urgency_score for tx in sorted_txs[mid_point:]) / (len(sorted_txs) - mid_point)
        
        if second_half_urgency > first_half_urgency * 1.2:
            return "rising"
        elif second_half_urgency < first_half_urgency * 0.8:
            return "falling"
        else:
            return "stable"
    
    async def _analyze_signal_patterns(self, context: SignalContext) -> List[SignalResult]:
        """Analyze patterns and generate signals"""
        signals = []
        
        # Pattern 1: Early Accumulation
        if (context.whale_activity_score > self.thresholds["whale_activity_min"] and
            abs(context.sentiment_score) < 0.3 and  # Low social noise
            context.whale_accumulation_data.get("accumulation_score", 0) > self.thresholds["accumulation_score_min"]):
            
            signal = SignalResult(
                signal_type=SignalType.EARLY_ACCUMULATION,
                action=SignalAction.BUY,
                confidence=self._calculate_early_accumulation_confidence(context),
                risk_score=self._calculate_risk_score(context),
                reasoning=f"Whales are accumulating {context.token_symbol} with low social attention. "
                         f"Net buying volume: ${context.whale_accumulation_data.get('net_volume', 0):,.0f}",
                key_factors=[
                    f"High whale activity score: {context.whale_activity_score:.2f}",
                    f"Low social sentiment: {context.sentiment_score:.2f}",
                    f"Strong accumulation pattern: {context.whale_accumulation_data.get('accumulation_score', 0):.2f}"
                ],
                risk_factors=self._identify_risk_factors(context),
                target_price=self._calculate_target_price(context, 1.2),
                stop_loss=self._calculate_stop_loss(context, 0.85),
                context=context
            )
            signals.append(signal)
        
        # Pattern 2: Momentum Build
        if (context.sentiment_trend == "rising" and
            context.sentiment_score > 0.3 and
            context.whale_activity_score > 0.5 and
            context.mention_velocity > 5):  # Increasing mentions
            
            signal = SignalResult(
                signal_type=SignalType.MOMENTUM_BUILD,
                action=SignalAction.BUY,
                confidence=self._calculate_momentum_confidence(context),
                risk_score=self._calculate_risk_score(context),
                reasoning=f"Social momentum building for {context.token_symbol} with whale backing. "
                         f"Sentiment trend: {context.sentiment_trend}, Velocity: {context.mention_velocity:.1f}/hr",
                key_factors=[
                    f"Rising sentiment: {context.sentiment_score:.2f}",
                    f"High mention velocity: {context.mention_velocity:.1f}/hr",
                    f"Whale support: {context.whale_activity_score:.2f}"
                ],
                risk_factors=self._identify_risk_factors(context),
                target_price=self._calculate_target_price(context, 1.5),
                stop_loss=self._calculate_stop_loss(context, 0.9),
                context=context
            )
            signals.append(signal)
        
        # Pattern 3: FOMO Warning
        if (context.sentiment_score > 0.7 and
            context.mention_velocity > 20 and  # High social buzz
            context.whale_accumulation_data.get("net_volume", 0) < 0):  # Whales selling
            
            signal = SignalResult(
                signal_type=SignalType.FOMO_WARNING,
                action=SignalAction.SELL,
                confidence=self._calculate_fomo_confidence(context),
                risk_score=0.8,  # High risk
                reasoning=f"FOMO warning for {context.token_symbol}. High social buzz but whales are selling. "
                         f"Sentiment: {context.sentiment_score:.2f}, Velocity: {context.mention_velocity:.1f}/hr",
                key_factors=[
                    f"Extreme sentiment: {context.sentiment_score:.2f}",
                    f"High social velocity: {context.mention_velocity:.1f}/hr",
                    f"Whales selling: {context.whale_accumulation_data.get('net_volume', 0):,.0f}"
                ],
                risk_factors=["High volatility", "Potential market manipulation", "Overbought conditions"],
                target_price=self._calculate_target_price(context, 0.8),
                stop_loss=self._calculate_stop_loss(context, 1.1),
                context=context
            )
            signals.append(signal)
        
        # Pattern 4: Contrarian Play
        if (context.sentiment_score < -0.3 and
            context.sentiment_trend == "falling" and
            context.whale_activity_score > self.thresholds["whale_activity_min"] and
            context.whale_accumulation_data.get("net_volume", 0) > 100000):  # Significant buying
            
            signal = SignalResult(
                signal_type=SignalType.CONTRARIAN_PLAY,
                action=SignalAction.BUY,
                confidence=self._calculate_contrarian_confidence(context),
                risk_score=0.7,  # Higher risk
                reasoning=f"Contrarian opportunity in {context.token_symbol}. Negative sentiment but whales accumulating. "
                         f"Sentiment: {context.sentiment_score:.2f}, Net buying: ${context.whale_accumulation_data.get('net_volume', 0):,.0f}",
                key_factors=[
                    f"Negative sentiment: {context.sentiment_score:.2f}",
                    f"Whale accumulation: ${context.whale_accumulation_data.get('net_volume', 0):,.0f}",
                    f"Contrarian opportunity"
                ],
                risk_factors=["High risk", "Negative sentiment", "Potential further decline"],
                target_price=self._calculate_target_price(context, 1.3),
                stop_loss=self._calculate_stop_loss(context, 0.8),
                context=context
            )
            signals.append(signal)
        
        return signals
    
    def _calculate_early_accumulation_confidence(self, context: SignalContext) -> float:
        """Calculate confidence for early accumulation signal"""
        base_confidence = 0.6
        
        # Whale activity bonus
        whale_bonus = context.whale_activity_score * 0.3
        
        # Accumulation score bonus
        accumulation_bonus = context.whale_accumulation_data.get("accumulation_score", 0) * 0.2
        
        # Low sentiment bonus (contrarian)
        sentiment_bonus = (0.3 - abs(context.sentiment_score)) * 0.5
        
        confidence = base_confidence + whale_bonus + accumulation_bonus + sentiment_bonus
        return min(confidence, 0.95)
    
    def _calculate_momentum_confidence(self, context: SignalContext) -> float:
        """Calculate confidence for momentum build signal"""
        base_confidence = 0.5
        
        # Sentiment trend bonus
        sentiment_bonus = context.sentiment_score * 0.3
        
        # Velocity bonus
        velocity_bonus = min(context.mention_velocity / 20, 1.0) * 0.2
        
        # Whale support bonus
        whale_bonus = context.whale_activity_score * 0.2
        
        confidence = base_confidence + sentiment_bonus + velocity_bonus + whale_bonus
        return min(confidence, 0.9)
    
    def _calculate_fomo_confidence(self, context: SignalContext) -> float:
        """Calculate confidence for FOMO warning signal"""
        base_confidence = 0.7
        
        # Extreme sentiment bonus
        sentiment_bonus = (context.sentiment_score - 0.5) * 0.5
        
        # High velocity bonus
        velocity_bonus = min((context.mention_velocity - 10) / 20, 1.0) * 0.3
        
        confidence = base_confidence + sentiment_bonus + velocity_bonus
        return min(confidence, 0.95)
    
    def _calculate_contrarian_confidence(self, context: SignalContext) -> float:
        """Calculate confidence for contrarian play signal"""
        base_confidence = 0.4
        
        # Whale accumulation bonus
        whale_bonus = context.whale_activity_score * 0.3
        
        # Volume bonus
        net_volume = context.whale_accumulation_data.get("net_volume", 0)
        volume_bonus = min(net_volume / 1000000, 1.0) * 0.3  # Up to $1M
        
        confidence = base_confidence + whale_bonus + volume_bonus
        return min(confidence, 0.8)
    
    def _calculate_risk_score(self, context: SignalContext) -> float:
        """Calculate risk score for a signal (0-1, higher = riskier)"""
        base_risk = 0.3
        
        # Market cap risk (smaller = riskier)
        if context.market_cap < 10000000:  # < $10M
            market_risk = 0.4
        elif context.market_cap < 100000000:  # < $100M
            market_risk = 0.2
        else:
            market_risk = 0.1
        
        # Volume risk
        volume_risk = 0.2 if context.volume_24h < 1000000 else 0.1
        
        # Sentiment volatility risk
        sentiment_risk = abs(context.sentiment_score) * 0.2
        
        total_risk = base_risk + market_risk + volume_risk + sentiment_risk
        return min(total_risk, 0.9)
    
    def _identify_risk_factors(self, context: SignalContext) -> List[str]:
        """Identify risk factors for a signal"""
        risks = []
        
        if context.market_cap < 10000000:
            risks.append("Small market cap")
        
        if context.volume_24h < 1000000:
            risks.append("Low liquidity")
        
        if abs(context.sentiment_score) > 0.7:
            risks.append("Extreme sentiment")
        
        if context.volume_change_24h > 500:  # >500% volume increase
            risks.append("Volume spike (potential manipulation)")
        
        return risks
    
    def _calculate_target_price(self, context: SignalContext, multiplier: float) -> float:
        """Calculate target price based on current price and multiplier"""
        return context.current_price * multiplier
    
    def _calculate_stop_loss(self, context: SignalContext, multiplier: float) -> float:
        """Calculate stop loss price"""
        return context.current_price * multiplier
    
    async def _store_signal(self, signal: SignalResult):
        """Store generated signal in database"""
        try:
            async with self.data_manager.get_db_session() as session:
                trading_signal = TradingSignal(
                    signal_id=str(uuid.uuid4()),
                    signal_type=signal.signal_type.value,
                    token_address=signal.context.token_address,
                    token_symbol=signal.context.token_symbol,
                    token_name=signal.context.token_name,
                    timestamp=datetime.utcnow(),
                    action=signal.action.value,
                    confidence_score=signal.confidence,
                    risk_score=signal.risk_score,
                    current_price=signal.context.current_price,
                    target_price=signal.target_price,
                    stop_loss_price=signal.stop_loss,
                    price_change_24h=signal.context.volume_change_24h,
                    market_cap=signal.context.market_cap,
                    volume_24h=signal.context.volume_24h,
                    volume_change_24h=signal.context.volume_change_24h,
                    whale_activity_score=signal.context.whale_activity_score,
                    sentiment_score=signal.context.sentiment_score,
                    technical_score=0.0,  # Would be calculated from technical indicators
                    volume_score=0.0,  # Would be calculated from volume analysis
                    whale_transaction_count=signal.context.whale_accumulation_data.get("total_transactions", 0),
                    whale_volume_usd=signal.context.whale_accumulation_data.get("net_volume", 0),
                    whale_accumulation_pattern=signal.context.whale_accumulation_data,
                    sentiment_trend=signal.context.sentiment_trend,
                    mention_velocity=signal.context.mention_velocity,
                    social_momentum=signal.context.social_momentum,
                    reasoning=signal.reasoning,
                    key_factors=signal.key_factors,
                    risk_factors=signal.risk_factors,
                    is_active=True
                )
                
                session.add(trading_signal)
                await session.commit()
                
                logger.info(f"Stored signal: {signal.signal_type.value} for {signal.context.token_symbol} "
                           f"(confidence: {signal.confidence:.2f})")
                
        except Exception as e:
            logger.error(f"Error storing signal: {e}")
    
    async def get_recent_signals(self, hours_back: int = 24, min_confidence: float = 0.7) -> List[Dict]:
        """Get recent high-confidence signals"""
        try:
            async with self.data_manager.get_db_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                
                stmt = select(TradingSignal).where(
                    and_(
                        TradingSignal.timestamp >= cutoff_time,
                        TradingSignal.confidence_score >= min_confidence,
                        TradingSignal.is_active == True
                    )
                ).order_by(desc(TradingSignal.confidence_score))
                
                result = await session.execute(stmt)
                signals = result.scalars().all()
                
                return [self._signal_to_dict(signal) for signal in signals]
                
        except Exception as e:
            logger.error(f"Error getting recent signals: {e}")
            return []
    
    def _signal_to_dict(self, signal: TradingSignal) -> Dict:
        """Convert signal model to dictionary"""
        return {
            "signal_id": signal.signal_id,
            "signal_type": signal.signal_type,
            "token_symbol": signal.token_symbol,
            "action": signal.action,
            "confidence": signal.confidence_score,
            "risk_score": signal.risk_score,
            "current_price": signal.current_price,
            "target_price": signal.target_price,
            "stop_loss": signal.stop_loss_price,
            "timestamp": signal.timestamp.isoformat(),
            "reasoning": signal.reasoning,
            "key_factors": signal.key_factors,
            "risk_factors": signal.risk_factors
        }
    
    async def start_signal_generation(self):
        """Start continuous signal generation"""
        logger.info("Starting signal generation...")
        self.is_running = True
        
        while self.is_running:
            try:
                # Generate signals every hour
                signals = await self.generate_signals(hours_back=48)
                
                if signals:
                    logger.info(f"Generated {len(signals)} new signals")
                
                # Wait 1 hour before next generation
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in signal generation: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def stop_signal_generation(self):
        """Stop signal generation"""
        logger.info("Stopping signal generation...")
        self.is_running = False


