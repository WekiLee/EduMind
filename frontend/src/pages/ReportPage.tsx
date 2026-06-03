import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { ArrowLeft, AlertTriangle, BarChart3 } from 'lucide-react';

interface ModuleMastery {
  module_name: string;
  total_nodes: number;
  completed: number;
  avg_mastery: number;
}

interface QuizItem {
  node_id: string;
  score: number;
  created_at: string | null;
}

export default function ReportPage() {
  const { pathId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState<any>(null);
  const [path, setPath] = useState<any>(null);

  useEffect(() => {
    if (!pathId) return;
    api.get(`/learning-paths/${pathId}`).then(({ data }) => setPath(data.data));
    api.get(`/learning-paths/${pathId}/report`).then(({ data }) => setReport(data.data));
  }, [pathId]);

  const masteryColor = (v: number) => {
    if (v >= 0.8) return 'bg-green-500';
    if (v >= 0.6) return 'bg-yellow-500';
    if (v >= 0.3) return 'bg-orange-500';
    return 'bg-red-500';
  };

  if (!report || !path) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <button onClick={() => navigate(`/learn/${pathId}`)} className="flex items-center gap-1 text-gray-500 mb-4 hover:text-gray-700">
        <ArrowLeft size={16} /> 返回学习
      </button>

      <div className="flex items-center gap-3 mb-6">
        <BarChart3 size={24} className="text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold">学习报告</h1>
          <p className="text-gray-400 text-sm">{path.topic}</p>
        </div>
      </div>

      {/* 整体进度 */}
      <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-medium">整体掌握度</h2>
          <span className="text-3xl font-bold text-indigo-600">
            {((report.overall_mastery || 0) * 100).toFixed(0)}%
          </span>
        </div>
        <div className="bg-gray-100 rounded-full h-3">
          <div className="bg-indigo-500 h-3 rounded-full transition-all"
            style={{ width: `${(report.overall_mastery || 0) * 100}%` }} />
        </div>
        <p className="text-xs text-gray-400 mt-2">共完成 {report.total_quizzes} 次测验</p>
      </div>

      {/* 模块掌握度热力图 */}
      <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
        <h2 className="font-medium mb-4">模块掌握度</h2>
        <div className="space-y-3">
          {(report.module_mastery || []).map((m: ModuleMastery, i: number) => (
            <div key={i}>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-gray-700">{m.module_name}</span>
                <span className="text-gray-400 text-xs">
                  {m.completed}/{m.total_nodes} 节点 · {(m.avg_mastery * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex gap-0.5 h-6">
                {Array.from({ length: Math.max(m.total_nodes, 1) }).map((_, j) => {
                  const color = j < m.completed ? masteryColor(m.avg_mastery) : 'bg-gray-200';
                  return <div key={j} className={`flex-1 rounded-sm ${color}`}
                    title={`${m.module_name} - 掌握度 ${(m.avg_mastery * 100).toFixed(0)}%`} />;
                })}
              </div>
            </div>
          ))}
        </div>
        {/* 图例 */}
        <div className="flex items-center gap-4 mt-4 text-xs text-gray-400">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500 inline-block" /> ≥80%</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-500 inline-block" /> 60-80%</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-500 inline-block" /> 30-60%</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500 inline-block" /> &lt;30%</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-gray-200 inline-block" /> 未学习</span>
        </div>
      </div>

      {/* 薄弱节点 */}
      {report.weak_nodes?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={18} className="text-red-500" />
            <h2 className="font-medium">需要加强的节点</h2>
          </div>
          <div className="space-y-2">
            {report.weak_nodes.map((np: any, i: number) => (
              <div key={i} className="flex items-center justify-between bg-red-50 rounded-lg px-3 py-2 text-sm">
                <span className="text-red-700 truncate">{np.node_id?.substring(0, 16)}...</span>
                <span className="text-red-500 font-medium">{((np.mastery || 0) * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 测验历史 */}
      {report.quiz_history?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="font-medium mb-4">测验记录</h2>
          <div className="space-y-1">
            {report.quiz_history.map((q: QuizItem, i: number) => (
              <div key={i} className="flex items-center justify-between text-sm py-1.5 border-b border-gray-50 last:border-0">
                <span className="text-gray-500 text-xs">{q.created_at?.substring(0, 10) || '-'}</span>
                <span className={`font-medium ${q.score >= 0.6 ? 'text-green-600' : 'text-red-500'}`}>
                  {((q.score || 0) * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
