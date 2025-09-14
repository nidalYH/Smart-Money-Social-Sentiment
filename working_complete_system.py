#!/usr/bin/env python3
"""
Smart Money Trading System - Complete Working Version
Sistema de trading completo y funcional sin WebSocket para máxima compatibilidad
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Any
import json

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/smartmoney.log')
    ]
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# FastAPI imports
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Database imports
from app.database import create_tables, get_db
from app.config import settings

# Core components
from app.core.data_manager import DataManager
from app.core.whale_tracker import WhaleTracker
from app.core.sentiment_analyzer import SentimentAnalyzer
from app.core.signal_engine import SignalEngine
from app.core.alert_manager import AlertManager
from app.core.paper_trading import PaperTradingEngine

# Models
from app.models import *

# Trading components
from app.trading.trading_controller import TradingController

# API routes
from app.api.trading_routes import router as trading_router

# Initialize FastAPI app
app = FastAPI(
    title="Smart Money Trading System",
    description="Complete trading system with whale tracking, sentiment analysis, and automated signals",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global instances
data_manager = None
whale_tracker = None
sentiment_analyzer = None
signal_engine = None
alert_manager = None
paper_trading = None
trading_controller = None

# Background tasks
background_tasks = []

@app.on_event("startup")
async def startup_event():
    """Initialize the trading system on startup"""
    global data_manager, whale_tracker, sentiment_analyzer, signal_engine
    global alert_manager, paper_trading, trading_controller, background_tasks
    
    try:
        logger.info("🚀 Starting Smart Money Trading System...")
        
        # Create database tables
        await create_tables()
        logger.info("✅ Database tables created")
        
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
        trading_controller = TradingController(data_manager)
        
        logger.info("✅ Core components initialized")
        
        # Start background tasks
        background_tasks = [
            asyncio.create_task(whale_tracker.start_monitoring()),
            asyncio.create_task(sentiment_analyzer.start_monitoring()),
            asyncio.create_task(signal_engine.start_signal_generation()),
            asyncio.create_task(alert_manager.start_alert_processing()),
            asyncio.create_task(paper_trading.start_monitoring()),
            asyncio.create_task(trading_controller.start_trading_loop())
        ]
        
        logger.info("✅ Background tasks started")
        logger.info("🎉 Smart Money Trading System is now running!")
        
    except Exception as e:
        logger.error(f"❌ Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global background_tasks
    
    try:
        logger.info("🛑 Shutting down Smart Money Trading System...")
        
        # Cancel all background tasks
        for task in background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*background_tasks, return_exceptions=True)
        
        logger.info("✅ Shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {
            "data_manager": data_manager is not None,
            "whale_tracker": whale_tracker is not None,
            "sentiment_analyzer": sentiment_analyzer is not None,
            "signal_engine": signal_engine is not None,
            "alert_manager": alert_manager is not None,
            "paper_trading": paper_trading is not None,
            "trading_controller": trading_controller is not None
        }
    }

# Main dashboard endpoint
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main trading dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smart Money Trading System</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .header {
                text-align: center;
                margin-bottom: 40px;
                color: white;
            }
            
            .header h1 {
                font-size: 3rem;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            
            .header p {
                font-size: 1.2rem;
                opacity: 0.9;
            }
            
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            
            .card {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            }
            
            .card h3 {
                color: #667eea;
                margin-bottom: 15px;
                font-size: 1.5rem;
            }
            
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }
            
            .status-online {
                background-color: #4CAF50;
                animation: pulse 2s infinite;
            }
            
            .status-offline {
                background-color: #f44336;
            }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }
            
            .metric {
                display: flex;
                justify-content: space-between;
                margin: 10px 0;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 8px;
            }
            
            .metric-value {
                font-weight: bold;
                color: #667eea;
            }
            
            .button {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 1rem;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
                margin: 5px;
            }
            
            .button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            
            .api-section {
                background: white;
                border-radius: 15px;
                padding: 25px;
                margin-top: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .api-section h2 {
                color: #667eea;
                margin-bottom: 20px;
            }
            
            .endpoint {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
                border-left: 4px solid #667eea;
            }
            
            .endpoint-method {
                display: inline-block;
                background: #4CAF50;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8rem;
                margin-right: 10px;
            }
            
            .footer {
                text-align: center;
                margin-top: 40px;
                color: white;
                opacity: 0.8;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Smart Money Trading System</h1>
                <p>Complete Trading Platform with Real-time Analysis</p>
            </div>
            
            <div class="dashboard-grid">
                <div class="card">
                    <h3>📊 System Status</h3>
                    <div class="metric">
                        <span>Overall Status</span>
                        <span><span class="status-indicator status-online"></span>Online</span>
                    </div>
                    <div class="metric">
                        <span>Uptime</span>
                        <span class="metric-value" id="uptime">Loading...</span>
                    </div>
                    <div class="metric">
                        <span>Active Components</span>
                        <span class="metric-value" id="components">7/7</span>
                    </div>
                </div>
                
                <div class="card">
                    <h3>💰 Paper Trading</h3>
                    <div class="metric">
                        <span>Demo Balance</span>
                        <span class="metric-value">$100,000</span>
                    </div>
                    <div class="metric">
                        <span>Active Positions</span>
                        <span class="metric-value" id="positions">0</span>
                    </div>
                    <div class="metric">
                        <span>Total P&L</span>
                        <span class="metric-value" id="pnl">$0.00</span>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🐋 Whale Tracking</h3>
                    <div class="metric">
                        <span>Monitored Wallets</span>
                        <span class="metric-value" id="whales">0</span>
                    </div>
                    <div class="metric">
                        <span>Recent Transactions</span>
                        <span class="metric-value" id="transactions">0</span>
                    </div>
                    <div class="metric">
                        <span>Last Update</span>
                        <span class="metric-value" id="lastUpdate">-</span>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📈 Trading Signals</h3>
                    <div class="metric">
                        <span>Signals Generated</span>
                        <span class="metric-value" id="signals">0</span>
                    </div>
                    <div class="metric">
                        <span>Success Rate</span>
                        <span class="metric-value" id="successRate">0%</span>
                    </div>
                    <div class="metric">
                        <span>Last Signal</span>
                        <span class="metric-value" id="lastSignal">-</span>
                    </div>
                </div>
            </div>
            
            <div class="api-section">
                <h2>🔗 API Endpoints</h2>
                <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <strong>/health</strong> - System health check
                </div>
                <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <strong>/api/signals/recent</strong> - Recent trading signals
                </div>
                <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <strong>/api/whales/activity</strong> - Whale activity data
                </div>
                <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <strong>/api/sentiment/overview</strong> - Sentiment analysis
                </div>
                <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <strong>/api/trading/portfolio</strong> - Portfolio status
                </div>
                <div class="endpoint">
                    <span class="endpoint-method">POST</span>
                    <strong>/api/trading/execute</strong> - Execute trade
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/docs" class="button">📚 API Documentation</a>
                <a href="/health" class="button">❤️ Health Check</a>
                <button onclick="refreshData()" class="button">🔄 Refresh Data</button>
            </div>
            
            <div class="footer">
                <p>Smart Money Trading System v1.0.0 | Demo Trading Platform</p>
                <p>⚠️ This is a demo system - No real money involved</p>
            </div>
        </div>
        
        <script>
            let startTime = new Date();
            
            function updateUptime() {
                const now = new Date();
                const diff = now - startTime;
                const hours = Math.floor(diff / 3600000);
                const minutes = Math.floor((diff % 3600000) / 60000);
                const seconds = Math.floor((diff % 60000) / 1000);
                document.getElementById('uptime').textContent = 
                    `${hours}h ${minutes}m ${seconds}s`;
            }
            
            function refreshData() {
                fetch('/health')
                    .then(response => response.json())
                    .then(data => {
                        console.log('System status:', data);
                        document.getElementById('lastUpdate').textContent = 
                            new Date().toLocaleTimeString();
                    })
                    .catch(error => {
                        console.error('Error fetching data:', error);
                    });
            }
            
            // Update uptime every second
            setInterval(updateUptime, 1000);
            
            // Initial data load
            refreshData();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# API Routes
@app.get("/api/signals/recent")
async def get_recent_signals():
    """Get recent trading signals"""
    try:
        if signal_engine:
            signals = await signal_engine.get_recent_signals(limit=10)
            return {"signals": signals, "count": len(signals)}
        else:
            return {"signals": [], "count": 0, "error": "Signal engine not initialized"}
    except Exception as e:
        logger.error(f"Error getting recent signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/whales/activity")
async def get_whale_activity():
    """Get whale activity data"""
    try:
        if whale_tracker:
            activity = await whale_tracker.get_recent_activity(limit=20)
            return {"activity": activity, "count": len(activity)}
        else:
            return {"activity": [], "count": 0, "error": "Whale tracker not initialized"}
    except Exception as e:
        logger.error(f"Error getting whale activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sentiment/overview")
async def get_sentiment_overview():
    """Get sentiment analysis overview"""
    try:
        if sentiment_analyzer:
            overview = await sentiment_analyzer.get_sentiment_overview()
            return overview
        else:
            return {"error": "Sentiment analyzer not initialized"}
    except Exception as e:
        logger.error(f"Error getting sentiment overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trading/portfolio")
async def get_portfolio_status():
    """Get portfolio status"""
    try:
        if paper_trading:
            portfolio = await paper_trading.get_portfolio_status()
            return portfolio
        else:
            return {"error": "Paper trading not initialized"}
    except Exception as e:
        logger.error(f"Error getting portfolio status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trading/execute")
async def execute_trade(trade_data: dict):
    """Execute a trade"""
    try:
        if trading_controller:
            result = await trading_controller.execute_trade(trade_data)
            return result
        else:
            return {"error": "Trading controller not initialized"}
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Include trading routes
app.include_router(trading_router, prefix="/api/trading", tags=["trading"])

def main():
    """Main function to run the trading system"""
    print("=" * 60)
    print("🚀 Smart Money Trading System - Complete Working Version")
    print("=" * 60)
    print("📊 Dashboard: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("❤️ Health Check: http://localhost:8000/health")
    print("=" * 60)
    print("📈 Features:")
    print("  • Real-time whale tracking")
    print("  • Social sentiment analysis")
    print("  • Automated trading signals")
    print("  • Paper trading with demo money")
    print("  • Live dashboard")
    print("  • Telegram/Discord alerts")
    print("=" * 60)
    print("⚠️  Important Notes:")
    print("  • This is a DEMO/PAPER trading system")
    print("  • No real money is involved")
    print("  • Perfect for testing strategies")
    print("=" * 60)
    print("Press Ctrl+C to stop the system")
    print()
    
    # Run the application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()
