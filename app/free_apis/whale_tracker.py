"""
Free whale tracker using Etherscan API
Tracks large transactions and whale wallet behavior without paid services
"""
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class WhaleTransaction:
    """Large transaction data structure"""
    hash: str
    from_address: str
    to_address: str
    value_eth: float
    value_usd: float
    timestamp: datetime
    block_number: int
    gas_used: int
    gas_price: int
    transaction_type: str  # 'buy', 'sell', 'transfer'
    token_address: Optional[str] = None
    token_symbol: Optional[str] = None
    is_exchange_related: bool = False
    urgency_score: float = 0.0


@dataclass
class WhaleWallet:
    """Whale wallet information"""
    address: str
    balance_eth: float
    balance_usd: float
    transaction_count: int
    first_seen: datetime
    last_active: datetime
    whale_rank: int
    labels: List[str]  # 'exchange', 'defi', 'institutional', etc.


@dataclass
class WhaleAnalysisResult:
    """Whale analysis result for a token/timeframe"""
    symbol: str
    token_address: Optional[str]
    analysis_period_hours: int
    whale_activity_score: float  # 0-1
    accumulation_score: float  # -1 to 1 (negative = distribution)
    urgency_score: float  # 0-1
    large_transactions: List[WhaleTransaction]
    unique_whales: int
    total_volume_eth: float
    total_volume_usd: float
    buy_sell_ratio: float
    exchange_flow_net: float  # Net flow to/from exchanges
    confidence: float


