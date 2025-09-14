"""
Complete example showing how to use all free APIs together
This demonstrates the full Smart Money Sentiment Analyzer using only free APIs
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict

from .free_signal_engine import FreeSignalEngine
from .rate_limiter import get_rate_limiter
from .reddit_sentiment import RedditSentimentEngine
from .whale_tracker import FreeWhaleTracker
from .market_data import FreeMarketData
from .google_trends import GoogleTrendsAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmartMoneyAnalyzer:
    """Complete Smart Money Sentiment Analyzer using free APIs"""

    def __init__(self, etherscan_api_key: str):
        """Initialize with your free Etherscan API key"""
        self.signal_engine = FreeSignalEngine(etherscan_api_key)
        self.rate_limiter = get_rate_limiter()

        # Track analysis state
        self.last_analysis_time = None
        self.cached_signals = {}

    async def analyze_portfolio(self, symbols: List[str]) -> Dict:
        """Analyze a portfolio of cryptocurrency symbols"""
        logger.info(f"Starting Smart Money analysis for {len(symbols)} symbols")

        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'analysis_summary': {},
            'signals': [],
            'market_overview': {},
            'recommendations': [],
            'risk_assessment': {}
        }

        try:
            # Get market overview first
            results['market_overview'] = await self.signal_engine.get_market_overview()

            # Generate signals for all symbols
            signals = await self.signal_engine.generate_signals(symbols, hours_back=48)
            results['signals'] = [self._signal_to_dict(signal) for signal in signals]

            # Create analysis summary
            results['analysis_summary'] = self._create_analysis_summary(signals)

            # Generate recommendations
            results['recommendations'] = self._generate_recommendations(signals, results['market_overview'])

            # Assess portfolio risk
            results['risk_assessment'] = self._assess_portfolio_risk(signals)

            # Cache results
            self.cached_signals = {signal.symbol: signal for signal in signals}
            self.last_analysis_time = datetime.utcnow()

            logger.info(f"Analysis complete: {len(signals)} signals generated")

        except Exception as e:
            logger.error(f"Error in portfolio analysis: {e}")
            results['error'] = str(e)

        return results

    async def quick_analysis(self, symbol: str) -> Dict:
        """Quick analysis of a single symbol"""
        logger.info(f"Quick analysis for {symbol}")

        try:
            signal = await self.signal_engine.generate_single_signal(symbol, hours_back=24)

            if not signal:
                return {'error': f'Unable to generate signal for {symbol}'}

            return {
                'symbol': symbol,
                'signal_type': signal.signal_type,
                'strength': round(signal.signal_strength, 3),
                'confidence': round(signal.confidence, 3),
                'risk_score': round(signal.risk_score, 3),
                'reasoning': signal.reasoning,
                'key_factors': {
                    'reddit_sentiment': round(signal.reddit_factor, 3),
                    'whale_activity': round(signal.whale_factor, 3),
                    'market_momentum': round(signal.market_factor, 3),
                    'search_interest': round(signal.search_factor, 3)
                },
                'price_targets': {
                    'entry': signal.entry_price,
                    'target': signal.target_price,
                    'stop_loss': signal.stop_loss
                } if signal.entry_price else None,
                'position_size': f"{signal.position_size_recommendation*100:.1f}%",
                'timestamp': signal.timestamp.isoformat()
            }

        except Exception as e:
            logger.error(f"Error in quick analysis for {symbol}: {e}")
            return {'error': str(e)}

    async def get_trending_opportunities(self, limit: int = 10) -> List[Dict]:
        """Find trending cryptocurrency opportunities"""
        logger.info("Finding trending opportunities")

        try:
            # Get trending tokens from market data
            trending_tokens = await self.signal_engine.market_data.get_trending_tokens()

            opportunities = []

            for token in trending_tokens[:limit]:
                try:
                    # Quick signal analysis for trending token
                    signal = await self.signal_engine.generate_single_signal(token.symbol, hours_back=24)

                    if signal and signal.confidence > 0.3:
                        opportunities.append({
                            'symbol': token.symbol,
                            'name': token.name,
                            'signal_type': signal.signal_type,
                            'strength': round(signal.signal_strength, 3),
                            'confidence': round(signal.confidence, 3),
                            'market_cap_rank': token.market_cap_rank,
                            'trending_score': token.score,
                            'reasoning': signal.reasoning[:100] + '...' if len(signal.reasoning) > 100 else signal.reasoning
                        })

                    # Rate limiting
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error analyzing trending token {token.symbol}: {e}")
                    continue

            # Sort by signal strength and confidence
            opportunities.sort(key=lambda x: (abs(x['strength']), x['confidence']), reverse=True)

            return opportunities[:10]  # Top 10 opportunities

        except Exception as e:
            logger.error(f"Error finding trending opportunities: {e}")
            return []

    async def monitor_alerts(self, symbols: List[str], alert_thresholds: Dict = None) -> List[Dict]:
        """Monitor for alert conditions"""
        if not alert_thresholds:
            alert_thresholds = {
                'strong_buy_threshold': 0.6,
                'strong_sell_threshold': -0.6,
                'confidence_threshold': 0.7,
                'risk_threshold': 0.8
            }

        alerts = []

        for symbol in symbols:
            try:
                signal = await self.signal_engine.generate_single_signal(symbol, hours_back=6)

                if not signal:
                    continue

                # Check for alert conditions
                if (signal.signal_strength >= alert_thresholds['strong_buy_threshold'] and
                    signal.confidence >= alert_thresholds['confidence_threshold']):

                    alerts.append({
                        'type': 'STRONG_BUY_ALERT',
                        'symbol': symbol,
                        'message': f"Strong buy signal for {symbol} (strength: {signal.signal_strength:.2f})",
                        'signal_data': self._signal_to_dict(signal),
                        'urgency': 'HIGH' if signal.confidence > 0.8 else 'MEDIUM'
                    })

                elif (signal.signal_strength <= alert_thresholds['strong_sell_threshold'] and
                      signal.confidence >= alert_thresholds['confidence_threshold']):

                    alerts.append({
                        'type': 'STRONG_SELL_ALERT',
                        'symbol': symbol,
                        'message': f"Strong sell signal for {symbol} (strength: {signal.signal_strength:.2f})",
                        'signal_data': self._signal_to_dict(signal),
                        'urgency': 'HIGH' if signal.confidence > 0.8 else 'MEDIUM'
                    })

                elif signal.risk_score >= alert_thresholds['risk_threshold']:

                    alerts.append({
                        'type': 'HIGH_RISK_ALERT',
                        'symbol': symbol,
                        'message': f"High risk detected for {symbol} (risk: {signal.risk_score:.2f})",
                        'signal_data': self._signal_to_dict(signal),
                        'urgency': 'MEDIUM'
                    })

            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")

        return alerts

    def _signal_to_dict(self, signal) -> Dict:
        """Convert signal object to dictionary"""
        return {
            'symbol': signal.symbol,
            'signal_type': signal.signal_type,
            'strength': round(signal.signal_strength, 3),
            'confidence': round(signal.confidence, 3),
            'risk_score': round(signal.risk_score, 3),
            'factors': {
                'reddit': round(signal.reddit_factor, 3),
                'whale': round(signal.whale_factor, 3),
                'market': round(signal.market_factor, 3),
                'search': round(signal.search_factor, 3)
            },
            'primary_driver': signal.primary_driver,
            'reasoning': signal.reasoning,
            'price_targets': {
                'entry': signal.entry_price,
                'target': signal.target_price,
                'stop_loss': signal.stop_loss
            } if signal.entry_price else None,
            'position_size': f"{signal.position_size_recommendation*100:.1f}%",
            'expires_at': signal.expires_at.isoformat(),
            'timestamp': signal.timestamp.isoformat()
        }

    def _create_analysis_summary(self, signals: List) -> Dict:
        """Create summary of analysis results"""
        if not signals:
            return {'message': 'No actionable signals found'}

        buy_signals = [s for s in signals if s.signal_type in ['BUY', 'STRONG_BUY']]
        sell_signals = [s for s in signals if s.signal_type in ['SELL', 'STRONG_SELL']]

        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        avg_risk = sum(s.risk_score for s in signals) / len(signals)

        return {
            'total_signals': len(signals),
            'buy_signals': len(buy_signals),
            'sell_signals': len(sell_signals),
            'hold_signals': len(signals) - len(buy_signals) - len(sell_signals),
            'average_confidence': round(avg_confidence, 3),
            'average_risk': round(avg_risk, 3),
            'strongest_buy': max(buy_signals, key=lambda x: x.signal_strength).symbol if buy_signals else None,
            'strongest_sell': min(sell_signals, key=lambda x: x.signal_strength).symbol if sell_signals else None,
            'highest_confidence': max(signals, key=lambda x: x.confidence).symbol,
            'market_sentiment': 'BULLISH' if len(buy_signals) > len(sell_signals) else 'BEARISH' if len(sell_signals) > len(buy_signals) else 'NEUTRAL'
        }

    def _generate_recommendations(self, signals: List, market_overview: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if not signals:
            return ["No clear signals - consider waiting for better opportunities"]

        # Market-wide recommendations
        fear_greed = market_overview.get('fear_greed_index', 50)
        if fear_greed < 25:
            recommendations.append("Extreme fear detected - potential buying opportunity for strong projects")
        elif fear_greed > 75:
            recommendations.append("Extreme greed detected - consider taking profits and reducing exposure")

        # Signal-based recommendations
        high_confidence_buys = [s for s in signals if s.signal_type in ['BUY', 'STRONG_BUY'] and s.confidence > 0.7]
        high_confidence_sells = [s for s in signals if s.signal_type in ['SELL', 'STRONG_SELL'] and s.confidence > 0.7]

        if high_confidence_buys:
            top_buy = max(high_confidence_buys, key=lambda x: x.confidence)
            recommendations.append(f"Strong buy opportunity: {top_buy.symbol} (confidence: {top_buy.confidence:.2f})")

        if high_confidence_sells:
            top_sell = max(high_confidence_sells, key=lambda x: x.confidence)
            recommendations.append(f"Consider selling: {top_sell.symbol} (confidence: {top_sell.confidence:.2f})")

        # Risk management
        high_risk_signals = [s for s in signals if s.risk_score > 0.7]
        if high_risk_signals:
            recommendations.append(f"High risk detected in {len(high_risk_signals)} signals - use smaller position sizes")

        # Portfolio diversification
        recommendations.append("Diversify across multiple signals to reduce risk")
        recommendations.append("Never invest more than you can afford to lose")

        return recommendations

    def _assess_portfolio_risk(self, signals: List) -> Dict:
        """Assess overall portfolio risk"""
        if not signals:
            return {'overall_risk': 'UNKNOWN', 'message': 'No signals to assess'}

        avg_risk = sum(s.risk_score for s in signals) / len(signals)
        high_risk_count = sum(1 for s in signals if s.risk_score > 0.7)
        low_confidence_count = sum(1 for s in signals if s.confidence < 0.5)

        # Determine risk level
        if avg_risk > 0.7 or high_risk_count > len(signals) * 0.5:
            risk_level = 'HIGH'
        elif avg_risk > 0.5 or high_risk_count > len(signals) * 0.3:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        return {
            'overall_risk': risk_level,
            'average_risk_score': round(avg_risk, 3),
            'high_risk_signals': high_risk_count,
            'low_confidence_signals': low_confidence_count,
            'risk_factors': [
                'High volatility detected' if avg_risk > 0.6 else None,
                'Multiple conflicting signals' if low_confidence_count > len(signals) * 0.4 else None,
                'Limited data quality' if low_confidence_count > len(signals) * 0.6 else None
            ],
            'recommendations': [
                'Use smaller position sizes' if risk_level == 'HIGH' else None,
                'Consider dollar-cost averaging' if risk_level != 'LOW' else None,
                'Set stop-losses for all positions' if risk_level != 'LOW' else None
            ]
        }

    def get_system_status(self) -> Dict:
        """Get system status and health"""
        rate_limiter_status = self.rate_limiter.get_health_status()
        usage_stats = self.rate_limiter.get_usage_statistics()

        return {
            'system_health': rate_limiter_status['overall_health'],
            'last_analysis': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            'cached_signals': len(self.cached_signals),
            'api_status': rate_limiter_status['api_health'],
            'usage_summary': {
                'total_api_calls': usage_stats['total_calls_all_apis'],
                'successful_calls': usage_stats['successful_calls_all_apis'],
                'failed_calls': usage_stats['failed_calls_all_apis']
            }
        }


async def main():
    """Example usage of the complete Smart Money Analyzer"""
    # Initialize with your free Etherscan API key
    # Get one free at: https://etherscan.io/apis
    ETHERSCAN_API_KEY = "YourFreeEtherscanAPIKeyHere"

    analyzer = SmartMoneyAnalyzer(ETHERSCAN_API_KEY)

    # Example 1: Analyze a portfolio
    print("=== Portfolio Analysis ===")
    portfolio = ["BTC", "ETH", "ADA", "SOL", "MATIC"]
    results = await analyzer.analyze_portfolio(portfolio)

    print(f"Analysis Summary:")
    print(f"- Total Signals: {results['analysis_summary'].get('total_signals', 0)}")
    print(f"- Buy Signals: {results['analysis_summary'].get('buy_signals', 0)}")
    print(f"- Sell Signals: {results['analysis_summary'].get('sell_signals', 0)}")
    print(f"- Market Sentiment: {results['analysis_summary'].get('market_sentiment', 'UNKNOWN')}")

    print(f"\nTop Recommendations:")
    for rec in results['recommendations'][:3]:
        print(f"- {rec}")

    # Example 2: Quick analysis of a single token
    print("\n=== Quick Analysis ===")
    btc_analysis = await analyzer.quick_analysis("BTC")
    print(f"BTC Signal: {btc_analysis.get('signal_type', 'UNKNOWN')}")
    print(f"Confidence: {btc_analysis.get('confidence', 0):.2f}")
    print(f"Reasoning: {btc_analysis.get('reasoning', 'N/A')}")

    # Example 3: Find trending opportunities
    print("\n=== Trending Opportunities ===")
    trending = await analyzer.get_trending_opportunities(5)
    for opp in trending[:3]:
        print(f"- {opp['symbol']}: {opp['signal_type']} (confidence: {opp['confidence']:.2f})")

    # Example 4: Monitor for alerts
    print("\n=== Alert Monitoring ===")
    alerts = await analyzer.monitor_alerts(portfolio)
    if alerts:
        for alert in alerts:
            print(f"- {alert['type']}: {alert['message']}")
    else:
        print("- No alerts detected")

    # Example 5: System status
    print("\n=== System Status ===")
    status = analyzer.get_system_status()
    print(f"System Health: {status['system_health']}")
    print(f"Total API Calls: {status['usage_summary']['total_api_calls']}")
    print(f"Success Rate: {(status['usage_summary']['successful_calls'] / max(status['usage_summary']['total_api_calls'], 1) * 100):.1f}%")


if __name__ == "__main__":
    print("🚀 Smart Money Social Sentiment Analyzer - Free APIs Edition")
    print("=" * 60)
    asyncio.run(main())