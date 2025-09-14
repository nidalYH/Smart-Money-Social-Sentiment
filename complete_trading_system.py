#!/usr/bin/env python3
"""
Complete Smart Money Trading System
Ready-to-use trading system with real-time dashboard and demo trading
"""
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from app.core.data_manager import DataManager
from app.core.whale_tracker import WhaleTracker
from app.core.sentiment_analyzer import SentimentAnalyzer
from app.core.signal_engine import SignalEngine
from app.core.alert_manager import AlertManager
from app.core.paper_trading import PaperTradingEngine
from app.trading.trading_controller import TradingController
from app.trading.tradingview_demo import TradingViewDemo
from app.trading.binance_testnet import BinanceTestnet
from app.websocket_manager import websocket_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
data_manager = None
whale_tracker = None
sentiment_analyzer = None
signal_engine = None
alert_manager = None
paper_trading = None
trading_controller = None
trading_platform = None

# Create FastAPI app
app = FastAPI(
    title="Smart Money Trading System",
    description="Complete trading system with whale tracking, sentiment analysis, and automated execution",
    version="2.0.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup"""
    global data_manager, whale_tracker, sentiment_analyzer, signal_engine
    global alert_manager, paper_trading, trading_controller, trading_platform
    
    logger.info("🚀 Starting Smart Money Trading System...")
    
    try:
        # Initialize data manager
        data_manager = DataManager()
        await data_manager.initialize()
        logger.info("✅ Data manager initialized")
        
        # Initialize core components
        whale_tracker = WhaleTracker(data_manager)
        sentiment_analyzer = SentimentAnalyzer(data_manager)
        signal_engine = SignalEngine(data_manager)
        alert_manager = AlertManager(data_manager)
        paper_trading = PaperTradingEngine(data_manager)
        
        # Initialize trading platform (choose one)
        trading_platform = TradingViewDemo(demo_balance=100000)  # or BinanceTestnet()
        await trading_platform.initialize()
        logger.info("✅ Trading platform initialized")
        
        # Initialize trading controller
        trading_controller = TradingController(data_manager)
        await trading_controller.initialize()
        logger.info("✅ Trading controller initialized")
        
        # Initialize WebSocket manager
        await websocket_manager.start()
        logger.info("✅ WebSocket manager started")
        
        # Initialize all components
        await whale_tracker.initialize()
        await sentiment_analyzer.initialize()
        await signal_engine.initialize()
        await alert_manager.initialize()
        await paper_trading.initialize()
        
        # Start background tasks
        asyncio.create_task(whale_tracker.start_monitoring())
        asyncio.create_task(sentiment_analyzer.start_monitoring())
        asyncio.create_task(signal_engine.start_signal_generation())
        asyncio.create_task(alert_manager.start_alert_processing())
        asyncio.create_task(trading_controller.start_live_trading())
        
        logger.info("🎉 All components initialized successfully!")
        logger.info("📊 Dashboard available at: http://localhost:8080/dashboard")
        logger.info("📚 API docs available at: http://localhost:8080/docs")
        
    except Exception as e:
        logger.error(f"❌ Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global data_manager, whale_tracker, sentiment_analyzer, signal_engine
    global alert_manager, paper_trading, trading_controller, trading_platform
    
    logger.info("🛑 Shutting down Smart Money Trading System...")
    
    try:
        # Stop trading controller
        if trading_controller:
            await trading_controller.stop_live_trading()
        
        # Stop components
        if whale_tracker:
            await whale_tracker.stop_monitoring()
        if sentiment_analyzer:
            await sentiment_analyzer.stop_monitoring()
        if signal_engine:
            await signal_engine.stop_signal_generation()
        if alert_manager:
            await alert_manager.stop_alert_processing()
        
        # Stop WebSocket manager
        await websocket_manager.stop()
        
        # Close data manager
        if data_manager:
            await data_manager.close()
        
        logger.info("✅ Shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "Smart Money Trading System",
        "status": "running",
        "version": "2.0.0",
        "features": [
            "whale tracking",
            "Sentiment analysis",
            "Trading signals",
            "Real-time updates",
            "Paper trading"
        ],
        "endpoints": {
            "health": "/health",
            "status": "/api/status",
            "whales": "/api/whales/activity",
            "sentiment": "/api/sentiment/overview",
            "signals": "/api/signals/recent",
            "portfolio": "/api/portfolio/summary",
            "trading": "/api/trading/status",
            "docs": "/docs",
            "dashboard": "/dashboard"
        }
    }

# Dashboard endpoint
@app.get("/dashboard")
async def dashboard():
    """Serve the trading dashboard"""
    return HTMLResponse(open("app/static/dashboard.html").read())

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not data_manager:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": "Data manager not initialized"}
        )
    
    try:
        health_status = await data_manager.check_health()
        
        if health_status["overall"]:
            return {"status": "healthy", **health_status}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", **health_status}
            )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# System status endpoint
