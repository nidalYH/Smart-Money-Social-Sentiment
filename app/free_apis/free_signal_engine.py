"""
Free Signal Engine - Combines all free data sources into trading signals
Uses Reddit sentiment, whale tracking, market data, and Google Trends
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json

from .reddit_sentiment import RedditSentimentEngine, RedditSentimentResult
from .whale_tracker import FreeWhaleTracker, WhaleAnalysisResult
from .market_data import FreeMarketData, TokenData, MarketMetrics
from .google_trends import GoogleTrendsAnalyzer, TrendsData, SearchMomentum

logger = logging.getLogger(__name__)


@dataclass
class SignalData:
    """Combined signal data from all sources"""
    symbol: str
    timestamp: datetime

    # Reddit data
    reddit_sentiment: float  # -1 to 1
    reddit_confidence: float  # 0 to 1
    reddit_mentions: int
    reddit_engagement: float

    # Whale data
    whale_activity_score: float  # 0 to 1
    accumulation_score: float  # -1 to 1 (negative = distribution)
    whale_confidence: float

    # Market data
    price_momentum: float  # -1 to 1
    volume_score: float  # 0 to 1
    market_position_score: float  # 0 to 1

    # Search data
    search_momentum: float  # -1 to 1
    search_breakout_probability: float  # 0 to 1

    # Combined metrics
    overall_signal_strength: float  # -1 to 1
    signal_confidence: float  # 0 to 1
    risk_score: float  # 0 to 1


@dataclass
class TradingSignal:
    """Final trading signal with actionable information"""
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD', 'WATCH'
    signal_strength: float  # -1 to 1
    confidence: float  # 0 to 1
    risk_score: float  # 0 to 1

    # Signal components
    reddit_factor: float
    whale_factor: float
    market_factor: float
    search_factor: float

    # Key insights
    primary_driver: str  # Which factor is driving the signal
    supporting_factors: List[str]
    risk_factors: List[str]
    reasoning: str

    # Actionable data
    entry_price: Optional[float]
    target_price: Optional[float]
    stop_loss: Optional[float]
    position_size_recommendation: float  # 0 to 1

    # Metadata
    timestamp: datetime
    expires_at: datetime
    signal_id: str


class FreeSignalEngine:
    """Main signal engine combining all free data sources"""

    def __init__(self, etherscan_api_key: str):
        # Initialize all engines
        self.reddit_engine = RedditSentimentEngine()
        self.whale_tracker = FreeWhaleTracker(etherscan_api_key)
        self.market_data = FreeMarketData()
        self.trends_analyzer = GoogleTrendsAnalyzer()

        # Signal thresholds
        self.signal_thresholds = {
            'strong_buy': 0.6,
            'buy': 0.3,
            'sell': -0.3,
            'strong_sell': -0.6,
            'min_confidence': 0.4,
            'min_data_quality': 0.3
        }

        # Component weights for signal calculation
        self.signal_weights = {
            'reddit': 0.25,
            'whale': 0.35,
            'market': 0.25,
            'search': 0.15
        }

    async def generate_signals(self, symbols: List[str], hours_back: int = 24) -> List[TradingSignal]:
        """Generate trading signals for multiple symbols"""
        logger.info(f"Generating signals for {len(symbols)} symbols")

        signals = []

        for symbol in symbols:
            try:
                signal = await self.generate_single_signal(symbol, hours_back)
                if signal and signal.confidence >= self.signal_thresholds['min_confidence']:
                    signals.append(signal)

                # Rate limiting between symbols
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error generating signal for {symbol}: {e}")

        # Sort by signal strength and confidence
        signals.sort(key=lambda x: (abs(x.signal_strength), x.confidence), reverse=True)

        logger.info(f"Generated {len(signals)} actionable signals")
        return signals

    async def generate_single_signal(self, symbol: str, hours_back: int = 24) -> Optional[TradingSignal]:
        """Generate a single trading signal for a symbol"""
        logger.info(f"Generating signal for {symbol}")

        try:
            # Gather data from all sources
            signal_data = await self._collect_signal_data(symbol, hours_back)

            if not signal_data or not self._validate_data_quality(signal_data):
                logger.warning(f"Insufficient data quality for {symbol}")
                return None

            # Calculate component scores
            reddit_score = self._calculate_reddit_score(signal_data)
            whale_score = self._calculate_whale_score(signal_data)
            market_score = self._calculate_market_score(signal_data)
            search_score = self._calculate_search_score(signal_data)

            # Calculate overall signal
            overall_strength = (
                reddit_score * self.signal_weights['reddit'] +
                whale_score * self.signal_weights['whale'] +
                market_score * self.signal_weights['market'] +
                search_score * self.signal_weights['search']
            )

            # Calculate confidence
            confidence = self._calculate_signal_confidence(signal_data, overall_strength)

            # Calculate risk
            risk_score = self._calculate_risk_score(signal_data)

            # Determine signal type
            signal_type = self._determine_signal_type(overall_strength, confidence, risk_score)

            # Generate reasoning and insights
            reasoning, primary_driver, supporting_factors, risk_factors = self._generate_signal_insights(
                signal_data, reddit_score, whale_score, market_score, search_score
            )

            # Calculate price targets (if market data available)
            entry_price, target_price, stop_loss = await self._calculate_price_targets(
                symbol, overall_strength, risk_score
            )

            # Calculate position size recommendation
            position_size = self._calculate_position_size(confidence, risk_score)

            # Create trading signal
            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                signal_strength=overall_strength,
                confidence=confidence,
                risk_score=risk_score,
                reddit_factor=reddit_score,
                whale_factor=whale_score,
                market_factor=market_score,
                search_factor=search_score,
                primary_driver=primary_driver,
                supporting_factors=supporting_factors,
                risk_factors=risk_factors,
                reasoning=reasoning,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                position_size_recommendation=position_size,
                timestamp=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=6),  # Signals expire in 6 hours
                signal_id=f"{symbol}_{int(datetime.utcnow().timestamp())}"
            )

            return signal

        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return None

    async def _collect_signal_data(self, symbol: str, hours_back: int) -> Optional[SignalData]:
        """Collect data from all sources"""
        logger.info(f"Collecting data for {symbol}")

        try:
            # Run all data collection concurrently
            reddit_task = self.reddit_engine.get_reddit_sentiment(symbol, hours_back)
            market_task = self.market_data.get_token_data(symbol)
            trends_task = self.trends_analyzer.get_search_interest(symbol)

            # Get whale data (requires token address)
            token_address = None
            market_data = await market_task
            if market_data:
                token_address = await self.market_data.get_token_contract_address(symbol)

            whale_task = self.whale_tracker.analyze_whale_activity(
                symbol, token_address, hours_back
            ) if token_address else None

            # Wait for all data
            reddit_data = await reddit_task
            trends_data = await trends_task

            whale_data = await whale_task if whale_task else None

            # Get search momentum
            search_momentum = await self.trends_analyzer.analyze_search_momentum(symbol) if trends_data else None

            # Create combined signal data
            signal_data = SignalData(
                symbol=symbol,
                timestamp=datetime.utcnow(),

                # Reddit data
                reddit_sentiment=reddit_data.overall_sentiment if reddit_data else 0.0,
                reddit_confidence=reddit_data.confidence if reddit_data else 0.0,
                reddit_mentions=reddit_data.total_mentions if reddit_data else 0,
                reddit_engagement=reddit_data.engagement_score if reddit_data else 0.0,

                # Whale data
                whale_activity_score=whale_data.whale_activity_score if whale_data else 0.0,
                accumulation_score=whale_data.accumulation_score if whale_data else 0.0,
                whale_confidence=whale_data.confidence if whale_data else 0.0,

                # Market data
                price_momentum=self._calculate_price_momentum(market_data) if market_data else 0.0,
                volume_score=self._calculate_volume_score(market_data) if market_data else 0.0,
                market_position_score=self._calculate_market_position_score(market_data) if market_data else 0.0,

                # Search data
                search_momentum=search_momentum.momentum_7d if search_momentum else 0.0,
                search_breakout_probability=search_momentum.breakout_probability if search_momentum else 0.0,

                # Will be calculated
                overall_signal_strength=0.0,
                signal_confidence=0.0,
                risk_score=0.0
            )

            return signal_data

        except Exception as e:
            logger.error(f"Error collecting signal data for {symbol}: {e}")
            return None

    def _calculate_reddit_score(self, data: SignalData) -> float:
        """Calculate Reddit sentiment component score"""
        if data.reddit_confidence < 0.2:
            return 0.0

        # Base sentiment with confidence weighting
        base_score = data.reddit_sentiment * data.reddit_confidence

        # Engagement bonus
        engagement_bonus = min(data.reddit_engagement * 0.2, 0.2)

        # Mention volume bonus
        mention_bonus = min(data.reddit_mentions / 100.0 * 0.1, 0.1)

        total_score = base_score + engagement_bonus + mention_bonus

        return max(-1.0, min(1.0, total_score))

    def _calculate_whale_score(self, data: SignalData) -> float:
        """Calculate whale activity component score"""
        if data.whale_confidence < 0.2:
            return 0.0

        # Activity score weighted by confidence
        activity_component = data.whale_activity_score * data.whale_confidence

        # Accumulation score (buying vs selling pressure)
        accumulation_component = data.accumulation_score

        # Combined with more weight on accumulation
        total_score = activity_component * 0.4 + accumulation_component * 0.6

        return max(-1.0, min(1.0, total_score))

    def _calculate_market_score(self, data: SignalData) -> float:
        """Calculate market data component score"""
        # Price momentum is the primary factor
        momentum_score = data.price_momentum * 0.5

        # Volume support
        volume_score = data.volume_score * 0.3

        # Market position (rank, distance from ATH, etc.)
        position_score = data.market_position_score * 0.2

        total_score = momentum_score + volume_score + position_score

        return max(-1.0, min(1.0, total_score))

    def _calculate_search_score(self, data: SignalData) -> float:
        """Calculate Google Trends component score"""
        # Search momentum
        momentum_component = data.search_momentum * 0.6

        # Breakout probability
        breakout_component = data.search_breakout_probability * 0.4

        total_score = momentum_component + breakout_component

        return max(-1.0, min(1.0, total_score))

    def _calculate_signal_confidence(self, data: SignalData, overall_strength: float) -> float:
        """Calculate overall signal confidence"""
        # Base confidence from individual data sources
        reddit_conf = data.reddit_confidence if data.reddit_mentions > 5 else 0.0
        whale_conf = data.whale_confidence
        search_conf = 0.5 if data.search_momentum != 0 else 0.0  # Search data is less reliable

        # Average confidence weighted by component weights
        avg_confidence = (
            reddit_conf * self.signal_weights['reddit'] +
            whale_conf * self.signal_weights['whale'] +
            0.7 * self.signal_weights['market'] +  # Market data is generally reliable
            search_conf * self.signal_weights['search']
        )

        # Signal strength bonus (stronger signals are more reliable)
        strength_bonus = min(abs(overall_strength) * 0.2, 0.2)

        # Multi-source confirmation bonus
        active_sources = sum([
            1 if data.reddit_confidence > 0.2 else 0,
            1 if data.whale_confidence > 0.2 else 0,
            1 if data.price_momentum != 0 else 0,
            1 if data.search_momentum != 0 else 0
        ])

        confirmation_bonus = (active_sources - 1) * 0.1  # Bonus for multiple sources

        total_confidence = avg_confidence + strength_bonus + confirmation_bonus

        return max(0.0, min(0.95, total_confidence))  # Cap at 95%

    def _calculate_risk_score(self, data: SignalData) -> float:
        """Calculate risk score for the signal"""
        risk_score = 0.3  # Base risk

        # High volatility risk (from market data)
        if abs(data.price_momentum) > 0.7:
            risk_score += 0.2

        # Low confidence risk
        if data.reddit_confidence < 0.3 and data.whale_confidence < 0.3:
            risk_score += 0.3

        # Conflicting signals risk
        signals = [data.reddit_sentiment, data.accumulation_score, data.price_momentum, data.search_momentum]
        positive_signals = sum(1 for s in signals if s > 0.1)
        negative_signals = sum(1 for s in signals if s < -0.1)

        if positive_signals > 0 and negative_signals > 0:
            risk_score += 0.2  # Conflicting signals

        # Low volume risk (from market data)
        if data.volume_score < 0.3:
            risk_score += 0.1

        return min(risk_score, 0.9)  # Cap at 90%

    def _determine_signal_type(self, strength: float, confidence: float, risk: float) -> str:
        """Determine the signal type based on strength, confidence, and risk"""
        # Require minimum confidence
        if confidence < self.signal_thresholds['min_confidence']:
            return 'HOLD'

        # High risk = more conservative signals
        if risk > 0.7:
            if strength > self.signal_thresholds['strong_buy']:
                return 'BUY'
            elif strength < self.signal_thresholds['strong_sell']:
                return 'SELL'
            else:
                return 'HOLD'

        # Normal risk levels
        if strength >= self.signal_thresholds['strong_buy']:
            return 'STRONG_BUY'
        elif strength >= self.signal_thresholds['buy']:
            return 'BUY'
        elif strength <= self.signal_thresholds['strong_sell']:
            return 'STRONG_SELL'
        elif strength <= self.signal_thresholds['sell']:
            return 'SELL'
        else:
            return 'HOLD'

    def _generate_signal_insights(self, data: SignalData, reddit_score: float,
                                whale_score: float, market_score: float,
                                search_score: float) -> Tuple[str, str, List[str], List[str]]:
        """Generate human-readable insights about the signal"""

        # Find primary driver
        scores = {
            'Reddit Sentiment': reddit_score,
            'Whale Activity': whale_score,
            'Market Data': market_score,
            'Search Interest': search_score
        }

        primary_driver = max(scores.keys(), key=lambda k: abs(scores[k]))

        # Find supporting factors
        supporting_factors = []
        risk_factors = []

        # Reddit analysis
        if abs(reddit_score) > 0.2:
            if reddit_score > 0:
                supporting_factors.append(f"Positive Reddit sentiment ({data.reddit_sentiment:.2f})")
            else:
                risk_factors.append(f"Negative Reddit sentiment ({data.reddit_sentiment:.2f})")

        # Whale analysis
        if abs(whale_score) > 0.2:
            if whale_score > 0:
                supporting_factors.append(f"Whale accumulation detected")
            else:
                risk_factors.append(f"Whale distribution detected")

        # Market analysis
        if abs(market_score) > 0.2:
            if market_score > 0:
                supporting_factors.append(f"Positive price momentum")
            else:
                risk_factors.append(f"Negative price momentum")

        # Search analysis
        if abs(search_score) > 0.2:
            if search_score > 0:
                supporting_factors.append(f"Rising search interest")
            else:
                risk_factors.append(f"Declining search interest")

        # Generate reasoning
        signal_direction = "bullish" if reddit_score + whale_score + market_score + search_score > 0 else "bearish"

        reasoning = (f"{data.symbol} shows {signal_direction} signals primarily driven by {primary_driver}. "
                   f"Key supporting factors: {', '.join(supporting_factors[:3]) if supporting_factors else 'None'}.")

        if risk_factors:
            reasoning += f" Risk factors include: {', '.join(risk_factors[:2])}."

        return reasoning, primary_driver, supporting_factors, risk_factors

    async def _calculate_price_targets(self, symbol: str, signal_strength: float,
                                     risk_score: float) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Calculate price targets based on signal strength and risk"""
        try:
            token_data = await self.market_data.get_token_data(symbol)
            if not token_data:
                return None, None, None

            current_price = token_data.current_price

            # Calculate targets based on signal strength and historical volatility
            volatility = abs(token_data.price_change_percentage_24h) / 100.0
            base_move = max(volatility, 0.05)  # Minimum 5% move

            # Scale move by signal strength
            expected_move = base_move * abs(signal_strength) * 2

            # Adjust for risk (higher risk = smaller targets)
            risk_adjustment = 1.0 - (risk_score * 0.3)
            expected_move *= risk_adjustment

            if signal_strength > 0:  # Bullish
                target_price = current_price * (1 + expected_move)
                stop_loss = current_price * (1 - expected_move * 0.5)
            else:  # Bearish
                target_price = current_price * (1 - expected_move)
                stop_loss = current_price * (1 + expected_move * 0.5)

            return current_price, target_price, stop_loss

        except Exception as e:
            logger.error(f"Error calculating price targets for {symbol}: {e}")
            return None, None, None

    def _calculate_position_size(self, confidence: float, risk_score: float) -> float:
        """Calculate recommended position size (0 to 1)"""
        # Base position size on confidence
        base_size = confidence

        # Reduce for high risk
        risk_adjustment = 1.0 - (risk_score * 0.5)

        position_size = base_size * risk_adjustment

        # Clamp to reasonable range
        return max(0.05, min(0.25, position_size))  # 5% to 25% max

    def _validate_data_quality(self, data: SignalData) -> bool:
        """Validate that we have sufficient data quality"""
        # Check for minimum data requirements
        has_reddit_data = data.reddit_confidence > 0.1 and data.reddit_mentions > 2
        has_whale_data = data.whale_confidence > 0.1
        has_market_data = data.price_momentum != 0 or data.volume_score > 0

        # Need at least 2 sources with decent data
        active_sources = sum([has_reddit_data, has_whale_data, has_market_data])

        return active_sources >= 2

    def _calculate_price_momentum(self, token_data: TokenData) -> float:
        """Calculate price momentum from token data"""
        if not token_data:
            return 0.0

        # Combine 24h and 7d momentum
        momentum_24h = token_data.price_change_percentage_24h / 100.0
        momentum_7d = token_data.price_change_percentage_7d / 100.0

        # Weight recent momentum more heavily
        combined_momentum = momentum_24h * 0.7 + momentum_7d * 0.3

        return max(-1.0, min(1.0, combined_momentum * 2))  # Scale to -1 to 1

    def _calculate_volume_score(self, token_data: TokenData) -> float:
        """Calculate volume score from token data"""
        if not token_data or token_data.market_cap <= 0:
            return 0.0

        # Volume to market cap ratio
        volume_ratio = token_data.volume_24h / token_data.market_cap

        # Normalize (10% ratio = score of 1.0)
        volume_score = min(volume_ratio / 0.1, 1.0)

        return volume_score

    def _calculate_market_position_score(self, token_data: TokenData) -> float:
        """Calculate market position score"""
        if not token_data:
            return 0.0

        # Market cap rank score (lower rank = better)
        rank_score = 0.0
        if token_data.market_cap_rank > 0:
            rank_score = max(0, (1000 - token_data.market_cap_rank) / 1000)

        # Distance from ATH score
        ath_score = max(0, (token_data.ath_change_percentage + 90) / 90)

        # Combined score
        position_score = rank_score * 0.6 + ath_score * 0.4

        return min(position_score, 1.0)

    async def get_market_overview(self) -> Dict:
        """Get overall market overview and sentiment"""
        try:
            # Get global market metrics
            market_metrics = await self.market_data.get_market_metrics()

            # Get Fear & Greed Index
            fear_greed = await self.market_data.get_fear_greed_index()

            # Get trending tokens
            trending = await self.market_data.get_trending_tokens()

            # Get Bitcoin trends as market indicator
            btc_trends = await self.trends_analyzer.get_search_interest("Bitcoin")

            overview = {
                'timestamp': datetime.utcnow().isoformat(),
                'market_cap': market_metrics.total_market_cap if market_metrics else 0,
                'btc_dominance': market_metrics.bitcoin_dominance if market_metrics else 0,
                'fear_greed_index': fear_greed['value'] if fear_greed else 50,
                'fear_greed_classification': fear_greed['value_classification'] if fear_greed else 'Neutral',
                'trending_tokens': [t.symbol for t in trending[:5]] if trending else [],
                'btc_search_trend': btc_trends.trend_direction if btc_trends else 'stable',
                'market_sentiment': 'neutral'  # Would be calculated from aggregated data
            }

            return overview

        except Exception as e:
            logger.error(f"Error getting market overview: {e}")
            return {'error': str(e)}


# Example usage
async def main():
    """Example usage of the free signal engine"""
    # You need an Etherscan API key (free from etherscan.io)
    api_key = "YourFreeEtherscanAPIKey"

    engine = FreeSignalEngine(api_key)

    # Generate signals for popular cryptocurrencies
    symbols = ["BTC", "ETH", "ADA", "SOL", "DOGE"]

    signals = await engine.generate_signals(symbols, hours_back=48)

    print(f"Generated {len(signals)} signals:")
    for signal in signals:
        print(f"\n{signal.symbol}: {signal.signal_type}")
        print(f"  Strength: {signal.signal_strength:.2f}")
        print(f"  Confidence: {signal.confidence:.2f}")
        print(f"  Risk: {signal.risk_score:.2f}")
        print(f"  Primary Driver: {signal.primary_driver}")
        print(f"  Reasoning: {signal.reasoning}")

        if signal.target_price:
            print(f"  Entry: ${signal.entry_price:.4f}")
            print(f"  Target: ${signal.target_price:.4f}")
            print(f"  Stop Loss: ${signal.stop_loss:.4f}")


if __name__ == "__main__":
    asyncio.run(main())