#!/usr/bin/env python3
"""
Smart Money Trading System Startup Script
Automated setup and launch script for the complete trading system
"""
import os
import sys
import subprocess
import asyncio
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        return False
    logger.info(f"Python version: {sys.version}")
    return True

def check_environment_file():
    """Check if .env file exists"""
    env_file = Path(".env")
    if not env_file.exists():
        logger.warning(".env file not found. Creating from template...")
        template_file = Path(".env.example")
        if template_file.exists():
            # Copy template to .env
            with open(template_file, 'r') as src, open(env_file, 'w') as dst:
                dst.write(src.read())
            logger.info("Created .env file from template. Please update it with your API keys.")
            return False
        else:
            logger.error(".env.example template not found")
            return False
    return True

def install_dependencies():
    """Install required dependencies"""
    logger.info("Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                      check=True, capture_output=True)
        logger.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False

def setup_frontend():
    """Set up frontend if needed"""
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        logger.info("Setting up frontend...")
        try:
            # Check if npm is available
            subprocess.run(["npm", "--version"], check=True, capture_output=True)

            # Install frontend dependencies
            subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
            logger.info("Frontend dependencies installed")
            return True
        except subprocess.CalledProcessError:
            logger.warning("npm not found. Frontend setup skipped.")
            return False
        except FileNotFoundError:
            logger.warning("Node.js/npm not installed. Frontend setup skipped.")
            return False
    return True

def check_api_keys():
    """Check if essential API keys are configured"""
    from dotenv import load_dotenv
    load_dotenv()

    required_keys = [
        'ETHERSCAN_API_KEY',
    ]

    optional_keys = [
        'TELEGRAM_BOT_TOKEN',
        'REDDIT_CLIENT_ID',
        'COINGECKO_API_KEY'
    ]

    missing_required = []
    missing_optional = []

    for key in required_keys:
        if not os.getenv(key):
            missing_required.append(key)

    for key in optional_keys:
        if not os.getenv(key):
            missing_optional.append(key)

    if missing_required:
        logger.error(f"Missing required API keys: {', '.join(missing_required)}")
        logger.error("Please update your .env file with the required API keys")
        return False

    if missing_optional:
        logger.warning(f"Missing optional API keys: {', '.join(missing_optional)}")
        logger.warning("Some features may be limited without these keys")

    logger.info("API key configuration validated")
    return True

def create_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "data",
        "backups"
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"Created directory: {directory}")

def start_backend():
    """Start the FastAPI backend"""
    logger.info("Starting FastAPI backend...")
    try:
        import uvicorn
        from app.main import app

        # Start the server
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8080,
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        return False

def start_frontend():
    """Start the React frontend in a separate process"""
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        logger.info("Starting React frontend...")
        try:
            subprocess.Popen(["npm", "start"], cwd=frontend_dir)
            logger.info("Frontend started on http://localhost:3000")
            return True
        except Exception as e:
            logger.warning(f"Failed to start frontend: {e}")
            return False
    return True

def display_startup_info():
    """Display startup information"""
    print("\n" + "="*60)
    print("🚀 Smart Money Trading System")
    print("="*60)
    print("Backend API: http://localhost:8080")
    print("Frontend UI: http://localhost:3000")
    print("API Docs: http://localhost:8080/docs")
    print("WebSocket: ws://localhost:8080/ws")
    print("="*60)
    print("📊 Features:")
    print("  • Free API-based sentiment analysis")
    print("  • Real-time whale transaction tracking")
    print("  • Paper trading with P&L tracking")
    print("  • Telegram alerts and notifications")
    print("  • Live WebSocket updates")
    print("  • One-click signal execution")
    print("="*60)
    print("⚠️  Important Notes:")
    print("  • This is a DEMO/PAPER trading system")
    print("  • No real money is involved")
    print("  • Update .env file with your API keys")
    print("  • Check logs/ directory for troubleshooting")
    print("="*60)
    print("Press Ctrl+C to stop the system\n")

def main():
    """Main startup routine"""
    logger.info("Starting Smart Money Trading System setup...")

    # Pre-flight checks
    if not check_python_version():
        sys.exit(1)

    if not check_environment_file():
        logger.error("Please update the .env file with your API keys and restart")
        sys.exit(1)

    if not check_api_keys():
        sys.exit(1)

    # Setup
    create_directories()

    if not install_dependencies():
        sys.exit(1)

    setup_frontend()

    # Display info
    display_startup_info()

    # Start services
    try:
        # Start frontend in background
        start_frontend()

        # Start backend (this blocks)
        start_backend()

    except KeyboardInterrupt:
        logger.info("Shutting down trading system...")
        print("👋 Trading system stopped. Goodbye!")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()