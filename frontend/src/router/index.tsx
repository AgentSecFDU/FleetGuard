import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp, theme } from 'antd';
import { AuthProvider, useAuth } from '../stores/auth';
import AppLayout from '../components/AppLayout';
import LoginPage from '../pages/Login';
import DashboardPage from '../pages/Dashboard';
import DevicesPage from '../pages/Devices';
import DeviceDetailPage from '../pages/DeviceDetail';
import EventsPage from '../pages/Events';
import PoliciesPage from '../pages/Policies';
import ApprovalsPage from '../pages/Approvals';
import AuditPage from '../pages/Audit';
import { JSX } from 'react';

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

export default function AppRouter() {
  return (
    <ConfigProvider theme={{
      algorithm: theme.defaultAlgorithm,
      token: { colorPrimary: '#1677ff' },
    }}>
      <AntApp>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/devices" element={<DevicesPage />} />
                <Route path="/devices/:deviceId" element={<DeviceDetailPage />} />
                <Route path="/events" element={<EventsPage />} />
                <Route path="/policies" element={<PoliciesPage />} />
                <Route path="/approvals" element={<ApprovalsPage />} />
                <Route path="/audit" element={<AuditPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </AntApp>
    </ConfigProvider>
  );
}
