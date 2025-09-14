"""
Trading API routes for real-time trading functionality
Provides endpoints for signal execution, portfolio management, and trading controls
"""
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from ..trading.paper_trading import PaperTradingEngine
from ..free_apis.free_signal_engine import FreeSignalEngine
from ..config import settings

logger = logging.getLogger(__name__)

# Global trading engine instance
trading_engine: Optional[PaperTradingEngine] = None
signal_engine: Optional[FreeSignalEngine] = None
auto_trading_enabled = False

# Pydantic models for requests
class SignalExecutionRequest(BaseModel):
    symbol: str
    signal_type: str
    confidence: float
    reasoning: str
    current_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    signal_id: Optional[str] = None

class PositionCloseRequest(BaseModel):
    symbol: str
    reason: Optional[str] = "MANUAL"

class AutoTradingRequest(BaseModel):
    enabled: bool
    risk_per_trade: Optional[float] = None
    max_positions: Optional[int] = None

class ManualOrderRequest(BaseModel):
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: Optional[float] = None
    amount_usd: Optional[float] = None

# Create API router
router = APIRouter(prefix="/api/trading", tags=["trading"])

def get_trading_engine() -> PaperTradingEngine:
    """Get or create trading engine instance"""
    global trading_engine
    if trading_engine is None:
        trading_engine = PaperTradingEngine(
            initial_balance=float(settings.get("INITIAL_DEMO_BALANCE", 100000)),
            max_positions=int(settings.get("MAX_POSITIONS", 10))
        )
    return trading_engine

def get_signal_engine() -> FreeSignalEngine:
    """Get or create signal engine instance"""
    global signal_engine
    if signal_engine is None:
        etherscan_key = settings.get("ETHERSCAN_API_KEY")
        if not etherscan_key:
            raise HTTPException(status_code=500, detail="ETHERSCAN_API_KEY not configured")
        signal_engine = FreeSignalEngine(etherscan_key)
    return signal_engine

@router.post("/execute-signal")
async def execute_trading_signal(request: SignalExecutionRequest):
    """Execute a trading signal in paper trading mode"""
    try:
        trading_engine = get_trading_engine()

        # Convert request to signal format
        signal = {
            "symbol": request.symbol,
            "signal_type": request.signal_type,
            "confidence": request.confidence,
            "reasoning": request.reasoning,
            "current_price": request.current_price,
            "target_price": request.target_price,
            "stop_loss": request.stop_loss,
            "signal_id": request.signal_id
        }

        # Execute signal
        result = await trading_engine.execute_signal(signal)

        if result["success"]:
            logger.info(f"Signal executed successfully: {request.symbol} {request.signal_type}")
            return {
                "success": True,
                "message": f"{request.signal_type} order executed for {request.symbol}",
                "trade": result.get("trade"),
                "position": result.get("position"),
                "remaining_balance": result.get("remaining_balance")
            }
        else:
            return {
                "success": False,
                "reason": result["reason"],
                "message": f"Failed to execute {request.signal_type} for {request.symbol}"
            }

    except Exception as e:
        logger.error(f"Error executing signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/manual-order")
async def place_manual_order(request: ManualOrderRequest):
    """Place a manual buy/sell order"""
    try:
        trading_engine = get_trading_engine()

        if request.side == "BUY":
            # Create a manual buy signal
            signal = {
                "symbol": request.symbol,
                "signal_type": "BUY",
                "confidence": 0.8,  # High confidence for manual orders
                "reasoning": "Manual buy order from dashboard",
                "signal_id": f"manual_{datetime.utcnow().timestamp()}"
            }

            result = await trading_engine.execute_signal(signal)

        elif request.side == "SELL":
            # Close existing position
            current_price = await trading_engine._get_current_price(request.symbol)
            if not current_price:
                raise HTTPException(status_code=400, detail="Unable to get current price")

            result = await trading_engine._close_position(
                request.symbol, current_price, "MANUAL"
            )

        else:
            raise HTTPException(status_code=400, detail="Invalid side. Must be 'BUY' or 'SELL'")

        return {
            "success": result["success"],
            "trade": result.get("trade"),
            "message": f"Manual {request.side} executed for {request.symbol}"
        }

    except Exception as e:
        logger.error(f"Error placing manual order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/close-position")
async def close_position(request: PositionCloseRequest):
    """Close an existing position"""
    try:
        trading_engine = get_trading_engine()

        # Get current price
        current_price = await trading_engine._get_current_price(request.symbol)
        if not current_price:
            raise HTTPException(status_code=400, detail="Unable to get current price")

        # Close the position
        result = await trading_engine._close_position(
            request.symbol, current_price, request.reason
        )

        if result["success"]:
            return {
                "success": True,
                "message": f"Position closed for {request.symbol}",
                "trade": result["trade"],
                "realized_pnl": result["realized_pnl"],
                "hold_duration_hours": result["hold_duration_hours"]
            }
        else:
            return {
                "success": False,
                "reason": result["reason"]
            }

    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/close-all-positions")
