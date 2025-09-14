# 🚀 Smart Money Trading System with Free APIs

A complete, ready-to-use cryptocurrency trading system that combines social sentiment analysis, whale tracking, and automated paper trading using **100% FREE APIs**.

## ✨ Features

### 🎯 Core Trading System
- **Paper Trading Engine** with real-time P&L tracking
- **One-Click Signal Execution** from the web dashboard
- **Automated Trading Controller** with customizable rules
- **Portfolio Management** with detailed analytics
- **Risk Management** with stop-loss and take-profit

### 📊 Free Data Sources
- **Reddit Sentiment Analysis** - Real-time social sentiment from crypto subreddits
- **Whale Transaction Tracking** - Large transactions via Etherscan API
- **Market Data Integration** - Price data and metrics via CoinGecko
- **Google Trends Analysis** - Search momentum and interest tracking

### 💻 Professional Interface
- **React Dashboard** with real-time updates
- **WebSocket Communication** for instant data
- **Mobile-Responsive Design** with professional charts
- **Live Trading Signals** with confidence scoring

### 🔔 Alert System
- **Telegram Bot Integration** for instant notifications
- **Discord Webhooks** support
- **Email Alerts** for important events
- **Real-time Browser Notifications**

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8+
- Node.js 14+ (optional, for frontend)
- Git

### 2. Clone and Setup
```bash
cd "D:\\Archivos de programa\\Smart Money Social Sentiment"

# Run the automated setup script
python start_trading_system.py
```

The script will:
- ✅ Check Python version
- ✅ Install dependencies
- ✅ Create `.env` file from template
- ✅ Set up directories
- ✅ Start both backend and frontend

### 3. Configure API Keys

Update the `.env` file with your API keys:

```env
# Required (Free)
ETHERSCAN_API_KEY=your-etherscan-api-key-here

# Optional but recommended
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
COINGECKO_API_KEY=your-coingecko-pro-api-key
```

### 4. Access the System

- **Web Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8080/docs
- **Backend API**: http://localhost:8080
- **WebSocket**: ws://localhost:8080/ws

## 📋 Getting Free API Keys

