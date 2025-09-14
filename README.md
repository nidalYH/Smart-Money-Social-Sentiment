# Smart Money Social Sentiment Analyzer

A comprehensive system that combines on-chain whale movements with social sentiment analysis to identify early investment opportunities before FOMO kicks in.

## 🚀 Features

### Core Functionality
- **Whale Tracking**: Monitor top 100+ wallets by ETH holdings
- **Social Sentiment**: Analyze Twitter and Telegram sentiment in real-time
- **Signal Generation**: Generate actionable trading signals combining whale activity and sentiment
- **Multi-Channel Alerts**: Telegram, Discord, Email, and SMS notifications
- **Real-Time Dashboard**: Live updates via WebSocket
- **Performance Analytics**: Track signal accuracy and system performance

### Signal Types
- **Early Accumulation**: Whales buying with low social attention
- **Momentum Build**: Social sentiment rising with whale backing
- **FOMO Warning**: High social buzz but whales selling
- **Contrarian Play**: Negative sentiment but whales accumulating

## 🏗️ Architecture

### Technology Stack
- **Backend**: Python 3.11+ with FastAPI
- **Database**: PostgreSQL with Redis caching
- **Frontend**: React with Ant Design
- **APIs**: Etherscan, CoinGecko, Twitter API v2, Telegram Bot API
- **Deployment**: Docker containers with Nginx reverse proxy

### System Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Whale Tracker │    │ Sentiment Engine│    │ Signal Generator│
│                 │    │                 │    │                 │
│ • Etherscan API │    │ • Twitter API   │    │ • Pattern Match │
│ • Transaction   │    │ • Telegram Bot  │    │ • Risk Scoring  │
│   Analysis      │    │ • VADER Sentiment│   │ • Confidence    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Alert Manager  │
                    │                 │
                    │ • Multi-channel │
                    │ • Rate Limiting │
                    │ • Delivery Stats│
                    └─────────────────┘
```

## 🛠️ Installation

### Prerequisites
- Docker and Docker Compose
- API keys for Etherscan, Twitter, and Telegram

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd smart-money-sentiment
   ```

2. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

3. **Run setup script**
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

4. **Access the dashboard**
   - Dashboard: http://localhost:8080
   - API Docs: http://localhost:8080/docs
   - Health Check: http://localhost:8080/health

### Manual Setup

1. **Start database services**
   ```bash
   docker-compose up -d postgres redis
   ```

2. **Build and start application**
   ```bash
   docker-compose build
   docker-compose up -d smartmoney-app
   ```

3. **Check logs**
   ```bash
   docker-compose logs -f smartmoney-app
   ```

## ⚙️ Configuration

### Required API Keys

Add these to your `.env` file:

```bash
# Etherscan API (Free tier: 5 req/sec)
ETHERSCAN_API_KEY=your_etherscan_api_key

# Twitter API v2 (Basic tier: 300 req/15min)
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Telegram Bot (for alerts)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Optional: CoinGecko API (Free tier: 30 req/min)
COINGECKO_API_KEY=your_coingecko_api_key

# Optional: Discord Webhook (for alerts)
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

### Whale Wallet Configuration

The system automatically tracks wallets with >1000 ETH. To customize:

```bash
MIN_WHALE_BALANCE=1000        # Minimum ETH balance
MAX_WHALE_WALLETS=100         # Maximum wallets to track
WHALE_TRACKING_INTERVAL=300   # Tracking interval (seconds)
```

### Signal Thresholds

```bash
SIGNAL_CONFIDENCE_THRESHOLD=0.7  # Minimum confidence for alerts
MAX_ALERTS_PER_HOUR=10           # Rate limiting
```

## 📊 Usage

### Dashboard Features

1. **Overview**: System status, whale activity, sentiment trends
2. **Whale Tracker**: Real-time whale transaction monitoring
3. **Sentiment Analysis**: Token sentiment with trend analysis
4. **Trading Signals**: Generated signals with confidence scores
5. **Alerts**: Alert delivery statistics and management
6. **System Status**: Component health and performance metrics

### API Endpoints

- `GET /health` - System health check
- `GET /api/whales/activity` - Recent whale activity
- `GET /api/sentiment/overview` - Market sentiment overview
- `GET /api/signals/recent` - Recent trading signals
- `POST /api/signals/generate` - Manually trigger signal generation
- `WebSocket /ws` - Real-time updates

### WebSocket Events

Connect to `ws://localhost:8080/ws` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle real-time updates
};
```

## 🔧 Development

### Local Development

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start database services**
   ```bash
   docker-compose up -d postgres redis
   ```

3. **Run backend**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
   ```

