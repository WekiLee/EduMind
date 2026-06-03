import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { ArrowLeft, GripVertical, Save } from 'lucide-react';

interface SyllabusModule {
  module_name: string;
  order: number;
  node_ids: string[];
  nodes?: { id: string; title?: string; status: string; mastery: number }[];
}

export default function SyllabusPage() {
  const { pathId } = useParams();
  const navigate = useNavigate();
  const [path, setPath] = useState<any>(null);
  const [modules, setModules] = useState<SyllabusModule[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!pathId) return;
    api.get(`/learning-paths/${pathId}`).then(({ data }) => {
      setPath(data.data);
      setModules(data.data.syllabus || []);
    });
  }, [pathId]);

  // 模块拖拽
  const moveModule = (fromIdx: number, toIdx: number) => {
    if (toIdx < 0 || toIdx >= modules.length) return;
    const newModules = [...modules];
    const [moved] = newModules.splice(fromIdx, 1);
    newModules.splice(toIdx, 0, moved);
    setModules(newModules.map((m, i) => ({ ...m, order: i + 1 })));
  };

  // 模块内节点拖拽
  const moveNode = (moduleIdx: number, fromIdx: number, toIdx: number) => {
    const newModules = [...modules];
    const nodeIds = [...newModules[moduleIdx].node_ids];
    if (toIdx < 0 || toIdx >= nodeIds.length) return;
    const [moved] = nodeIds.splice(fromIdx, 1);
    nodeIds.splice(toIdx, 0, moved);
    newModules[moduleIdx] = { ...newModules[moduleIdx], node_ids: nodeIds };
    setModules(newModules);
  };

  const handleConfirm = async () => {
    setSaving(true);
    try {
      const syllabus = modules.map((m) => ({
        module_name: m.module_name,
        order: m.order,
        node_ids: m.node_ids,
      }));
      await api.patch(`/learning-paths/${pathId}`, syllabus);
      setSaved(true);
      setTimeout(() => navigate(`/learn/${pathId}`), 800);
    } catch (err) {
      console.error('保存失败', err);
    } finally {
      setSaving(false);
    }
  };

  if (!path) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <button onClick={() => navigate(`/learn/${pathId}`)} className="flex items-center gap-1 text-gray-500 mb-4 hover:text-gray-700">
        <ArrowLeft size={16} /> 返回
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{path.topic}</h1>
          <p className="text-gray-400 text-sm mt-1">拖拽模块和知识点调整学习顺序</p>
        </div>
        <button onClick={handleConfirm} disabled={saving || saved}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 text-sm">
          <Save size={16} />
          {saved ? '已保存 ✓' : saving ? '保存中...' : '确认并开始学习'}
        </button>
      </div>

      <div className="space-y-4">
        {modules.map((module, mi) => (
          <div key={mi} className="bg-white rounded-xl border border-gray-100 p-4">
            {/* 模块头 */}
            <div className="flex items-center gap-2 mb-3">
              <span className="text-gray-300">
                <GripVertical size={16} />
              </span>
              <span className="bg-indigo-100 text-indigo-600 text-xs px-2 py-0.5 rounded-full">模块 {mi + 1}</span>
              <input
                value={module.module_name}
                onChange={(e) => {
                  const newModules = [...modules];
                  newModules[mi] = { ...newModules[mi], module_name: e.target.value };
                  setModules(newModules);
                }}
                className="font-medium bg-transparent border-b border-transparent hover:border-gray-300 focus:border-indigo-500 outline-none text-sm"
              />
              <span className="text-xs text-gray-400 ml-auto">{module.node_ids.length} 个知识点</span>
              {/* 模块上移/下移 */}
              <button onClick={() => moveModule(mi, mi - 1)} disabled={mi === 0}
                className="text-xs text-gray-400 hover:text-gray-600 disabled:opacity-30">↑</button>
              <button onClick={() => moveModule(mi, mi + 1)} disabled={mi === modules.length - 1}
                className="text-xs text-gray-400 hover:text-gray-600 disabled:opacity-30">↓</button>
            </div>

            {/* 节点列表 */}
            <div className="space-y-1 ml-6">
              {module.node_ids.map((nid, ni) => {
                const node = (module.nodes || []).find((n) => n.id === nid);
                return (
                  <div key={nid} className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2 group">
                    <span className="text-gray-300 text-xs w-5">{ni + 1}.</span>
                    <span className="flex-1 truncate">{node?.title || nid.substring(0, 12)}</span>
                    {node?.status === 'completed' && <span className="text-green-500 text-xs">✅</span>}
                    <button onClick={() => moveNode(mi, ni, ni - 1)} disabled={ni === 0}
                      className="text-xs text-gray-300 hover:text-gray-500 opacity-0 group-hover:opacity-100 disabled:opacity-0">↑</button>
                    <button onClick={() => moveNode(mi, ni, ni + 1)} disabled={ni === module.node_ids.length - 1}
                      className="text-xs text-gray-300 hover:text-gray-500 opacity-0 group-hover:opacity-100 disabled:opacity-0">↓</button>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {saved && (
        <div className="fixed bottom-6 right-6 bg-green-600 text-white px-6 py-3 rounded-xl shadow-lg text-sm">
          ✅ 大纲已保存，即将进入学习...
        </div>
      )}
    </div>
  );
}
