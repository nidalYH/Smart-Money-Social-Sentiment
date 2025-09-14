"""
Multi-Exchange Integration Manager
"""
import asyncio
import aiohttp
import hmac
import hashlib
import time
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class ExchangeType(Enum):
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    KUCOIN = "kucoin"
    BYBIT = "bybit"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

@dataclass
class Order:
    """Order data structure"""
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    price: Optional[float]
    status: str
    filled_quantity: float
    remaining_quantity: float
    timestamp: datetime
    exchange: ExchangeType

@dataclass
class Balance:
    """Account balance data structure"""
    asset: str
    free: float
    locked: float
    total: float
    exchange: ExchangeType

@dataclass
class Ticker:
    """Price ticker data structure"""
    symbol: str
    price: float
    volume: float
    change_24h: float
    high_24h: float
    low_24h: float
    timestamp: datetime
    exchange: ExchangeType

class BaseExchange(ABC):
    """Base exchange interface"""
    
    def __init__(self, api_key: str, secret_key: str, sandbox: bool = False):
        self.api_key = api_key
        self.secret_key = secret_key
        self.sandbox = sandbox
        self.base_url = self._get_base_url()
        self.session = None
    
    @abstractmethod
    def _get_base_url(self) -> str:
        """Get base API URL"""
        pass
    
    @abstractmethod
    async def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """Make authenticated API request"""
        pass
    
    @abstractmethod
    async def get_balance(self, asset: str = None) -> List[Balance]:
        """Get account balance"""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get price ticker"""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: float = None) -> Order:
        """Place order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel order"""
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str, symbol: str) -> Order:
        """Get order status"""
        pass
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

class BinanceExchange(BaseExchange):
    """Binance exchange implementation"""
    
    def _get_base_url(self) -> str:
        if self.sandbox:
            return "https://testnet.binance.vision"
        return "https://api.binance.com"
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """Make authenticated Binance API request"""
        try:
            if params is None:
                params = {}
            
            # Add timestamp
            params['timestamp'] = int(time.time() * 1000)
            
            # Create signature
            query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            params['signature'] = signature
            
            headers = {
                'X-MBX-APIKEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}{endpoint}"
            
            async with self.session.request(
                method, url, params=params, data=json.dumps(data) if data else None, headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Binance API error: {response.status} - {error_text}")
                    return {}
        
        except Exception as e:
            logger.error(f"Error making Binance request: {e}")
            return {}
    
    async def get_balance(self, asset: str = None) -> List[Balance]:
        """Get Binance account balance"""
        try:
            response = await self._make_request('GET', '/api/v3/account')
            
            balances = []
            for balance_data in response.get('balances', []):
                if asset and balance_data['asset'] != asset:
                    continue
                
                balance = Balance(
                    asset=balance_data['asset'],
                    free=float(balance_data['free']),
                    locked=float(balance_data['locked']),
                    total=float(balance_data['free']) + float(balance_data['locked']),
                    exchange=ExchangeType.BINANCE
                )
                balances.append(balance)
            
            return balances
        
        except Exception as e:
            logger.error(f"Error getting Binance balance: {e}")
            return []
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get Binance price ticker"""
        try:
            params = {'symbol': symbol.upper()}
            response = await self._make_request('GET', '/api/v3/ticker/24hr', params=params)
            
            return Ticker(
                symbol=symbol,
                price=float(response['lastPrice']),
                volume=float(response['volume']),
                change_24h=float(response['priceChangePercent']),
                high_24h=float(response['highPrice']),
                low_24h=float(response['lowPrice']),
                timestamp=datetime.utcnow(),
                exchange=ExchangeType.BINANCE
            )
        
        except Exception as e:
            logger.error(f"Error getting Binance ticker for {symbol}: {e}")
            return None
    
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: float = None) -> Order:
        """Place Binance order"""
        try:
            data = {
                'symbol': symbol.upper(),
                'side': side.value.upper(),
                'type': order_type.value.upper(),
                'quantity': str(quantity)
            }
            
            if price and order_type != OrderType.MARKET:
                data['price'] = str(price)
            
            response = await self._make_request('POST', '/api/v3/order', data=data)
            
            return Order(
                id=str(response['orderId']),
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                price=price,
                status=response['status'].lower(),
                filled_quantity=float(response.get('executedQty', 0)),
                remaining_quantity=float(response.get('origQty', 0)) - float(response.get('executedQty', 0)),
                timestamp=datetime.utcnow(),
                exchange=ExchangeType.BINANCE
            )
        
        except Exception as e:
            logger.error(f"Error placing Binance order: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel Binance order"""
        try:
            params = {
                'symbol': symbol.upper(),
                'orderId': order_id
            }
            
            response = await self._make_request('DELETE', '/api/v3/order', params=params)
            return response.get('status') == 'CANCELED'
        
        except Exception as e:
            logger.error(f"Error canceling Binance order: {e}")
            return False
    
    async def get_order(self, order_id: str, symbol: str) -> Order:
        """Get Binance order status"""
        try:
            params = {
                'symbol': symbol.upper(),
                'orderId': order_id
            }
            
            response = await self._make_request('GET', '/api/v3/order', params=params)
            
            return Order(
                id=str(response['orderId']),
                symbol=symbol,
                side=OrderSide(response['side'].lower()),
                type=OrderType(response['type'].lower()),
                quantity=float(response['origQty']),
                price=float(response.get('price', 0)) if response.get('price') else None,
                status=response['status'].lower(),
                filled_quantity=float(response['executedQty']),
                remaining_quantity=float(response['origQty']) - float(response['executedQty']),
                timestamp=datetime.utcnow(),
                exchange=ExchangeType.BINANCE
            )
        
        except Exception as e:
            logger.error(f"Error getting Binance order: {e}")
            return None

class CoinbaseExchange(BaseExchange):
    """Coinbase Pro exchange implementation"""
    
    def _get_base_url(self) -> str:
        if self.sandbox:
            return "https://api-public.sandbox.pro.coinbase.com"
        return "https://api.pro.coinbase.com"
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """Make authenticated Coinbase API request"""
        try:
            timestamp = str(int(time.time()))
            message = timestamp + method + endpoint + (json.dumps(data) if data else '')
            
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'CB-ACCESS-KEY': self.api_key,
                'CB-ACCESS-SIGN': signature,
                'CB-ACCESS-TIMESTAMP': timestamp,
                'CB-ACCESS-PASSPHRASE': 'your_passphrase',  # This should be configurable
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}{endpoint}"
            
            async with self.session.request(
                method, url, params=params, data=json.dumps(data) if data else None, headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Coinbase API error: {response.status} - {error_text}")
                    return {}
        
        except Exception as e:
            logger.error(f"Error making Coinbase request: {e}")
            return {}
    
    async def get_balance(self, asset: str = None) -> List[Balance]:
        """Get Coinbase account balance"""
        try:
            response = await self._make_request('GET', '/accounts')
            
            balances = []
            for balance_data in response:
                if asset and balance_data['currency'] != asset:
                    continue
                
                balance = Balance(
                    asset=balance_data['currency'],
                    free=float(balance_data['available']),
                    locked=float(balance_data['hold']),
                    total=float(balance_data['balance']),
                    exchange=ExchangeType.COINBASE
                )
                balances.append(balance)
            
            return balances
        
        except Exception as e:
            logger.error(f"Error getting Coinbase balance: {e}")
            return []
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get Coinbase price ticker"""
        try:
            endpoint = f"/products/{symbol}/ticker"
            response = await self._make_request('GET', endpoint)
            
            return Ticker(
                symbol=symbol,
                price=float(response['price']),
                volume=float(response['volume']),
                change_24h=0.0,  # Coinbase doesn't provide this in ticker
                high_24h=0.0,
                low_24h=0.0,
                timestamp=datetime.utcnow(),
                exchange=ExchangeType.COINBASE
            )
        
        except Exception as e:
            logger.error(f"Error getting Coinbase ticker for {symbol}: {e}")
            return None
    
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: float = None) -> Order:
        """Place Coinbase order"""
        try:
            data = {
                'product_id': symbol,
                'side': side.value,
                'size': str(quantity),
                'type': order_type.value
            }
            
            if price and order_type != OrderType.MARKET:
                data['price'] = str(price)
            
            response = await self._make_request('POST', '/orders', data=data)
            
            return Order(
                id=response['id'],
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                price=price,
                status=response['status'],
                filled_quantity=float(response.get('filled_size', 0)),
                remaining_quantity=float(response.get('size', 0)) - float(response.get('filled_size', 0)),
                timestamp=datetime.utcnow(),
                exchange=ExchangeType.COINBASE
            )
        
        except Exception as e:
            logger.error(f"Error placing Coinbase order: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel Coinbase order"""
        try:
            response = await self._make_request('DELETE', f'/orders/{order_id}')
            return response.get('status') == 'cancelled'
        
        except Exception as e:
            logger.error(f"Error canceling Coinbase order: {e}")
            return False
    
    async def get_order(self, order_id: str, symbol: str) -> Order:
        """Get Coinbase order status"""
        try:
            response = await self._make_request('GET', f'/orders/{order_id}')
            
            return Order(
                id=response['id'],
                symbol=symbol,
                side=OrderSide(response['side']),
                type=OrderType(response['type']),
                quantity=float(response['size']),
                price=float(response.get('price', 0)) if response.get('price') else None,
                status=response['status'],
                filled_quantity=float(response.get('filled_size', 0)),
                remaining_quantity=float(response['size']) - float(response.get('filled_size', 0)),
                timestamp=datetime.utcnow(),
                exchange=ExchangeType.COINBASE
            )
        
        except Exception as e:
            logger.error(f"Error getting Coinbase order: {e}")
            return None

class ExchangeManager:
    """Multi-exchange management system"""
    
    def __init__(self, config: Dict[str, Dict[str, Any]]):
        self.config = config
        self.exchanges = {}
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize configured exchanges"""
        for exchange_name, exchange_config in self.config.items():
            try:
                if exchange_name == 'binance':
                    self.exchanges[ExchangeType.BINANCE] = BinanceExchange(
                        api_key=exchange_config.get('api_key'),
                        secret_key=exchange_config.get('secret_key'),
                        sandbox=exchange_config.get('sandbox', False)
                    )
                elif exchange_name == 'coinbase':
                    self.exchanges[ExchangeType.COINBASE] = CoinbaseExchange(
                        api_key=exchange_config.get('api_key'),
                        secret_key=exchange_config.get('secret_key'),
                        sandbox=exchange_config.get('sandbox', False)
                    )
                # Add more exchanges as needed
                
            except Exception as e:
                logger.error(f"Error initializing {exchange_name}: {e}")
    
    async def get_balance(self, exchange: ExchangeType, asset: str = None) -> List[Balance]:
        """Get balance from specific exchange"""
        if exchange not in self.exchanges:
            logger.error(f"Exchange {exchange} not configured")
            return []
        
        async with self.exchanges[exchange] as exchange_client:
            return await exchange_client.get_balance(asset)
    
    async def get_ticker(self, exchange: ExchangeType, symbol: str) -> Ticker:
        """Get ticker from specific exchange"""
        if exchange not in self.exchanges:
            logger.error(f"Exchange {exchange} not configured")
            return None
        
        async with self.exchanges[exchange] as exchange_client:
            return await exchange_client.get_ticker(symbol)
    
    async def place_order(self, exchange: ExchangeType, symbol: str, side: OrderSide, 
                         order_type: OrderType, quantity: float, price: float = None) -> Order:
        """Place order on specific exchange"""
        if exchange not in self.exchanges:
            logger.error(f"Exchange {exchange} not configured")
            return None
        
        async with self.exchanges[exchange] as exchange_client:
            return await exchange_client.place_order(symbol, side, order_type, quantity, price)
    
    async def get_best_price(self, symbol: str, side: OrderSide) -> Tuple[ExchangeType, float]:
        """Get best price across all exchanges"""
        best_price = None
        best_exchange = None
        
        for exchange_type in self.exchanges.keys():
            try:
                ticker = await self.get_ticker(exchange_type, symbol)
                if ticker:
                    price = ticker.price
                    if side == OrderSide.BUY:
                        if best_price is None or price < best_price:
                            best_price = price
                            best_exchange = exchange_type
                    else:  # SELL
                        if best_price is None or price > best_price:
                            best_price = price
                            best_exchange = exchange_type
            
            except Exception as e:
                logger.error(f"Error getting price from {exchange_type}: {e}")
                continue
        
        return best_exchange, best_price
    
    async def get_all_balances(self) -> Dict[ExchangeType, List[Balance]]:
        """Get balances from all exchanges"""
        all_balances = {}
        
        for exchange_type in self.exchanges.keys():
            try:
                balances = await self.get_balance(exchange_type)
                all_balances[exchange_type] = balances
            except Exception as e:
                logger.error(f"Error getting balances from {exchange_type}: {e}")
                all_balances[exchange_type] = []
        
        return all_balances