class FreeWhaleTracker:
    """Free whale tracking using Etherscan API"""

    def __init__(self, etherscan_api_key: str):
        self.api_key = etherscan_api_key
        self.base_url = "https://api.etherscan.io/api"

        # Whale thresholds
        self.whale_threshold_eth = 100.0  # 100+ ETH transactions
        self.whale_threshold_usd = 100000.0  # $100k+ USD transactions
        self.large_wallet_threshold = 1000.0  # 1000+ ETH balance

        # Known exchange addresses (major ones)
        self.exchange_addresses = {
            '0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be': 'Binance',
            '0xd551234ae421e3bcba99a0da6d736074f22192ff': 'Binance',
            '0x564286362092d8e7936f0549571a803b203aaced': 'Binance',
            '0x0681d8db095565fe8a346fa0277bffde9c0edbbf': 'Binance',
            '0xfe9e8709d3215310075d67e3ed32a380ccf451c8': 'Coinbase',
            '0xa090e606e30bd747d4e6245a1517ebe430f0057e': 'Coinbase',
            '0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511': 'Coinbase',
            '0xeb2629a2734e272bcc07bda959863f316f4bd4cf': 'Coinbase',
            '0x267be1c1d684f78cb4f42f4b8b614cb48a39b913': 'Kraken',
            '0xfa52274dd61e1643d2205169732f29114bc240b3': 'Kraken',
            '0x53d284357ec70ce289d6d64134dfac8e511c8a3d': 'Kraken',
            '0x742d35cc6bf8b4f3e89e4e8d6d0e9a3b9a8c7e3c': 'Bitfinex',
            '0x876eabf441b2ee5b5b0554fd502a8e0600950cfa': 'Bitfinex'
        }

        # Rate limiting
        self.request_delay = 0.2  # 5 requests/second (free tier)
        self.last_request_time = 0

    async def analyze_whale_activity(self, symbol: str, token_address: Optional[str] = None,
                                   hours_back: int = 24) -> WhaleAnalysisResult:
        """
        Analyze whale activity for a token using free Etherscan API
        """
        logger.info(f"Analyzing whale activity for {symbol} (last {hours_back} hours)")

        # If no token address provided, focus on ETH whales
        if not token_address and symbol.upper() == 'ETH':
            return await self._analyze_eth_whale_activity(hours_back)
        elif token_address:
            return await self._analyze_token_whale_activity(symbol, token_address, hours_back)
        else:
            logger.warning(f"No token address provided for {symbol}, skipping analysis")
            return self._create_empty_result(symbol, hours_back)

    async def _analyze_eth_whale_activity(self, hours_back: int) -> WhaleAnalysisResult:
        """Analyze ETH whale transactions"""

        # Get recent large ETH transactions
        large_txs = await self._get_large_eth_transactions(hours_back)

        # Analyze transaction patterns
        whale_score = self._calculate_whale_activity_score(large_txs)
        accumulation_score = self._calculate_accumulation_score(large_txs)
        urgency_score = self._calculate_urgency_score(large_txs)

        # Calculate metrics
        unique_whales = len(set(tx.from_address for tx in large_txs) |
                           set(tx.to_address for tx in large_txs))

        total_volume_eth = sum(tx.value_eth for tx in large_txs)
        total_volume_usd = sum(tx.value_usd for tx in large_txs)

        buy_sell_ratio = self._calculate_buy_sell_ratio(large_txs)
        exchange_flow = self._calculate_exchange_flow(large_txs)
        confidence = self._calculate_confidence(large_txs, hours_back)

        return WhaleAnalysisResult(
            symbol='ETH',
            token_address=None,
            analysis_period_hours=hours_back,
            whale_activity_score=whale_score,
            accumulation_score=accumulation_score,
            urgency_score=urgency_score,
            large_transactions=large_txs,
            unique_whales=unique_whales,
            total_volume_eth=total_volume_eth,
            total_volume_usd=total_volume_usd,
            buy_sell_ratio=buy_sell_ratio,
            exchange_flow_net=exchange_flow,
            confidence=confidence
        )

    async def _analyze_token_whale_activity(self, symbol: str, token_address: str,
                                          hours_back: int) -> WhaleAnalysisResult:
        """Analyze ERC-20 token whale transactions"""

        # Get large token transfers
        large_transfers = await self._get_large_token_transfers(token_address, hours_back)

        # Convert to WhaleTransaction format
        whale_txs = []
        for transfer in large_transfers:
            tx = await self._enrich_transaction_data(transfer, symbol, token_address)
            if tx and tx.value_usd >= self.whale_threshold_usd:
                whale_txs.append(tx)

        # Analyze patterns
        whale_score = self._calculate_whale_activity_score(whale_txs)
        accumulation_score = self._calculate_accumulation_score(whale_txs)
        urgency_score = self._calculate_urgency_score(whale_txs)

        # Calculate metrics
        unique_whales = len(set(tx.from_address for tx in whale_txs) |
                           set(tx.to_address for tx in whale_txs))

        total_volume_eth = sum(tx.value_eth for tx in whale_txs)
        total_volume_usd = sum(tx.value_usd for tx in whale_txs)

        buy_sell_ratio = self._calculate_buy_sell_ratio(whale_txs)
        exchange_flow = self._calculate_exchange_flow(whale_txs)
        confidence = self._calculate_confidence(whale_txs, hours_back)

        return WhaleAnalysisResult(
            symbol=symbol,
            token_address=token_address,
            analysis_period_hours=hours_back,
            whale_activity_score=whale_score,
            accumulation_score=accumulation_score,
            urgency_score=urgency_score,
            large_transactions=whale_txs,
            unique_whales=unique_whales,
            total_volume_eth=total_volume_eth,
            total_volume_usd=total_volume_usd,
            buy_sell_ratio=buy_sell_ratio,
            exchange_flow_net=exchange_flow,
            confidence=confidence
        )

    async def _get_large_eth_transactions(self, hours_back: int) -> List[WhaleTransaction]:
        """Get large ETH transactions from recent blocks"""
        whale_txs = []

        try:
            # Get current block number
            current_block = await self._get_current_block_number()

            # Estimate blocks to look back (15 seconds per block average)
            blocks_to_check = min((hours_back * 3600) // 15, 1000)  # Limit to 1000 blocks
            start_block = max(current_block - blocks_to_check, 1)

            # Check recent blocks for large transactions
            for block_num in range(current_block, start_block, -50):  # Check every 50th block
                block_data = await self._get_block_transactions(block_num)

                if block_data:
                    for tx_data in block_data:
                        try:
                            value_eth = int(tx_data.get('value', '0')) / 10**18

                            if value_eth >= self.whale_threshold_eth:
                                # Get current ETH price for USD conversion
                                eth_price = await self._get_eth_price()
                                value_usd = value_eth * eth_price

                                tx = WhaleTransaction(
                                    hash=tx_data.get('hash', ''),
                                    from_address=tx_data.get('from', '').lower(),
                                    to_address=tx_data.get('to', '').lower(),
                                    value_eth=value_eth,
                                    value_usd=value_usd,
                                    timestamp=datetime.fromtimestamp(int(tx_data.get('timeStamp', 0))),
                                    block_number=int(tx_data.get('blockNumber', 0)),
                                    gas_used=int(tx_data.get('gasUsed', 0)),
                                    gas_price=int(tx_data.get('gasPrice', 0)),
                                    transaction_type=self._classify_transaction_type(
                                        tx_data.get('from', '').lower(),
                                        tx_data.get('to', '').lower()
                                    ),
                                    is_exchange_related=self._is_exchange_related(
                                        tx_data.get('from', '').lower(),
                                        tx_data.get('to', '').lower()
                                    ),
                                    urgency_score=self._calculate_tx_urgency_score(tx_data)
                                )

                                whale_txs.append(tx)

                        except (ValueError, KeyError) as e:
                            continue

                # Rate limiting
                await self._respect_rate_limit()

        except Exception as e:
            logger.error(f"Error getting large ETH transactions: {e}")

        # Sort by timestamp (newest first) and limit results
        whale_txs.sort(key=lambda x: x.timestamp, reverse=True)
        return whale_txs[:100]  # Limit to 100 transactions

    async def _get_large_token_transfers(self, token_address: str, hours_back: int) -> List[Dict]:
        """Get large ERC-20 token transfers"""
        transfers = []

        try:
            # Get token transfers for the contract
            url = self.base_url
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': token_address,
                'page': 1,
                'offset': 1000,  # Max allowed
                'sort': 'desc',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()

                    if data.get('status') == '1' and data.get('result'):
                        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

                        for transfer in data['result']:
                            tx_time = datetime.fromtimestamp(int(transfer.get('timeStamp', 0)))

                            if tx_time >= cutoff_time:
                                transfers.append(transfer)

            await self._respect_rate_limit()

        except Exception as e:
            logger.error(f"Error getting token transfers: {e}")

        return transfers

    async def _enrich_transaction_data(self, transfer_data: Dict, symbol: str,
                                     token_address: str) -> Optional[WhaleTransaction]:
        """Enrich token transfer data with pricing and classification"""
        try:
            # Get token details
            token_decimals = int(transfer_data.get('tokenDecimal', 18))
            value_tokens = int(transfer_data.get('value', 0)) / (10 ** token_decimals)

            # Get token price (this would need a price API)
            token_price = await self._get_token_price(symbol, token_address)
            value_usd = value_tokens * token_price if token_price else 0

            # Skip if below USD threshold
            if value_usd < self.whale_threshold_usd:
                return None

            from_addr = transfer_data.get('from', '').lower()
            to_addr = transfer_data.get('to', '').lower()

            tx = WhaleTransaction(
                hash=transfer_data.get('hash', ''),
                from_address=from_addr,
                to_address=to_addr,
                value_eth=value_usd / (await self._get_eth_price()),  # ETH equivalent
                value_usd=value_usd,
                timestamp=datetime.fromtimestamp(int(transfer_data.get('timeStamp', 0))),
                block_number=int(transfer_data.get('blockNumber', 0)),
                gas_used=int(transfer_data.get('gasUsed', 0)),
                gas_price=int(transfer_data.get('gasPrice', 0)),
                transaction_type=self._classify_transaction_type(from_addr, to_addr),
                token_address=token_address,
                token_symbol=symbol,
                is_exchange_related=self._is_exchange_related(from_addr, to_addr),
                urgency_score=self._calculate_tx_urgency_score(transfer_data)
            )

            return tx

        except Exception as e:
            logger.error(f"Error enriching transaction data: {e}")
            return None

    async def _get_current_block_number(self) -> int:
        """Get current Ethereum block number"""
        try:
            url = self.base_url
            params = {
                'module': 'proxy',
                'action': 'eth_blockNumber',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()

                    if data.get('result'):
                        return int(data['result'], 16)  # Convert hex to int

            await self._respect_rate_limit()

        except Exception as e:
            logger.error(f"Error getting current block number: {e}")

        return 18500000  # Fallback to approximate current block

    async def _get_block_transactions(self, block_number: int) -> List[Dict]:
        """Get transactions from a specific block"""
        try:
            url = self.base_url
            params = {
                'module': 'proxy',
                'action': 'eth_getBlockByNumber',
                'tag': hex(block_number),
                'boolean': 'true',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()

                    if data.get('result') and data['result'].get('transactions'):
                        return data['result']['transactions']

            await self._respect_rate_limit()

        except Exception as e:
            logger.error(f"Error getting block transactions: {e}")

        return []

    async def _get_eth_price(self) -> float:
        """Get current ETH price in USD (using free CoinGecko API)"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': 'ethereum', 'vs_currencies': 'usd'}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    return data.get('ethereum', {}).get('usd', 2000.0)  # Fallback to $2000

        except Exception:
            return 2000.0  # Fallback price

    async def _get_token_price(self, symbol: str, token_address: str) -> float:
        """Get token price in USD (using free CoinGecko API)"""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/token_price/ethereum"
            params = {
                'contract_addresses': token_address,
                'vs_currencies': 'usd'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    return data.get(token_address.lower(), {}).get('usd', 0.0)

        except Exception:
            return 0.0

    def _classify_transaction_type(self, from_addr: str, to_addr: str) -> str:
        """Classify transaction as buy/sell/transfer"""
        from_is_exchange = from_addr in self.exchange_addresses
        to_is_exchange = to_addr in self.exchange_addresses

        if from_is_exchange and not to_is_exchange:
            return 'buy'  # From exchange to wallet
        elif not from_is_exchange and to_is_exchange:
            return 'sell'  # From wallet to exchange
        else:
            return 'transfer'  # Wallet to wallet or exchange to exchange

    def _is_exchange_related(self, from_addr: str, to_addr: str) -> bool:
        """Check if transaction involves known exchange addresses"""
        return (from_addr in self.exchange_addresses or
                to_addr in self.exchange_addresses)

    def _calculate_tx_urgency_score(self, tx_data: Dict) -> float:
        """Calculate urgency score based on gas price and other factors"""
        try:
            gas_price = int(tx_data.get('gasPrice', 0))

            # Normalize gas price (100 gwei = high urgency)
            gas_price_gwei = gas_price / 10**9
            urgency = min(gas_price_gwei / 100.0, 1.0)

            return urgency

        except Exception:
            return 0.5  # Default medium urgency

    def _calculate_whale_activity_score(self, transactions: List[WhaleTransaction]) -> float:
        """Calculate overall whale activity score (0-1)"""
        if not transactions:
            return 0.0

        # Base score from transaction count
        tx_count_score = min(len(transactions) / 20.0, 1.0)  # 20+ transactions = max score

        # Volume score
        total_volume = sum(tx.value_usd for tx in transactions)
        volume_score = min(total_volume / 10000000.0, 1.0)  # $10M+ = max score

        # Unique whale count score
        unique_whales = len(set(tx.from_address for tx in transactions) |
                           set(tx.to_address for tx in transactions))
        whale_count_score = min(unique_whales / 10.0, 1.0)  # 10+ whales = max score

        # Average urgency score
        avg_urgency = sum(tx.urgency_score for tx in transactions) / len(transactions)

        # Combined score
        score = (tx_count_score * 0.25 +
                volume_score * 0.35 +
                whale_count_score * 0.25 +
                avg_urgency * 0.15)

        return min(score, 1.0)

    def _calculate_accumulation_score(self, transactions: List[WhaleTransaction]) -> float:
        """Calculate accumulation vs distribution score (-1 to 1)"""
        if not transactions:
            return 0.0

        buy_volume = sum(tx.value_usd for tx in transactions if tx.transaction_type == 'buy')
        sell_volume = sum(tx.value_usd for tx in transactions if tx.transaction_type == 'sell')

        total_volume = buy_volume + sell_volume

        if total_volume == 0:
            return 0.0

        # Calculate net buying pressure
        net_buying = (buy_volume - sell_volume) / total_volume

        return max(-1.0, min(1.0, net_buying))

    def _calculate_urgency_score(self, transactions: List[WhaleTransaction]) -> float:
        """Calculate average urgency score"""
        if not transactions:
            return 0.0

        return sum(tx.urgency_score for tx in transactions) / len(transactions)

    def _calculate_buy_sell_ratio(self, transactions: List[WhaleTransaction]) -> float:
        """Calculate buy/sell ratio"""
        buy_count = sum(1 for tx in transactions if tx.transaction_type == 'buy')
        sell_count = sum(1 for tx in transactions if tx.transaction_type == 'sell')

        if sell_count == 0:
            return 10.0 if buy_count > 0 else 1.0

        return buy_count / sell_count

    def _calculate_exchange_flow(self, transactions: List[WhaleTransaction]) -> float:
        """Calculate net flow to exchanges (negative) or from exchanges (positive)"""
        flow_to_exchange = sum(tx.value_usd for tx in transactions
                              if tx.transaction_type == 'sell')
        flow_from_exchange = sum(tx.value_usd for tx in transactions
                                if tx.transaction_type == 'buy')

        return flow_from_exchange - flow_to_exchange

    def _calculate_confidence(self, transactions: List[WhaleTransaction], hours_back: int) -> float:
        """Calculate confidence in the analysis"""
        if not transactions:
            return 0.0

        # Base confidence from sample size
        sample_confidence = min(len(transactions) / 10.0, 1.0)  # 10+ transactions = full confidence

        # Time coverage confidence (more recent = higher confidence)
        if transactions:
            time_span_hours = (max(tx.timestamp for tx in transactions) -
                             min(tx.timestamp for tx in transactions)).total_seconds() / 3600
            time_confidence = min(time_span_hours / hours_back, 1.0)
        else:
            time_confidence = 0.0

        # Exchange involvement confidence (more exchange data = higher confidence)
        exchange_txs = sum(1 for tx in transactions if tx.is_exchange_related)
        exchange_confidence = min(exchange_txs / len(transactions), 1.0)

        # Combined confidence
        confidence = (sample_confidence * 0.5 +
                     time_confidence * 0.3 +
                     exchange_confidence * 0.2)

        return min(confidence, 0.95)  # Cap at 95%

    def _create_empty_result(self, symbol: str, hours_back: int) -> WhaleAnalysisResult:
        """Create empty result when no data available"""
        return WhaleAnalysisResult(
            symbol=symbol,
            token_address=None,
            analysis_period_hours=hours_back,
            whale_activity_score=0.0,
            accumulation_score=0.0,
            urgency_score=0.0,
            large_transactions=[],
            unique_whales=0,
            total_volume_eth=0.0,
            total_volume_usd=0.0,
            buy_sell_ratio=1.0,
            exchange_flow_net=0.0,
            confidence=0.0
        )

    async def _respect_rate_limit(self):
        """Ensure we don't exceed Etherscan's rate limits (5 requests/second)"""
        current_time = datetime.utcnow().timestamp()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            await asyncio.sleep(sleep_time)

        self.last_request_time = datetime.utcnow().timestamp()

    async def get_top_whale_wallets(self, limit: int = 100) -> List[WhaleWallet]:
        """Get top whale wallets by ETH balance"""
        # This would require more complex analysis of many addresses
        # For now, return empty list as it's beyond free API capabilities
        logger.info("Top whale wallets analysis requires premium data sources")
        return []

    async def track_wallet_activity(self, wallet_address: str, hours_back: int = 24) -> Dict:
        """Track specific wallet's recent activity"""
        try:
            # Get wallet's recent transactions
            url = self.base_url
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': wallet_address,
                'startblock': 0,
                'endblock': 99999999,
                'page': 1,
                'offset': 100,
                'sort': 'desc',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()

                    if data.get('status') == '1' and data.get('result'):
                        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

                        recent_txs = []
                        for tx in data['result']:
                            tx_time = datetime.fromtimestamp(int(tx.get('timeStamp', 0)))
                            if tx_time >= cutoff_time:
                                recent_txs.append(tx)

                        return {
                            'wallet_address': wallet_address,
                            'recent_transactions': len(recent_txs),
                            'total_volume_eth': sum(int(tx.get('value', 0)) / 10**18 for tx in recent_txs),
                            'gas_spent_eth': sum(int(tx.get('gasUsed', 0)) * int(tx.get('gasPrice', 0)) / 10**18 for tx in recent_txs),
                            'transactions': recent_txs[:10]  # Top 10 recent
                        }

            await self._respect_rate_limit()

        except Exception as e:
            logger.error(f"Error tracking wallet {wallet_address}: {e}")

        return {'error': 'Unable to track wallet activity'}


# Example usage
async def main():
    """Example usage of whale tracker"""
    # You need to get a free API key from etherscan.io
    api_key = "YourFreeEtherscanAPIKey"

    tracker = FreeWhaleTracker(api_key)

    # Analyze ETH whale activity
    eth_analysis = await tracker.analyze_whale_activity("ETH", hours_back=48)

    print(f"ETH Whale Analysis:")
    print(f"Activity Score: {eth_analysis.whale_activity_score:.3f}")
    print(f"Accumulation Score: {eth_analysis.accumulation_score:.3f}")
    print(f"Large Transactions: {len(eth_analysis.large_transactions)}")
    print(f"Total Volume: ${eth_analysis.total_volume_usd:,.0f}")
    print(f"Confidence: {eth_analysis.confidence:.3f}")


if __name__ == "__main__":
    asyncio.run(main())