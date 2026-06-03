import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useLearningStore } from '../stores/useLearningStore';
import { useAuthStore } from '../stores/useAuthStore';
import { BookOpen, Plus, FileText, ChevronRight, Shield } from 'lucide-react';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { paths, setPaths } = useLearningStore();
  const { user, isAdmin } = useAuthStore();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [topic, setTopic] = useState('');
  const [domainId, setDomainId] = useState('general');
  const [creating, setCreating] = useState(false);
  const [createMode, setCreateMode] = useState<'topic' | 'upload'>('topic');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadPaths();
  }, []);

  const loadPaths = async () => {
    try {
      const { data } = await api.get('/learning-paths');
      setPaths(data.data);
    } catch (err) {
      console.error('加载学习路径失败', err);
    }
  };

  const handleCreate = async () => {
    if (createMode === 'topic') {
      if (!topic.trim()) return;
      setCreating(true);
      try {
        const { data } = await api.post('/learning-paths', { mode: 'topic', topic, domain_id: domainId });
        setShowCreateModal(false);
        setTopic('');
        navigate(`/learn/${data.data.id}`);
      } catch (err) {
        console.error('创建失败', err);
      } finally {
        setCreating(false);
      }
    } else {
      if (!uploadFile) return;
      setUploading(true);
      try {
        const formData = new FormData();
        formData.append('file', uploadFile);
        formData.append('domain_id', domainId);
        const { data } = await api.post('/learning-paths/upload', formData);
        setShowCreateModal(false);
        setUploadFile(null);
        navigate(`/learn/${data.data.id}`);
      } catch (err) {
        console.error('上传失败', err);
      } finally {
        setUploading(false);
      }
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-50';
      case 'processing': return 'text-yellow-600 bg-yellow-50';
      case 'completed': return 'text-blue-600 bg-blue-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const resetCreateForm = () => {
    setTopic('');
    setUploadFile(null);
    setCreateMode('topic');
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* 管理员首页提示 */}
      {isAdmin() ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Shield size={24} className="text-yellow-600" />
            <h2 className="text-lg font-bold text-yellow-800">管理员控制台</h2>
          </div>
          <p className="text-yellow-700 text-sm mb-4">
            当前账号为管理员，仅用于管理用户和系统配置，无法创建学习路径。
            如需学习，请使用普通用户账号登录。
          </p>
          <div className="flex gap-3">
            <button onClick={() => navigate('/admin/users')}
              className="bg-yellow-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-yellow-700">
              用户管理
            </button>
            <button onClick={() => navigate('/admin/config')}
              className="bg-white text-yellow-700 border border-yellow-300 px-4 py-2 rounded-lg text-sm hover:bg-yellow-50">
              系统配置
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* 头部 */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl font-bold">我的学习</h1>
              <p className="text-gray-400 text-sm mt-1">管理和追踪你的学习路径</p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
            >
              <Plus size={18} />
              新建学习
            </button>
          </div>
        </>
      )}

      {/* 学习路径列表 */}
      {paths.length === 0 ? (
        <div className="text-center py-20">
          <BookOpen size={48} className="mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-500">还没有学习路径</h3>
          <p className="text-gray-400 text-sm mt-1">点击上方按钮创建你的第一个学习路径</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {paths.map((path) => (
            <div
              key={path.id}
              onClick={() => navigate(`/learn/${path.id}`)}
              className="bg-white rounded-xl p-5 border border-gray-100 hover:shadow-md cursor-pointer transition-shadow flex items-center justify-between"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-medium">{path.topic}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(path.status)}`}>
                    {path.status === 'active' ? '学习中' : path.status === 'completed' ? '已完成' : '处理中'}
                  </span>
                  {path.domain_id && (
                    <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                      {path.domain_id}
                    </span>
                  )}
                </div>
                {/* 进度条 */}
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div
                      className="bg-indigo-500 h-2 rounded-full transition-all"
                      style={{ width: `${(path.progress || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-400">
                    {path.completed_count || 0}/{path.node_count || 0}
                  </span>
                </div>
              </div>
              <ChevronRight size={20} className="text-gray-300 ml-4" />
            </div>
          ))}
        </div>
      )}

      {/* 创建弹窗 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => { resetCreateForm(); setShowCreateModal(false); }}>
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold mb-4">创建学习路径</h2>

            {/* Tab 切换 */}
            <div className="flex border-b border-gray-200 mb-4">
              <button onClick={() => { setCreateMode('topic'); setUploadFile(null); }}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  createMode === 'topic' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-400 hover:text-gray-600'
                }`}>✏️ 输入主题</button>
              <button onClick={() => { setCreateMode('upload'); setTopic(''); }}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  createMode === 'upload' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-400 hover:text-gray-600'
                }`}>📄 上传文件</button>
            </div>

            <div className="space-y-4">
              {createMode === 'topic' ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">学习主题</label>
                  <input type="text" value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="例如：Python 入门、微积分基础..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">选择文件</label>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-indigo-400 cursor-pointer"
                    onClick={() => document.getElementById('file-input')?.click()}>
                    {uploadFile ? (
                      <p className="text-sm text-indigo-600">{uploadFile.name} ({(uploadFile.size / 1024).toFixed(1)} KB)</p>
                    ) : (
                      <>
                        <FileText size={32} className="mx-auto text-gray-300 mb-2" />
                        <p className="text-sm text-gray-500">点击或拖拽上传文件</p>
                        <p className="text-xs text-gray-400 mt-1">支持 PDF、MD、TXT</p>
                      </>
                    )}
                  </div>
                  <input id="file-input" type="file" accept=".pdf,.md,.txt"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    className="hidden" />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">领域</label>
                <select value={domainId} onChange={(e) => setDomainId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                  <option value="general">通用</option>
                  <option value="math">数学</option>
                  <option value="programming">编程</option>
                  <option value="language">语言</option>
                  <option value="history">历史</option>
                  <option value="physics">物理</option>
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button onClick={() => { resetCreateForm(); setShowCreateModal(false); }}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">取消</button>
                <button onClick={handleCreate}
                  disabled={creating || uploading || (createMode === 'topic' && !topic.trim()) || (createMode === 'upload' && !uploadFile)}
                  className="flex-1 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50">
                  {creating || uploading ? '创建中...' : '创建'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
