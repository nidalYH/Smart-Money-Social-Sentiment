import React, { useState, useEffect } from 'react';
import { Card, Typography, Row, Col, Statistic, Progress, Tag, Space, Button, Alert, Table } from 'antd';
import { 
  CheckCircleOutlined, 
  CloseCircleOutlined, 
  ReloadOutlined,
  DatabaseOutlined,
  CloudOutlined,
  ApiOutlined,
  BellOutlined
} from '@ant-design/icons';
import { systemApi } from '../services/api';

const { Title, Text } = Typography;

const SystemStatus = () => {
  const [loading, setLoading] = useState(false);
  const [systemStatus, setSystemStatus] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);

  useEffect(() => {
    loadSystemStatus();
    const interval = setInterval(loadSystemStatus, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadSystemStatus = async () => {
    try {
      setLoading(true);
      const [statusResponse, healthResponse] = await Promise.all([
        systemApi.status().then(res => res.data).catch(() => null),
        systemApi.health().then(res => res.data).catch(() => null)
      ]);
      
      setSystemStatus(statusResponse);
      setHealthStatus(healthResponse);
    } catch (error) {
      console.error('Error loading system status:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'operational':
      case 'healthy':
      case true:
        return 'green';
      case 'unhealthy':
      case false:
        return 'red';
      default:
        return 'orange';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'operational':
      case 'healthy':
      case true:
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'unhealthy':
      case false:
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <CloseCircleOutlined style={{ color: '#faad14' }} />;
    }
  };

  const getComponentStatus = (component) => {
    if (!systemStatus?.components) return 'unknown';
    return systemStatus.components[component] || 'unknown';
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading && !systemStatus) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Button loading>Loading system status...</Button>
      </div>
    );
  }

  const componentColumns = [
    {
      title: 'Component',
      dataIndex: 'name',
      key: 'name',
      render: (name) => (
        <Space>
          {name === 'whale_tracker' && <DatabaseOutlined />}
          {name === 'sentiment_analyzer' && <BellOutlined />}
          {name === 'signal_engine' && <ApiOutlined />}
          {name === 'alert_manager' && <BellOutlined />}
          <span style={{ textTransform: 'capitalize' }}>
            {name.replace('_', ' ')}
          </span>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag 
          color={getStatusColor(status)} 
          icon={getStatusIcon(status)}
        >
          {status.toUpperCase()}
        </Tag>
      ),
    },
  ];

  const componentData = [
    { name: 'whale_tracker', status: getComponentStatus('whale_tracker') },
    { name: 'sentiment_analyzer', status: getComponentStatus('sentiment_analyzer') },
    { name: 'signal_engine', status: getComponentStatus('signal_engine') },
    { name: 'alert_manager', status: getComponentStatus('alert_manager') },
  ];

  return (
    <div>
      <Title level={2}>System Status</Title>
      
      {/* System Health Overview */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="System Status"
              value={systemStatus?.system || 'Unknown'}
              prefix={getStatusIcon(systemStatus?.system)}
              valueStyle={{ 
                color: getStatusColor(systemStatus?.system) === 'green' ? '#52c41a' : '#ff4d4f' 
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Database"
              value={healthStatus?.database ? 'Connected' : 'Disconnected'}
              prefix={getStatusIcon(healthStatus?.database)}
              valueStyle={{ 
                color: getStatusColor(healthStatus?.database) === 'green' ? '#52c41a' : '#ff4d4f' 
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Redis Cache"
              value={healthStatus?.redis ? 'Connected' : 'Disconnected'}
              prefix={getStatusIcon(healthStatus?.redis)}
              valueStyle={{ 
                color: getStatusColor(healthStatus?.redis) === 'green' ? '#52c41a' : '#ff4d4f' 
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Overall Health"
              value={healthStatus?.overall ? 'Healthy' : 'Unhealthy'}
              prefix={getStatusIcon(healthStatus?.overall)}
              valueStyle={{ 
                color: getStatusColor(healthStatus?.overall) === 'green' ? '#52c41a' : '#ff4d4f' 
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Performance Metrics */}
      {systemStatus?.performance && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Memory Usage"
                value={systemStatus.performance.redis_memory_usage || 'N/A'}
                prefix={<CloudOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Connected Clients"
                value={systemStatus.performance.redis_connected_clients || 0}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Commands Processed"
                value={systemStatus.performance.redis_total_commands_processed || 0}
                prefix={<ApiOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Cache Hit Rate"
                value={systemStatus.performance.cache_hit_rate || 0}
                suffix="%"
                valueStyle={{ 
                  color: systemStatus.performance.cache_hit_rate > 80 ? '#52c41a' : '#faad14' 
                }}
              />
              <Progress
                percent={systemStatus.performance.cache_hit_rate || 0}
                strokeColor={systemStatus.performance.cache_hit_rate > 80 ? '#52c41a' : '#faad14'}
                showInfo={false}
                size="small"
                style={{ marginTop: 8 }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Component Status */}
      <Card 
        title="Component Status" 
        extra={
          <Button 
            icon={<ReloadOutlined />} 
            onClick={loadSystemStatus}
            loading={loading}
          >
            Refresh
          </Button>
        }
        style={{ marginBottom: 24 }}
      >
        <Table
          columns={componentColumns}
          dataSource={componentData}
          rowKey="name"
          pagination={false}
          size="small"
        />
      </Card>

      {/* Alert Statistics */}
      {systemStatus?.alerts && (
        <Card title="Alert Performance (24h)" style={{ marginBottom: 24 }}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} lg={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff' }}>
                  {systemStatus.alerts.total_alerts || 0}
                </div>
                <div style={{ color: '#666' }}>Total Alerts</div>
              </div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                  {systemStatus.alerts.successful_deliveries || 0}
                </div>
                <div style={{ color: '#666' }}>Successful</div>
              </div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ff4d4f' }}>
                  {systemStatus.alerts.failed_deliveries || 0}
                </div>
                <div style={{ color: '#666' }}>Failed</div>
              </div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ 
                  fontSize: '24px', 
                  fontWeight: 'bold', 
                  color: getDeliveryRateColor(systemStatus.alerts.delivery_rate_percent) 
                }}>
                  {systemStatus.alerts.delivery_rate_percent || 0}%
                </div>
                <div style={{ color: '#666' }}>Delivery Rate</div>
                <Progress
                  percent={systemStatus.alerts.delivery_rate_percent || 0}
                  strokeColor={getDeliveryRateColor(systemStatus.alerts.delivery_rate_percent)}
                  showInfo={false}
                  size="small"
                  style={{ marginTop: 8 }}
                />
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {/* System Health Alerts */}
      {(!healthStatus?.overall || systemStatus?.alerts?.delivery_rate_percent < 80) && (
        <Alert
          message="System Health Alert"
          description={
            !healthStatus?.overall 
              ? "System health is degraded. Check component status above."
              : "Alert delivery rate is below 80%. Check alert configuration."
          }
          type="warning"
          showIcon
          action={
            <Button size="small" onClick={loadSystemStatus}>
              Refresh Status
            </Button>
          }
        />
      )}

      {/* Last Updated */}
      <div style={{ textAlign: 'center', marginTop: 24, color: '#666' }}>
        <Text type="secondary">
          Last updated: {systemStatus?.timestamp ? 
            new Date(systemStatus.timestamp).toLocaleString() : 
            'Never'
          }
        </Text>
      </div>
    </div>
  );
};

const getDeliveryRateColor = (rate) => {
  if (rate >= 95) return '#52c41a';
  if (rate >= 80) return '#faad14';
  return '#ff4d4f';
};

export default SystemStatus;


