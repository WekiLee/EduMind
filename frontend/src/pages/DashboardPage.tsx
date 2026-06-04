import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useLearningStore } from '../stores/useLearningStore';
import { useAuthStore } from '../stores/useAuthStore';
import { BookOpen, Plus, FileText, ChevronRight, Shield, Search } from 'lucide-react';
import { LoadingSpinner, EmptyState, ErrorBanner } from '../components/common';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { paths, setPaths } = useLearningStore();
  const { user, isAdmin } = useAuthStore();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [topic, setTopic] = useState('');
  const [domainId, setDomainId] = useState('general');
  const [creating, setCreating] = useState(false);
  const [createMode, setCreateMode] = useState<'topic' | 'search' | 'upload'>('topic');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [reviewDue, setReviewDue] = useState<{ node_id: string; path_id: string; path_topic: string; mastery: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadPaths();
  }, []);

  const loadPaths = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await api.get('/learning-paths');
      setPaths(data.data);

      // 并行加载待复习节点（取代串行）
      const duePromises = data.data.map(async (p: any) => {
        try {
          const prog = await api.get(`/learning-paths/${p.id}/progress`);
          const reviewItems = prog.data.data.review_due || [];
          return reviewItems.map((item: any) => ({
            node_id: item.node_id, path_id: p.id, path_topic: p.topic, mastery: item.mastery || 0,
          }));
        } catch {
          return [];
        }
      });
      const dueArrays = await Promise.all(duePromises);
      setReviewDue(dueArrays.flat().slice(0, 10));
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载学习路径失败');
      console.error('加载学习路径失败', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (createMode === 'topic' || createMode === 'search') {
      if (!topic.trim()) return;
      setCreating(true);
      try {
        const endpoint = createMode === 'search' ? '/learning-paths/with-search' : '/learning-paths';
        const { data } = await api.post(endpoint, { mode: createMode, topic, domain_id: domainId });
        setShowCreateModal(false);
        setTopic('');
        navigate(`/learn/${data.data.id}`);
      } catch (err: any) {
        setError(err.response?.data?.detail || '创建失败');
      } finally {
        setCreating(false);
      }
    } else {
      if (!uploadFile) return;
      setUploading(true);
      setUploadProgress(0);
      try {
        const formData = new FormData();
        formData.append('file', uploadFile);
        formData.append('domain_id', domainId);
        const { data } = await api.post('/learning-paths/upload', formData, {
          onUploadProgress: (e) => {
            if (e.total) setUploadProgress(Math.round((e.loaded / e.total) * 100));
          },
        });
        setShowCreateModal(false);
        setUploadFile(null);
        navigate(`/learn/${data.data.id}`);
      } catch (err: any) {
        setError(err.response?.data?.detail || '上传失败');
      } finally {
        setUploading(false);
        setUploadProgress(0);
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
          </p>
          <div className="flex gap-3">
            <button onClick={() => navigate('/admin/users')}
              className="bg-yellow-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-yellow-700">用户管理</button>
            <button onClick={() => navigate('/admin/config')}
              className="bg-white text-yellow-700 border border-yellow-300 px-4 py-2 rounded-lg text-sm hover:bg-yellow-50">系统配置</button>
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl font-bold">我的学习</h1>
              <p className="text-gray-400 text-sm mt-1">管理和追踪你的学习路径</p>
            </div>
            <button onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
              <Plus size={18} /> 新建学习
            </button>
          </div>
        </>
      )}

      {/* 错误提示 */}
      {error && <ErrorBanner message={error} onRetry={loadPaths} />}

      {/* 待复习提醒 */}
      {reviewDue.length > 0 && !loading && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-orange-500 text-lg">📚</span>
            <h3 className="text-sm font-medium text-orange-800">待复习 {reviewDue.length} 个知识点</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {reviewDue.map((item, i) => (
              <button key={i} onClick={() => navigate(`/learn/${item.path_id}?review=${item.node_id}`)}
                className="bg-white text-xs text-orange-700 px-3 py-1.5 rounded-full border border-orange-200 hover:bg-orange-100">
                {item.path_topic.substring(0, 12)} · {(item.mastery * 100).toFixed(0)}%
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 加载态 */}
      {loading ? (
        <LoadingSpinner text="加载学习路径..." />
      ) : paths.length === 0 ? (
        <EmptyState icon="📖" title="还没有学习路径" description="点击上方按钮创建你的第一个学习路径" />
      ) : (
        <div className="grid gap-4">
          {paths.map((path) => (
            <div key={path.id} onClick={() => navigate(`/learn/${path.id}`)}
              className="bg-white rounded-xl p-5 border border-gray-100 hover:shadow-md cursor-pointer transition-shadow flex items-center justify-between group">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-medium">{path.topic}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(path.status)}`}>
                    {path.status === 'active' ? '学习中' : path.status === 'completed' ? '已完成' : '处理中'}
                  </span>
                  {path.domain_id && (
                    <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{path.domain_id}</span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div className="bg-indigo-500 h-2 rounded-full transition-all" style={{ width: `${(path.progress || 0) * 100}%` }} />
                  </div>
                  <span className="text-xs text-gray-400">{path.completed_count || 0}/{path.node_count || 0}</span>
                </div>
              </div>
              <ChevronRight size={20} className="text-gray-300 ml-4 group-hover:text-gray-500 transition-colors" />
            </div>
          ))}
        </div>
      )}

      {/* 创建弹窗 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => { resetCreateForm(); setShowCreateModal(false); }}>
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold mb-4">创建学习路径</h2>

            <div className="flex border-b border-gray-200 mb-4">
              <button onClick={() => { setCreateMode('topic'); setUploadFile(null); }}
                disabled={creating || uploading}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${createMode === 'topic' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-400 hover:text-gray-600'} disabled:opacity-30`}>
                ✏️ 输入主题</button>
              <button onClick={() => { setCreateMode('search'); setUploadFile(null); }}
                disabled={creating || uploading}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${createMode === 'search' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-400 hover:text-gray-600'} disabled:opacity-30`}>
                🔍 搜索增强</button>
              <button onClick={() => { setCreateMode('upload'); setTopic(''); }}
                disabled={creating || uploading}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${createMode === 'upload' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-400 hover:text-gray-600'} disabled:opacity-30`}>
                📄 上传文件</button>
            </div>

            <div className="space-y-4">
              {createMode !== 'upload' ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">学习主题</label>
                  <input type="text" value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder={createMode === 'search' ? '搜索增强将自动查找网络资料补充内容...' : '例如：Python 入门、微积分基础...'}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                  {createMode === 'search' && (
                    <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                      <Search size={12} /> 将通过 DuckDuckGo 搜索相关主题并交叉验证
                    </p>
                  )}
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">选择文件</label>
                  <div onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={(e) => { e.preventDefault(); setDragOver(false); setUploadFile(e.dataTransfer.files[0] || null); }}
                    className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${dragOver ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 hover:border-indigo-400'} cursor-pointer`}
                    onClick={() => document.getElementById('file-input')?.click()}>
                    {uploadFile ? (
                      <p className="text-sm text-indigo-600">{uploadFile.name} ({(uploadFile.size / 1024).toFixed(1)} KB)</p>
                    ) : (
                      <>
                        <FileText size={32} className="mx-auto text-gray-300 mb-2" />
                        <p className="text-sm text-gray-500">点击或拖拽上传文件</p>
                        <p className="text-xs text-gray-400 mt-1">支持 PDF、DOCX、MD、TXT</p>
                      </>
                    )}
                    {uploading && uploadProgress > 0 && (
                      <div className="mt-2">
                        <div className="bg-gray-200 rounded-full h-2">
                          <div className="bg-indigo-500 h-2 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
                        </div>
                        <p className="text-xs text-gray-400 mt-1">上传中 {uploadProgress}%</p>
                      </div>
                    )}
                  </div>
                  <input id="file-input" type="file" accept=".pdf,.docx,.md,.txt"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)} className="hidden" />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">领域</label>
                <select value={domainId} onChange={(e) => setDomainId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                  <option value="auto">🤖 自动检测</option>
                  <option value="general">通用</option>
                  <option value="math">数学</option>
                  <option value="programming">编程</option>
                  <option value="language">语言</option>
                  <option value="history">历史</option>
                  <option value="physics">物理</option>
                  <option value="music">音乐</option>
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button onClick={() => { resetCreateForm(); setShowCreateModal(false); }}
                  disabled={creating || uploading}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-30">取消</button>
                <button onClick={handleCreate}
                  disabled={creating || uploading || (createMode !== 'upload' && !topic.trim()) || (createMode === 'upload' && !uploadFile)}
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
