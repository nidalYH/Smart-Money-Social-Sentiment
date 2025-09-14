"""
Main FastAPI application for Smart Money Social Sentiment Analyzer
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.config import settings
from app.database import create_tables
from app.core.data_manager import DataManager
from app.core.whale_tracker import WhaleTracker
from app.core.sentiment_analyzer import SentimentAnalyzer
from app.core.signal_engine import SignalEngine
from app.core.alert_manager import AlertManager

# Import new trading components
from app.api.trading_routes import router as trading_router
from app.websockets.websocket_manager import websocket_endpoint as new_websocket_endpoint, get_websocket_manager
from app.trading.trading_controller import get_trading_controller, start_trading_system
from app.alerts.telegram_bot import get_telegram_alerts

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
data_manager = None
whale_tracker = None
sentiment_analyzer = None
signal_engine = None
alert_manager = None
background_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global data_manager, whale_tracker, sentiment_analyzer, signal_engine, alert_manager, background_tasks
    
    logger.info("Starting Smart Money Social Sentiment Analyzer...")
    
    try:
        # Initialize data manager
        data_manager = DataManager()
        await data_manager.initialize()
        
        # Create database tables
        await create_tables()
        
        # Initialize core components
        whale_tracker = WhaleTracker(data_manager)
        sentiment_analyzer = SentimentAnalyzer(data_manager)
        signal_engine = SignalEngine(data_manager)
        alert_manager = AlertManager(data_manager)
        
        # Initialize components
        await whale_tracker.initialize()
        await sentiment_analyzer.initialize()
        
        # Initialize trading system
        trading_controller = get_trading_controller()

        # Initialize Telegram bot
        telegram_alerts = get_telegram_alerts()
        if telegram_alerts:
            await telegram_alerts.send_quick_alert(
                "🚀", "System Starting",
                "Smart Money Trading System is initializing..."
            )

        # Start background tasks
        background_tasks = [
            asyncio.create_task(whale_tracker.start_monitoring()),
            asyncio.create_task(sentiment_analyzer.start_monitoring()),
            asyncio.create_task(signal_engine.start_signal_generation()),
            asyncio.create_task(alert_manager.start_alert_processing()),
            asyncio.create_task(start_trading_system())
        ]
        
        logger.info("All components initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down...")
        
        # Stop background tasks
        if background_tasks:
            for task in background_tasks:
                task.cancel()
            await asyncio.gather(*background_tasks, return_exceptions=True)
        
        # Stop components
        if whale_tracker:
            await whale_tracker.stop_monitoring()
        if sentiment_analyzer:
            await sentiment_analyzer.stop_monitoring()
        if signal_engine:
            await signal_engine.stop_signal_generation()
        if alert_manager:
            await alert_manager.stop_alert_processing()

        # Stop trading system
        trading_controller = get_trading_controller()
        await trading_controller.stop()
        
        # Close data manager
        if data_manager:
            await data_manager.close()
        
        logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Smart Money Social Sentiment Analyzer",
    description="Combines whale tracking with social sentiment analysis for trading signals",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include trading routes
app.include_router(trading_router, prefix="/api/trading", tags=["trading"])

# Additional endpoints for frontend compatibility
@app.get("/api/market/overview")
async def get_market_overview():
    """Get market overview data"""
    try:
        return {
            "fear_greed_index": 45,
            "fear_greed_classification": "Neutral",
            "btc_dominance": 42.5,
            "market_cap": 2.4e12,
            "total_volume_24h": 89.5e9,
            "btc_price": 45000,
            "eth_price": 2800,
            "market_trend": "sideways"
        }
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/status")
async def get_system_health():
    """Get system health status"""
    try:
        health_status = "healthy" if data_manager else "unhealthy"
        return {
            "health": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": "operational" if data_manager else "down",
                "whale_tracker": "running" if whale_tracker and whale_tracker.is_running else "stopped",
                "sentiment_analyzer": "running" if sentiment_analyzer and sentiment_analyzer.is_running else "stopped",
                "signal_engine": "running" if signal_engine and signal_engine.is_running else "stopped"
            },
            "uptime_hours": 24,
            "last_restart": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dependency to get data manager
async def get_data_manager() -> DataManager:
    if not data_manager:
        raise HTTPException(status_code=503, detail="Data manager not initialized")
    return data_manager


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not data_manager:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": "Data manager not initialized"}
        )
    
    health_status = await data_manager.check_health()
    
    if health_status["overall"]:
        return {"status": "healthy", **health_status}
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", **health_status}
        )


# System status endpoint
@app.get("/status")
async def system_status():
    """Get system status and metrics"""
    try:
        # Get performance metrics
        metrics = await data_manager.get_performance_metrics()
        
        # Get alert statistics
        alert_stats = await alert_manager.get_alert_statistics(hours_back=24)
        
        return {
            "system": "operational",
            "timestamp": metrics["timestamp"],
            "performance": metrics,
            "alerts": alert_stats,
            "components": {
                "whale_tracker": "running" if whale_tracker and whale_tracker.is_running else "stopped",
                "sentiment_analyzer": "running" if sentiment_analyzer and sentiment_analyzer.is_running else "stopped",
                "signal_engine": "running" if signal_engine and signal_engine.is_running else "stopped",
                "alert_manager": "running" if alert_manager and alert_manager.is_running else "stopped"
            }
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Whale tracking endpoints
@app.get("/api/whales/activity")
async def get_whale_activity(hours_back: int = 24, dm: DataManager = Depends(get_data_manager)):
    """Get recent whale activity"""
    try:
        if not whale_tracker:
            raise HTTPException(status_code=503, detail="Whale tracker not initialized")
        
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
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/whales/accumulation/{token_address}")
async def get_whale_accumulation(token_address: str, hours_back: int = 48, 
                               dm: DataManager = Depends(get_data_manager)):
    """Get whale accumulation analysis for a token"""
    try:
        if not whale_tracker:
            raise HTTPException(status_code=503, detail="Whale tracker not initialized")
        
        analysis = await whale_tracker.analyze_accumulation_patterns(token_address, hours_back)
        
        return {
            "token_address": token_address,
            "hours_back": hours_back,
            **analysis
        }
    except Exception as e:
        logger.error(f"Error getting whale accumulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Sentiment analysis endpoints
@app.get("/api/sentiment/overview")
async def get_sentiment_overview(dm: DataManager = Depends(get_data_manager)):
    """Get market sentiment overview"""
    try:
        if not sentiment_analyzer:
            raise HTTPException(status_code=503, detail="Sentiment analyzer not initialized")
        
        overview = await sentiment_analyzer.get_market_sentiment_overview()
        
        return overview
    except Exception as e:
        logger.error(f"Error getting sentiment overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sentiment/token/{token_symbol}")
async def get_token_sentiment(token_symbol: str, hours_back: int = 24, 
                            dm: DataManager = Depends(get_data_manager)):
    """Get sentiment analysis for a specific token"""
    try:
        if not sentiment_analyzer:
            raise HTTPException(status_code=503, detail="Sentiment analyzer not initialized")
        
        trends = await sentiment_analyzer.get_sentiment_trends(token_symbol, hours_back)
        
        return {
            "token_symbol": token_symbol,
            "hours_back": hours_back,
            **trends
        }
    except Exception as e:
        logger.error(f"Error getting token sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Signal endpoints
@app.get("/api/signals/recent")
async def get_recent_signals(hours_back: int = 24, min_confidence: float = 0.7, 
                           dm: DataManager = Depends(get_data_manager)):
    """Get recent trading signals"""
    try:
        if not signal_engine:
            raise HTTPException(status_code=503, detail="Signal engine not initialized")
        
        signals = await signal_engine.get_recent_signals(hours_back, min_confidence)
        
        return {
            "hours_back": hours_back,
            "min_confidence": min_confidence,
            "total_signals": len(signals),
            "signals": signals
        }
    except Exception as e:
        logger.error(f"Error getting recent signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/signals/generate")
async def generate_signals_now(hours_back: int = 48, dm: DataManager = Depends(get_data_manager)):
    """Manually trigger signal generation"""
    try:
        if not signal_engine:
            raise HTTPException(status_code=503, detail="Signal engine not initialized")
        
        signals = await signal_engine.generate_signals(hours_back)
        
        return {
            "generated_at": "now",
            "hours_back": hours_back,
            "total_signals": len(signals),
            "signals": [signal_engine._signal_to_dict(signal) for signal in signals]
        }
    except Exception as e:
        logger.error(f"Error generating signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Alert endpoints
@app.get("/api/alerts/statistics")
async def get_alert_statistics(hours_back: int = 24, dm: DataManager = Depends(get_data_manager)):
    """Get alert delivery statistics"""
    try:
        if not alert_manager:
            raise HTTPException(status_code=503, detail="Alert manager not initialized")
        
        stats = await alert_manager.get_alert_statistics(hours_back)
        
        return stats
    except Exception as e:
        logger.error(f"Error getting alert statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/alerts/retry")
async def retry_failed_alerts(max_retries: int = 3, dm: DataManager = Depends(get_data_manager)):
    """Manually retry failed alert deliveries"""
    try:
        if not alert_manager:
            raise HTTPException(status_code=503, detail="Alert manager not initialized")
        
        retry_count = await alert_manager.retry_failed_deliveries(max_retries)
        
        return {
            "retried_count": retry_count,
            "max_retries": max_retries
        }
    except Exception as e:
        logger.error(f"Error retrying alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint_handler(websocket: WebSocket):
    """WebSocket endpoint for real-time trading updates"""
    await new_websocket_endpoint(websocket)


# Data export endpoints
@app.get("/api/export/whale-transactions")
async def export_whale_transactions(hours_back: int = 168, dm: DataManager = Depends(get_data_manager)):  # 1 week
    """Export whale transaction data"""
    try:
        from app.models.whale import WhaleTransaction
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        async with dm.get_db_session() as session:
            from sqlalchemy import select, and_
            
            stmt = select(WhaleTransaction).where(
                WhaleTransaction.timestamp >= cutoff_time
            ).order_by(WhaleTransaction.timestamp.desc()).limit(10000)
            
            result = await session.execute(stmt)
            transactions = result.scalars().all()
            
            export_data = []
            for tx in transactions:
                export_data.append({
                    "timestamp": tx.timestamp.isoformat(),
                    "wallet_address": tx.whale_wallet_id,
                    "token_address": tx.token_address,
                    "token_symbol": tx.token_symbol,
                    "transaction_type": tx.transaction_type,
                    "amount": tx.amount,
                    "amount_usd": tx.amount_usd,
                    "gas_price_gwei": tx.gas_price_gwei,
                    "urgency_score": tx.urgency_score,
                    "impact_score": tx.impact_score
                })
            
            return {
                "export_type": "whale_transactions",
                "hours_back": hours_back,
                "total_records": len(export_data),
                "data": export_data
            }
            
    except Exception as e:
        logger.error(f"Error exporting whale transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/signals")
async def export_signals(hours_back: int = 168, dm: DataManager = Depends(get_data_manager)):  # 1 week
    """Export trading signals data"""
    try:
        from app.models.signal import TradingSignal
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        async with dm.get_db_session() as session:
            from sqlalchemy import select, and_
            
            stmt = select(TradingSignal).where(
                and_(
                    TradingSignal.timestamp >= cutoff_time,
                    TradingSignal.is_active == True
                )
            ).order_by(TradingSignal.timestamp.desc()).limit(1000)
            
            result = await session.execute(stmt)
            signals = result.scalars().all()
            
            export_data = []
            for signal in signals:
                export_data.append({
                    "timestamp": signal.timestamp.isoformat(),
                    "signal_type": signal.signal_type,
                    "token_symbol": signal.token_symbol,
                    "action": signal.action,
                    "confidence_score": signal.confidence_score,
                    "risk_score": signal.risk_score,
                    "current_price": signal.current_price,
                    "target_price": signal.target_price,
                    "stop_loss_price": signal.stop_loss_price,
                    "reasoning": signal.reasoning,
                    "key_factors": signal.key_factors,
                    "risk_factors": signal.risk_factors
                })
            
            return {
                "export_type": "trading_signals",
                "hours_back": hours_back,
                "total_records": len(export_data),
                "data": export_data
            }
            
    except Exception as e:
        logger.error(f"Error exporting signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found", "path": str(request.url)}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Background task to broadcast updates via WebSocket
async def broadcast_updates():
    """Background task to broadcast updates to WebSocket clients"""
    while True:
        try:
            if connection_manager.active_connections:
                # Get latest system status
                status = await system_status()
                
                # Broadcast to all connected clients
                await connection_manager.broadcast({
                    "type": "system_status",
                    "data": status,
                    "timestamp": "now"
                })
            
            # Wait 30 seconds before next broadcast
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in broadcast_updates: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


