"""
Google Trends integration for cryptocurrency search interest analysis
Uses pytrends library to access Google Trends data for free
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
from pytrends.request import TrendReq
import time

logger = logging.getLogger(__name__)


@dataclass
class TrendsData:
    """Google Trends data structure"""
    keyword: str
    timeframe: str
    region: str
    interest_over_time: Dict[str, int]  # date -> search interest (0-100)
    current_interest: int
    peak_interest: int
    peak_date: datetime
    average_interest: float
    trend_direction: str  # 'rising', 'falling', 'stable'
    trend_strength: float  # 0-1


@dataclass
class RelatedQueries:
    """Related search queries data"""
    keyword: str
    top_queries: List[Dict[str, str]]  # [{'query': str, 'value': str}]
    rising_queries: List[Dict[str, str]]
    breakout_queries: List[str]  # Queries with >5000% increase


@dataclass
class RegionalInterest:
    """Regional interest data"""
    keyword: str
    region_data: Dict[str, int]  # region -> interest level
    top_regions: List[Tuple[str, int]]
    concentration_score: float  # How concentrated interest is geographically


@dataclass
class SearchMomentum:
    """Search momentum analysis"""
    keyword: str
    momentum_1d: float  # -1 to 1
    momentum_7d: float
    momentum_30d: float
    acceleration: float  # Rate of change in momentum
    breakout_probability: float  # 0-1 chance of search breakout
    seasonal_factor: float  # Seasonal adjustment


class GoogleTrendsAnalyzer:
    """Free Google Trends analysis using pytrends"""

    def __init__(self):
        self.pytrends = TrendReq(hl='en-US', tz=360)
        self.request_delay = 2.0  # 2 seconds between requests to be respectful
        self.last_request_time = 0

        # Crypto-related keywords for context
        self.crypto_context_keywords = [
            'cryptocurrency', 'bitcoin', 'crypto', 'blockchain'
        ]

    async def get_search_interest(self, keyword: str, timeframe: str = 'today 90-d',
                                region: str = '', category: int = 0) -> Optional[TrendsData]:
        """
        Get search interest data for a cryptocurrency keyword

        timeframe options:
        - 'today 1-m': Past month
        - 'today 3-m': Past 3 months
        - 'today 12-m': Past year
        - 'today 5-y': Past 5 years
        """
        logger.info(f"Getting search interest for {keyword} ({timeframe})")

        try:
            await self._respect_rate_limit()

            # Build interest over time
            self.pytrends.build_payload([keyword], cat=category, timeframe=timeframe, geo=region)
            interest_data = self.pytrends.interest_over_time()

            if interest_data.empty or keyword not in interest_data.columns:
                return None

            # Process data
            interest_series = interest_data[keyword]
            interest_dict = interest_series.to_dict()

            # Convert datetime keys to strings
            interest_over_time = {
                date.strftime('%Y-%m-%d'): int(value)
                for date, value in interest_dict.items()
            }

            current_interest = int(interest_series.iloc[-1])
            peak_interest = int(interest_series.max())
            peak_date = interest_series.idxmax()
            average_interest = float(interest_series.mean())

            # Calculate trend
            trend_direction, trend_strength = self._calculate_trend(interest_series)

            trends_data = TrendsData(
                keyword=keyword,
                timeframe=timeframe,
                region=region or 'Global',
                interest_over_time=interest_over_time,
                current_interest=current_interest,
                peak_interest=peak_interest,
                peak_date=peak_date,
                average_interest=average_interest,
                trend_direction=trend_direction,
                trend_strength=trend_strength
            )

            return trends_data

        except Exception as e:
            logger.error(f"Error getting search interest for {keyword}: {e}")
            return None

    async def get_related_queries(self, keyword: str, timeframe: str = 'today 90-d') -> Optional[RelatedQueries]:
        """Get related search queries"""
        logger.info(f"Getting related queries for {keyword}")

        try:
            await self._respect_rate_limit()

            self.pytrends.build_payload([keyword], timeframe=timeframe)
            related_data = self.pytrends.related_queries()

            if not related_data or keyword not in related_data:
                return None

            keyword_data = related_data[keyword]

            # Process top queries
            top_queries = []
            if keyword_data['top'] is not None:
                top_df = keyword_data['top']
                top_queries = [
                    {'query': row['query'], 'value': str(row['value'])}
                    for _, row in top_df.head(10).iterrows()
                ]

            # Process rising queries
            rising_queries = []
            breakout_queries = []
            if keyword_data['rising'] is not None:
                rising_df = keyword_data['rising']
                for _, row in rising_df.head(20).iterrows():
                    query_data = {'query': row['query'], 'value': str(row['value'])}
                    rising_queries.append(query_data)

                    # Check for breakout queries (>5000% increase)
                    if 'Breakout' in str(row['value']) or '+' in str(row['value']):
                        if '+5000%' in str(row['value']) or 'Breakout' in str(row['value']):
                            breakout_queries.append(row['query'])

            return RelatedQueries(
                keyword=keyword,
                top_queries=top_queries,
                rising_queries=rising_queries,
                breakout_queries=breakout_queries
            )

        except Exception as e:
            logger.error(f"Error getting related queries for {keyword}: {e}")
            return None

    async def get_regional_interest(self, keyword: str, timeframe: str = 'today 90-d') -> Optional[RegionalInterest]:
        """Get regional interest breakdown"""
        logger.info(f"Getting regional interest for {keyword}")

        try:
            await self._respect_rate_limit()

            self.pytrends.build_payload([keyword], timeframe=timeframe)
            regional_data = self.pytrends.interest_by_region()

            if regional_data.empty or keyword not in regional_data.columns:
                return None

            region_series = regional_data[keyword]
            region_dict = region_series.to_dict()

            # Get top regions
            top_regions = region_series.nlargest(10).items()
            top_regions = [(region, int(interest)) for region, interest in top_regions if interest > 0]

            # Calculate concentration score
            total_interest = region_series.sum()
            top_5_interest = region_series.nlargest(5).sum()
            concentration_score = float(top_5_interest / max(total_interest, 1))

            return RegionalInterest(
                keyword=keyword,
                region_data={region: int(interest) for region, interest in region_dict.items() if interest > 0},
                top_regions=top_regions,
                concentration_score=concentration_score
            )

        except Exception as e:
            logger.error(f"Error getting regional interest for {keyword}: {e}")
            return None

    async def analyze_search_momentum(self, keyword: str) -> Optional[SearchMomentum]:
        """Analyze search momentum and acceleration"""
        logger.info(f"Analyzing search momentum for {keyword}")

        try:
            # Get different timeframes
            trends_1m = await self.get_search_interest(keyword, 'today 1-m')
            trends_3m = await self.get_search_interest(keyword, 'today 3-m')

            if not trends_1m or not trends_3m:
                return None

            # Calculate momentum for different periods
            momentum_1d = self._calculate_momentum(trends_1m.interest_over_time, days=1)
            momentum_7d = self._calculate_momentum(trends_1m.interest_over_time, days=7)
            momentum_30d = self._calculate_momentum(trends_3m.interest_over_time, days=30)

            # Calculate acceleration (change in momentum)
            acceleration = self._calculate_acceleration(trends_1m.interest_over_time)

            # Calculate breakout probability
            breakout_prob = self._calculate_breakout_probability(
                trends_1m, trends_3m, momentum_1d, momentum_7d
            )

            # Calculate seasonal factor (simplified)
            seasonal_factor = self._calculate_seasonal_factor(trends_3m.interest_over_time)

            return SearchMomentum(
                keyword=keyword,
                momentum_1d=momentum_1d,
                momentum_7d=momentum_7d,
                momentum_30d=momentum_30d,
                acceleration=acceleration,
                breakout_probability=breakout_prob,
                seasonal_factor=seasonal_factor
            )

        except Exception as e:
            logger.error(f"Error analyzing search momentum for {keyword}: {e}")
            return None

    async def compare_keywords(self, keywords: List[str], timeframe: str = 'today 90-d') -> Dict[str, TrendsData]:
        """Compare multiple keywords"""
        logger.info(f"Comparing keywords: {keywords}")

        results = {}

        # Process in batches of 5 (Google Trends limit)
        for i in range(0, len(keywords), 5):
            batch = keywords[i:i+5]

            try:
                await self._respect_rate_limit()

                self.pytrends.build_payload(batch, timeframe=timeframe)
                interest_data = self.pytrends.interest_over_time()

                if not interest_data.empty:
                    for keyword in batch:
                        if keyword in interest_data.columns:
                            interest_series = interest_data[keyword]
                            interest_over_time = {
                                date.strftime('%Y-%m-%d'): int(value)
                                for date, value in interest_series.items()
                            }

                            current_interest = int(interest_series.iloc[-1])
                            peak_interest = int(interest_series.max())
                            peak_date = interest_series.idxmax()
                            average_interest = float(interest_series.mean())

                            trend_direction, trend_strength = self._calculate_trend(interest_series)

                            results[keyword] = TrendsData(
                                keyword=keyword,
                                timeframe=timeframe,
                                region='Global',
                                interest_over_time=interest_over_time,
                                current_interest=current_interest,
                                peak_interest=peak_interest,
                                peak_date=peak_date,
                                average_interest=average_interest,
                                trend_direction=trend_direction,
                                trend_strength=trend_strength
                            )

                # Extra delay between batches
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error comparing keywords batch {batch}: {e}")
                continue

        return results

    async def detect_emerging_trends(self, base_keywords: List[str]) -> List[str]:
        """Detect emerging cryptocurrency trends"""
        logger.info("Detecting emerging cryptocurrency trends")

        emerging_trends = []

        try:
            # Get related queries for each base keyword
            for keyword in base_keywords:
                related = await self.get_related_queries(keyword)

                if related:
                    # Add breakout queries
                    emerging_trends.extend(related.breakout_queries)

                    # Add high-growth rising queries
                    for query_data in related.rising_queries:
                        value_str = query_data['value']
                        if '+' in value_str and '%' in value_str:
                            try:
                                # Extract percentage
                                percent_str = value_str.replace('+', '').replace('%', '')
                                if percent_str.replace(',', '').isdigit():
                                    percent = int(percent_str.replace(',', ''))
                                    if percent > 1000:  # >1000% growth
                                        emerging_trends.append(query_data['query'])
                            except:
                                continue

                # Rate limiting
                await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"Error detecting emerging trends: {e}")

        # Remove duplicates and filter
        unique_trends = list(set(emerging_trends))

        # Filter out non-crypto terms (basic filtering)
        crypto_trends = [
            trend for trend in unique_trends
            if any(crypto_word in trend.lower()
                  for crypto_word in ['coin', 'token', 'crypto', 'bitcoin', 'eth', 'defi', 'nft'])
        ]

        return crypto_trends[:20]  # Top 20 emerging trends

    def _calculate_trend(self, interest_series: pd.Series) -> Tuple[str, float]:
        """Calculate trend direction and strength"""
        if len(interest_series) < 2:
            return 'stable', 0.0

        # Use linear regression slope
        x = range(len(interest_series))
        y = interest_series.values

        # Simple linear regression
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] * x[i] for i in range(n))

        if n * sum_x2 - sum_x * sum_x == 0:
            return 'stable', 0.0

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        # Determine direction
        if slope > 0.1:
            direction = 'rising'
        elif slope < -0.1:
            direction = 'falling'
        else:
            direction = 'stable'

        # Calculate strength (normalized slope)
        max_value = max(y) if y else 1
        strength = abs(slope) / max(max_value / len(y), 0.1)
        strength = min(strength, 1.0)

        return direction, float(strength)

    def _calculate_momentum(self, interest_data: Dict[str, int], days: int) -> float:
        """Calculate momentum over specified days"""
        if len(interest_data) < days + 1:
            return 0.0

        dates = sorted(interest_data.keys())
        recent_dates = dates[-days:]
        older_dates = dates[-days*2:-days] if len(dates) >= days*2 else dates[:-days]

        if not recent_dates or not older_dates:
            return 0.0

        recent_avg = sum(interest_data[date] for date in recent_dates) / len(recent_dates)
        older_avg = sum(interest_data[date] for date in older_dates) / len(older_dates)

        if older_avg == 0:
            return 1.0 if recent_avg > 0 else 0.0

        momentum = (recent_avg - older_avg) / older_avg
        return max(-1.0, min(1.0, momentum))  # Clamp to [-1, 1]

    def _calculate_acceleration(self, interest_data: Dict[str, int]) -> float:
        """Calculate acceleration in search interest"""
        if len(interest_data) < 4:
            return 0.0

        dates = sorted(interest_data.keys())

        # Calculate momentum for two periods
        mid_point = len(dates) // 2
        first_half = dates[:mid_point]
        second_half = dates[mid_point:]

        if len(first_half) < 2 or len(second_half) < 2:
            return 0.0

        first_momentum = self._calculate_momentum_from_dates(interest_data, first_half)
        second_momentum = self._calculate_momentum_from_dates(interest_data, second_half)

        acceleration = second_momentum - first_momentum
        return max(-1.0, min(1.0, acceleration))

    def _calculate_momentum_from_dates(self, interest_data: Dict[str, int], dates: List[str]) -> float:
        """Calculate momentum for specific date range"""
        if len(dates) < 2:
            return 0.0

        values = [interest_data[date] for date in dates]
        start_avg = sum(values[:len(values)//2]) / max(len(values)//2, 1)
        end_avg = sum(values[len(values)//2:]) / max(len(values) - len(values)//2, 1)

        if start_avg == 0:
            return 1.0 if end_avg > 0 else 0.0

        return (end_avg - start_avg) / start_avg

    def _calculate_breakout_probability(self, trends_1m: TrendsData, trends_3m: TrendsData,
                                      momentum_1d: float, momentum_7d: float) -> float:
        """Calculate probability of search breakout"""
        score = 0.0

        # Recent interest vs historical average
        if trends_3m.average_interest > 0:
            recent_vs_avg = trends_1m.current_interest / trends_3m.average_interest
            score += min(recent_vs_avg / 3.0, 0.3)  # Max 0.3 points

        # Momentum factors
        if momentum_1d > 0.2 and momentum_7d > 0.1:
            score += 0.25

        # Peak proximity
        if trends_1m.current_interest >= trends_3m.peak_interest * 0.8:
            score += 0.2

        # Trend strength
        if trends_1m.trend_direction == 'rising':
            score += trends_1m.trend_strength * 0.25

        return min(score, 1.0)

    def _calculate_seasonal_factor(self, interest_data: Dict[str, int]) -> float:
        """Calculate seasonal adjustment factor (simplified)"""
        if len(interest_data) < 30:
            return 1.0

        # Simple seasonal pattern detection
        dates = sorted(interest_data.keys())
        values = [interest_data[date] for date in dates]

        # Check for weekly patterns (every 7 days)
        weekly_correlation = 0.0
        if len(values) >= 14:
            first_week = values[:7]
            second_week = values[7:14]

            if sum(first_week) > 0 and sum(second_week) > 0:
                weekly_correlation = abs(sum(first_week) - sum(second_week)) / max(sum(first_week), sum(second_week))

        # Seasonal factor (1.0 = no seasonality, <1.0 = seasonal patterns detected)
        seasonal_factor = max(0.5, 1.0 - weekly_correlation)
        return seasonal_factor

    async def _respect_rate_limit(self):
        """Respect Google Trends rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()

    def calculate_search_signals(self, trends_data: TrendsData, momentum: SearchMomentum) -> Dict:
        """Calculate trading signals based on search data"""
        signals = {
            'search_momentum_score': 0.0,
            'breakout_score': 0.0,
            'interest_level_score': 0.0,
            'trend_strength_score': 0.0,
            'overall_search_score': 0.0,
            'signals': []
        }

        try:
            # Search momentum score
            momentum_score = (momentum.momentum_1d * 0.4 +
                            momentum.momentum_7d * 0.4 +
                            momentum.momentum_30d * 0.2)
            signals['search_momentum_score'] = momentum_score

            # Breakout score
            signals['breakout_score'] = momentum.breakout_probability

            # Interest level score (relative to peak)
            if trends_data.peak_interest > 0:
                interest_score = trends_data.current_interest / trends_data.peak_interest
                signals['interest_level_score'] = interest_score
            else:
                signals['interest_level_score'] = 0.0

            # Trend strength score
            trend_multiplier = 1.0 if trends_data.trend_direction == 'rising' else -1.0
            signals['trend_strength_score'] = trends_data.trend_strength * trend_multiplier

            # Overall search score
            signals['overall_search_score'] = (
                signals['search_momentum_score'] * 0.3 +
                signals['breakout_score'] * 0.25 +
                signals['interest_level_score'] * 0.2 +
                signals['trend_strength_score'] * 0.25
            )

            # Generate specific signals
            if momentum.breakout_probability > 0.7:
                signals['signals'].append('SEARCH_BREAKOUT')

            if momentum.momentum_1d > 0.3 and momentum.momentum_7d > 0.2:
                signals['signals'].append('RISING_SEARCH_INTEREST')

            if trends_data.current_interest >= trends_data.peak_interest * 0.9:
                signals['signals'].append('NEAR_SEARCH_PEAK')

            if momentum.acceleration > 0.3:
                signals['signals'].append('ACCELERATING_INTEREST')

        except Exception as e:
            logger.error(f"Error calculating search signals: {e}")

        return signals


# Example usage
async def main():
    """Example usage of Google Trends analyzer"""
    analyzer = GoogleTrendsAnalyzer()

    # Analyze Bitcoin search interest
    btc_trends = await analyzer.get_search_interest("Bitcoin")
    if btc_trends:
        print(f"Bitcoin search interest: {btc_trends.current_interest}/100")
        print(f"Trend: {btc_trends.trend_direction} (strength: {btc_trends.trend_strength:.2f})")

    # Get search momentum
    btc_momentum = await analyzer.analyze_search_momentum("Bitcoin")
    if btc_momentum:
        print(f"Search momentum (1d): {btc_momentum.momentum_1d:.2f}")
        print(f"Breakout probability: {btc_momentum.breakout_probability:.2f}")

    # Compare multiple cryptocurrencies
    symbols = ["Bitcoin", "Ethereum", "Dogecoin"]
    comparison = await analyzer.compare_keywords(symbols)

    for symbol, data in comparison.items():
        print(f"{symbol}: {data.current_interest}/100 ({data.trend_direction})")


if __name__ == "__main__":
    asyncio.run(main())