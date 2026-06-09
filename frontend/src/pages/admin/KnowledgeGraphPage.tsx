import { useEffect, useState } from 'react';
import { api } from '../../services/api';
import { Search, Edit3, Trash2, Save, X, ChevronRight, AlertTriangle } from 'lucide-react';

interface LearningPath {
  id: string;
  topic: string;
  domain_id: string;
  status: string;
  source: string;
  created_at: string;
}

interface NodeItem {
  node: {
    id: string;
    title: string;
    summary: string;
    content: string;
    difficulty: string;
    node_type: string;
    confidence: number;
    source: string;
  };
  module: { name: string; order: number };
  prerequisites: string[];
}

export default function AdminKnowledgeGraphPage() {
  const [paths, setPaths] = useState<LearningPath[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);
  const [nodes, setNodes] = useState<NodeItem[]>([]);
  const [nodesLoading, setNodesLoading] = useState(false);
  const [editingNode, setEditingNode] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    api.get('/admin/learning-paths', { params: { page: 1, size: 100 } }).then(({ data }) => {
      setPaths(data.data);
      setTotal(data.total);
    }).catch(console.error);
  }, []);

  const loadNodes = async (pathId: string) => {
    setSelectedPathId(pathId);
    setNodesLoading(true);
    setEditingNode(null);
    try {
      const { data } = await api.get(`/admin/learning-paths/${pathId}/nodes`);
      setNodes(data.data);
    } catch (err) {
      console.error(err);
    } finally {
      setNodesLoading(false);
    }
  };

  const startEdit = (item: NodeItem) => {
    setEditingNode(item.node.id);
    setEditForm({
      title: item.node.title || '',
      summary: item.node.summary || '',
      content: item.node.content || '',
      difficulty: item.node.difficulty || 'intro',
      node_type: item.node.node_type || 'concept',
    });
  };

  const saveEdit = async () => {
    if (!editingNode) return;
    setSaving(true);
    try {
      await api.put(`/admin/nodes/${editingNode}`, editForm);
      setEditingNode(null);
      if (selectedPathId) loadNodes(selectedPathId);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const deleteNode = async (nodeId: string) => {
    if (!window.confirm('确定删除此节点？此操作不可恢复。')) return;
    setDeleting(nodeId);
    try {
      await api.delete(`/admin/nodes/${nodeId}`);
      if (selectedPathId) loadNodes(selectedPathId);
    } catch (err) {
      console.error(err);
    } finally {
      setDeleting(null);
    }
  };

  const filteredPaths = paths.filter((p) =>
    !search || p.topic.toLowerCase().includes(search.toLowerCase())
  );

  const selectedPath = paths.find((p) => p.id === selectedPathId);
  const moduleOrder = ['intro', 'intermediate', 'advanced'];
  const difficultyLabel = (d: string) => ({ intro: '入门', intermediate: '中级', advanced: '高级' }[d] || d);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">知识图谱管理</h1>
        <p className="text-gray-400 text-sm mt-1">浏览、编辑和删除知识点节点</p>
      </div>

      <div className="flex gap-6">
        {/* 左侧：路径列表 */}
        <div className="w-72 shrink-0">
          <div className="relative mb-3">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索路径..." className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
          <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
            <div className="px-4 py-2 bg-gray-50 border-b border-gray-100 text-xs text-gray-400 font-medium">
              共 {total} 条学习路径
            </div>
            <div className="max-h-[70vh] overflow-auto divide-y divide-gray-50">
              {filteredPaths.map((p) => (
                <button key={p.id} onClick={() => loadNodes(p.id)}
                  className={`w-full text-left px-4 py-3 text-sm hover:bg-gray-50 transition-colors ${
                    selectedPathId === p.id ? 'bg-indigo-50 border-l-2 border-indigo-500' : ''
                  }`}>
                  <div className="font-medium truncate">{p.topic}</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {p.domain_id} · {p.status === 'active' ? '学习中' : p.status}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 右侧：节点列表 */}
        <div className="flex-1">
          {!selectedPathId ? (
            <div className="bg-white rounded-xl border border-gray-100 p-12 text-center text-gray-400">
              <Edit3 size={40} className="mx-auto mb-3 text-gray-300" />
              <p className="text-sm">选择左侧一条学习路径查看节点</p>
            </div>
          ) : nodesLoading ? (
            <div className="bg-white rounded-xl border border-gray-100 p-12 text-center text-gray-400">
              <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm">加载节点中...</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-100">
              <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                <div>
                  <h2 className="font-medium">{selectedPath?.topic}</h2>
                  <p className="text-xs text-gray-400 mt-0.5">{nodes.length} 个知识点</p>
                </div>
              </div>

              {/* 按模块分组显示 */}
              {nodes.length === 0 ? (
                <div className="p-12 text-center text-gray-400 text-sm">
                  该路径暂无节点
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {(() => {
                    const grouped: Record<string, NodeItem[]> = {};
                    nodes.forEach((n) => {
                      const key = n.module.name;
                      if (!grouped[key]) grouped[key] = [];
                      grouped[key].push(n);
                    });
                    return Object.entries(grouped).map(([moduleName, moduleNodes]) => (
                      <div key={moduleName}>
                        <div className="px-5 py-2 bg-gray-50 text-xs font-medium text-gray-500">
                          📦 {moduleName}（{moduleNodes.length} 节点）
                        </div>
                        {moduleNodes.map((item) => {
                          const n = item.node;
                          const isEditing = editingNode === n.id;
                          return (
                            <div key={n.id} className="px-5 py-3 hover:bg-gray-50 transition-colors">
                              {isEditing ? (
                                <div className="space-y-2">
                                  <div className="flex gap-2">
                                    <input type="text" value={editForm.title}
                                      onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                                      className="flex-1 px-2 py-1.5 border border-gray-300 rounded text-sm font-medium"
                                      placeholder="标题" />
                                    <select value={editForm.difficulty}
                                      onChange={(e) => setEditForm({ ...editForm, difficulty: e.target.value })}
                                      className="px-2 py-1.5 border border-gray-300 rounded text-xs">
                                      <option value="intro">入门</option>
                                      <option value="intermediate">中级</option>
                                      <option value="advanced">高级</option>
                                    </select>
                                    <select value={editForm.node_type}
                                      onChange={(e) => setEditForm({ ...editForm, node_type: e.target.value })}
                                      className="px-2 py-1.5 border border-gray-300 rounded text-xs">
                                      <option value="concept">概念</option>
                                      <option value="skill">技能</option>
                                      <option value="fact">事实</option>
                                      <option value="procedure">步骤</option>
                                    </select>
                                  </div>
                                  <textarea value={editForm.summary}
                                    onChange={(e) => setEditForm({ ...editForm, summary: e.target.value })}
                                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-xs"
                                    placeholder="摘要" rows={2} />
                                  <textarea value={editForm.content}
                                    onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-xs font-mono"
                                    placeholder="内容（Markdown）" rows={4} />
                                  <div className="flex gap-2">
                                    <button onClick={saveEdit} disabled={saving}
                                      className="flex items-center gap-1 bg-indigo-600 text-white px-3 py-1.5 rounded text-xs hover:bg-indigo-700 disabled:opacity-50">
                                      <Save size={14} /> 保存
                                    </button>
                                    <button onClick={() => setEditingNode(null)}
                                      className="flex items-center gap-1 border border-gray-300 px-3 py-1.5 rounded text-xs hover:bg-gray-50">
                                      <X size={14} /> 取消
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <div className="flex items-start gap-3">
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span className="font-medium text-sm truncate">{n.title}</span>
                                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                                        n.difficulty === 'intro' ? 'bg-green-50 text-green-600' :
                                        n.difficulty === 'intermediate' ? 'bg-yellow-50 text-yellow-600' :
                                        'bg-red-50 text-red-600'
                                      }`}>{difficultyLabel(n.difficulty)}</span>
                                      <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{n.node_type}</span>
                                      {n.confidence && n.confidence < 0.6 && (
                                        <span className="text-xs text-orange-500 flex items-center gap-0.5"><AlertTriangle size={12} /> 低置信</span>
                                      )}
                                    </div>
                                    {n.summary && (
                                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{n.summary}</p>
                                    )}
                                    {item.prerequisites.length > 0 && (
                                      <p className="text-xs text-gray-400 mt-1">前置: {item.prerequisites.length} 个</p>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-1 shrink-0">
                                    <button onClick={() => startEdit(item)}
                                      className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                                      title="编辑">
                                      <Edit3 size={14} />
                                    </button>
                                    <button onClick={() => deleteNode(n.id)} disabled={deleting === n.id}
                                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                                      title="删除">
                                      <Trash2 size={14} />
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ));
                  })()}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
