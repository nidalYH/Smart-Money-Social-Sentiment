# 🔗 Frontend-Backend Integration Guide

## 🎯 Complete Setup & Connection Instructions

Your Smart Money Social Sentiment system now has full frontend-backend integration. Here's how to run it:

## 🚀 Quick Start (Recommended)

### Option 1: Use the Complete Startup Script
```bash
python start_complete_system.py
```

This script will:
- ✅ Start the FastAPI backend on port 8080
- ✅ Start the React frontend on port 3000
- ✅ Configure all environment variables
- ✅ Handle port conflicts
- ✅ Install npm dependencies if needed

### Option 2: Manual Startup

#### Start Backend (Terminal 1)
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

#### Start Frontend (Terminal 2)
```bash
cd frontend

# Install dependencies (first time only)
npm install

# Add required dependencies
npm install dayjs react-hot-toast recharts

# Start React development server
npm start
```

## 🌐 Access URLs

Once both servers are running:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend Dashboard** | http://localhost:3000 | Main React application |
| **Backend API** | http://localhost:8080 | FastAPI server |
| **API Documentation** | http://localhost:8080/docs | Interactive API docs |
| **WebSocket** | ws://localhost:8080/ws | Real-time updates |

## 📊 Available Features

### 🏠 Dashboard (`/`)
- System status overview
- Whale activity summary
- Market sentiment metrics
- Recent trading signals
- Real-time WebSocket updates

### 💼 Trading Panel (`/trading`)
- Live trading signals
- Portfolio performance
- Current positions
- Trade execution
- Auto-trading controls
- Real-time P&L updates

### 🐋 Whale Tracker (`/whales`)
- Recent whale transactions
- Large holder activity
- Transaction analysis

### 💭 Sentiment Analysis (`/sentiment`)
- Social sentiment metrics
- Market mood analysis
- Token-specific sentiment

### 🎯 Signal History (`/signals`)
- Trading signal archive
- Confidence scores
- Performance tracking

## 🔧 API Integration Details

### ✅ Connected Endpoints

The frontend now connects to these backend endpoints:

#### System Endpoints
- `GET /health` - Health check
- `GET /status` - System metrics
- `GET /api/system/status` - System health
- `GET /api/market/overview` - Market data

#### Whale Tracking
- `GET /api/whales/activity` - Recent whale activity
- `GET /api/whales/accumulation/{token}` - Token accumulation

#### Sentiment Analysis
- `GET /api/sentiment/overview` - Market sentiment
- `GET /api/sentiment/token/{symbol}` - Token sentiment

#### Trading Signals
- `GET /api/signals/recent` - Recent signals
- `POST /api/signals/generate` - Generate new signals

#### Trading System
- `GET /api/trading/portfolio` - Portfolio metrics
- `GET /api/trading/positions` - Current positions
- `GET /api/trading/trades` - Trade history
- `POST /api/trading/execute-signal` - Execute signal
- `POST /api/trading/close-position` - Close position
- `POST /api/trading/auto-trading` - Toggle auto-trading

#### Alerts & Export
- `GET /api/alerts/statistics` - Alert stats
- `GET /api/export/whale-transactions` - Export whale data
- `GET /api/export/signals` - Export signals

### 🔌 WebSocket Integration

Real-time updates for:
- New trading signals
- Trade executions
- Portfolio updates
- Position changes
- System alerts
- Market updates

## 🧪 Testing the Integration

### Test Backend APIs
```bash
python test_system.py
```

### Manual API Testing
```bash
# Test health endpoint
curl http://localhost:8080/health

# Test whale activity
curl http://localhost:8080/api/whales/activity

# Test signals
curl http://localhost:8080/api/signals/recent
```

### Frontend Testing
1. Navigate to http://localhost:3000
2. Check browser console for connection status
3. Verify real-time updates work
4. Test trading dashboard functionality

## 🛠️ Configuration

### Environment Variables

#### Backend (`.env` in root)
```env
# Database
DATABASE_URL=sqlite:///./smart_money.db

# API Keys (optional)
ETHERSCAN_API_KEY=your_key_here
COINGECKO_API_KEY=your_key_here

# Trading Settings
INITIAL_DEMO_BALANCE=100000
MAX_POSITIONS=10

# System
DEBUG=True
LOG_LEVEL=INFO
```

#### Frontend (`frontend/.env`)
```env
REACT_APP_API_URL=http://localhost:8080
REACT_APP_WS_URL=ws://localhost:8080/ws
REACT_APP_ENVIRONMENT=development
```

## 🔍 Troubleshooting

### Port Conflicts
If ports 3000 or 8080 are in use:
```bash
# Windows
netstat -ano | findstr :8080
taskkill /F /PID <PID>

# Linux/Mac
lsof -ti:8080 | xargs kill -9
```

### Common Issues

#### ❌ "Connection refused"
- Backend not running on port 8080
- Check with: `curl http://localhost:8080/health`

#### ❌ WebSocket connection fails
- Ensure WebSocket endpoint is available
- Check browser console for errors
- Verify `/ws` endpoint responds

#### ❌ API calls return 404
- Backend routes not properly configured
- Check API documentation at `/docs`

#### ❌ Frontend build errors
- Install missing dependencies: `npm install`
- Clear cache: `npm start -- --reset-cache`

### Debug Mode

Enable detailed logging:
```bash
# Backend
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload

# Frontend
REACT_APP_DEBUG=true npm start
```

## 📈 Performance Notes

### Optimizations Applied
- ✅ API request caching
- ✅ WebSocket reconnection logic
- ✅ Error boundary components
- ✅ Loading states
- ✅ Responsive design
- ✅ Real-time data updates

### Resource Usage
- Backend: ~100-200MB RAM
- Frontend: ~50-100MB RAM
- Database: SQLite (~10-50MB)

## 🔧 Development

### Adding New Features
1. Backend: Add routes in `app/api/`
2. Frontend: Add services in `src/services/api.js`
3. Components: Create in `src/components/`
4. Update WebSocket messages if needed

### Code Structure
```
app/                          # Backend
├── api/                      # API routes
├── core/                     # Business logic
├── models/                   # Database models
├── websockets/              # WebSocket handling
└── main.py                  # FastAPI app

frontend/
├── src/
│   ├── components/          # React components
│   ├── services/           # API integration
│   ├── hooks/              # Custom hooks
│   └── App.js              # Main application
└── public/                 # Static files
```

## 🎉 Success!

Your Smart Money Social Sentiment system now has:
- ✅ Full frontend-backend integration
- ✅ Real-time WebSocket communication
- ✅ Complete API connectivity
- ✅ Trading functionality
- ✅ Live data updates
- ✅ Error handling
- ✅ Production-ready setup

Navigate to http://localhost:3000 and start trading! 🚀