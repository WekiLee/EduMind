import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/useAuthStore';
import { BookOpen, LayoutDashboard, Settings, LogOut, Shield, Users, Sliders } from 'lucide-react';

export default function Layout() {
  const navigate = useNavigate();
  const { user, logout, isAdmin } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen">
      <aside className="w-60 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-100">
          <h1 className="text-xl font-bold text-indigo-600">EduMind</h1>
          <p className="text-xs text-gray-400 mt-1">
            {user?.name || '用户'}
            {user?.role === 'admin' && <span className="ml-1 text-yellow-600">(管理员)</span>}
          </p>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-auto">
          {isAdmin() ? (
            <>
              <p className="text-xs text-gray-400 uppercase mb-2 px-2">管理后台</p>
              <NavLink
                to="/admin/users"
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${isActive ? 'bg-indigo-50 text-indigo-600' : 'text-gray-600 hover:bg-gray-50'}`
                }
              >
                <Users size={18} />
                用户管理
              </NavLink>
              <NavLink
                to="/admin/config"
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${isActive ? 'bg-indigo-50 text-indigo-600' : 'text-gray-600 hover:bg-gray-50'}`
                }
              >
                <Sliders size={18} />
                系统配置
              </NavLink>
            </>
          ) : (
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${isActive ? 'bg-indigo-50 text-indigo-600' : 'text-gray-600 hover:bg-gray-50'}`
              }
            >
              <LayoutDashboard size={18} />
              我的学习
            </NavLink>
          )}

          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${isActive ? 'bg-indigo-50 text-indigo-600' : 'text-gray-600 hover:bg-gray-50'}`
            }
          >
            <Settings size={18} />
            个人设置
          </NavLink>
        </nav>

        <div className="p-3 border-t border-gray-100">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50 w-full"
          >
            <LogOut size={18} />
            退出
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