### Etherscan API (Required)
1. Go to [etherscan.io/apis](https://etherscan.io/apis)
2. Create free account
3. Generate API key
4. **Free tier**: 100,000 requests/day

### Telegram Bot (Recommended)
1. Message @BotFather on Telegram
2. Use `/newbot` command
3. Get your bot token
4. Add bot to your chat and get chat ID

### Reddit API (Optional)
1. Go to [reddit.com/prefs/apps](https://reddit.com/prefs/apps)
2. Create new "script" application
3. Get client ID and secret

### CoinGecko API (Optional)
1. Sign up at [coingecko.com](https://coingecko.com)
2. Free tier: 50 requests/minute
3. Pro tier available for higher limits

## 🎮 Using the Trading System

### Dashboard Overview
- **Signal Feed**: Live trading signals with confidence scores
- **Portfolio View**: Real-time balance and P&L
- **Position Manager**: Open positions with current status
- **Market Overview**: Key market metrics and trends

### Signal Execution
1. **Manual**: Click "Execute" on any signal in the dashboard
2. **Automatic**: Enable auto-trading in settings
3. **Customizable**: Set confidence thresholds and risk limits

### Auto-Trading Settings
```python
# Configure in .env file
MIN_SIGNAL_CONFIDENCE=0.7      # Only execute high-confidence signals
MAX_RISK_PER_TRADE=0.03        # Risk max 3% per trade
MAX_POSITIONS=10               # Maximum concurrent positions
SIGNAL_COOLDOWN_MINUTES=30     # Wait between signals for same asset
```

## 📊 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Free APIs     │    │   Signal        │    │   Trading       │
│                 │    │   Engine        │    │   Controller    │
│ • Reddit        │───▶│                 │───▶│                 │
│ • Etherscan     │    │ • Sentiment     │    │ • Paper Trading │
│ • CoinGecko     │    │ • Whale Tracks  │    │ • Risk Mgmt     │
│ • Google Trends │    │ • Market Data   │    │ • Execution     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Rate Limiter  │    │   WebSocket     │    │   Alert System  │
│                 │    │   Manager       │    │                 │
│ • Smart Queuing │    │                 │    │ • Telegram      │
│ • Usage Monitor │    │ • Real-time     │    │ • Discord       │
│ • Error Recovery│    │ • Multi-client  │    │ • Email         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │   React UI      │
                    │                 │
                    │ • Live Charts   │
                    │ • One-click UI  │
                    │ • Portfolio     │
                    │ • Settings      │
                    └─────────────────┘
```

## 🔧 Configuration Options

### Trading Parameters
```env
INITIAL_DEMO_BALANCE=100000.0     # Starting balance
MAX_POSITIONS=10                  # Max concurrent positions
MIN_SIGNAL_CONFIDENCE=0.7         # Minimum confidence to execute
MAX_RISK_PER_TRADE=0.03          # Maximum risk per trade (3%)
TRADING_WATCHLIST=BTC,ETH,ADA,SOL # Symbols to monitor
```

### Alert Settings
```env
TELEGRAM_ALERTS_ENABLED=true
DISCORD_ALERTS_ENABLED=false
EMAIL_ALERTS_ENABLED=false
```

### Rate Limiting
```env
REDDIT_REQUESTS_PER_MINUTE=60
ETHERSCAN_REQUESTS_PER_SECOND=5
COINGECKO_REQUESTS_PER_MINUTE=50
GOOGLE_TRENDS_REQUESTS_PER_HOUR=100
```

## 📈 Signal Types

### 1. Sentiment Signals
- **Bullish Social**: Positive Reddit sentiment spike
- **Bearish Social**: Negative sentiment increase
- **Viral Potential**: Unusual engagement growth

### 2. Whale Signals
- **Accumulation**: Large wallets buying
- **Distribution**: Large wallets selling
- **Exchange Flow**: Unusual exchange movements

### 3. Market Signals
- **Breakout**: Price breaking resistance with volume
- **Mean Reversion**: Oversold/overbought conditions
- **Trend Following**: Momentum continuation

### 4. Search Signals
- **Search Spike**: Google Trends breakout
- **Geographic Interest**: Regional search patterns
- **Related Queries**: Associated search terms

## 🛡️ Risk Management

### Position Sizing
- **Dynamic Sizing**: Based on signal confidence and volatility
- **Risk Parity**: Equal risk across positions
- **Portfolio Heat**: Maximum total portfolio risk

### Stop Loss/Take Profit
- **Volatility-Based**: ATR-based levels
- **Technical Levels**: Support/resistance
- **Time-Based**: Maximum holding period

### Portfolio Protection
- **Maximum Drawdown**: System stops at -10%
- **Correlation Limits**: Avoid highly correlated positions
- **Sector Diversification**: Spread across different crypto sectors

## 📊 Performance Analytics

### Portfolio Metrics
- **Total Return**: Overall performance
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Worst peak-to-trough
- **Win Rate**: Percentage of profitable trades

### Signal Performance
- **Confidence Accuracy**: How often high-confidence signals win
- **Source Performance**: Which data sources work best
- **Time Analysis**: Best times of day/week
- **Market Conditions**: Performance in different markets

## 🐛 Troubleshooting

### Common Issues

1. **API Rate Limits**
   - Check `logs/` directory for rate limit errors
   - Adjust rate limiting settings in `.env`
   - Consider upgrading to paid API tiers

2. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Frontend Issues**
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. **Database Issues**
   - Check `DATABASE_URL` in `.env`
   - Ensure PostgreSQL is running (if using)
   - SQLite is used by default for simplicity

### Logging
- **Application Logs**: `logs/smart_money.log`
- **Error Logs**: Console output
- **Debug Mode**: Set `DEBUG=true` in `.env`

## 🚨 Important Disclaimers

⚠️ **This is a PAPER TRADING system for educational purposes only**

- ❌ **No real money** is involved
- ❌ **No real trading** is executed
- ✅ All trades are **simulated**
- ✅ Perfect for **learning and testing**
- ✅ **Safe environment** to test strategies

## 🤝 Contributing

This system is designed to be:
- **Extensible**: Add new data sources easily
- **Modular**: Swap components without affecting others
- **Well-documented**: Clear code structure and comments
- **Test-friendly**: Built with testing in mind

## 📞 Support

- **Documentation**: Check this README and code comments
- **Logs**: Check `logs/` directory for detailed information
- **API Docs**: Visit http://localhost:8080/docs for API reference

---

## 🎯 Next Steps

1. **Get API Keys**: Set up your free API keys
2. **Run the System**: Use `python start_trading_system.py`
3. **Explore Dashboard**: Open http://localhost:3000
4. **Watch Signals**: See live signals in the interface
5. **Test Trading**: Try executing signals manually
6. **Enable Auto-Trading**: Let the system trade automatically
7. **Monitor Performance**: Track your paper trading results

**Happy Trading!** 📈🚀