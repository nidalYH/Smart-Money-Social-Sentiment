import React, { useState, useEffect } from 'react';
import { Card, Typography, Row, Col, Statistic, Select, Button, Space, Tag, Progress } from 'antd';
import { HeartOutlined, TrendingUpOutlined, TrendingDownOutlined, ReloadOutlined } from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { sentimentApi } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const SentimentAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [sentimentData, setSentimentData] = useState(null);
  const [selectedToken, setSelectedToken] = useState('BTC');
  const [hoursBack, setHoursBack] = useState(24);

  const tokenOptions = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'MATIC', 'AVAX', 'NEAR', 'FTM'];

  useEffect(() => {
    loadSentimentData();
  }, [selectedToken, hoursBack]);

  const loadSentimentData = async () => {
    try {
      setLoading(true);
      const [overview, tokenData] = await Promise.all([
        sentimentApi.getOverview().then(res => res.data).catch(() => null),
        sentimentApi.getTokenSentiment(selectedToken, hoursBack).then(res => res.data).catch(() => null)
      ]);
      
      setSentimentData({ overview, tokenData });
    } catch (error) {
      console.error('Error loading sentiment data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSentimentColor = (sentiment) => {
    if (sentiment > 0.2) return '#52c41a';
    if (sentiment < -0.2) return '#ff4d4f';
    return '#666';
  };

  const getSentimentIcon = (sentiment) => {
    if (sentiment > 0.2) return <TrendingUpOutlined style={{ color: '#52c41a' }} />;
    if (sentiment < -0.2) return <TrendingDownOutlined style={{ color: '#ff4d4f' }} />;
    return <HeartOutlined style={{ color: '#666' }} />;
  };

  const getSentimentText = (sentiment) => {
    if (sentiment > 0.5) return 'Very Bullish';
    if (sentiment > 0.2) return 'Bullish';
    if (sentiment > -0.2) return 'Neutral';
    if (sentiment > -0.5) return 'Bearish';
    return 'Very Bearish';
  };

  // Mock data for charts (in real app, this would come from API)
  const sentimentHistoryData = [
    { time: '00:00', sentiment: 0.2 },
    { time: '04:00', sentiment: 0.3 },
    { time: '08:00', sentiment: 0.1 },
    { time: '12:00', sentiment: -0.1 },
    { time: '16:00', sentiment: 0.0 },
    { time: '20:00', sentiment: 0.4 },
    { time: '24:00', sentiment: 0.6 },
  ];

  const tokenSentimentData = [
    { token: 'BTC', sentiment: 0.6, mentions: 1250 },
    { token: 'ETH', sentiment: 0.4, mentions: 980 },
    { token: 'SOL', sentiment: -0.2, mentions: 650 },
    { token: 'ADA', sentiment: 0.3, mentions: 420 },
    { token: 'DOT', sentiment: 0.1, mentions: 380 },
  ];

  return (
    <div>
      <Title level={2}>Sentiment Analysis</Title>
      
      {/* Controls */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Select
              value={selectedToken}
              onChange={setSelectedToken}
              style={{ width: 120 }}
            >
              {tokenOptions.map(token => (
                <Option key={token} value={token}>{token}</Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Select
              value={hoursBack}
              onChange={setHoursBack}
              style={{ width: 120 }}
            >
              <Option value={6}>6 hours</Option>
              <Option value={12}>12 hours</Option>
              <Option value={24}>24 hours</Option>
              <Option value={48}>48 hours</Option>
            </Select>
          </Col>
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadSentimentData}
              loading={loading}
            >
              Refresh
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Market Overview */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Overall Sentiment"
              value={sentimentData?.overview?.overall_sentiment ? 
                (sentimentData.overview.overall_sentiment * 100).toFixed(1) + '%' : 'N/A'}
              prefix={getSentimentIcon(sentimentData?.overview?.overall_sentiment)}
              valueStyle={{ 
                color: getSentimentColor(sentimentData?.overview?.overall_sentiment) 
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Market Trend"
              value={sentimentData?.overview?.trend || 'Unknown'}
              valueStyle={{ 
                color: sentimentData?.overview?.trend === 'bullish' ? '#52c41a' : 
                       sentimentData?.overview?.trend === 'bearish' ? '#ff4d4f' : '#666'
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Tokens"
              value={sentimentData?.overview?.active_tokens || 0}
              prefix={<HeartOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Confidence"
              value={sentimentData?.overview?.confidence ? 
                (sentimentData.overview.confidence * 100).toFixed(1) + '%' : 'N/A'}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title={`${selectedToken} Sentiment Trend`} extra={
            <Tag color={getSentimentColor(sentimentData?.tokenData?.current_sentiment)}>
              {getSentimentText(sentimentData?.tokenData?.current_sentiment)}
            </Tag>
          }>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={sentimentHistoryData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis domain={[-1, 1]} />
                <Tooltip formatter={(value) => [value.toFixed(2), 'Sentiment']} />
                <Line 
                  type="monotone" 
                  dataKey="sentiment" 
                  stroke={getSentimentColor(sentimentData?.tokenData?.current_sentiment)}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Token Sentiment Comparison" extra={
            <Space>
              <Tag color="blue">Sentiment</Tag>
              <Tag color="green">Mentions</Tag>
            </Space>
          }>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={tokenSentimentData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="token" />
                <YAxis yAxisId="left" domain={[-1, 1]} />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip 
                  formatter={(value, name) => [
                    name === 'sentiment' ? value.toFixed(2) : value,
                    name === 'sentiment' ? 'Sentiment' : 'Mentions'
                  ]}
                />
                <Bar 
                  yAxisId="left"
                  dataKey="sentiment" 
                  fill={(entry) => getSentimentColor(entry.sentiment)}
                />
                <Bar 
                  yAxisId="right"
                  dataKey="mentions" 
                  fill="#1890ff"
                  opacity={0.6}
                />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Token Details */}
      {sentimentData?.tokenData && (
        <Card title={`${selectedToken} Sentiment Details`}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} lg={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: getSentimentColor(sentimentData.tokenData.current_sentiment) }}>
                  {sentimentData.tokenData.current_sentiment?.toFixed(2) || 'N/A'}
                </div>
                <div style={{ color: '#666' }}>Current Sentiment</div>
              </div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
                  {sentimentData.tokenData.sentiment_change?.toFixed(2) || 'N/A'}
                </div>
                <div style={{ color: '#666' }}>Change (24h)</div>
              </div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
                  {sentimentData.tokenData.mention_velocity?.toFixed(1) || 'N/A'}
                </div>
                <div style={{ color: '#666' }}>Mentions/hour</div>
              </div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
                  {(sentimentData.tokenData.confidence * 100)?.toFixed(0) || 'N/A'}%
                </div>
                <div style={{ color: '#666' }}>Confidence</div>
              </div>
            </Col>
          </Row>
          
          <div style={{ marginTop: 24 }}>
            <Progress
              percent={Math.abs(sentimentData.tokenData.current_sentiment * 100) || 0}
              strokeColor={getSentimentColor(sentimentData.tokenData.current_sentiment)}
              format={(percent) => `${getSentimentText(sentimentData.tokenData.current_sentiment)}`}
            />
          </div>
        </Card>
      )}
    </div>
  );
};

export default SentimentAnalysis;


