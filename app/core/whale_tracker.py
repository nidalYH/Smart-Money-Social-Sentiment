"""
Whale wallet tracking and analysis module
"""
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.orm import selectinload

from app.config import settings, ETHERSCAN_BASE_URL
from app.models.whale import WhaleWallet, WhaleTransaction, WhalePortfolio
from app.models.token import Token, TokenPrice
from app.core.data_manager import DataManager

logger = logging.getLogger(__name__)


@dataclass
class WhaleActivity:
    """Data class for whale activity analysis"""
    wallet_address: str
    token_address: str
    token_symbol: str
    transaction_type: str
    amount: float
    amount_usd: float
    timestamp: datetime
    gas_price_gwei: float
    urgency_score: float
    impact_score: float


class WhaleTracker:
    """Main whale tracking and analysis class"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.session = None
        self.known_exchange_addresses = self._load_known_exchanges()
        self.whale_wallets = []
        self.is_running = False
        
    def _load_known_exchanges(self) -> List[str]:
        """Load known exchange wallet addresses"""
        # Known exchange addresses (simplified list)
        return [
            "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",  # Binance
            "0xd551234ae421e3bcba99a0da6d736074f22192ff",  # Binance 2
            "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance 3
            "0x21a31ee1afc51d94c2efccaa2092ad1028285549",  # Binance 4
            "0x56eddb7aa87536c09ccc2793473599fd21a8b17f",  # Coinbase
            "0x503828976d22510aad0201ac7ec88293211d23da",  # Coinbase 2
            "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740",  # Coinbase 3
            "0x71660c4005ba85c37ccec55d0c4493e66fe775d3",  # Coinbase 4
            "0x503828976d22510aad0201ac7ec88293211d23da",  # Coinbase 5
            "0x89e51fa8ca5d66cd220baed62ed01e8951aa7c40",  # Coinbase 6
            "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",  # Kraken
            "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13",  # Kraken 2
            "0xe853c56864a2ebe4576a807d26fdc4a0ada51919",  # Kraken 3
        ]
    
    async def initialize(self):
        """Initialize the whale tracker"""
        logger.info("Initializing whale tracker...")
        await self._load_whale_wallets()
        await self._update_wallet_balances()
        logger.info(f"Whale tracker initialized with {len(self.whale_wallets)} wallets")
    
    async def _load_whale_wallets(self):
        """Load whale wallets from database"""
        async with self.data_manager.get_db_session() as session:
            stmt = select(WhaleWallet).where(
                and_(
                    WhaleWallet.balance_eth >= settings.min_whale_balance,
                    WhaleWallet.is_active == True
                )
            ).limit(settings.max_whale_wallets)
            
            result = await session.execute(stmt)
            self.whale_wallets = result.scalars().all()
    
    async def _update_wallet_balances(self):
        """Update wallet balances from Etherscan"""
        logger.info("Updating whale wallet balances...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for wallet in self.whale_wallets[:10]:  # Limit concurrent requests
                tasks.append(self._fetch_wallet_balance(session, wallet))
            
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _fetch_wallet_balance(self, session: aiohttp.ClientSession, wallet: WhaleWallet):
        """Fetch wallet balance from Etherscan"""
        try:
            url = f"{ETHERSCAN_BASE_URL}"
            params = {
                "module": "account",
                "action": "balance",
                "address": wallet.address,
                "tag": "latest",
                "apikey": settings.etherscan_api_key
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["status"] == "1":
                        balance_wei = int(data["result"])
                        balance_eth = balance_wei / 1e18
                        
                        # Update wallet balance
                        await self._update_wallet_balance(wallet.address, balance_eth)
                        
        except Exception as e:
            logger.error(f"Error fetching balance for wallet {wallet.address}: {e}")
    
    async def _update_wallet_balance(self, address: str, balance_eth: float):
        """Update wallet balance in database"""
        async with self.data_manager.get_db_session() as session:
            stmt = update(WhaleWallet).where(
                WhaleWallet.address == address
            ).values(
                balance_eth=balance_eth,
                balance_usd=balance_eth * await self._get_eth_price(),
                last_activity=datetime.utcnow()
            )
            await session.execute(stmt)
            await session.commit()
    
    async def _get_eth_price(self) -> float:
        """Get current ETH price from cache or API"""
        # Try cache first
        eth_price = await self.data_manager.get_cached_data("eth_price")
        if eth_price:
            return float(eth_price)
        
        # Fetch from API
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{ETHERSCAN_BASE_URL}"
                params = {
                    "module": "stats",
                    "action": "ethprice",
                    "apikey": settings.etherscan_api_key
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["status"] == "1":
                            price = float(data["result"]["ethusd"])
                            await self.data_manager.cache_data("eth_price", price, ttl=300)
                            return price
        except Exception as e:
            logger.error(f"Error fetching ETH price: {e}")
        
        return 3000.0  # Fallback price
    
    async def track_whale_transactions(self, hours_back: int = 24) -> List[WhaleActivity]:
        """Track whale transactions in the last N hours"""
        logger.info(f"Tracking whale transactions for last {hours_back} hours...")
        
        activities = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        async with aiohttp.ClientSession() as session:
            for wallet in self.whale_wallets:
                try:
                    wallet_activities = await self._fetch_wallet_transactions(
                        session, wallet, cutoff_time
                    )
                    activities.extend(wallet_activities)
                    
                    # Rate limiting
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Error tracking wallet {wallet.address}: {e}")
        
        # Sort by timestamp (newest first)
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        
        logger.info(f"Found {len(activities)} whale activities")
        return activities
    
    async def _fetch_wallet_transactions(self, session: aiohttp.ClientSession, 
                                       wallet: WhaleWallet, 
                                       cutoff_time: datetime) -> List[WhaleActivity]:
        """Fetch transactions for a specific wallet"""
        activities = []
        
        try:
            # Get ERC-20 token transfers
            url = f"{ETHERSCAN_BASE_URL}"
            params = {
                "module": "account",
                "action": "tokentx",
                "address": wallet.address,
                "startblock": 0,
                "endblock": 99999999,
                "sort": "desc",
                "apikey": settings.etherscan_api_key
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["status"] == "1":
                        for tx in data["result"][:50]:  # Limit to recent transactions
                            tx_time = datetime.fromtimestamp(int(tx["timeStamp"]))
                            
                            if tx_time < cutoff_time:
                                break
                            
                            # Skip known exchanges
                            if tx["from"] in self.known_exchange_addresses or \
                               tx["to"] in self.known_exchange_addresses:
                                continue
                            
                            # Determine transaction type
                            if tx["to"].lower() == wallet.address.lower():
                                tx_type = "buy"
                            elif tx["from"].lower() == wallet.address.lower():
                                tx_type = "sell"
                            else:
                                continue
                            
                            # Get token info
                            token_info = await self._get_token_info(tx["contractAddress"])
                            
                            # Calculate amounts
                            amount = float(tx["value"]) / (10 ** int(tx["tokenDecimal"]))
                            amount_usd = amount * token_info.get("price_usd", 0)
                            
                            # Calculate urgency score based on gas price
                            urgency_score = self._calculate_urgency_score(float(tx["gasPrice"]))
                            
                            # Calculate impact score
                            impact_score = self._calculate_impact_score(
                                amount_usd, token_info.get("market_cap", 0)
                            )
                            
                            activity = WhaleActivity(
                                wallet_address=wallet.address,
                                token_address=tx["contractAddress"],
                                token_symbol=token_info.get("symbol", "UNKNOWN"),
                                transaction_type=tx_type,
                                amount=amount,
                                amount_usd=amount_usd,
                                timestamp=tx_time,
                                gas_price_gwei=float(tx["gasPrice"]) / 1e9,
                                urgency_score=urgency_score,
                                impact_score=impact_score
                            )
                            
                            activities.append(activity)
                            
                            # Store transaction in database
                            await self._store_transaction(activity, tx, wallet)
                            
        except Exception as e:
            logger.error(f"Error fetching transactions for {wallet.address}: {e}")
        
        return activities
    
    async def _get_token_info(self, token_address: str) -> Dict:
        """Get token information from database or API"""
        # Try database first
        async with self.data_manager.get_db_session() as session:
            stmt = select(Token).where(Token.address == token_address)
            result = await session.execute(stmt)
            token = result.scalar_one_or_none()
            
            if token:
                return {
                    "symbol": token.symbol,
                    "name": token.name,
                    "price_usd": token.current_price,
                    "market_cap": token.market_cap,
                    "decimals": token.decimals
                }
        
        # Fallback to API if not in database
        return {
            "symbol": "UNKNOWN",
            "name": "Unknown Token",
            "price_usd": 0.0,
            "market_cap": 0.0,
            "decimals": 18
        }
    
    def _calculate_urgency_score(self, gas_price_wei: float) -> float:
        """Calculate urgency score based on gas price"""
        gas_price_gwei = gas_price_wei / 1e9
        
        # Higher gas price = higher urgency
        if gas_price_gwei > 100:
            return 1.0
        elif gas_price_gwei > 50:
            return 0.8
        elif gas_price_gwei > 20:
            return 0.6
        elif gas_price_gwei > 10:
            return 0.4
        else:
            return 0.2
    
    def _calculate_impact_score(self, amount_usd: float, market_cap: float) -> float:
        """Calculate market impact score"""
        if market_cap == 0:
            return 0.0
        
        # Calculate percentage of market cap
        impact_percentage = (amount_usd / market_cap) * 100
        
        # Scale to 0-1
        if impact_percentage > 1.0:
            return 1.0
        elif impact_percentage > 0.5:
            return 0.8
        elif impact_percentage > 0.1:
            return 0.6
        elif impact_percentage > 0.05:
            return 0.4
        else:
            return 0.2
    
    async def _store_transaction(self, activity: WhaleActivity, tx_data: Dict, wallet: WhaleWallet):
        """Store transaction in database"""
        try:
            async with self.data_manager.get_db_session() as session:
                transaction = WhaleTransaction(
                    whale_wallet_id=wallet.id,
                    tx_hash=tx_data["hash"],
                    block_number=int(tx_data["blockNumber"]),
                    timestamp=activity.timestamp,
                    token_address=activity.token_address,
                    token_symbol=activity.token_symbol,
                    token_name=await self._get_token_name(activity.token_address),
                    transaction_type=activity.transaction_type,
                    amount=activity.amount,
                    amount_usd=activity.amount_usd,
                    price_per_token=activity.amount_usd / activity.amount if activity.amount > 0 else 0,
                    gas_price_gwei=activity.gas_price_gwei,
                    gas_used=int(tx_data.get("gasUsed", 0)),
                    gas_cost_eth=float(tx_data.get("gasUsed", 0)) * float(tx_data.get("gasPrice", 0)) / 1e18,
                    gas_cost_usd=0,  # Will be calculated
                    token_price_at_tx=activity.amount_usd / activity.amount if activity.amount > 0 else 0,
                    is_large_transaction=activity.amount_usd > 100000,  # > $100k
                    urgency_score=activity.urgency_score,
                    impact_score=activity.impact_score
                )
                
                session.add(transaction)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing transaction: {e}")
    
    async def _get_token_name(self, token_address: str) -> str:
        """Get token name from database or return placeholder"""
        async with self.data_manager.get_db_session() as session:
            stmt = select(Token.name).where(Token.address == token_address)
            result = await session.execute(stmt)
            name = result.scalar_one_or_none()
            return name or "Unknown Token"
    
    async def analyze_accumulation_patterns(self, token_address: str, hours_back: int = 48) -> Dict:
        """Analyze whale accumulation patterns for a specific token"""
        logger.info(f"Analyzing accumulation patterns for {token_address}")
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        async with self.data_manager.get_db_session() as session:
            # Get all transactions for this token in the time window
            stmt = select(WhaleTransaction).where(
                and_(
                    WhaleTransaction.token_address == token_address,
                    WhaleTransaction.timestamp >= cutoff_time,
                    WhaleTransaction.transaction_type == "buy"
                )
            ).order_by(WhaleTransaction.timestamp.desc())
            
            result = await session.execute(stmt)
            transactions = result.scalars().all()
            
            # Analyze patterns
            analysis = {
                "token_address": token_address,
                "time_window_hours": hours_back,
                "total_buy_transactions": len(transactions),
                "unique_whale_wallets": len(set(tx.whale_wallet_id for tx in transactions)),
                "total_volume_usd": sum(tx.amount_usd for tx in transactions),
                "avg_transaction_size_usd": 0,
                "largest_transaction_usd": 0,
                "accumulation_score": 0.0,
                "urgency_trend": "stable",
                "whale_activity_summary": []
            }
            
            if transactions:
                analysis["avg_transaction_size_usd"] = analysis["total_volume_usd"] / len(transactions)
                analysis["largest_transaction_usd"] = max(tx.amount_usd for tx in transactions)
                
                # Calculate accumulation score
                analysis["accumulation_score"] = self._calculate_accumulation_score(transactions)
                
                # Analyze urgency trend
                analysis["urgency_trend"] = self._analyze_urgency_trend(transactions)
                
                # Get whale activity summary
                analysis["whale_activity_summary"] = await self._get_whale_activity_summary(transactions)
            
            return analysis
    
    def _calculate_accumulation_score(self, transactions: List[WhaleTransaction]) -> float:
        """Calculate accumulation score based on transaction patterns"""
        if not transactions:
            return 0.0
        
        # Factors: volume, number of unique wallets, urgency, timing
        volume_score = min(len(transactions) * 0.1, 1.0)
        wallet_diversity_score = min(len(set(tx.whale_wallet_id for tx in transactions)) * 0.2, 1.0)
        urgency_score = sum(tx.urgency_score for tx in transactions) / len(transactions)
        
        # Time clustering bonus (multiple transactions close together)
        time_clustering_score = self._calculate_time_clustering_score(transactions)
        
        total_score = (volume_score * 0.3 + 
                      wallet_diversity_score * 0.3 + 
                      urgency_score * 0.2 + 
                      time_clustering_score * 0.2)
        
        return min(total_score, 1.0)
    
    def _calculate_time_clustering_score(self, transactions: List[WhaleTransaction]) -> float:
        """Calculate time clustering score"""
        if len(transactions) < 2:
            return 0.0
        
        # Sort by timestamp
        sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
        
        # Calculate time differences between consecutive transactions
        time_diffs = []
        for i in range(1, len(sorted_txs)):
            diff = (sorted_txs[i].timestamp - sorted_txs[i-1].timestamp).total_seconds() / 3600  # hours
            time_diffs.append(diff)
        
        # If transactions are clustered within 6 hours, give bonus
        clustered_count = sum(1 for diff in time_diffs if diff < 6)
        clustering_ratio = clustered_count / len(time_diffs) if time_diffs else 0
        
        return clustering_ratio
    
    def _analyze_urgency_trend(self, transactions: List[WhaleTransaction]) -> str:
        """Analyze urgency trend over time"""
        if len(transactions) < 3:
            return "stable"
        
        # Sort by timestamp
        sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
        
        # Calculate average urgency for first half vs second half
        mid_point = len(sorted_txs) // 2
        first_half_urgency = sum(tx.urgency_score for tx in sorted_txs[:mid_point]) / mid_point
        second_half_urgency = sum(tx.urgency_score for tx in sorted_txs[mid_point:]) / (len(sorted_txs) - mid_point)
        
        if second_half_urgency > first_half_urgency * 1.2:
            return "rising"
        elif second_half_urgency < first_half_urgency * 0.8:
            return "falling"
        else:
            return "stable"
    
    async def _get_whale_activity_summary(self, transactions: List[WhaleTransaction]) -> List[Dict]:
        """Get summary of whale activity"""
        summary = []
        
        # Group by wallet
        wallet_activities = {}
        for tx in transactions:
            wallet_id = str(tx.whale_wallet_id)
            if wallet_id not in wallet_activities:
                wallet_activities[wallet_id] = {
                    "wallet_id": wallet_id,
                    "transaction_count": 0,
                    "total_volume_usd": 0,
                    "avg_urgency_score": 0,
                    "last_transaction_time": tx.timestamp
                }
            
            wallet_activities[wallet_id]["transaction_count"] += 1
            wallet_activities[wallet_id]["total_volume_usd"] += tx.amount_usd
            wallet_activities[wallet_id]["avg_urgency_score"] += tx.urgency_score
            wallet_activities[wallet_id]["last_transaction_time"] = max(
                wallet_activities[wallet_id]["last_transaction_time"], 
                tx.timestamp
            )
        
        # Calculate averages and sort by volume
        for wallet_id, activity in wallet_activities.items():
            activity["avg_urgency_score"] /= activity["transaction_count"]
            summary.append(activity)
        
        # Sort by total volume (descending)
        summary.sort(key=lambda x: x["total_volume_usd"], reverse=True)
        
        return summary[:10]  # Return top 10
    
    async def start_monitoring(self):
        """Start continuous whale monitoring"""
        logger.info("Starting whale monitoring...")
        self.is_running = True
        
        while self.is_running:
            try:
                # Track recent transactions
                activities = await self.track_whale_transactions(hours_back=2)
                
                # Analyze patterns for active tokens
                active_tokens = await self._get_active_tokens()
                for token_address in active_tokens[:5]:  # Limit to top 5
                    analysis = await self.analyze_accumulation_patterns(token_address)
                    
                    # Generate alerts for high-confidence patterns
                    if analysis["accumulation_score"] > 0.7:
                        await self._generate_accumulation_alert(analysis)
                
                # Wait before next iteration
                await asyncio.sleep(settings.whale_tracking_interval)
                
            except Exception as e:
                logger.error(f"Error in whale monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def stop_monitoring(self):
        """Stop whale monitoring"""
        logger.info("Stopping whale monitoring...")
        self.is_running = False
    
    async def _get_active_tokens(self) -> List[str]:
        """Get list of active tokens based on recent volume"""
        async with self.data_manager.get_db_session() as session:
            # Get tokens with recent high volume
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            stmt = select(WhaleTransaction.token_address).where(
                and_(
                    WhaleTransaction.timestamp >= cutoff_time,
                    WhaleTransaction.amount_usd > 50000  # > $50k transactions
                )
            ).distinct()
            
            result = await session.execute(stmt)
            return [row[0] for row in result.fetchall()]
    
    async def _generate_accumulation_alert(self, analysis: Dict):
        """Generate alert for significant accumulation pattern"""
        # This will be implemented in the alert system
        logger.info(f"Significant accumulation detected for {analysis['token_address']}: "
                   f"Score: {analysis['accumulation_score']:.2f}, "
                   f"Volume: ${analysis['total_volume_usd']:,.0f}")


