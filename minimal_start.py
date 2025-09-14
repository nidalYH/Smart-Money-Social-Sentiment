#!/usr/bin/env python3
"""
Minimal startup script for Smart Money Trading System
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_minimal_app():
    """Create a minimal FastAPI app for testing"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    
    app = FastAPI(
        title="Smart Money Social Sentiment Analyzer",
        description="Combines whale tracking with social sentiment analysis for trading signals",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        return {
            "message": "Smart Money Trading System",
            "status": "running",
            "version": "1.0.0",
            "features": [
                "Whale tracking",
                "Sentiment analysis", 
                "Trading signals",
                "Real-time updates"
            ]
        }
    
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "database": "sqlite",
            "cache": "disabled",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    
    @app.get("/api/status")
    async def system_status():
        return {
            "system": "operational",
            "components": {
                "whale_tracker": "ready",
                "sentiment_analyzer": "ready", 
                "signal_engine": "ready",
                "alert_manager": "ready"
            },
            "database": "sqlite",
            "cache": "disabled"
        }
    
    @app.get("/api/whales/activity")
    async def get_whale_activity(hours_back: int = 24):
        """Mock whale activity data"""
        return {
            "hours_back": hours_back,
            "total_activities": 0,
            "activities": [],
            "message": "Whale tracking not yet implemented"
        }
    
    @app.get("/api/sentiment/overview")
    async def get_sentiment_overview():
        """Mock sentiment overview"""
        return {
            "overall_sentiment": 0.0,
            "trend": "neutral",
            "active_tokens": 0,
            "message": "Sentiment analysis not yet implemented"
        }
    
    @app.get("/api/signals/recent")
    async def get_recent_signals(hours_back: int = 24, min_confidence: float = 0.7):
        """Mock recent signals"""
        return {
            "hours_back": hours_back,
            "min_confidence": min_confidence,
            "total_signals": 0,
            "signals": [],
            "message": "Signal generation not yet implemented"
        }
    
    return app

def main():
    """Start the minimal trading system"""
    print("\n" + "="*60)
    print("🚀 Smart Money Trading System - Minimal Mode")
    print("="*60)
    print("Backend API: http://localhost:8080")
    print("API Docs: http://localhost:8080/docs")
    print("="*60)
    print("📊 Features:")
    print("  • Basic API endpoints")
    print("  • Health monitoring")
    print("  • Ready for full implementation")
    print("="*60)
    print("⚠️  Important Notes:")
    print("  • This is a minimal demo version")
    print("  • Full features will be implemented")
    print("  • Using SQLite database")
    print("="*60)
    print("Press Ctrl+C to stop the system\n")
    
    try:
        import uvicorn
        app = create_minimal_app()
        
        # Start the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Shutting down trading system...")
        print("👋 Trading system stopped. Goodbye!")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
