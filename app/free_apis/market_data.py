"""
Free market data integration using CoinGecko API
Provides comprehensive cryptocurrency market data without cost
"""
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class TokenData:
    """Token market data structure"""
    id: str
    symbol: str
    name: str
    current_price: float
    market_cap: float
    market_cap_rank: int
    volume_24h: float
    price_change_24h: float
    price_change_percentage_24h: float
    price_change_7d: float
    price_change_percentage_7d: float
    circulating_supply: float
    total_supply: float
    max_supply: Optional[float]
    ath: float
    ath_change_percentage: float
    ath_date: datetime
    atl: float
    atl_change_percentage: float
    atl_date: datetime
    last_updated: datetime


@dataclass
class MarketMetrics:
    """Market-wide metrics"""
    total_market_cap: float
    total_volume_24h: float
    market_cap_change_24h: float
    volume_change_24h: float
    bitcoin_dominance: float
    ethereum_dominance: float
    active_cryptocurrencies: int
    markets: int
    market_cap_change_percentage_24h: float


@dataclass
class TrendingToken:
    """Trending token data"""
    id: str
    coin_id: str
    name: str
    symbol: str
    market_cap_rank: int
    thumb: str
    small: str
    large: str
    slug: str
    price_btc: float
    score: int


@dataclass
class PriceAlert:
    """Price alert data structure"""
    token_id: str
    symbol: str
    alert_type: str  # 'breakout', 'breakdown', 'volume_spike', 'unusual_activity'
    current_price: float
    trigger_price: float
    percentage_change: float
    volume_change: float
    alert_strength: float  # 0-1
    message: str


