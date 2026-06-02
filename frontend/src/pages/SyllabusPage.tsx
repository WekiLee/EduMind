import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { ArrowLeft } from 'lucide-react';

export default function SyllabusPage() {
  const { pathId } = useParams();
  const navigate = useNavigate();
  const [path, setPath] = useState<any>(null);

  useEffect(() => {
    if (!pathId) return;
    api.get(`/learning-paths/${pathId}`).then(({ data }) => setPath(data.data));
  }, [pathId]);

  const handleConfirm = async () => {
    if (!path) return;
    await api.patch(`/learning-paths/${pathId}`, path.syllabus);
    navigate(`/learn/${pathId}`);
  };

  if (!path) return <div className="p-6">加载中...</div>;

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <button onClick={() => navigate(`/learn/${pathId}`)} className="flex items-center gap-1 text-gray-500 mb-4">
        <ArrowLeft size={16} /> 返回
      </button>

      <h1 className="text-2xl font-bold mb-2">{path.topic}</h1>
      <p className="text-gray-400 text-sm mb-6">请确认以下学习大纲，你可以拖拽调整模块和节点顺序</p>

      <div className="space-y-4">
        {(path.syllabus || []).map((module: any, mi: number) => (
          <div key={mi} className="bg-white rounded-xl border border-gray-100 p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="bg-indigo-100 text-indigo-600 text-xs px-2 py-0.5 rounded-full">模块 {mi + 1}</span>
              <h3 className="font-medium">{module.module_name || module.module_name}</h3>
              <span className="text-xs text-gray-400">{(module.nodes || []).length} 个知识点</span>
            </div>
            <div className="space-y-2">
              {(module.nodes || []).map((node: any, ni: number) => (
                <div key={ni} className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
                  <span className="text-gray-300">{ni + 1}.</span>
                  <span>{node.id?.substring(0, 12)}...</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    node.status === 'completed' ? 'bg-green-50 text-green-600' : 'bg-gray-100 text-gray-400'
                  }`}>
                    {node.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={handleConfirm}
        className="mt-6 w-full bg-indigo-600 text-white py-3 rounded-xl hover:bg-indigo-700 font-medium"
      >
        确认大纲，开始学习
      </button>
    </div>
  );
}
