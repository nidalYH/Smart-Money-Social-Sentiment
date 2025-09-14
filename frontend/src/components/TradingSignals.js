import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Typography, Space, Button, Select, Progress, Row, Col, Statistic } from 'antd';
import { 
  RocketOutlined, 
  TrendingUpOutlined, 
  WarningOutlined, 
  AimOutlined,
  ReloadOutlined,
  PlayCircleOutlined
} from '@ant-design/icons';
import { signalsApi } from '../services/api';
import dayjs from 'dayjs';

const { Title } = Typography;
const { Option } = Select;

const TradingSignals = () => {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [signals, setSignals] = useState([]);
  const [hoursBack, setHoursBack] = useState(24);
  const [minConfidence, setMinConfidence] = useState(0.7);

  useEffect(() => {
    loadSignals();
  }, [hoursBack, minConfidence]);

  const loadSignals = async () => {
    try {
      setLoading(true);
      const response = await signalsApi.getRecent(hoursBack, minConfidence);
      setSignals(response.data.signals || []);
    } catch (error) {
      console.error('Error loading signals:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateSignals = async () => {
    try {
      setGenerating(true);
      const response = await signalsApi.generate(hoursBack);
      setSignals(response.data.signals || []);
    } catch (error) {
      console.error('Error generating signals:', error);
    } finally {
      setGenerating(false);
    }
  };

  const getSignalIcon = (type) => {
    switch (type) {
      case 'early_accumulation':
        return <RocketOutlined style={{ color: '#52c41a' }} />;
      case 'momentum_build':
        return <TrendingUpOutlined style={{ color: '#1890ff' }} />;
      case 'fomo_warning':
        return <WarningOutlined style={{ color: '#ff4d4f' }} />;
      case 'contrarian_play':
        return <AimOutlined style={{ color: '#722ed1' }} />;
      default:
        return <TrendingUpOutlined style={{ color: '#666' }} />;
    }
  };

  const getSignalTypeColor = (type) => {
    switch (type) {
      case 'early_accumulation':
        return 'green';
      case 'momentum_build':
        return 'blue';
      case 'fomo_warning':
        return 'red';
      case 'contrarian_play':
        return 'purple';
      default:
        return 'default';
    }
  };

  const getActionColor = (action) => {
    switch (action.toLowerCase()) {
      case 'buy':
        return 'green';
      case 'sell':
        return 'red';
      case 'hold':
        return 'blue';
      default:
        return 'default';
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return '#52c41a';
    if (confidence >= 0.6) return '#faad14';
    return '#ff4d4f';
  };

  const formatPrice = (price) => {
    if (!price) return 'N/A';
    return `$${price.toFixed(4)}`;
  };

  const columns = [
    {
      title: 'Time',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp) => dayjs(timestamp).format('MMM DD, HH:mm'),
      sorter: (a, b) => new Date(a.timestamp) - new Date(b.timestamp),
    },
    {
      title: 'Signal',
      key: 'signal',
      render: (_, record) => (
        <Space>
          {getSignalIcon(record.signal_type)}
          <Tag color={getSignalTypeColor(record.signal_type)}>
            {record.signal_type.replace('_', ' ').toUpperCase()}
          </Tag>
        </Space>
      ),
    },
    {
      title: 'Token',
      dataIndex: 'token_symbol',
      key: 'token_symbol',
      render: (symbol) => <Tag color="blue">{symbol}</Tag>,
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
      render: (action) => (
        <Tag color={getActionColor(action)}>
          {action.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Price',
      key: 'price',
      render: (_, record) => (
        <div>
          <div>{formatPrice(record.current_price)}</div>
          {record.target_price && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              Target: {formatPrice(record.target_price)}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Confidence',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (confidence) => (
        <div style={{ width: 100 }}>
          <Progress
            percent={Math.round(confidence * 100)}
            size="small"
            strokeColor={getConfidenceColor(confidence)}
            format={(percent) => `${percent}%`}
          />
        </div>
      ),
      sorter: (a, b) => a.confidence - b.confidence,
    },
    {
      title: 'Risk',
      dataIndex: 'risk_score',
      key: 'risk_score',
      render: (risk) => (
        <Tag color={risk > 0.7 ? 'red' : risk > 0.4 ? 'orange' : 'green'}>
          {(risk * 100).toFixed(0)}%
        </Tag>
      ),
      sorter: (a, b) => a.risk_score - b.risk_score,
    },
  ];

  const signalStats = {
    total: signals.length,
    buy: signals.filter(s => s.action === 'buy').length,
    sell: signals.filter(s => s.action === 'sell').length,
    highConfidence: signals.filter(s => s.confidence >= 0.8).length,
  };

  return (
    <div>
      <Title level={2}>Trading Signals</Title>
      
      {/* Controls */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
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
            <Select
              value={minConfidence}
              onChange={setMinConfidence}
              style={{ width: 140 }}
            >
              <Option value={0.5}>50%+ Confidence</Option>
              <Option value={0.6}>60%+ Confidence</Option>
              <Option value={0.7}>70%+ Confidence</Option>
              <Option value={0.8}>80%+ Confidence</Option>
            </Select>
          </Col>
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadSignals}
              loading={loading}
            >
              Refresh
            </Button>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={generateSignals}
              loading={generating}
            >
              Generate Signals
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Signals"
              value={signalStats.total}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Buy Signals"
              value={signalStats.buy}
              valueStyle={{ color: '#52c41a' }}
              prefix={<TrendingUpOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Sell Signals"
              value={signalStats.sell}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="High Confidence"
              value={signalStats.highConfidence}
              valueStyle={{ color: '#722ed1' }}
              prefix={<RocketOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Signals Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={signals}
          rowKey="signal_id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} of ${total} signals`,
          }}
          scroll={{ x: 1000 }}
          expandable={{
            expandedRowRender: (record) => (
              <div style={{ margin: 0 }}>
                <div style={{ marginBottom: 8 }}>
                  <strong>Reasoning:</strong> {record.reasoning}
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Key Factors:</strong>
                  <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
                    {record.key_factors?.map((factor, index) => (
                      <li key={index}>{factor}</li>
                    ))}
                  </ul>
                </div>
                {record.risk_factors?.length > 0 && (
                  <div>
                    <strong>Risk Factors:</strong>
                    <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
                      {record.risk_factors.map((risk, index) => (
                        <li key={index} style={{ color: '#ff4d4f' }}>{risk}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ),
            rowExpandable: (record) => record.reasoning || record.key_factors?.length > 0,
          }}
        />
      </Card>
    </div>
  );
};

export default TradingSignals;


