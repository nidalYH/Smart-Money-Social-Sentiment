import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Typography, Space, Button, Input, Select, DatePicker, Row, Col } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { whaleApi } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const WhaleTracker = () => {
  const [loading, setLoading] = useState(false);
  const [whaleData, setWhaleData] = useState([]);
  const [searchToken, setSearchToken] = useState('');
  const [hoursBack, setHoursBack] = useState(24);

  useEffect(() => {
    loadWhaleActivity();
  }, [hoursBack]);

  const loadWhaleActivity = async () => {
    try {
      setLoading(true);
      const response = await whaleApi.getActivity(hoursBack);
      setWhaleData(response.data.activities || []);
    } catch (error) {
      console.error('Error loading whale activity:', error);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'Time',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp) => new Date(timestamp).toLocaleString(),
      sorter: (a, b) => new Date(a.timestamp) - new Date(b.timestamp),
    },
    {
      title: 'Token',
      dataIndex: 'token_symbol',
      key: 'token_symbol',
      render: (symbol) => <Tag color="blue">{symbol}</Tag>,
    },
    {
      title: 'Type',
      dataIndex: 'transaction_type',
      key: 'transaction_type',
      render: (type) => (
        <Tag color={type === 'buy' ? 'green' : 'red'}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Amount (USD)',
      dataIndex: 'amount_usd',
      key: 'amount_usd',
      render: (amount) => `$${amount.toLocaleString()}`,
      sorter: (a, b) => a.amount_usd - b.amount_usd,
    },
    {
      title: 'Wallet',
      dataIndex: 'wallet_address',
      key: 'wallet_address',
      render: (address) => `${address.slice(0, 8)}...${address.slice(-6)}`,
    },
    {
      title: 'Urgency',
      dataIndex: 'urgency_score',
      key: 'urgency_score',
      render: (score) => (
        <Tag color={score > 0.7 ? 'red' : score > 0.4 ? 'orange' : 'green'}>
          {(score * 100).toFixed(0)}%
        </Tag>
      ),
      sorter: (a, b) => a.urgency_score - b.urgency_score,
    },
    {
      title: 'Impact',
      dataIndex: 'impact_score',
      key: 'impact_score',
      render: (score) => (
        <Tag color={score > 0.7 ? 'red' : score > 0.4 ? 'orange' : 'blue'}>
          {(score * 100).toFixed(0)}%
        </Tag>
      ),
      sorter: (a, b) => a.impact_score - b.impact_score,
    },
  ];

  const filteredData = whaleData.filter(item =>
    item.token_symbol.toLowerCase().includes(searchToken.toLowerCase())
  );

  return (
    <div>
      <Title level={2}>Whale Tracker</Title>
      
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Input
              placeholder="Search by token symbol"
              value={searchToken}
              onChange={(e) => setSearchToken(e.target.value)}
              prefix={<SearchOutlined />}
              style={{ width: 200 }}
            />
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
              onClick={loadWhaleActivity}
              loading={loading}
            >
              Refresh
            </Button>
          </Col>
        </Row>
      </Card>

      <Card>
        <Table
          columns={columns}
          dataSource={filteredData}
          rowKey="timestamp"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} of ${total} transactions`,
          }}
          scroll={{ x: 800 }}
        />
      </Card>
    </div>
  );
};

export default WhaleTracker;


