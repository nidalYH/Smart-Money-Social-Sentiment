import React, { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Layout, Menu, Typography, Badge } from 'antd';
import {
  DashboardOutlined,
  LineChartOutlined,
  HeartOutlined,
  BellOutlined,
  SettingOutlined,
  ApiOutlined,
  BarChartOutlined,
  WalletOutlined
} from '@ant-design/icons';
import styled from 'styled-components';

import Dashboard from './components/Dashboard';
import TradingDashboard from './components/TradingDashboard';
import WhaleTracker from './components/WhaleTracker';
import SentimentAnalysis from './components/SentimentAnalysis';
import TradingSignals from './components/TradingSignals';
import Alerts from './components/Alerts';
import SystemStatus from './components/SystemStatus';
import { useWebSocket } from './hooks/useWebSocket';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const StyledHeader = styled(Header)`
  background: #fff;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const Logo = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
`;

const LogoIcon = styled.div`
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
`;

const StatusBadge = styled(Badge)`
  margin-left: 16px;
`;

const StyledSider = styled(Sider)`
  background: #fff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
`;

const StyledContent = styled(Content)`
  margin: 24px;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 112px);
  overflow-y: auto;
`;

const menuItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: 'Overview',
  },
  {
    key: '/trading',
    icon: <LineChartOutlined />,
    label: '🚀 Live Trading',
  },
  {
    key: '/whales',
    icon: <WalletOutlined />,
    label: 'Whale Tracker',
  },
  {
    key: '/sentiment',
    icon: <HeartOutlined />,
    label: 'Sentiment Analysis',
  },
  {
    key: '/signals',
    icon: <BarChartOutlined />,
    label: 'Signal History',
  },
  {
    key: '/alerts',
    icon: <BellOutlined />,
    label: 'Alerts',
  },
  {
    key: '/api',
    icon: <ApiOutlined />,
    label: 'API Status',
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: 'Settings',
  },
];

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedKey, setSelectedKey] = useState('/');
  const [systemStatus, setSystemStatus] = useState(null);
  const [alertCount, setAlertCount] = useState(0);

  const { isConnected, lastMessage } = useWebSocket();

  useEffect(() => {
    if (lastMessage) {
      if (lastMessage.type === 'system_status') {
        setSystemStatus(lastMessage.data);
      }
    }
  }, [lastMessage]);

  const handleMenuClick = ({ key }) => {
    setSelectedKey(key);
  };

  const getStatusColor = () => {
    if (!isConnected) return 'red';
    if (!systemStatus) return 'yellow';
    if (systemStatus.system === 'operational') return 'green';
    return 'red';
  };

  const getStatusText = () => {
    if (!isConnected) return 'Disconnected';
    if (!systemStatus) return 'Connecting...';
    if (systemStatus.system === 'operational') return 'Online';
    return 'Error';
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <StyledHeader>
        <Logo>
          <LogoIcon>SM</LogoIcon>
          <Title level={4} style={{ margin: 0 }}>
            Smart Money Sentiment
          </Title>
        </Logo>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <StatusBadge
            status={getStatusColor()}
            text={getStatusText()}
          />
          {alertCount > 0 && (
            <Badge count={alertCount} style={{ marginLeft: 16 }}>
              <BellOutlined style={{ fontSize: 18 }} />
            </Badge>
          )}
        </div>
      </StyledHeader>

      <Layout>
        <StyledSider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          width={250}
        >
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            onClick={handleMenuClick}
            style={{ height: '100%', borderRight: 0 }}
            items={menuItems}
          />
        </StyledSider>

        <StyledContent>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/trading" element={<TradingDashboard />} />
            <Route path="/whales" element={<WhaleTracker />} />
            <Route path="/sentiment" element={<SentimentAnalysis />} />
            <Route path="/signals" element={<TradingSignals />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/api" element={<SystemStatus />} />
            <Route path="/settings" element={<div>Settings - Coming Soon</div>} />
          </Routes>
        </StyledContent>
      </Layout>
    </Layout>
  );
}

export default App;