4. **Run frontend**
   ```bash
   cd frontend
   npm install
   npm start
   ```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head
```

### Testing

```bash
# Run backend tests
pytest tests/

# Run frontend tests
cd frontend
npm test
```

## 📈 Performance

### System Requirements

- **CPU**: 2+ cores
- **RAM**: 4GB+ (8GB recommended)
- **Storage**: 10GB+ (for historical data)
- **Network**: Stable internet connection

### Optimization Tips

1. **Database Indexing**: Ensure proper indexes on frequently queried columns
2. **Redis Caching**: Tune cache TTL based on data freshness requirements
3. **API Rate Limits**: Monitor and optimize API usage
4. **Background Tasks**: Adjust tracking intervals based on system load

### Monitoring

- Health check endpoint: `/health`
- System status: `/status`
- Alert delivery statistics: `/api/alerts/statistics`
- Component performance metrics via dashboard

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   docker-compose logs postgres
   docker-compose restart postgres
   ```

2. **API Rate Limit Exceeded**
   - Check API key limits
   - Adjust tracking intervals
   - Implement request queuing

3. **High Memory Usage**
   ```bash
   # Monitor memory usage
   docker stats
   
   # Adjust Redis memory limits
   # Update docker-compose.yml redis service
   ```

4. **WebSocket Connection Issues**
   - Check firewall settings
   - Verify nginx configuration
   - Check browser console for errors

### Logs

```bash
# Application logs
docker-compose logs -f smartmoney-app

# Database logs
docker-compose logs -f postgres

# Redis logs
docker-compose logs -f redis

# All services
docker-compose logs -f
```

## 🔒 Security

### Production Deployment

1. **Environment Variables**
   - Use strong, unique passwords
   - Rotate API keys regularly
   - Enable HTTPS with valid certificates

2. **Network Security**
   - Use firewall rules
   - Implement rate limiting
   - Monitor for suspicious activity

3. **Data Protection**
   - Regular database backups
   - Encrypt sensitive data
   - Implement access controls

### Security Headers

The nginx configuration includes security headers:
- X-Frame-Options
- X-XSS-Protection
- X-Content-Type-Options
- Content-Security-Policy

## 📝 API Documentation

Full API documentation is available at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

### Key Endpoints

#### Whale Tracking
```bash
# Get whale activity
GET /api/whales/activity?hours_back=24

# Get accumulation analysis
GET /api/whales/accumulation/{token_address}?hours_back=48
```

#### Sentiment Analysis
```bash
# Market sentiment overview
GET /api/sentiment/overview

# Token sentiment
GET /api/sentiment/token/{token_symbol}?hours_back=24
```

#### Trading Signals
```bash
# Recent signals
GET /api/signals/recent?hours_back=24&min_confidence=0.7

# Generate signals
POST /api/signals/generate?hours_back=48
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style

- Python: Follow PEP 8
- JavaScript: Use ESLint configuration
- Use meaningful commit messages
- Add documentation for new features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. It is not financial advice. Always do your own research and consider the risks before making investment decisions.

## 🆘 Support

- Create an issue for bugs or feature requests
- Check the troubleshooting section
- Review API documentation
- Monitor system logs for errors

---

**Built with ❤️ for the crypto community**


