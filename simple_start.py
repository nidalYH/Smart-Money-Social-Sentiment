#!/usr/bin/env python3
"""
Simplified startup script for Smart Money Trading System
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.main import app
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the simplified trading system"""
    print("\n" + "="*60)
    print("🚀 Smart Money Trading System - Simplified Mode")
    print("="*60)
    print("Backend API: http://localhost:8080")
    print("API Docs: http://localhost:8080/docs")
    print("WebSocket: ws://localhost:8080/ws")
    print("="*60)
    print("📊 Features:")
    print("  • Free API-based sentiment analysis")
    print("  • Real-time whale transaction tracking")
    print("  • Paper trading with P&L tracking")
    print("  • Live WebSocket updates")
    print("  • One-click signal execution")
    print("="*60)
    print("⚠️  Important Notes:")
    print("  • This is a DEMO/PAPER trading system")
    print("  • No real money is involved")
    print("  • Using SQLite database (no Redis required)")
    print("  • Check logs/ directory for troubleshooting")
    print("="*60)
    print("Press Ctrl+C to stop the system\n")
    
    try:
        # Start the server
        uvicorn.run(
            "app.main:app",
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