@app.get("/api/status")
async def system_status():
    """Get system status and metrics"""
    try:
        # Get performance metrics
        metrics = await data_manager.get_performance_metrics()
        
        # Get alert statistics
        alert_stats = await alert_manager.get_alert_statistics(hours_back=24)
        
        # Get trading status
        trading_status = await trading_controller.get_trading_status()
        
        return {
            "system": "operational",
            "timestamp": metrics["timestamp"],
            "performance": metrics,
            "alerts": alert_stats,
            "trading": trading_status,
            "components": {
                "whale_tracker": "running" if whale_tracker and whale_tracker.is_running else "stopped",
                "sentiment_analyzer": "running" if sentiment_analyzer and sentiment_analyzer.is_running else "stopped",
                "signal_engine": "running" if signal_engine and signal_engine.is_running else "stopped",
                "alert_manager": "running" if alert_manager and alert_manager.is_running else "stopped",
                "trading_controller": "running" if trading_controller and trading_controller.is_running else "stopped"
            }
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {"error": str(e)}

# Whale tracking endpoints
@app.get("/api/whales/activity")
async def get_whale_activity(hours_back: int = 24):
    """Get recent whale activity"""
    try:
        if not whale_tracker:
            return {"error": "Whale tracker not initialized"}
        
        activities = await whale_tracker.track_whale_transactions(hours_back)
        
        return {
            "hours_back": hours_back,
            "total_activities": len(activities),
            "activities": [
                {
                    "wallet_address": activity.wallet_address,
                    "token_symbol": activity.token_symbol,
                    "transaction_type": activity.transaction_type,
                    "amount_usd": activity.amount_usd,
                    "timestamp": activity.timestamp.isoformat(),
                    "urgency_score": activity.urgency_score,
                    "impact_score": activity.impact_score
                }
                for activity in activities
            ]
        }
    except Exception as e:
        logger.error(f"Error getting whale activity: {e}")
        return {"error": str(e)}

# Sentiment analysis endpoints
@app.get("/api/sentiment/overview")
async def get_sentiment_overview():
    """Get market sentiment overview"""
    try:
        if not sentiment_analyzer:
            return {"error": "Sentiment analyzer not initialized"}
        
        overview = await sentiment_analyzer.get_market_sentiment_overview()
        return overview
    except Exception as e:
        logger.error(f"Error getting sentiment overview: {e}")
        return {"error": str(e)}

# Signal endpoints
@app.get("/api/signals/recent")
async def get_recent_signals(hours_back: int = 24, min_confidence: float = 0.7):
    """Get recent trading signals"""
    try:
        if not signal_engine:
            return {"error": "Signal engine not initialized"}
        
        signals = await signal_engine.get_recent_signals(hours_back, min_confidence)
        
        return {
            "hours_back": hours_back,
            "min_confidence": min_confidence,
            "total_signals": len(signals),
            "signals": signals
        }
    except Exception as e:
        logger.error(f"Error getting recent signals: {e}")
        return {"error": str(e)}

# Portfolio endpoints
@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary"""
    try:
        if not paper_trading:
            return {"error": "Paper trading not initialized"}
        
        summary = await paper_trading.get_portfolio_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        return {"error": str(e)}

@app.get("/api/portfolio/positions")
async def get_portfolio_positions():
    """Get current positions"""
    try:
        if not paper_trading:
            return {"error": "Paper trading not initialized"}
        
        positions = await paper_trading.get_positions()
        return {"positions": positions}
    except Exception as e:
        logger.error(f"Error getting portfolio positions: {e}")
        return {"error": str(e)}

@app.get("/api/portfolio/trades")
async def get_trade_history(limit: int = 100):
    """Get trade history"""
    try:
        if not paper_trading:
            return {"error": "Paper trading not initialized"}
        
        trades = await paper_trading.get_trade_history(limit)
        return {"trades": trades}
    except Exception as e:
        logger.error(f"Error getting trade history: {e}")
        return {"error": str(e)}

# Trading endpoints
@app.get("/api/trading/status")
async def get_trading_status():
    """Get trading status"""
    try:
        if not trading_controller:
            return {"error": "Trading controller not initialized"}
        
        status = await trading_controller.get_trading_status()
        return status
    except Exception as e:
        logger.error(f"Error getting trading status: {e}")
        return {"error": str(e)}

@app.post("/api/trading/execute-signal")
async def execute_signal(signal_data: dict):
    """Execute a trading signal"""
    try:
        if not trading_controller:
            return {"success": False, "error": "Trading controller not initialized"}
        
        # Create trade request from signal data
        from app.trading.trading_controller import TradeRequest, OrderType
        
        trade_request = TradeRequest(
            token_symbol=signal_data.get("token_symbol"),
            token_address=signal_data.get("token_address"),
            action=signal_data.get("action"),
            amount=signal_data.get("amount", 100),
            order_type=OrderType.MARKET,
            signal_id=signal_data.get("signal_id")
        )
        
        result = await trading_controller.execute_manual_trade(trade_request)
        return result
    except Exception as e:
        logger.error(f"Error executing signal: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/trading/config")
async def update_trading_config(config: dict):
    """Update trading configuration"""
    try:
        if not trading_controller:
            return {"success": False, "error": "Trading controller not initialized"}
        
        await trading_controller.update_config(config)
        return {"success": True, "message": "Configuration updated"}
    except Exception as e:
        logger.error(f"Error updating trading config: {e}")
        return {"success": False, "error": str(e)}

# Market overview endpoint
@app.get("/api/market/overview")
async def get_market_overview():
    """Get market overview data"""
    try:
        # Mock market data for demo
        market_data = [
            {"symbol": "BTC", "price": 45000.0, "change": 2.5},
            {"symbol": "ETH", "price": 3000.0, "change": 1.8},
            {"symbol": "SOL", "price": 100.0, "change": -0.5},
            {"symbol": "ADA", "price": 0.5, "change": 3.2},
            {"symbol": "DOT", "price": 7.0, "change": -1.1}
        ]
        return market_data
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        return {"error": str(e)}

# Alerts endpoint
@app.get("/api/alerts/recent")
async def get_recent_alerts(limit: int = 20):
    """Get recent alerts"""
    try:
        # Mock alerts for demo
        alerts = [
            {
                "type": "success",
                "message": "Trade executed: BUY BTC at $45,000",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "type": "info",
                "message": "New signal generated: ETH confidence 85%",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        return alerts
    except Exception as e:
        logger.error(f"Error getting recent alerts: {e}")
        return {"error": str(e)}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.handle_connection(websocket)

def main():
    """Main function to start the trading system"""
    print("\n" + "="*60)
    print("🚀 Smart Money Trading System - Complete Version")
    print("="*60)
    print("📊 Dashboard: http://localhost:8080/dashboard")
    print("📚 API Docs: http://localhost:8080/docs")
    print("🔌 WebSocket: ws://localhost:8080/ws")
    print("="*60)
    print("📈 Features:")
    print("  • Real-time whale tracking")
    print("  • Social sentiment analysis")
    print("  • Automated trading signals")
    print("  • Paper trading with demo money")
    print("  • Live dashboard with WebSocket")
    print("  • Telegram/Discord alerts")
    print("="*60)
    print("⚠️  Important Notes:")
    print("  • This is a DEMO/PAPER trading system")
    print("  • No real money is involved")
    print("  • Perfect for testing strategies")
    print("="*60)
    print("Press Ctrl+C to stop the system\n")
    
    # Start the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
