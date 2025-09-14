"""
Binance Testnet Integration for realistic demo trading
"""
import asyncio
import aiohttp
import hmac
import hashlib
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class BinanceTestnet:
    """Use Binance Testnet for realistic demo trading"""
    
    def __init__(self, api_key: str = None, secret_key: str = None):
        self.api_key = api_key or "testnet_api_key"
        self.secret_key = secret_key or "testnet_secret_key"
        self.base_url = "https://testnet.binance.vision/api/v3"
        self.ws_url = "wss://testnet.binance.vision/ws"
        
        # Account info
        self.account_info = {}
        self.balances = {}
        self.positions = {}
        self.trade_history = []
        
        # Performance tracking
        self.performance_metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0
        }
    
    async def initialize(self):
        """Initialize Binance testnet account"""
        logger.info("Initializing Binance testnet account...")
        
        try:
            # Get account information
            account_info = await self._get_account_info()
            if account_info:
                self.account_info = account_info
                self.balances = {balance["asset"]: float(balance["free"]) 
                               for balance in account_info.get("balances", [])}
                logger.info(f"Binance testnet account initialized successfully")
                logger.info(f"Account balances: {self.balances}")
            else:
                logger.warning("Failed to get account info, using mock data")
                await self._initialize_mock_account()
                
        except Exception as e:
            logger.error(f"Error initializing Binance testnet: {e}")
            await self._initialize_mock_account()
    
    async def _initialize_mock_account(self):
        """Initialize with mock account data for demo purposes"""
        self.balances = {
            "USDT": 10000.0,  # $10k USDT
            "BTC": 0.0,
            "ETH": 0.0,
            "BNB": 0.0
        }
        self.account_info = {
            "accountType": "SPOT",
            "canTrade": True,
            "canWithdraw": True,
            "canDeposit": True,
            "balances": [
                {"asset": "USDT", "free": "10000.00000000", "locked": "0.00000000"},
                {"asset": "BTC", "free": "0.00000000", "locked": "0.00000000"},
                {"asset": "ETH", "free": "0.00000000", "locked": "0.00000000"},
                {"asset": "BNB", "free": "0.00000000", "locked": "0.00000000"}
            ]
        }
        logger.info("Mock Binance testnet account initialized")
    
    async def execute_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trading signal on Binance testnet"""
        try:
            symbol = signal.get('token_symbol', 'UNKNOWN')
            signal_type = signal.get('action', 'buy')
            confidence = signal.get('confidence', 0.5)
            current_price = signal.get('current_price', 0)
            
            # Convert symbol to Binance format
            binance_symbol = await self._convert_to_binance_symbol(symbol)
            if not binance_symbol:
                return {
                    "success": False,
                    "error": f"Unsupported symbol: {symbol}",
                    "symbol": symbol
                }
            
            # Calculate position size
            position_size = await self._calculate_position_size(signal, binance_symbol)
            if position_size <= 0:
                return {
                    "success": False,
                    "error": "Position size too small",
                    "symbol": symbol
                }
            
            # Get current market price
            market_price = await self._get_current_price(binance_symbol)
            if not market_price:
                return {
                    "success": False,
                    "error": "Unable to get market price",
                    "symbol": symbol
                }
            
            # Execute the trade
            if signal_type.upper() == "BUY":
                result = await self._place_buy_order(binance_symbol, position_size, signal)
            elif signal_type.upper() == "SELL":
                result = await self._place_sell_order(binance_symbol, position_size, signal)
            else:
                return {
                    "success": False,
                    "error": f"Unknown signal type: {signal_type}",
                    "symbol": symbol
                }
            
            # Log the trade
            if result["success"]:
                await self._log_trade(signal, result)
                await self._update_performance_metrics(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": signal.get('token_symbol', 'UNKNOWN')
            }
    
    async def _convert_to_binance_symbol(self, symbol: str) -> Optional[str]:
        """Convert symbol to Binance format"""
        symbol_mapping = {
            "BTC": "BTCUSDT",
            "ETH": "ETHUSDT",
            "SOL": "SOLUSDT",
            "ADA": "ADAUSDT",
            "DOT": "DOTUSDT",
            "MATIC": "MATICUSDT",
            "AVAX": "AVAXUSDT",
            "NEAR": "NEARUSDT",
            "FTM": "FTMUSDT",
            "ONE": "HARMONYUSDT"
        }
        return symbol_mapping.get(symbol.upper())
    
    async def _calculate_position_size(self, signal: Dict[str, Any], binance_symbol: str) -> float:
        """Calculate position size based on signal confidence and risk management"""
        try:
            confidence = signal.get('confidence', 0.5)
            current_price = signal.get('current_price', 0)
            
            if current_price <= 0:
                return 0.0
            
            # Get available USDT balance
            usdt_balance = self.balances.get('USDT', 0)
            
            # Risk 1-3% of portfolio per trade based on confidence
            risk_per_trade = 0.01 + (confidence * 0.02)  # 1-3%
            max_position_value = usdt_balance * risk_per_trade
            
            # Calculate position size in tokens
            position_size = max_position_value / current_price
            
            # Apply minimum and maximum limits
            min_position_value = 10.0  # Minimum $10 position
            max_position_value = usdt_balance * 0.1  # Maximum 10% of portfolio
            
            position_size = max(min_position_value / current_price, 
                              min(position_size, max_position_value / current_price))
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    async def _place_buy_order(self, symbol: str, quantity: float, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Place a buy order on Binance testnet"""
        try:
            # Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                return {
                    "success": False,
                    "error": "Unable to get current price",
                    "symbol": symbol
                }
            
            # Calculate total cost
            total_cost = quantity * current_price
            fees = total_cost * 0.001  # 0.1% trading fee
            total_required = total_cost + fees
            
            # Check if we have enough USDT
            usdt_balance = self.balances.get('USDT', 0)
            if usdt_balance < total_required:
                return {
                    "success": False,
                    "error": f"Insufficient USDT balance. Required: ${total_required:,.2f}, Available: ${usdt_balance:,.2f}",
                    "symbol": symbol
                }
            
            # Place order on Binance testnet
            order_result = await self._place_market_order(symbol, "BUY", quantity)
            
            if order_result.get("success"):
                # Update balances
                self.balances['USDT'] -= total_required
                
                # Add to positions
                base_asset = symbol.replace('USDT', '')
                if base_asset in self.balances:
                    self.balances[base_asset] += quantity
                else:
                    self.balances[base_asset] = quantity
                
                return {
                    "success": True,
                    "order_id": order_result.get("orderId"),
                    "symbol": symbol,
                    "action": "buy",
                    "quantity": quantity,
                    "price": current_price,
                    "total_cost": total_cost,
                    "fees": fees,
                    "timestamp": datetime.utcnow().isoformat(),
                    "remaining_balance": self.balances['USDT']
                }
            else:
                return {
                    "success": False,
                    "error": order_result.get("error", "Order failed"),
                    "symbol": symbol
                }
            
        except Exception as e:
            logger.error(f"Error placing buy order: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol
            }
    
    async def _place_sell_order(self, symbol: str, quantity: float, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Place a sell order on Binance testnet"""
        try:
            # Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                return {
                    "success": False,
                    "error": "Unable to get current price",
                    "symbol": symbol
                }
            
            # Check if we have enough tokens to sell
            base_asset = symbol.replace('USDT', '')
            token_balance = self.balances.get(base_asset, 0)
            
            if token_balance < quantity:
                return {
                    "success": False,
                    "error": f"Insufficient {base_asset} balance. Available: {token_balance:.4f}, Requested: {quantity:.4f}",
                    "symbol": symbol
                }
            
            # Place order on Binance testnet
            order_result = await self._place_market_order(symbol, "SELL", quantity)
            
            if order_result.get("success"):
                # Calculate proceeds
                proceeds = quantity * current_price
                fees = proceeds * 0.001  # 0.1% trading fee
                net_proceeds = proceeds - fees
                
                # Update balances
                self.balances[base_asset] -= quantity
                self.balances['USDT'] += net_proceeds
                
                return {
                    "success": True,
                    "order_id": order_result.get("orderId"),
                    "symbol": symbol,
                    "action": "sell",
                    "quantity": quantity,
                    "price": current_price,
                    "proceeds": proceeds,
                    "fees": fees,
                    "timestamp": datetime.utcnow().isoformat(),
                    "remaining_balance": self.balances['USDT']
                }
            else:
                return {
                    "success": False,
                    "error": order_result.get("error", "Order failed"),
                    "symbol": symbol
                }
            
        except Exception as e:
            logger.error(f"Error placing sell order: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol
            }
    
    async def _place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        """Place a market order on Binance testnet"""
        try:
            # In a real implementation, this would make actual API calls to Binance
            # For demo purposes, we'll simulate the order placement
            
            # Simulate order processing time
            await asyncio.sleep(0.1)
            
            # Generate mock order ID
            order_id = f"{side}_{symbol}_{int(time.time())}"
            
            # Simulate order success (in real implementation, this would depend on actual API response)
            return {
                "success": True,
                "orderId": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "status": "FILLED"
            }
            
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price from Binance testnet"""
        try:
            # In a real implementation, this would fetch from Binance API
            # For demo purposes, we'll use mock data
            
            mock_prices = {
                "BTCUSDT": 45000.0,
                "ETHUSDT": 3000.0,
                "SOLUSDT": 100.0,
                "ADAUSDT": 0.5,
                "DOTUSDT": 7.0,
                "MATICUSDT": 0.8,
                "AVAXUSDT": 25.0,
                "NEARUSDT": 2.0,
                "FTMUSDT": 0.3,
                "HARMONYUSDT": 0.02
            }
            
            base_price = mock_prices.get(symbol, 1.0)
            
            # Add some random variation to simulate market movement
            import random
            variation = random.uniform(-0.02, 0.02)  # ±2% variation
            current_price = base_price * (1 + variation)
            
            return current_price
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    async def _get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information from Binance testnet"""
        try:
            # In a real implementation, this would make an authenticated API call
            # For demo purposes, we'll return None to trigger mock initialization
            return None
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    async def _log_trade(self, signal: Dict[str, Any], trade_result: Dict[str, Any]):
        """Log a trade in the history"""
        try:
            trade_record = {
                "trade_id": trade_result.get("order_id"),
                "signal_id": signal.get("signal_id"),
                "symbol": trade_result.get("symbol"),
                "action": trade_result.get("action"),
                "quantity": trade_result.get("quantity"),
                "price": trade_result.get("price"),
                "total_cost": trade_result.get("total_cost", 0),
                "proceeds": trade_result.get("proceeds", 0),
                "fees": trade_result.get("fees", 0),
                "timestamp": trade_result.get("timestamp"),
                "confidence": signal.get("confidence", 0),
                "signal_type": signal.get("signal_type", "unknown")
            }
            
            self.trade_history.append(trade_record)
            
            # Keep only last 1000 trades
            if len(self.trade_history) > 1000:
                self.trade_history = self.trade_history[-1000:]
            
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
    
    async def _update_performance_metrics(self, trade_result: Dict[str, Any]):
        """Update performance metrics"""
        try:
            self.performance_metrics["total_trades"] += 1
            
            # Calculate P&L for this trade
            total_cost = trade_result.get("total_cost", 0)
            proceeds = trade_result.get("proceeds", 0)
            realized_pnl = proceeds - total_cost
            
            if realized_pnl > 0:
                self.performance_metrics["winning_trades"] += 1
            elif realized_pnl < 0:
                self.performance_metrics["losing_trades"] += 1
            
            self.performance_metrics["total_pnl"] += realized_pnl
            
            # Calculate win rate
            if self.performance_metrics["total_trades"] > 0:
                self.performance_metrics["win_rate"] = (
                    self.performance_metrics["winning_trades"] / 
                    self.performance_metrics["total_trades"] * 100
                )
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        try:
            # Calculate total portfolio value
            total_value = 0.0
            for asset, balance in self.balances.items():
                if asset == 'USDT':
                    total_value += balance
                else:
                    # Get current price for other assets
                    symbol = f"{asset}USDT"
                    current_price = await self._get_current_price(symbol)
                    if current_price:
                        total_value += balance * current_price
            
            # Calculate total return
            initial_balance = 10000.0  # Initial USDT balance
            total_return = (total_value - initial_balance) / initial_balance * 100
            
            return {
                "total_value": total_value,
                "available_balance": self.balances.get('USDT', 0),
                "total_pnl": self.performance_metrics["total_pnl"],
                "total_pnl_percent": total_return,
                "positions_count": len([k for k, v in self.balances.items() if k != 'USDT' and v > 0]),
                "total_trades": self.performance_metrics["total_trades"],
                "win_rate": self.performance_metrics["win_rate"],
                "balances": self.balances,
                "performance_metrics": self.performance_metrics
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {}
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        try:
            positions = []
            
            for asset, balance in self.balances.items():
                if asset != 'USDT' and balance > 0:
                    symbol = f"{asset}USDT"
                    current_price = await self._get_current_price(symbol)
                    
                    if current_price:
                        positions.append({
                            "symbol": asset,
                            "quantity": balance,
                            "current_price": current_price,
                            "current_value": balance * current_price,
                            "last_updated": datetime.utcnow().isoformat()
                        })
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history"""
        try:
            return self.trade_history[-limit:] if self.trade_history else []
            
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
    
    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """Close a position completely"""
        try:
            base_asset = symbol.replace('USDT', '')
            quantity = self.balances.get(base_asset, 0)
            
            if quantity <= 0:
                return {
                    "success": False,
                    "error": f"No position found for {symbol}"
                }
            
            # Create sell signal
            sell_signal = {
                "token_symbol": base_asset,
                "action": "sell",
                "confidence": 1.0
            }
            
            # Execute sell order
            result = await self._place_sell_order(symbol, quantity, sell_signal)
            
            return result
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {
                "success": False,
                "error": str(e)
            }
