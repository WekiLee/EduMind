import { useEffect, useState } from 'react';
import { api } from '../../services/api';
import { useAuthStore } from '../../stores/useAuthStore';
import { Shield, Search, CheckCircle, XCircle, Plus, UserPlus } from 'lucide-react';

interface UserData {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  organization: string | null;
  path_count: number;
  completed_count: number;
  created_at: string;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserData[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', email: '', password: '', role: 'user', organization: '' });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const { user: currentUser } = useAuthStore();

  useEffect(() => { loadUsers(); }, []);

  const loadUsers = async () => {
    try {
      const { data } = await api.get('/admin/users', { params: { page: 1, size: 100 } });
      setUsers(data.data);
      setTotal(data.total);
    } catch (err) {
      console.error('加载用户列表失败', err);
    }
  };

  const startEdit = (u: UserData) => {
    setEditingId(u.id);
    setEditForm({ name: u.name, role: u.role, is_active: u.is_active, organization: u.organization || '' });
  };

  const saveEdit = async (userId: string) => {
    setSaving(true);
    try {
      await api.patch(`/admin/users/${userId}`, editForm);
      setEditingId(null);
      loadUsers();
    } catch (err) {
      console.error('保存失败', err);
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (userId: string, current: boolean) => {
    await api.patch(`/admin/users/${userId}`, { is_active: !current });
    loadUsers();
  };

  const toggleRole = async (userId: string, current: string) => {
    const newRole = current === 'admin' ? 'user' : 'admin';
    await api.patch(`/admin/users/${userId}`, { role: newRole });
    loadUsers();
  };

  const handleCreate = async () => {
    if (!createForm.name || !createForm.email || !createForm.password) {
      setCreateError('请填写所有必填项');
      return;
    }
    setCreating(true);
    setCreateError('');
    try {
      await api.post('/admin/users', createForm);
      setShowCreate(false);
      setCreateForm({ name: '', email: '', password: '', role: 'user', organization: '' });
      loadUsers();
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const filtered = users.filter((u) =>
    u.name.includes(search) || u.email.includes(search)
  );

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">用户管理</h1>
          <p className="text-gray-400 text-sm mt-1">共 {total} 个用户</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-2.5 text-gray-400" />
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索用户..."
              className="pl-8 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-1 bg-indigo-600 text-white px-3 py-2 rounded-lg hover:bg-indigo-700 text-sm">
            <UserPlus size={16} /> 新建用户
          </button>
        </div>
      </div>

      {/* 创建用户弹窗 */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
          onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2"><UserPlus size={20} /> 新建用户</h2>
            <div className="space-y-3">
              <input type="text" value={createForm.name}
                onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                placeholder="姓名 *" className="w-full px-3 py-2 border rounded-lg text-sm" />
              <input type="email" value={createForm.email}
                onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                placeholder="邮箱 *" className="w-full px-3 py-2 border rounded-lg text-sm" />
              <input type="password" value={createForm.password}
                onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                placeholder="密码 *（不少于6位）" className="w-full px-3 py-2 border rounded-lg text-sm" />
              <select value={createForm.role}
                onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm">
                <option value="user">普通用户</option>
                <option value="admin">管理员</option>
              </select>
              <input type="text" value={createForm.organization}
                onChange={(e) => setCreateForm({ ...createForm, organization: e.target.value })}
                placeholder="所属组织（可选）" className="w-full px-3 py-2 border rounded-lg text-sm" />
              {createError && <p className="text-red-500 text-sm">{createError}</p>}
              <div className="flex gap-2 pt-2">
                <button onClick={() => setShowCreate(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">取消</button>
                <button onClick={handleCreate} disabled={creating}
                  className="flex-1 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50">
                  {creating ? '创建中...' : '创建'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              <th className="text-left px-4 py-3 font-medium">姓名</th>
              <th className="text-left px-4 py-3 font-medium">邮箱</th>
              <th className="text-center px-4 py-3 font-medium">角色</th>
              <th className="text-center px-4 py-3 font-medium">状态</th>
              <th className="text-center px-4 py-3 font-medium">组织</th>
              <th className="text-center px-4 py-3 font-medium">路径数</th>
              <th className="text-right px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                {editingId === u.id ? (
                  <>
                    <td className="px-4 py-3">
                      <input
                        value={editForm.name}
                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                        className="border border-gray-300 rounded px-2 py-1 w-full text-sm"
                      />
                    </td>
                    <td className="px-4 py-3 text-gray-400">{u.email}</td>
                    <td className="px-4 py-3 text-center">
                      <select
                        value={editForm.role}
                        onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                        disabled={u.id === currentUser?.id}
                        className={`border rounded px-2 py-1 text-sm ${u.id === currentUser?.id ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'border-gray-300'}`}
                      >
                        <option value="user">用户</option>
                        <option value="admin">管理员</option>
                      </select>
                      {u.id === currentUser?.id && <p className="text-xs text-gray-400 mt-1">不能更改自己的角色</p>}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => setEditForm({ ...editForm, is_active: !editForm.is_active })}
                        className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full ${
                          editForm.is_active ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'
                        }`}
                      >
                        {editForm.is_active ? '启用' : '禁用'}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <input
                        value={editForm.organization}
                        onChange={(e) => setEditForm({ ...editForm, organization: e.target.value })}
                        className="border border-gray-300 rounded px-2 py-1 w-full text-sm"
                        placeholder="所属组织"
                      />
                    </td>
                    <td className="px-4 py-3 text-center text-gray-400">{u.path_count}</td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button onClick={() => saveEdit(u.id)} disabled={saving} className="text-indigo-600 hover:underline text-xs">
                        {saving ? '保存中...' : '保存'}
                      </button>
                      <button onClick={() => setEditingId(null)} className="text-gray-400 hover:underline text-xs">
                        取消
                      </button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-4 py-3 font-medium">
                      {u.name}
                      {u.id === currentUser?.id && <span className="text-xs text-gray-400 ml-1">(你)</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{u.email}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                        u.role === 'admin' ? 'bg-yellow-50 text-yellow-700' : 'bg-gray-50 text-gray-500'
                      }`}>
                        {u.role === 'admin' && <Shield size={12} />}
                        {u.role === 'admin' ? '管理员' : '用户'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {u.is_active
                        ? <CheckCircle size={16} className="text-green-500 inline" />
                        : <XCircle size={16} className="text-red-400 inline" />
                      }
                    </td>
                    <td className="px-4 py-3 text-center text-gray-500">{u.organization || '-'}</td>
                    <td className="px-4 py-3 text-center text-gray-500">{u.path_count}</td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button onClick={() => startEdit(u)} className="text-indigo-600 hover:underline text-xs">编辑</button>
                      {u.id === currentUser?.id && u.role === 'admin' ? (
                        <span className="text-xs text-gray-300">不能降级自己</span>
                      ) : (
                        <button onClick={() => toggleRole(u.id, u.role)} className="text-gray-500 hover:underline text-xs">
                          {u.role === 'admin' ? '降为用户' : '升为管理员'}
                        </button>
                      )}
                      {u.id !== currentUser?.id && (
                        <button onClick={() => toggleActive(u.id, u.is_active)} className={`text-xs hover:underline ${u.is_active ? 'text-red-500' : 'text-green-500'}`}>
                          {u.is_active ? '禁用' : '启用'}
                        </button>
                      )}
                      {u.id === currentUser?.id && (
                        <span className="text-xs text-gray-300 ml-2">不能禁用自己</span>
                      )}
                      {u.id !== currentUser?.id && (
                        <button onClick={() => { if (window.confirm(`确认删除用户 ${u.name}？此操作不可恢复。`)) { api.delete(`/admin/users/${u.id}`).then(loadUsers); } }}
                          className="text-red-400 hover:text-red-600 hover:underline text-xs ml-2">
                          删除
                        </button>
                      )}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
