import React from 'react';
import { List, Avatar, Tag, Typography, Space, Progress } from 'antd';
import { 
  RocketOutlined, 
  TrendingUpOutlined, 
  WarningOutlined, 
  AimOutlined 
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { Text } = Typography;

const RecentSignals = ({ signals = [] }) => {
  if (!signals.length) {
    return (
      <div style={{ textAlign: 'center', padding: '20px', color: '#666' }}>
        No recent signals with high confidence
      </div>
    );
  }

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

  return (
    <List
      itemLayout="horizontal"
      dataSource={signals.slice(0, 10)}
      renderItem={(signal) => (
        <List.Item
          className={`signal-card signal-type-${signal.signal_type}`}
          actions={[
            <Tag color={getActionColor(signal.action)}>
              {signal.action.toUpperCase()}
            </Tag>
          ]}
        >
          <List.Item.Meta
            avatar={
              <Avatar 
                icon={getSignalIcon(signal.signal_type)}
                style={{ 
                  backgroundColor: getConfidenceColor(signal.confidence) 
                }}
              />
            }
            title={
              <Space>
                <Tag color={getSignalTypeColor(signal.signal_type)}>
                  {signal.signal_type.replace('_', ' ').toUpperCase()}
                </Tag>
                <Text strong>{signal.token_symbol}</Text>
              </Space>
            }
            description={
              <div>
                <div style={{ marginBottom: 8 }}>
                  <Text>{signal.reasoning}</Text>
                </div>
                
                <Space direction="vertical" size={4}>
                  <div>
                    <Text type="secondary">Price: </Text>
                    <Text strong>{formatPrice(signal.current_price)}</Text>
                    {signal.target_price && (
                      <>
                        <Text type="secondary"> → </Text>
                        <Text type="success">{formatPrice(signal.target_price)}</Text>
                      </>
                    )}
                  </div>
                  
                  <div>
                    <Text type="secondary">Confidence: </Text>
                    <Progress
                      percent={Math.round(signal.confidence * 100)}
                      size="small"
                      strokeColor={getConfidenceColor(signal.confidence)}
                      showInfo={false}
                      style={{ width: 100, display: 'inline-block' }}
                    />
                    <Text style={{ marginLeft: 8 }}>
                      {Math.round(signal.confidence * 100)}%
                    </Text>
                  </div>
                  
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {dayjs(signal.timestamp).fromNow()}
                  </Text>
                </Space>
              </div>
            }
          />
        </List.Item>
      )}
    />
  );
};

export default RecentSignals;


