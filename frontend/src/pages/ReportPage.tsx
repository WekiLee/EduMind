import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { ArrowLeft, AlertTriangle, BarChart3, BookOpen, Clock, Target, TrendingUp, Download } from 'lucide-react';
import { LoadingSpinner, EmptyState } from '../components/common';

interface ModuleMastery {
  module_name: string;
  total_nodes: number;
  completed: number;
  avg_mastery: number;
}

interface WeakNode {
  node_id: string;
  title: string;
  mastery: number;
  status: string;
}

interface QuizItem {
  node_id: string;
  score: number;
  created_at: string | null;
}

interface ReportData {
  module_mastery: ModuleMastery[];
  weak_nodes: WeakNode[];
  quiz_history: QuizItem[];
  total_quizzes: number;
  overall_mastery: number;
  total_nodes: number;
  completed_nodes: number;
  in_progress_nodes: number;
}

export default function ReportPage() {
  const { pathId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState<ReportData | null>(null);
  const [path, setPath] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!pathId) return;
    setLoading(true);
    Promise.all([
      api.get(`/learning-paths/${pathId}`),
      api.get(`/learning-paths/${pathId}/report`),
    ]).then(([pathRes, reportRes]) => {
      setPath(pathRes.data.data);
      setReport(reportRes.data.data);
    }).catch(console.error).finally(() => setLoading(false));
  }, [pathId]);

  const masteryColor = (v: number) => {
    if (v >= 0.8) return 'bg-green-500';
    if (v >= 0.6) return 'bg-yellow-500';
    if (v >= 0.3) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const handleExport = () => {
    if (!pathId || !path) return;
    // 使用 api 实例获取 blob 并触发下载
    api.get(`/learning-paths/${pathId}/report/export`, { responseType: 'blob' })
      .then((res) => {
        const blob = res.data;
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `学习报告_${path.topic}_${new Date().toISOString().slice(0, 10)}.md`;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch(console.error);
  };

  if (loading) return <LoadingSpinner text="加载学习报告..." />;
  if (!report || !path) return <EmptyState icon="📊" title="暂无报告数据" description="完成一些学习节点后，报告将自动生成" />;

  const progressPct = report.total_nodes > 0
    ? Math.round((report.completed_nodes / report.total_nodes) * 100)
    : 0;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <button onClick={() => navigate(`/learn/${pathId}`)}
        className="flex items-center gap-1 text-gray-500 mb-4 hover:text-gray-700">
        <ArrowLeft size={16} /> 返回学习
      </button>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <BarChart3 size={24} className="text-indigo-600" />
          <div>
            <h1 className="text-2xl font-bold">学习报告</h1>
            <p className="text-gray-400 text-sm">{path.topic}</p>
          </div>
        </div>
        <button onClick={handleExport}
          className="flex items-center gap-2 bg-white border border-gray-300 text-gray-600 px-3 py-2 rounded-lg text-sm hover:bg-gray-50 transition-colors">
          <Download size={16} /> 导出报告
        </button>
      </div>

      {/* 概览卡片：双指标 */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 text-indigo-600 mb-1">
            <Target size={16} />
            <span className="text-xs font-medium text-gray-500">整体掌握度</span>
          </div>
          <span className="text-2xl font-bold text-indigo-600">
            {((report.overall_mastery || 0) * 100).toFixed(0)}%
          </span>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 text-green-600 mb-1">
            <BookOpen size={16} />
            <span className="text-xs font-medium text-gray-500">学习进度</span>
          </div>
          <span className="text-2xl font-bold text-green-600">{progressPct}%</span>
          <p className="text-xs text-gray-400 mt-0.5">
            {report.completed_nodes}/{report.total_nodes} 节点
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 text-orange-500 mb-1">
            <TrendingUp size={16} />
            <span className="text-xs font-medium text-gray-500">学习活动</span>
          </div>
          <span className="text-2xl font-bold text-orange-500">{report.total_quizzes}</span>
          <p className="text-xs text-gray-400 mt-0.5">次测验</p>
        </div>
      </div>

      {/* 进度 + 掌握度双进度条 */}
      <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-600 flex items-center gap-1"><BookOpen size={14} /> 学习进度</span>
              <span className="text-xs text-gray-400">{report.completed_nodes}/{report.total_nodes} 节点 · {report.in_progress_nodes} 进行中</span>
            </div>
            <div className="bg-gray-100 rounded-full h-3 flex">
              {report.completed_nodes > 0 && (
                <div className="bg-green-500 h-3 rounded-full transition-all"
                  style={{ width: `${progressPct}%` }} />
              )}
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-600 flex items-center gap-1"><Target size={14} /> 掌握度</span>
              <span className="text-xs text-gray-400">{((report.overall_mastery || 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="bg-gray-100 rounded-full h-3">
              <div className={`h-3 rounded-full transition-all ${masteryColor(report.overall_mastery || 0)}`}
                style={{ width: `${(report.overall_mastery || 0) * 100}%` }} />
            </div>
          </div>
        </div>
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
        <div className="flex items-center gap-4 mt-4 text-xs text-gray-400">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500 inline-block" /> ≥80%</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-500 inline-block" /> 60-80%</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-500 inline-block" /> 30-60%</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500 inline-block" /> &lt;30%</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-gray-200 inline-block" /> 未学习</span>
        </div>
      </div>

      {/* 薄弱节点（含标题、可点击） */}
      {report.weak_nodes?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={18} className="text-red-500" />
            <h2 className="font-medium">需要加强的节点</h2>
            <span className="text-xs text-gray-400">（{report.weak_nodes.length} 个）</span>
          </div>
          <div className="space-y-2">
            {report.weak_nodes.map((np: WeakNode, i: number) => (
              <div key={i} className="flex items-center justify-between bg-red-50 rounded-lg px-3 py-2 text-sm group hover:bg-red-100 transition-colors cursor-pointer"
                onClick={() => navigate(`/learn/${pathId}?review=${np.node_id}`)}>
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-red-500 text-xs">⬤</span>
                  <span className="text-red-700 truncate">{np.title}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-red-500 font-medium">{((np.mastery || 0) * 100).toFixed(0)}%</span>
                  <span className="text-xs text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">去复习 →</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 测验历史趋势图 */}
      {report.quiz_history?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-medium">测验记录</h2>
            <span className="text-xs text-gray-400">共 {report.total_quizzes} 次</span>
          </div>
          {/* 成绩趋势简图 */}
          <div className="flex items-end gap-1 h-12 mb-3">
            {report.quiz_history.slice(-14).map((q: QuizItem, i: number) => {
              const h = Math.max((q.score || 0) * 100, 4);
              return (
                <div key={i} className="flex-1 flex flex-col items-center group relative">
                  <div className={`w-full rounded-t-sm ${q.score >= 0.6 ? 'bg-green-400' : 'bg-red-400'}`}
                    style={{ height: `${h}%` }}
                    title={`${q.created_at?.substring(0, 10) || '-'}: ${((q.score || 0) * 100).toFixed(0)}%`} />
                </div>
              );
            })}
          </div>
          <div className="space-y-1">
            {report.quiz_history.slice(-10).reverse().map((q: QuizItem, i: number) => (
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

      {report.total_quizzes === 0 && report.weak_nodes?.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-6 text-center text-gray-400 text-sm">
          <Clock size={32} className="mx-auto mb-2" />
          还没有足够的学习数据，完成节点学习后报告将自动更新
        </div>
      )}
    </div>
  );
}
