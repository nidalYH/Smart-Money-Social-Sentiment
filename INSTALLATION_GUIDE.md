# 🚀 Smart Money Trading System - Installation Guide

## 📋 Prerequisites

- **Python 3.8+** (Recommended: Python 3.11)
- **Git** (for cloning the repository)
- **Windows 10/11** (current setup)
- **8GB+ RAM** (recommended for optimal performance)
- **Stable Internet Connection** (for real-time data)

## 🛠️ Quick Installation (5 minutes)

### Step 1: Clone and Setup
```bash
# Navigate to your project directory
cd "D:\Archivos de programa\Smart Money Social Sentiment"

# Install Python dependencies
pip install -r requirements.txt

# Copy the complete environment configuration
copy .env.complete .env
```

### Step 2: Configure API Keys
Edit the `.env` file and replace the placeholder values:

```bash
# Essential APIs (Get these free keys)
ETHERSCAN_API_KEY=YourActualEtherscanKey
COINGECKO_API_KEY=YourActualCoinGeckoKey
TELEGRAM_BOT_TOKEN=YourActualTelegramBotToken
TELEGRAM_CHAT_ID=YourActualChatID
```

### Step 3: Start the System
```bash
# Start the complete trading system
python complete_trading_system.py
```

## 🔑 API Keys Setup

### 1. Etherscan API (Free)
- Visit: https://etherscan.io/apis
- Sign up for free account
- Get your API key
- Rate limit: 5 calls/second, 100,000 calls/day

### 2. CoinGecko API (Free)
- Visit: https://www.coingecko.com/en/api
- Sign up for free account
- Get your API key
- Rate limit: 10-50 calls/minute

### 3. Telegram Bot (Free)
- Message @BotFather on Telegram
- Create new bot with `/newbot`
- Get bot token
- Get your chat ID by messaging @userinfobot

### 4. Twitter API (Optional)
- Visit: https://developer.twitter.com/
- Apply for developer account
- Get bearer token
- Rate limit: 500,000 tweets/month

## 🎯 Trading Platform Setup

### Option 1: TradingView Paper Trading (Recommended)
```python
# Already configured in the system
# No additional setup required
# Uses $100,000 demo balance
```

### Option 2: Binance Testnet
```python
# Visit: https://testnet.binance.vision/
# Create testnet account
# Get testnet API keys
# Update .env file:
BINANCE_TESTNET_API_KEY=your_testnet_key
BINANCE_TESTNET_SECRET_KEY=your_testnet_secret
```

### Option 3: Custom Paper Trading
```python
# Already configured
# Uses local SQLite database
# No external setup required
```

## 🖥️ Web Dashboard Access

Once the system is running:

1. **Main Dashboard**: http://localhost:8000
2. **API Documentation**: http://localhost:8000/docs
3. **WebSocket**: ws://localhost:8000/ws
4. **Health Check**: http://localhost:8000/health

## 📊 System Components

### Core Modules
- **Whale Tracker**: Monitors large wallet movements
- **Sentiment Analyzer**: Analyzes social media sentiment
- **Signal Engine**: Generates trading signals
- **Alert Manager**: Sends notifications
- **Trading Controller**: Executes trades

### Data Sources
- **Etherscan**: Ethereum blockchain data
- **CoinGecko**: Price and market data
- **Twitter**: Social sentiment
- **Telegram**: Community sentiment

### Trading Features
- **Real-time Signals**: AI-powered trading signals
- **Risk Management**: Stop-loss and take-profit
- **Portfolio Tracking**: P&L and performance metrics
- **Auto-trading**: One-click execution
- **Demo Mode**: Safe paper trading

## 🔧 Configuration Options

### Trading Settings
```bash
# Risk Management
MAX_POSITION_SIZE_PERCENT=0.05  # 5% per trade
STOP_LOSS_PERCENT=0.05  # 5% stop loss
TAKE_PROFIT_MULTIPLIER=2.0  # 2:1 risk/reward

# Signal Settings
SIGNAL_CONFIDENCE_THRESHOLD=0.7  # 70% confidence minimum
MAX_DAILY_TRADES=10  # Maximum trades per day
```

### Alert Settings
```bash
# Notification Channels
TELEGRAM_ALERTS_ENABLED=true
DISCORD_ALERTS_ENABLED=true
EMAIL_ALERTS_ENABLED=false

# Alert Thresholds
ALERT_CONFIDENCE_THRESHOLD=0.8  # 80% confidence for alerts
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Solution: Install missing dependencies
pip install -r requirements.txt
```

#### 2. Database Errors
```bash
# Solution: Delete old database and restart
del smartmoney.db
python complete_trading_system.py
```

#### 3. API Rate Limits
```bash
# Solution: Wait or upgrade API plan
# Check .env file for correct API keys
```

#### 4. WebSocket Connection Issues
```bash
# Solution: Check firewall settings
# Ensure port 8000 is not blocked
```

### Performance Optimization

#### For Better Performance
```bash
# Increase monitoring intervals
WHALE_MONITORING_INTERVAL=600  # 10 minutes
SENTIMENT_ANALYSIS_INTERVAL=600  # 10 minutes

# Reduce data retention
MAX_TRADE_HISTORY=500
MAX_SIGNAL_HISTORY=250
```

#### For More Signals
```bash
# Decrease confidence threshold
SIGNAL_CONFIDENCE_THRESHOLD=0.6  # 60% confidence

# Increase monitoring frequency
WHALE_MONITORING_INTERVAL=180  # 3 minutes
```

## 📈 Success Metrics

After installation, you should see:

- ✅ **System Status**: All components running
- ✅ **Database**: SQLite database created
- ✅ **API Health**: All endpoints responding
- ✅ **WebSocket**: Real-time connection active
- ✅ **Trading**: Demo account initialized
- ✅ **Alerts**: Telegram notifications working

## 🎯 Next Steps

1. **Monitor Signals**: Watch for trading signals in the dashboard
2. **Configure Alerts**: Set up Telegram notifications
3. **Adjust Settings**: Fine-tune risk parameters
4. **Track Performance**: Monitor demo trading results
5. **Scale Up**: Consider upgrading to live trading

## 📞 Support

If you encounter issues:

1. Check the logs in `logs/smartmoney.log`
2. Verify all API keys are correct
3. Ensure all dependencies are installed
4. Check system requirements
5. Review configuration settings

## 🔒 Security Notes

- **Never share your API keys**
- **Use demo mode for testing**
- **Keep your .env file secure**
- **Regularly update dependencies**
- **Monitor system logs**

---

**Ready to start trading? Run `python complete_trading_system.py` and visit http://localhost:8000!** 🚀
