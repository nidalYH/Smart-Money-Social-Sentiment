#!/bin/bash

echo "========================================"
echo "Smart Money Trading System"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.complete .env
    echo
    echo "IMPORTANT: Please edit .env file and add your API keys"
    echo "Press Enter to continue after editing .env..."
    read
fi

# Check if requirements are installed
echo "Checking dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies"
        exit 1
    fi
fi

# Create logs directory
mkdir -p logs

# Start the trading system
echo
echo "Starting Smart Money Trading System..."
echo "Dashboard: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo
echo "Press Ctrl+C to stop the system"
echo

python3 complete_trading_system.py