class FreeMarketData:
    """Free market data using CoinGecko API"""

    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.request_delay = 6.0  # 10 calls/minute for free tier
        self.last_request_time = 0

        # Cache for token IDs (symbol -> coingecko_id mapping)
        self._token_id_cache = {}

    async def get_token_data(self, symbol: str) -> Optional[TokenData]:
        """Get comprehensive token data"""
        logger.info(f"Getting market data for {symbol}")

        try:
            # Get CoinGecko ID for the symbol
            coin_id = await self._get_coin_id(symbol)
            if not coin_id:
                return None

            url = f"{self.base_url}/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()
                    market_data = data.get('market_data', {})

                    token_data = TokenData(
                        id=data.get('id', ''),
                        symbol=data.get('symbol', '').upper(),
                        name=data.get('name', ''),
                        current_price=market_data.get('current_price', {}).get('usd', 0.0),
                        market_cap=market_data.get('market_cap', {}).get('usd', 0.0),
                        market_cap_rank=market_data.get('market_cap_rank', 0),
                        volume_24h=market_data.get('total_volume', {}).get('usd', 0.0),
                        price_change_24h=market_data.get('price_change_24h', 0.0),
                        price_change_percentage_24h=market_data.get('price_change_percentage_24h', 0.0),
                        price_change_7d=market_data.get('price_change_7d', 0.0),
                        price_change_percentage_7d=market_data.get('price_change_percentage_7d', 0.0),
                        circulating_supply=market_data.get('circulating_supply', 0.0),
                        total_supply=market_data.get('total_supply', 0.0),
                        max_supply=market_data.get('max_supply'),
                        ath=market_data.get('ath', {}).get('usd', 0.0),
                        ath_change_percentage=market_data.get('ath_change_percentage', {}).get('usd', 0.0),
                        ath_date=datetime.fromisoformat(market_data.get('ath_date', {}).get('usd', '').replace('Z', '+00:00'))
                        if market_data.get('ath_date', {}).get('usd') else datetime.utcnow(),
                        atl=market_data.get('atl', {}).get('usd', 0.0),
                        atl_change_percentage=market_data.get('atl_change_percentage', {}).get('usd', 0.0),
                        atl_date=datetime.fromisoformat(market_data.get('atl_date', {}).get('usd', '').replace('Z', '+00:00'))
                        if market_data.get('atl_date', {}).get('usd') else datetime.utcnow(),
                        last_updated=datetime.fromisoformat(market_data.get('last_updated', '').replace('Z', '+00:00'))
                        if market_data.get('last_updated') else datetime.utcnow()
                    )

                    await self._respect_rate_limit()
                    return token_data

        except Exception as e:
            logger.error(f"Error getting token data for {symbol}: {e}")

        return None

    async def get_multiple_tokens_data(self, symbols: List[str]) -> Dict[str, TokenData]:
        """Get data for multiple tokens efficiently"""
        logger.info(f"Getting market data for {len(symbols)} tokens")

        # Convert symbols to CoinGecko IDs
        coin_ids = []
        symbol_to_id = {}

        for symbol in symbols:
            coin_id = await self._get_coin_id(symbol)
            if coin_id:
                coin_ids.append(coin_id)
                symbol_to_id[coin_id] = symbol.upper()

        if not coin_ids:
            return {}

        results = {}

        try:
            # Use the markets endpoint for efficiency (up to 250 coins)
            url = f"{self.base_url}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'ids': ','.join(coin_ids[:250]),  # Limit to 250
                'order': 'market_cap_desc',
                'per_page': 250,
                'page': 1,
                'sparkline': 'false',
                'price_change_percentage': '24h,7d'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return results

                    data = await response.json()

                    for coin_data in data:
                        coin_id = coin_data.get('id', '')
                        symbol = symbol_to_id.get(coin_id, coin_data.get('symbol', '').upper())

                        token_data = TokenData(
                            id=coin_id,
                            symbol=symbol,
                            name=coin_data.get('name', ''),
                            current_price=coin_data.get('current_price', 0.0),
                            market_cap=coin_data.get('market_cap', 0.0),
                            market_cap_rank=coin_data.get('market_cap_rank', 0),
                            volume_24h=coin_data.get('total_volume', 0.0),
                            price_change_24h=coin_data.get('price_change_24h', 0.0),
                            price_change_percentage_24h=coin_data.get('price_change_percentage_24h', 0.0),
                            price_change_7d=0.0,  # Not available in markets endpoint
                            price_change_percentage_7d=coin_data.get('price_change_percentage_7d_in_currency', 0.0),
                            circulating_supply=coin_data.get('circulating_supply', 0.0),
                            total_supply=coin_data.get('total_supply', 0.0),
                            max_supply=coin_data.get('max_supply'),
                            ath=coin_data.get('ath', 0.0),
                            ath_change_percentage=coin_data.get('ath_change_percentage', 0.0),
                            ath_date=datetime.fromisoformat(coin_data.get('ath_date', '').replace('Z', '+00:00'))
                            if coin_data.get('ath_date') else datetime.utcnow(),
                            atl=coin_data.get('atl', 0.0),
                            atl_change_percentage=coin_data.get('atl_change_percentage', 0.0),
                            atl_date=datetime.fromisoformat(coin_data.get('atl_date', '').replace('Z', '+00:00'))
                            if coin_data.get('atl_date') else datetime.utcnow(),
                            last_updated=datetime.fromisoformat(coin_data.get('last_updated', '').replace('Z', '+00:00'))
                            if coin_data.get('last_updated') else datetime.utcnow()
                        )

                        results[symbol] = token_data

            await self._respect_rate_limit()

        except Exception as e:
            logger.error(f"Error getting multiple tokens data: {e}")

        return results

    async def get_market_metrics(self) -> Optional[MarketMetrics]:
        """Get global cryptocurrency market metrics"""
        logger.info("Getting global market metrics")

        try:
            url = f"{self.base_url}/global"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()
                    global_data = data.get('data', {})

                    total_market_cap = global_data.get('total_market_cap', {}).get('usd', 0.0)
                    total_volume_24h = global_data.get('total_volume', {}).get('usd', 0.0)

                    metrics = MarketMetrics(
                        total_market_cap=total_market_cap,
                        total_volume_24h=total_volume_24h,
                        market_cap_change_24h=global_data.get('market_cap_change_24h_usd', 0.0),
                        volume_change_24h=0.0,  # Not provided directly
                        bitcoin_dominance=global_data.get('market_cap_percentage', {}).get('btc', 0.0),
                        ethereum_dominance=global_data.get('market_cap_percentage', {}).get('eth', 0.0),
                        active_cryptocurrencies=global_data.get('active_cryptocurrencies', 0),
                        markets=global_data.get('markets', 0),
                        market_cap_change_percentage_24h=global_data.get('market_cap_change_percentage_24h_usd', 0.0)
                    )

                    await self._respect_rate_limit()
                    return metrics

        except Exception as e:
            logger.error(f"Error getting market metrics: {e}")

        return None

    async def get_trending_tokens(self) -> List[TrendingToken]:
        """Get currently trending tokens"""
        logger.info("Getting trending tokens")

        trending_tokens = []

        try:
            url = f"{self.base_url}/search/trending"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return trending_tokens

                    data = await response.json()
                    coins = data.get('coins', [])

                    for coin_data in coins:
                        item = coin_data.get('item', {})

                        trending_token = TrendingToken(
                            id=item.get('id', ''),
                            coin_id=item.get('coin_id', 0),
                            name=item.get('name', ''),
                            symbol=item.get('symbol', '').upper(),
                            market_cap_rank=item.get('market_cap_rank', 0),
                            thumb=item.get('thumb', ''),
                            small=item.get('small', ''),
                            large=item.get('large', ''),
                            slug=item.get('slug', ''),
                            price_btc=item.get('price_btc', 0.0),
                            score=item.get('score', 0)
                        )

                        trending_tokens.append(trending_token)

            await self._respect_rate_limit()

        except Exception as e:
            logger.error(f"Error getting trending tokens: {e}")

        return trending_tokens

    async def detect_price_alerts(self, tokens: List[TokenData]) -> List[PriceAlert]:
        """Detect various price alerts and unusual market conditions"""
        alerts = []

        for token in tokens:
            try:
                # Breakout detection (price near ATH)
                if token.ath_change_percentage > -10.0:  # Within 10% of ATH
                    alert = PriceAlert(
                        token_id=token.id,
                        symbol=token.symbol,
                        alert_type='breakout',
                        current_price=token.current_price,
                        trigger_price=token.ath,
                        percentage_change=token.price_change_percentage_24h,
                        volume_change=0.0,  # Would need historical data
                        alert_strength=min(1.0, abs(token.ath_change_percentage) / 10.0),
                        message=f"{token.symbol} is within {abs(token.ath_change_percentage):.1f}% of its ATH"
                    )
                    alerts.append(alert)

                # Large 24h movement
                if abs(token.price_change_percentage_24h) > 15.0:
                    direction = 'up' if token.price_change_percentage_24h > 0 else 'down'
                    alert = PriceAlert(
                        token_id=token.id,
                        symbol=token.symbol,
                        alert_type='large_movement',
                        current_price=token.current_price,
                        trigger_price=token.current_price * (1 - token.price_change_percentage_24h / 100),
                        percentage_change=token.price_change_percentage_24h,
                        volume_change=0.0,
                        alert_strength=min(1.0, abs(token.price_change_percentage_24h) / 50.0),
                        message=f"{token.symbol} moved {direction} {abs(token.price_change_percentage_24h):.1f}% in 24h"
                    )
                    alerts.append(alert)

                # Volume spike detection (would need historical volume data)
                # For now, we'll use market cap rank as a proxy
                if token.market_cap_rank > 0 and token.market_cap_rank <= 100:
                    volume_to_mcap = token.volume_24h / max(token.market_cap, 1)

                    if volume_to_mcap > 0.1:  # Volume > 10% of market cap
                        alert = PriceAlert(
                            token_id=token.id,
                            symbol=token.symbol,
                            alert_type='volume_spike',
                            current_price=token.current_price,
                            trigger_price=token.current_price,
                            percentage_change=token.price_change_percentage_24h,
                            volume_change=volume_to_mcap * 100,
                            alert_strength=min(1.0, volume_to_mcap / 0.2),
                            message=f"{token.symbol} showing unusual volume: {volume_to_mcap*100:.1f}% of market cap"
                        )
                        alerts.append(alert)

            except Exception as e:
                logger.error(f"Error detecting alerts for {token.symbol}: {e}")

        # Sort by alert strength
        alerts.sort(key=lambda x: x.alert_strength, reverse=True)

        return alerts

    async def get_token_contract_address(self, symbol: str) -> Optional[str]:
        """Get token contract address (Ethereum)"""
        try:
            coin_id = await self._get_coin_id(symbol)
            if not coin_id:
                return None

            url = f"{self.base_url}/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'false',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()
                    platforms = data.get('platforms', {})

                    # Look for Ethereum contract address
                    ethereum_address = platforms.get('ethereum', '')
                    if ethereum_address and ethereum_address.startswith('0x'):
                        return ethereum_address

                    # Fallback to other EVM chains
                    for platform, address in platforms.items():
                        if address and address.startswith('0x'):
                            return address

            await self._respect_rate_limit()

        except Exception as e:
            logger.error(f"Error getting contract address for {symbol}: {e}")

        return None

    async def _get_coin_id(self, symbol: str) -> Optional[str]:
        """Get CoinGecko coin ID for a symbol"""
        symbol_upper = symbol.upper()

        # Check cache first
        if symbol_upper in self._token_id_cache:
            return self._token_id_cache[symbol_upper]

        try:
            url = f"{self.base_url}/coins/list"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None

                    coins = await response.json()

                    # Build cache
                    for coin in coins:
                        coin_symbol = coin.get('symbol', '').upper()
                        coin_id = coin.get('id', '')

                        if coin_symbol and coin_id:
                            self._token_id_cache[coin_symbol] = coin_id

                    await self._respect_rate_limit()

                    return self._token_id_cache.get(symbol_upper)

        except Exception as e:
            logger.error(f"Error getting coin ID for {symbol}: {e}")

        return None

    async def get_fear_greed_index(self) -> Optional[Dict]:
        """Get Fear & Greed Index from alternative.me (free)"""
        try:
            url = "https://api.alternative.me/fng/"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()

                    if data.get('data'):
                        latest = data['data'][0]
                        return {
                            'value': int(latest.get('value', 50)),
                            'value_classification': latest.get('value_classification', 'Neutral'),
                            'timestamp': datetime.fromtimestamp(int(latest.get('timestamp', 0))),
                            'time_until_update': latest.get('time_until_update')
                        }

        except Exception as e:
            logger.error(f"Error getting Fear & Greed Index: {e}")

        return None

    async def get_defi_tvl_data(self) -> Optional[Dict]:
        """Get DeFi TVL data from DefiLlama (free)"""
        try:
            url = "https://api.llama.fi/protocols"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None

                    protocols = await response.json()

                    # Calculate total TVL and top protocols
                    total_tvl = sum(p.get('tvl', 0) for p in protocols)
                    top_protocols = sorted(protocols, key=lambda x: x.get('tvl', 0), reverse=True)[:10]

                    return {
                        'total_tvl': total_tvl,
                        'protocol_count': len(protocols),
                        'top_protocols': [
                            {
                                'name': p.get('name', ''),
                                'tvl': p.get('tvl', 0),
                                'change_1d': p.get('change_1d', 0),
                                'change_7d': p.get('change_7d', 0),
                                'mcap': p.get('mcap', 0)
                            }
                            for p in top_protocols
                        ],
                        'last_updated': datetime.utcnow()
                    }

        except Exception as e:
            logger.error(f"Error getting DeFi TVL data: {e}")

        return None

    async def _respect_rate_limit(self):
        """Respect CoinGecko's rate limits (10 calls/minute for free tier)"""
        current_time = datetime.utcnow().timestamp()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            await asyncio.sleep(sleep_time)

        self.last_request_time = datetime.utcnow().timestamp()

    def calculate_market_signals(self, token_data: TokenData, market_metrics: MarketMetrics) -> Dict:
        """Calculate market-based trading signals"""
        signals = {
            'momentum_score': 0.0,
            'volatility_score': 0.0,
            'volume_score': 0.0,
            'market_position_score': 0.0,
            'overall_score': 0.0,
            'signals': []
        }

        try:
            # Momentum score based on price changes
            momentum_24h = token_data.price_change_percentage_24h / 100.0
            momentum_7d = token_data.price_change_percentage_7d / 100.0

            momentum_score = (momentum_24h * 0.6 + momentum_7d * 0.4)
            signals['momentum_score'] = max(-1.0, min(1.0, momentum_score * 2))  # Scale to -1,1

            # Volatility score
            volatility = abs(token_data.price_change_percentage_24h)
            volatility_score = min(volatility / 20.0, 1.0)  # 20%+ = max volatility score
            signals['volatility_score'] = volatility_score

            # Volume score (relative to market cap)
            if token_data.market_cap > 0:
                volume_ratio = token_data.volume_24h / token_data.market_cap
                volume_score = min(volume_ratio / 0.1, 1.0)  # 10%+ = max volume score
                signals['volume_score'] = volume_score

            # Market position score (based on rank and ATH distance)
            rank_score = max(0, (500 - token_data.market_cap_rank) / 500) if token_data.market_cap_rank > 0 else 0
            ath_score = max(0, (token_data.ath_change_percentage + 90) / 90)  # -90% to 0%
            signals['market_position_score'] = (rank_score * 0.6 + ath_score * 0.4)

            # Overall score
            signals['overall_score'] = (
                signals['momentum_score'] * 0.3 +
                signals['volume_score'] * 0.25 +
                signals['market_position_score'] * 0.25 +
                (1 - signals['volatility_score']) * 0.2  # Lower volatility = better
            )

            # Generate specific signals
            if signals['momentum_score'] > 0.5 and signals['volume_score'] > 0.3:
                signals['signals'].append('BULLISH_MOMENTUM')

            if signals['momentum_score'] < -0.5 and signals['volume_score'] > 0.3:
                signals['signals'].append('BEARISH_MOMENTUM')

            if signals['volume_score'] > 0.7:
                signals['signals'].append('VOLUME_BREAKOUT')

            if token_data.ath_change_percentage > -5.0:
                signals['signals'].append('NEAR_ATH')

        except Exception as e:
            logger.error(f"Error calculating market signals: {e}")

        return signals


# Example usage
async def main():
    """Example usage of market data engine"""
    market_data = FreeMarketData()

    # Get Bitcoin data
    btc_data = await market_data.get_token_data("BTC")
    if btc_data:
        print(f"Bitcoin: ${btc_data.current_price:,.2f} ({btc_data.price_change_percentage_24h:+.2f}%)")

    # Get market metrics
    metrics = await market_data.get_market_metrics()
    if metrics:
        print(f"Total Market Cap: ${metrics.total_market_cap:,.0f}")
        print(f"Bitcoin Dominance: {metrics.bitcoin_dominance:.1f}%")

    # Get trending tokens
    trending = await market_data.get_trending_tokens()
    print(f"Trending tokens: {[t.symbol for t in trending[:5]]}")

    # Get Fear & Greed Index
    fear_greed = await market_data.get_fear_greed_index()
    if fear_greed:
        print(f"Fear & Greed: {fear_greed['value']} ({fear_greed['value_classification']})")


if __name__ == "__main__":
    asyncio.run(main())