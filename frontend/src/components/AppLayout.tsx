import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, theme, Typography, Badge, Space } from 'antd';
import {
  DashboardOutlined, DesktopOutlined, ThunderboltOutlined,
  FileProtectOutlined, SafetyCertificateOutlined,
  AuditOutlined, LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons';
import { useAuth } from '../stores/auth';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: 'Dashboard' },
  { key: '/devices', icon: <DesktopOutlined />, label: 'Devices' },
  { key: '/events', icon: <ThunderboltOutlined />, label: 'Events' },
  { key: '/policies', icon: <FileProtectOutlined />, label: 'Policies' },
  { key: '/approvals', icon: <SafetyCertificateOutlined />, label: 'Approvals' },
  { key: '/audit', icon: <AuditOutlined />, label: 'Audit' },
];

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { token: themeToken } = theme.useToken();

  const handleMenuClick = ({ key }: { key: string }) => navigate(key);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="dark"
        style={{ borderRight: `1px solid ${themeToken.colorBorderSecondary}` }}>
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <Text strong style={{ color: '#fff', fontSize: collapsed ? 14 : 18 }}>
            {collapsed ? 'FG' : 'AgentFleetControl'}
          </Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: themeToken.colorBgContainer,
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <Space>
            <Text type="secondary">{user?.username} ({user?.role})</Text>
            <Button type="text" icon={<LogoutOutlined />} onClick={logout} danger>
              Logout
            </Button>
          </Space>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: themeToken.colorBgContainer, borderRadius: 8, overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
