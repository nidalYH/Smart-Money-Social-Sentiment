import React from 'react';
import { List, Avatar, Tag, Typography, Space, Tooltip } from 'antd';
import { WalletOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { Text } = Typography;

const WhaleActivity = ({ activities = [] }) => {
  if (!activities.length) {
    return (
      <div style={{ textAlign: 'center', padding: '20px', color: '#666' }}>
        No whale activity in the last 24 hours
      </div>
    );
  }

  const getTransactionIcon = (type) => {
    return type === 'buy' ? <ArrowUpOutlined style={{ color: '#52c41a' }} /> : 
           <ArrowDownOutlined style={{ color: '#ff4d4f' }} />;
  };

  const getTransactionColor = (type) => {
    return type === 'buy' ? 'green' : 'red';
  };

  const formatAmount = (amount) => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(1)}K`;
    }
    return `$${amount.toFixed(0)}`;
  };

  const getUrgencyLevel = (urgency) => {
    if (urgency > 0.8) return { color: 'red', text: 'High' };
    if (urgency > 0.6) return { color: 'orange', text: 'Medium' };
    return { color: 'green', text: 'Low' };
  };

  const getImpactLevel = (impact) => {
    if (impact > 0.8) return { color: 'red', text: 'High' };
    if (impact > 0.6) return { color: 'orange', text: 'Medium' };
    return { color: 'blue', text: 'Low' };
  };

  return (
    <List
      itemLayout="horizontal"
      dataSource={activities.slice(0, 10)}
      renderItem={(activity) => {
        const urgency = getUrgencyLevel(activity.urgency_score);
        const impact = getImpactLevel(activity.impact_score);
        
        return (
          <List.Item
            actions={[
              <Tooltip title="Urgency Score">
                <Tag color={urgency.color}>{urgency.text}</Tag>
              </Tooltip>,
              <Tooltip title="Market Impact">
                <Tag color={impact.color}>{impact.text}</Tag>
              </Tooltip>
            ]}
          >
            <List.Item.Meta
              avatar={
                <Avatar 
                  icon={<WalletOutlined />} 
                  style={{ 
                    backgroundColor: getTransactionColor(activity.transaction_type) === 'green' ? '#52c41a' : '#ff4d4f'
                  }} 
                />
              }
              title={
                <Space>
                  {getTransactionIcon(activity.transaction_type)}
                  <Text strong>{activity.token_symbol}</Text>
                  <Tag color={getTransactionColor(activity.transaction_type)}>
                    {activity.transaction_type.toUpperCase()}
                  </Tag>
                </Space>
              }
              description={
                <div>
                  <div>
                    <Text strong>{formatAmount(activity.amount_usd)}</Text>
                    <Text type="secondary" style={{ marginLeft: 8 }}>
                      {dayjs(activity.timestamp).fromNow()}
                    </Text>
                  </div>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    Wallet: {activity.wallet_address.slice(0, 8)}...{activity.wallet_address.slice(-6)}
                  </Text>
                </div>
              }
            />
          </List.Item>
        );
      }}
    />
  );
};

export default WhaleActivity;