async def close_all_positions():
    """Close all open positions"""
    try:
        trading_engine = get_trading_engine()
        results = await trading_engine.close_all_positions("MANUAL")

        successful_closes = [r for r in results if r.get("success")]
        failed_closes = [r for r in results if not r.get("success")]

        return {
            "success": True,
            "message": f"Closed {len(successful_closes)} positions, {len(failed_closes)} failed",
            "closed_positions": len(successful_closes),
            "failed_positions": len(failed_closes),
            "results": results
        }

    except Exception as e:
        logger.error(f"Error closing all positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio")
async def get_portfolio_metrics():
    """Get current portfolio performance metrics"""
    try:
        trading_engine = get_trading_engine()
        metrics = await trading_engine.get_portfolio_metrics()

        return {
            "total_value": metrics.total_value,
            "cash_balance": metrics.cash_balance,
            "positions_value": metrics.positions_value,
            "total_return": metrics.total_return,
            "total_return_pct": metrics.total_return_pct,
            "daily_return_pct": metrics.daily_return_pct,
            "unrealized_pnl": metrics.unrealized_pnl,
            "realized_pnl": metrics.realized_pnl,
            "total_pnl": metrics.total_pnl,
            "win_rate": metrics.win_rate,
            "profit_factor": metrics.profit_factor,
            "sharpe_ratio": metrics.sharpe_ratio,
            "max_drawdown": metrics.max_drawdown,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "losing_trades": metrics.losing_trades,
            "avg_hold_time": metrics.avg_hold_time,
            "last_updated": metrics.last_updated.isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting portfolio metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions")
async def get_current_positions():
    """Get all current open positions"""
    try:
        trading_engine = get_trading_engine()

        # Update positions with current prices
        await trading_engine.update_positions()

        positions = trading_engine.get_position_summary()
        return positions

    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades")
async def get_trade_history(limit: int = 50):
    """Get recent trade history"""
    try:
        trading_engine = get_trading_engine()
        trades = trading_engine.get_recent_trades(limit)
        return trades

    except Exception as e:
        logger.error(f"Error getting trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auto-trading")
async def toggle_auto_trading(request: AutoTradingRequest):
    """Enable or disable automatic trading"""
    global auto_trading_enabled

    try:
        auto_trading_enabled = request.enabled

        # Update trading engine settings if provided
        trading_engine = get_trading_engine()

        if request.risk_per_trade:
            trading_engine.max_risk_per_trade = request.risk_per_trade

        if request.max_positions:
            trading_engine.max_positions = request.max_positions

        logger.info(f"Auto-trading {'enabled' if request.enabled else 'disabled'}")

        return {
            "success": True,
            "auto_trading_enabled": auto_trading_enabled,
            "message": f"Auto-trading {'enabled' if request.enabled else 'disabled'}",
            "settings": {
                "max_risk_per_trade": trading_engine.max_risk_per_trade,
                "max_positions": trading_engine.max_positions,
                "min_confidence_threshold": trading_engine.min_confidence_threshold
            }
        }

    except Exception as e:
        logger.error(f"Error toggling auto-trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auto-trading/status")
async def get_auto_trading_status():
    """Get current auto-trading status"""
    return {
        "auto_trading_enabled": auto_trading_enabled,
        "settings": {
            "max_risk_per_trade": get_trading_engine().max_risk_per_trade,
            "max_positions": get_trading_engine().max_positions,
            "min_confidence_threshold": get_trading_engine().min_confidence_threshold
        }
    }

@router.get("/performance/export")
async def export_performance_data():
    """Export all performance data for analysis"""
    try:
        trading_engine = get_trading_engine()
        data = trading_engine.export_performance_data()
        return data

    except Exception as e:
        logger.error(f"Error exporting performance data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-portfolio")
async def reset_portfolio():
    """Reset portfolio to initial state (demo only)"""
    global trading_engine

    try:
        # Create new trading engine instance
        initial_balance = float(settings.get("INITIAL_DEMO_BALANCE", 100000))
        trading_engine = PaperTradingEngine(initial_balance=initial_balance)

        logger.info(f"Portfolio reset to ${initial_balance:,.2f}")

        return {
            "success": True,
            "message": f"Portfolio reset to ${initial_balance:,.2f}",
            "initial_balance": initial_balance
        }

    except Exception as e:
        logger.error(f"Error resetting portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-overview")
async def get_market_overview():
    """Get market overview for trading decisions"""
    try:
        signal_engine = get_signal_engine()
        overview = await signal_engine.get_market_overview()
        return overview

    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task for position monitoring
async def monitor_positions():
    """Background task to monitor positions and execute stop losses/take profits"""
    global auto_trading_enabled

    while True:
        try:
            if auto_trading_enabled:
                trading_engine = get_trading_engine()

                # Update all positions and check exit conditions
                update_result = await trading_engine.update_positions()

                # Log any exits that were executed
                for exit in update_result.get("exits_executed", []):
                    if exit.get("success"):
                        logger.info(f"Auto-exit executed: {exit}")

            # Wait 30 seconds before next check
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Error in position monitoring: {e}")
            await asyncio.sleep(60)  # Wait longer on error

# Start background monitoring when module is imported
import threading
def start_background_monitoring():
    """Start background position monitoring"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(monitor_positions())

# Start monitoring in background thread
monitoring_thread = threading.Thread(target=start_background_monitoring, daemon=True)
monitoring_thread.start()

logger.info("Trading API routes initialized")