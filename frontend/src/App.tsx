import { lazy, Suspense, useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from './stores/useAuthStore';
import Layout from './components/common/Layout';
import { ToastContainer, LoadingSpinner } from './components/common';
import { ThemeProvider } from './hooks/useTheme';

const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const LearnPage = lazy(() => import('./pages/LearnPage'));
const SyllabusPage = lazy(() => import('./pages/SyllabusPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const ReportPage = lazy(() => import('./pages/ReportPage'));
const AdminUsersPage = lazy(() => import('./pages/admin/UsersPage'));
const AdminConfigPage = lazy(() => import('./pages/admin/ConfigPage'));
const AdminKnowledgeGraphPage = lazy(() => import('./pages/admin/KnowledgeGraphPage'));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const loadUser = useAuthStore((s) => s.loadUser);
  const location = useLocation();

  useEffect(() => {
    if (token && !user) { loadUser(); }
  }, [token, user]);

  if (!token) return <Navigate to="/login" replace />;
  if (!user) return <LoadingSpinner text="验证身份..." />;
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
    <ThemeProvider>
      <ToastContainer />
      <Suspense fallback={<LoadingSpinner text="加载页面..." />}>
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
          <Route path="admin/knowledge-graph" element={<AdminRoute><AdminKnowledgeGraphPage /></AdminRoute>} />
        </Route>
      </Routes>
      </Suspense>
    </ThemeProvider>
  );
}
