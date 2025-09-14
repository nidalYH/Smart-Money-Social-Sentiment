import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// System endpoints
export const systemApi = {
  health: () => api.get('/health'),
  status: () => api.get('/status'),
};

// Whale tracking endpoints
export const whaleApi = {
  getActivity: (hoursBack = 24) => api.get(`/api/whales/activity?hours_back=${hoursBack}`),
  getAccumulation: (tokenAddress, hoursBack = 48) => 
    api.get(`/api/whales/accumulation/${tokenAddress}?hours_back=${hoursBack}`),
};

// Sentiment analysis endpoints
export const sentimentApi = {
  getOverview: () => api.get('/api/sentiment/overview'),
  getTokenSentiment: (tokenSymbol, hoursBack = 24) => 
    api.get(`/api/sentiment/token/${tokenSymbol}?hours_back=${hoursBack}`),
};

// Trading signals endpoints
export const signalsApi = {
  getRecent: (hoursBack = 24, minConfidence = 0.7) => 
    api.get(`/api/signals/recent?hours_back=${hoursBack}&min_confidence=${minConfidence}`),
  generate: (hoursBack = 48) => api.post(`/api/signals/generate?hours_back=${hoursBack}`),
};

// Alert endpoints
export const alertsApi = {
  getStatistics: (hoursBack = 24) => api.get(`/api/alerts/statistics?hours_back=${hoursBack}`),
  retryFailed: (maxRetries = 3) => api.post(`/api/alerts/retry?max_retries=${maxRetries}`),
};

// Export endpoints
export const exportApi = {
  whaleTransactions: (hoursBack = 168) =>
    api.get(`/api/export/whale-transactions?hours_back=${hoursBack}`),
  signals: (hoursBack = 168) =>
    api.get(`/api/export/signals?hours_back=${hoursBack}`),
};

// Trading endpoints for TradingDashboard
export const tradingApi = {
  getPortfolio: () => api.get('/api/trading/portfolio'),
  getPositions: () => api.get('/api/trading/positions'),
  getTrades: () => api.get('/api/trading/trades'),
  executeSignal: (signal) => api.post('/api/trading/execute-signal', signal),
  closePosition: (symbol) => api.post('/api/trading/close-position', { symbol }),
  toggleAutoTrading: (enabled) => api.post('/api/trading/auto-trading', { enabled }),
  getMarketOverview: () => api.get('/api/market/overview'),
  getSystemStatus: () => api.get('/api/system/status'),
};

export default api;


