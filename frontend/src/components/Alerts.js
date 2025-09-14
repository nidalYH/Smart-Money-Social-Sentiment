import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Typography, Space, Button, Progress, Row, Col, Statistic, Alert } from 'antd';
import { BellOutlined, ReloadOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { alertsApi } from '../services/api';
import dayjs from 'dayjs';

const { Title } = Typography;

const Alerts = () => {
  const [loading, setLoading] = useState(false);
  const [alertStats, setAlertStats] = useState(null);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    loadAlertStats();
  }, []);

  const loadAlertStats = async () => {
    try {
      setLoading(true);
      const response = await alertsApi.getStatistics(24);
      setAlertStats(response.data);
    } catch (error) {
      console.error('Error loading alert stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const retryFailedAlerts = async () => {
    try {
      setRetrying(true);
      await alertsApi.retryFailed(3);
      await loadAlertStats(); // Refresh stats
    } catch (error) {
      console.error('Error retrying alerts:', error);
    } finally {
      setRetrying(false);
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical':
        return 'red';
      case 'high':
        return 'orange';
      case 'medium':
        return 'blue';
      case 'low':
        return 'green';
      default:
        return 'default';
    }
  };

  const getPriorityIcon = (priority) => {
    switch (priority) {
      case 'critical':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'high':
        return <BellOutlined style={{ color: '#fa8c16' }} />;
      default:
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    }
  };

  const getDeliveryRateColor = (rate) => {
    if (rate >= 95) return '#52c41a';
    if (rate >= 80) return '#faad14';
    return '#ff4d4f';
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Button loading>Loading alert statistics...</Button>
      </div>
    );
  }

  if (!alertStats) {
    return (
      <Alert
        message="Error"
        description="Failed to load alert statistics"
        type="error"
        showIcon
        action={
          <Button onClick={loadAlertStats}>Retry</Button>
        }
      />
    );
  }

  return (
    <div>
      <Title level={2}>Alert Management</Title>
      
      {/* Alert Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Alerts (24h)"
              value={alertStats.total_alerts || 0}
              valueStyle={{ color: '#1890ff' }}
              prefix={<BellOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Successful Deliveries"
              value={alertStats.successful_deliveries || 0}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Failed Deliveries"
              value={alertStats.failed_deliveries || 0}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Delivery Rate"
              value={alertStats.delivery_rate_percent || 0}
              suffix="%"
              valueStyle={{ 
                color: getDeliveryRateColor(alertStats.delivery_rate_percent) 
              }}
            />
            <Progress
              percent={alertStats.delivery_rate_percent || 0}
              strokeColor={getDeliveryRateColor(alertStats.delivery_rate_percent)}
              showInfo={false}
              size="small"
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Alert Actions */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadAlertStats}
              loading={loading}
            >
              Refresh Statistics
            </Button>
          </Col>
          <Col>
            <Button
              type="primary"
              danger={alertStats.failed_deliveries > 0}
              icon={<CheckCircleOutlined />}
              onClick={retryFailedAlerts}
              loading={retrying}
              disabled={!alertStats.failed_deliveries || alertStats.failed_deliveries === 0}
            >
              Retry Failed Alerts ({alertStats.failed_deliveries || 0})
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Alert Breakdown */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Alerts by Type">
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {alertStats.alerts_by_type && Object.entries(alertStats.alerts_by_type).map(([type, count]) => (
                <div key={type} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  padding: '8px 0',
                  borderBottom: '1px solid #f0f0f0'
                }}>
                  <Space>
                    <Tag color="blue">{type.replace('_', ' ').toUpperCase()}</Tag>
                  </Space>
                  <span style={{ fontWeight: 'bold' }}>{count}</span>
                </div>
              ))}
            </div>
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Alerts by Priority">
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {alertStats.alerts_by_priority && Object.entries(alertStats.alerts_by_priority).map(([priority, count]) => (
                <div key={priority} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  padding: '8px 0',
                  borderBottom: '1px solid #f0f0f0'
                }}>
                  <Space>
                    {getPriorityIcon(priority)}
                    <Tag color={getPriorityColor(priority)}>
                      {priority.toUpperCase()}
                    </Tag>
                  </Space>
                  <span style={{ fontWeight: 'bold' }}>{count}</span>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>

      {/* System Health Alert */}
      {alertStats.delivery_rate_percent < 80 && (
        <Alert
          message="Alert Delivery Issue"
          description={`Delivery rate is below 80% (${alertStats.delivery_rate_percent}%). ${alertStats.failed_deliveries || 0} alerts failed to deliver.`}
          type="warning"
          showIcon
          style={{ marginTop: 24 }}
          action={
            <Button 
              size="small" 
              onClick={retryFailedAlerts}
              loading={retrying}
            >
              Retry Failed
            </Button>
          }
        />
      )}
    </div>
  );
};

export default Alerts;


