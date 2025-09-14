import React, { useState, useEffect, useCallback } from 'react';
import { Card, Row, Col, Button, Switch, Statistic, Tag, Timeline, Progress, Alert, Space, Spin } from 'antd';
import {
  TrophyOutlined,
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  ThunderboltOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import toast, { Toaster } from 'react-hot-toast';
import { tradingApi } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import dayjs from 'dayjs';

const TradingDashboard = () => {
  // State management
  const [signals, setSignals] = useState([]);
  const [portfolio, setPortfolio] = useState({});
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [autoTrading, setAutoTrading] = useState(false);
  const [systemStatus, setSystemStatus] = useState('healthy');
  const [marketOverview, setMarketOverview] = useState({});
  const [loading, setLoading] = useState(true);

  // Use the WebSocket hook
  const { isConnected, lastMessage } = useWebSocket();

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      const { type, data } = lastMessage;

      switch (type) {
        case 'connection_established':
          toast.success('🔗 Connected to live trading system');
          break;

        case 'new_signal':
          setSignals(prev => [data.signal || data, ...prev.slice(0, 19)]);
          toast.success(`🚨 New signal: ${data.signal?.symbol || 'Unknown'}`);
          break;

        case 'portfolio_update':
          setPortfolio(data.portfolio || data);
          setPositions(data.positions || []);
          break;

        case 'trade_executed':
          setTrades(prev => [data.trade || data, ...prev.slice(0, 49)]);
          const emoji = data.trade?.side === 'BUY' ? '🟢' : '🔴';
          toast.success(`${emoji} Trade executed: ${data.trade?.symbol || 'Unknown'}`);
          break;

        case 'position_closed':
          const pnlColor = data.realized_pnl > 0 ? '💚' : '❤️';
          const pnlText = data.realized_pnl > 0 ? 'profit' : 'loss';
          toast.success(`${pnlColor} Position closed: ${data.symbol} (${pnlText})`);
          break;

        case 'system_alert':
          if (data.level === 'error') {
            toast.error(`⚠️ ${data.message}`);
          } else if (data.level === 'warning') {
            toast.error(`⚠️ ${data.message}`);
          } else {
            toast(`ℹ️ ${data.message}`);
          }
          break;
      }
    }
  }, [lastMessage]);

  // Load initial data
  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      // Load all dashboard data in parallel
      const [
        signalsRes,
        portfolioRes,
        positionsRes,
        tradesRes,
        marketRes,
        statusRes
      ] = await Promise.all([
        tradingApi.getSystemStatus(),
        tradingApi.getPortfolio(),
        tradingApi.getPositions(),
        tradingApi.getTrades(),
        tradingApi.getMarketOverview(),
        tradingApi.getSystemStatus()
      ].map(p => p.catch(e => ({ data: null }))));

      setSignals(signalsRes.data);
      setPortfolio(portfolioRes.data);
      setPositions(positionsRes.data);
      setTrades(tradesRes.data);
      setMarketOverview(marketRes.data);
      setSystemStatus(statusRes.data.health);

    } catch (error) {
      console.error('Error loading dashboard data:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  // Execute signal manually
  const executeSignal = async (signal) => {
    try {
      const response = await tradingApi.executeSignal(signal);

      if (response.data.success) {
        toast.success(`✅ ${signal.signal_type} order executed for ${signal.symbol}`);
      } else {
        toast.error(`❌ Failed to execute: ${response.data.reason}`);
      }
    } catch (error) {
      console.error('Error executing signal:', error);
      toast.error('Failed to execute signal');
    }
  };

  // Toggle auto-trading
  const toggleAutoTrading = async (enabled) => {
    try {
      await tradingApi.toggleAutoTrading(enabled);
      setAutoTrading(enabled);

      if (enabled) {
        toast.success('🤖 Auto-trading ENABLED');
      } else {
        toast.success('⏸️ Auto-trading DISABLED');
      }
    } catch (error) {
      console.error('Error toggling auto-trading:', error);
      toast.error('Failed to toggle auto-trading');
    }
  };

  // Close position manually
  const closePosition = async (symbol) => {
    try {
      const response = await tradingApi.closePosition(symbol);

      if (response.data.success) {
        toast.success(`✅ Position closed: ${symbol}`);
      } else {
        toast.error(`❌ Failed to close position: ${response.data.reason}`);
      }
    } catch (error) {
      console.error('Error closing position:', error);
      toast.error('Failed to close position');
    }
  };

  const SignalCard = ({ signal }) => (
    <Card
      size="small"
      className="mb-2"
      style={{
        borderLeft: `4px solid ${
          signal.signal_type.includes('BUY') ? '#52c41a' :
          signal.signal_type.includes('SELL') ? '#ff4d4f' : '#1890ff'
        }`
      }}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Tag
              color={
                signal.signal_type.includes('BUY') ? 'green' :
                signal.signal_type.includes('SELL') ? 'red' : 'blue'
              }
              className="font-bold"
            >
              {signal.signal_type}
            </Tag>
            <span className="font-semibold text-lg">{signal.symbol}</span>
            <Tag color="purple">{(signal.confidence * 100).toFixed(1)}%</Tag>
          </div>

          <div className="text-sm text-gray-600 mb-2">
            <div>Entry: ${signal.entry_price?.toFixed(4) || 'N/A'}</div>
            <div>Target: ${signal.target_price?.toFixed(4) || 'N/A'}</div>
            <div>Stop: ${signal.stop_loss?.toFixed(4) || 'N/A'}</div>
          </div>

          <div className="text-xs text-gray-500 mb-2">
            {signal.reasoning.length > 100
              ? signal.reasoning.substring(0, 100) + '...'
              : signal.reasoning}
          </div>

          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span>{dayjs(signal.timestamp).format('HH:mm:ss')}</span>
            <span>•</span>
            <span>Risk: {(signal.risk_score * 100).toFixed(0)}%</span>
          </div>
        </div>

        <div className="ml-4">
          <Button
            type={signal.signal_type.includes('BUY') ? 'primary' : 'danger'}
            size="small"
            icon={<ThunderboltOutlined />}
            onClick={() => executeSignal(signal)}
            disabled={autoTrading}
          >
            {autoTrading ? '🤖' : 'Execute'}
          </Button>
        </div>
      </div>
    </Card>
  );

  const PositionCard = ({ position }) => (
    <Card size="small" className="mb-2">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold">{position.symbol}</span>
            <Tag color={position.unrealized_pnl >= 0 ? 'green' : 'red'}>
              {position.unrealized_pnl >= 0 ? '+' : ''}{position.unrealized_pnl_pct.toFixed(2)}%
            </Tag>
          </div>

          <div className="text-sm text-gray-600">
            <div>Qty: {position.quantity.toFixed(4)}</div>
            <div>Entry: ${position.entry_price.toFixed(4)}</div>
            <div>Current: ${position.current_price.toFixed(4)}</div>
            <div>P&L: ${position.unrealized_pnl.toFixed(2)}</div>
          </div>
        </div>

        <Button
          size="small"
          danger
          onClick={() => closePosition(position.symbol)}
        >
          Close
        </Button>
      </div>
    </Card>
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <Spin size="large" />
        <span className="ml-3">Loading Trading Dashboard...</span>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
        }}
      />

      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">
              🚀 Smart Money Trading Dashboard
            </h1>
            <p className="text-gray-600">Real-time signals • Demo trading • Performance analytics</p>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span>Auto-Trading:</span>
              <Switch
                checked={autoTrading}
                onChange={toggleAutoTrading}
                checkedChildren={<PlayCircleOutlined />}
                unCheckedChildren={<PauseCircleOutlined />}
              />
            </div>

            <Tag color={systemStatus === 'healthy' ? 'green' : 'red'}>
              {systemStatus === 'healthy' ? '🟢' : '🔴'} System {systemStatus}
            </Tag>
          </div>
        </div>
      </div>

      {/* Key Metrics Row */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Portfolio Value"
              value={portfolio.total_value || 0}
              precision={2}
              prefix="$"
              valueStyle={{ color: portfolio.total_return_pct >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Return"
              value={portfolio.total_return_pct || 0}
              precision={2}
              suffix="%"
              prefix={portfolio.total_return_pct >= 0 ? <RiseOutlined /> : <FallOutlined />}
              valueStyle={{ color: portfolio.total_return_pct >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Win Rate"
              value={portfolio.win_rate || 0}
              precision={1}
              suffix="%"
              prefix={<TrophyOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Active Positions"
              value={positions.length || 0}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Row gutter={[16, 16]}>
        {/* Live Signals */}
        <Col xs={24} lg={12}>
          <Card
            title="🚨 Live Trading Signals"
            extra={
              <Tag color="blue">{signals.length} signals</Tag>
            }
            className="h-96"
          >
            <div className="h-80 overflow-y-auto">
              {signals.length > 0 ? (
                signals.map((signal, index) => (
                  <SignalCard key={index} signal={signal} />
                ))
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <div className="text-center">
                    <EyeOutlined className="text-4xl mb-2" />
                    <p>Waiting for trading signals...</p>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </Col>

        {/* Current Positions */}
        <Col xs={24} lg={12}>
          <Card
            title="📊 Current Positions"
            extra={
              <Tag color="green">{positions.length} positions</Tag>
            }
            className="h-96"
          >
            <div className="h-80 overflow-y-auto">
              {positions.length > 0 ? (
                positions.map((position, index) => (
                  <PositionCard key={index} position={position} />
                ))
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <div className="text-center">
                    <DollarOutlined className="text-4xl mb-2" />
                    <p>No open positions</p>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </Col>

        {/* Portfolio Performance Chart */}
        <Col xs={24} lg={16}>
          <Card title="📈 Portfolio Performance" className="h-96">
            <div className="h-80">
              {portfolio.balance_history && portfolio.balance_history.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={portfolio.balance_history}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => dayjs(value).format('MMM DD')}
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                    />
                    <Tooltip
                      formatter={(value) => [`$${value.toFixed(2)}`, 'Portfolio Value']}
                      labelFormatter={(value) => dayjs(value).format('MMM DD, YYYY HH:mm')}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#1890ff"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <div className="text-center">
                    <BarChartOutlined className="text-4xl mb-2" />
                    <p>Portfolio chart will appear after first trades</p>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </Col>

        {/* Recent Trades */}
        <Col xs={24} lg={8}>
          <Card title="📋 Recent Trades" className="h-96">
            <div className="h-80 overflow-y-auto">
              <Timeline
                items={trades.slice(0, 10).map((trade, index) => ({
                  children: (
                    <div key={index} className="text-xs">
                      <div className="flex items-center gap-2 mb-1">
                        <Tag
                          color={trade.side === 'BUY' ? 'green' : 'red'}
                          size="small"
                        >
                          {trade.side}
                        </Tag>
                        <span className="font-medium">{trade.symbol}</span>
                        {trade.realized_pnl && (
                          <Tag
                            color={trade.realized_pnl > 0 ? 'green' : 'red'}
                            size="small"
                          >
                            {trade.realized_pnl > 0 ? '+' : ''}${trade.realized_pnl.toFixed(2)}
                          </Tag>
                        )}
                      </div>
                      <div className="text-gray-500">
                        {trade.quantity.toFixed(4)} @ ${trade.price.toFixed(4)}
                      </div>
                      <div className="text-gray-400">
                        {dayjs(trade.timestamp).format('MMM DD, HH:mm:ss')}
                      </div>
                    </div>
                  ),
                  color: trade.side === 'BUY' ? 'green' : 'red'
                }))}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* Market Overview */}
      <Row gutter={[16, 16]} className="mt-6">
        <Col span={24}>
          <Card title="🌍 Market Overview">
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={8}>
                <Statistic
                  title="Fear & Greed Index"
                  value={marketOverview.fear_greed_index || 50}
                  suffix="/100"
                  valueStyle={{
                    color: marketOverview.fear_greed_index > 50 ? '#cf1322' : '#3f8600'
                  }}
                />
                <div className="text-sm text-gray-500 mt-1">
                  {marketOverview.fear_greed_classification || 'Neutral'}
                </div>
              </Col>
              <Col xs={24} sm={8}>
                <Statistic
                  title="Bitcoin Dominance"
                  value={marketOverview.btc_dominance || 0}
                  precision={1}
                  suffix="%"
                />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic
                  title="Total Market Cap"
                  value={marketOverview.market_cap || 0}
                  formatter={(value) => `$${(value / 1e12).toFixed(2)}T`}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default TradingDashboard;