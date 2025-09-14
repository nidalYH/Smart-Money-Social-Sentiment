import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Typography, Space, Spin, Alert } from 'antd';
import {
  TrendingUpOutlined,
  WalletOutlined,
  HeartOutlined,
  BellOutlined,
  DollarCircleOutlined,
  TrophyOutlined
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

import { systemApi, whaleApi, sentimentApi, signalsApi } from '../services/api';
import WhaleActivity from './WhaleActivity';
import RecentSignals from './RecentSignals';

const { Title, Text } = Typography;

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dashboardData, setDashboardData] = useState({
    systemStatus: null,
    whaleActivity: null,
    sentimentOverview: null,
    recentSignals: null,
  });

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [systemStatus, whaleActivity, sentimentOverview, recentSignals] = await Promise.all([
        systemApi.status().then(res => res.data),
        whaleApi.getActivity(24).then(res => res.data).catch(() => null),
        sentimentApi.getOverview().then(res => res.data).catch(() => null),
        signalsApi.getRecent(24, 0.7).then(res => res.data).catch(() => null),
      ]);

      setDashboardData({
        systemStatus,
        whaleActivity,
        sentimentOverview,
        recentSignals,
      });
    } catch (err) {
      console.error('Error loading dashboard data:', err);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-spinner">
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="Error"
        description={error}
        type="error"
        showIcon
        action={
          <button onClick={loadDashboardData} style={{ marginLeft: 16 }}>
            Retry
          </button>
        }
      />
    );
  }

  const { systemStatus, whaleActivity, sentimentOverview, recentSignals } = dashboardData;

  // Prepare chart data
  const whaleActivityData = whaleActivity?.activities?.slice(0, 10).map(activity => ({
    time: new Date(activity.timestamp).toLocaleTimeString(),
    amount: activity.amount_usd,
    urgency: activity.urgency_score,
  })) || [];

  const sentimentData = [
    { name: 'BTC', sentiment: sentimentOverview?.overall_sentiment || 0 },
    { name: 'ETH', sentiment: 0.2 },
    { name: 'SOL', sentiment: -0.1 },
    { name: 'ADA', sentiment: 0.3 },
    { name: 'DOT', sentiment: 0.1 },
  ];

  return (
    <div>
      <Title level={2}>Dashboard</Title>
      
      {/* System Status Overview */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="System Status"
              value={systemStatus?.system || 'Unknown'}
              prefix={<TrophyOutlined />}
              valueStyle={{ 
                color: systemStatus?.system === 'operational' ? '#3f8600' : '#cf1322' 
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Whales"
              value={whaleActivity?.total_activities || 0}
              prefix={<WalletOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Market Sentiment"
              value={sentimentOverview?.overall_sentiment ? 
                (sentimentOverview.overall_sentiment * 100).toFixed(1) + '%' : 'N/A'}
              prefix={<HeartOutlined />}
              valueStyle={{ 
                color: sentimentOverview?.overall_sentiment > 0 ? '#3f8600' : 
                       sentimentOverview?.overall_sentiment < 0 ? '#cf1322' : '#666'
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Signals"
              value={recentSignals?.total_signals || 0}
              prefix={<BellOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="Recent Whale Activity" extra={<Text type="secondary">Last 24 hours</Text>}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={whaleActivityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip formatter={(value) => [`$${value.toLocaleString()}`, 'Amount']} />
                <Bar dataKey="amount" fill="#1890ff" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Token Sentiment" extra={<Text type="secondary">Current sentiment</Text>}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={sentimentData} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[-1, 1]} />
                <YAxis dataKey="name" type="category" />
                <Tooltip formatter={(value) => [value.toFixed(2), 'Sentiment']} />
                <Bar 
                  dataKey="sentiment" 
                  fill={(entry) => entry > 0 ? '#52c41a' : entry < 0 ? '#ff4d4f' : '#666'}
                />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Recent Activity Row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Recent Whale Activity" extra={<Text type="secondary">Live updates</Text>}>
            <WhaleActivity activities={whaleActivity?.activities || []} />
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Recent Trading Signals" extra={<Text type="secondary">High confidence</Text>}>
            <RecentSignals signals={recentSignals?.signals || []} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;


