@echo off
echo ========================================
echo Smart Money Trading System
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo Creating .env file from template...
    copy .env.complete .env
    echo.
    echo IMPORTANT: Please edit .env file and add your API keys
    echo Press any key to continue after editing .env...
    pause
)

REM Check if requirements are installed
echo Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Create logs directory
if not exist logs mkdir logs

REM Start the trading system
echo.
echo Starting Smart Money Trading System...
echo Dashboard: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the system
echo.

python complete_trading_system.py

pause
