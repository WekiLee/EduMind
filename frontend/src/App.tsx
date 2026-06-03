import { useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from './stores/useAuthStore';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import LearnPage from './pages/LearnPage';
import SyllabusPage from './pages/SyllabusPage';
import SettingsPage from './pages/SettingsPage';
import AdminUsersPage from './pages/admin/UsersPage';
import AdminConfigPage from './pages/admin/ConfigPage';
import ReportPage from './pages/ReportPage';
import Layout from './components/common/Layout';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const loadUser = useAuthStore((s) => s.loadUser);
  const location = useLocation();

  // 页面刷新后从 Token 恢复用户信息
  useEffect(() => {
    if (token && !user) {
      loadUser();
    }
  }, [token, user]);

  if (!token) return <Navigate to="/login" replace />;
  // 等待用户信息加载
  if (!user) return <div className="flex items-center justify-center h-screen text-gray-400">加载中...</div>;
  // 首次登录必须改密码（已在设置页时不要死循环）
  if (user.must_change_password && !location.pathname.startsWith('/settings')) {
    return <Navigate to="/settings?force_password=1" replace />;
  }
  return <>{children}</>;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { token, user } = useAuthStore();
  if (!token) return <Navigate to="/login" replace />;
  if (user?.role !== 'admin') return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

function HomeRedirect() {
  const user = useAuthStore((s) => s.user);
  if (user?.role === 'admin') return <Navigate to="/admin/users" replace />;
  return <Navigate to="/dashboard" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<HomeRedirect />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="learn/:pathId" element={<LearnPage />} />
        <Route path="learn/:pathId/syllabus" element={<SyllabusPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="report/:pathId" element={<ReportPage />} />

        {/* 管理员路由 */}
        <Route path="admin/users" element={<AdminRoute><AdminUsersPage /></AdminRoute>} />
        <Route path="admin/config" element={<AdminRoute><AdminConfigPage /></AdminRoute>} />
      </Route>
    </Routes>
  );
}
