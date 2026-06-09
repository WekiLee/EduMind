import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { connectChatWS, sendChatMessage, sendExtensionRequest, sendAudioMessage, closeChatWS } from '../services/api';
import { isVoiceSupported, startRecording, stopRecording, cancelRecording, isVoiceActivationActive, startVoiceActivation, stopVoiceActivation } from '../services/voice';
import { useLearningStore } from '../stores/useLearningStore';
import { ChevronRight, MessageSquare, Brain, Send, Maximize2, BarChart3 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import GraphView from '../components/KnowledgeGraph/GraphView';
import KnowledgeCard from '../components/KnowledgeCard';

interface QuizQuestion {
  id: string;
  type: string;
  question: string;
  options?: string[];
}

interface QuizResult {
  score: number;
  total: number;
  correct: number;
  passed: boolean;
  mastery_update?: number;
  results: { question_id: string; correct: boolean; correct_answer: string }[];
}

export default function LearnPage() {
  const { pathId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const reviewNodeId = searchParams.get('review');
  const {
    currentPath, setCurrentPath,
    currentNode, setCurrentNode,
    chatMessages, addChatMessage, appendChatChunk, clearChat,
    setChatLoading, isChatLoading,
  } = useLearningStore();

  const [message, setMessage] = useState('');
  const [showGraph, setShowGraph] = useState(false);
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([]);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, string>>({});
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });
  const [isRecording, setIsRecording] = useState(false);
  const [quizGenerating, setQuizGenerating] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const quizSectionRef = useRef<HTMLDivElement>(null);

  // 加载路径（切换路径时先清空旧数据）
  useEffect(() => {
    if (!pathId) return;
    setCurrentNode(null);
    setCurrentPath(null);
    clearChat();
    setGraphData({ nodes: [], edges: [] });
    api.get(`/learning-paths/${pathId}`).then(({ data }) => setCurrentPath(data.data));
    return () => { closeChatWS(); clearChat(); };
  }, [pathId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // 测验生成后自动滚动到答题区
  useEffect(() => {
    if (quizQuestions.length > 0) {
      setTimeout(() => quizSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }
  }, [quizQuestions]);

  const allNodes = currentPath?.syllabus?.flatMap((m) => m.nodes || []) || [];
  const firstIncompleteNode = allNodes.find((n) => n.status !== 'completed');

  // 加载节点
  const loadNode = async (nodeId: string) => {
    try {
      const { data } = await api.get(`/nodes/${nodeId}`);
      setCurrentNode(data.data);
      clearChat();
      setQuizQuestions([]);
      setQuizAnswers({});
      setQuizResult(null);
      setGraphData({ nodes: [], edges: [] });  // 清除旧图谱防止闪烁

      await api.post(`/nodes/${nodeId}/start`, {}, { params: { path_id: pathId } });

      // 等待 WebSocket 连接就绪后再发送消息
      await connectChatWS(
        (chunk) => appendChatChunk(chunk),
        () => setChatLoading(false),
        (err) => console.error(err)
      );

      setChatLoading(true);
      sendChatMessage(nodeId, '请开始讲解这个知识点', pathId);

      // 加载图谱
      try {
        const graphRes = await api.get(`/nodes/${nodeId}/graph`, { params: { path_id: pathId } });
        setGraphData(graphRes.data.data);
      } catch (_) { /* 图谱加载失败不影响主流程 */ }
    } catch (err) {
      console.error('加载节点失败', err);
    }
  };

  useEffect(() => {
    if (!currentNode && (firstIncompleteNode || reviewNodeId)) {
      // 如果有 review 参数，加载指定的复习节点；否则加载第一个未完成节点
      const targetId = reviewNodeId || firstIncompleteNode!.id;
      loadNode(targetId);
    }
  }, [firstIncompleteNode, currentNode, reviewNodeId]);

  // 发送聊天消息
  const handleSend = () => {
    if (!message.trim() || !currentNode) return;
    addChatMessage({ id: `user-${Date.now()}`, role: 'user', content: message });
    setChatLoading(true);
    sendChatMessage(currentNode.id, message, pathId);
    setMessage('');
  };

  // 生成测验
  const handleComplete = async () => {
    if (!currentNode) return;
    setQuizGenerating(true);
    try {
      const { data } = await api.post(`/nodes/${currentNode.id}/quiz`);
      setQuizQuestions(data.data.questions);
      setQuizAnswers({});
      setQuizResult(null);
    } catch (err) {
      console.error('生成测验失败', err);
    } finally {
      setQuizGenerating(false);
    }
  };

  // review 模式下，节点加载完毕后自动出题
  const reviewTriggered = useRef(false);
  useEffect(() => {
    if (reviewNodeId && currentNode && !reviewTriggered.current) {
      reviewTriggered.current = true;
      setTimeout(() => handleComplete(), 1000);
    }
  }, [reviewNodeId, currentNode]);

  // 选择答案
  const selectAnswer = (questionId: string, option: string) => {
    setQuizAnswers((prev) => ({ ...prev, [questionId]: option }));
  };

  // 提交答案
  const submitQuiz = async () => {
    if (!currentNode || !pathId || submitting) return;
    const answers = Object.entries(quizAnswers).map(([question_id, selected]) => ({
      question_id,
      selected,
    }));
    setSubmitting(true);
    try {
      const { data } = await api.post(`/quiz/${currentNode.id}/submit`, {
        answers,
        path_id: pathId,
      });
      setQuizResult(data.data);

      // 通过 → 调用完成节点
      if (data.data.passed) {
        const mastery = data.data.mastery_update ?? data.data.score;
        await api.post(`/nodes/${currentNode.id}/complete`, { mastery }, { params: { path_id: pathId } });
      }
    } catch (err) {
      console.error('提交答案失败', err);
    } finally {
      setSubmitting(false);
    }
  };

  // 渲染内容：整个内容用等宽字体 + 保留空白显示
  const renderContent = (text: string) => {
    if (!text) return null;
    return (
      <div className="whitespace-pre-wrap break-all text-sm leading-relaxed font-mono">
        {text}
      </div>
    );
  };

  // 语音录制（含 VAD 自动停止）
  const handleVoiceToggle = async () => {
    if (isRecording) {
      try {
        cancelRecording();
        setIsRecording(false);
      } catch (_) { /* 取消 */ }
    } else {
      try {
        await startRecording(
          async () => {
            // VAD 自动停止回调
            setIsRecording(false);
            try {
              if (currentNode) {
                const { base64 } = await stopRecording();
                addChatMessage({ id: `voice-${Date.now()}`, role: 'user', content: '🎤 [语音消息]' });
                setChatLoading(true);
                sendAudioMessage(base64, currentNode.id, pathId);
              }
            } catch { /*  */ }
          }
        );
        setIsRecording(true);
      } catch (_) {
        alert('无法访问麦克风，请检查权限设置');
      }
    }
  };

  // 语音唤醒模式切换
  const handleVoiceActivationToggle = async () => {
    if (isVoiceActivationActive()) {
      stopVoiceActivation();
      return;
    }
    try {
      await startVoiceActivation(async (base64) => {
        if (base64 && currentNode) {
          addChatMessage({ id: `wake-${Date.now()}`, role: 'user', content: '🎤 [语音唤醒]' });
          setChatLoading(true);
          sendAudioMessage(base64, currentNode.id, pathId);
        }
      });
    } catch (_) {
      alert('无法访问麦克风，请检查权限设置');
    }
  };

  // 继续下一节点
  const goToNextNode = () => {
    const currentIdx = allNodes.findIndex((n) => n.id === currentNode?.id);
    const nextNode = allNodes[currentIdx + 1];
    if (nextNode) loadNode(nextNode.id);
  };

  return (
    <div className="flex h-full">
      {/* 左侧：模块导航 */}
      <aside className="w-56 border-r border-gray-200 bg-white p-4 overflow-auto">
        {reviewNodeId && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg px-3 py-2 mb-3">
            <p className="text-xs font-medium text-orange-700">🔄 复习模式</p>
            <p className="text-xs text-orange-500 mt-0.5">完成测验后将更新掌握度</p>
          </div>
        )}
        <h3 className="text-sm font-medium text-gray-400 uppercase mb-3">目录</h3>
        {currentPath?.syllabus?.map((module) => (
          <div key={module.module_name} className="mb-3">
            <p className="text-xs font-medium text-gray-500 mb-1">{module.module_name}</p>
            <div className="space-y-1">
              {(module.nodes || []).slice(0, 10).map((node) => (
                <button
                  key={node.id}
                  onClick={() => loadNode(node.id)}
                  className={`w-full text-left px-2 py-1.5 rounded text-xs truncate ${
                    node.id === currentNode?.id
                      ? 'bg-indigo-100 text-indigo-700'
                      : node.status === 'completed'
                      ? 'text-green-600'
                      : 'text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  {node.status === 'completed' && node.mastery < 0.8 && '⚠️ '}
                  {node.status === 'completed' && node.mastery >= 0.8 && '✅ '}
                  {node.status === 'learning' && '📖 '}
                  {node.id === currentNode?.id && '▶ '}
                  {node.title || node.id.substring(0, 8)}
                </button>
              ))}
            </div>
          </div>
        ))}
      </aside>

      {/* 中间：主内容 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 知识卡片 */}
        {currentNode && quizQuestions.length === 0 && (
          <div className="p-4 border-b border-gray-200">
            <KnowledgeCard node={currentNode} />
            <div className="flex items-center gap-2 mt-3">
              <button onClick={handleComplete} className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700">
                ✅ 完成并测验
              </button>
              <button onClick={goToNextNode} className="flex items-center gap-1 text-gray-500 px-3 py-2 rounded-lg text-sm hover:bg-gray-100">
                下一节点 <ChevronRight size={16} />
              </button>
              <button onClick={() => sendExtensionRequest(currentNode.id)} className="flex items-center gap-1 text-gray-500 px-3 py-2 rounded-lg text-sm hover:bg-gray-100">
                <Brain size={16} /> 延伸
              </button>
              <button onClick={() => navigate(`/report/${pathId}`)} className="flex items-center gap-1 text-gray-500 px-3 py-2 rounded-lg text-sm hover:bg-gray-100">
                <BarChart3 size={16} /> 报告
              </button>
            </div>
          </div>
        )}

        {/* Quiz 面板 */}
        {(quizGenerating || quizQuestions.length > 0) && (
          <div ref={quizSectionRef} className="p-4 border-b border-gray-200 bg-white">
            {quizGenerating ? (
              <div className="flex items-center justify-center gap-2 text-gray-400 text-sm py-4">
                <span className="w-4 h-4 border-2 border-indigo-300 border-t-indigo-600 rounded-full animate-spin" />
                正在生成题目...
              </div>
            ) : (<>
            <h3 className="font-medium mb-3">📝 知识测验</h3>
            <div className="space-y-4">
              {quizQuestions.map((q, qi) => (
                <div key={q.id} className="border border-gray-200 rounded-lg p-3">
                  <p className="text-sm font-medium mb-2">{qi + 1}. {q.question}</p>
                  {q.type === 'fill_blank' || !q.options ? (
                    <div className="space-y-1">
                      <input
                        type="text"
                        value={quizAnswers[q.id] || ''}
                        onChange={(e) => selectAnswer(q.id, e.target.value)}
                        disabled={!!quizResult}
                        placeholder="在此输入答案..."
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50"
                      />
                      {(() => {
                        const r = quizResult?.results.find((x) => x.question_id === q.id);
                        if (!r) return null;
                        return (
                          <p className={`text-xs mt-1 ${r.correct ? 'text-green-600' : 'text-red-600'}`}>
                            {r.correct ? '✓ 正确' : `✗ 正确答案：${r.correct_answer}`}
                          </p>
                        );
                      })()}
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {(q.options || []).map((opt) => {
                        const isSelected = quizAnswers[q.id] === opt;
                        const isCorrect = quizResult?.results.find((r) => r.question_id === q.id);
                        const showResult = quizResult && isCorrect;
                        const bgColor = showResult
                          ? isCorrect.correct && isSelected
                            ? 'bg-green-50 border-green-400'
                            : !isCorrect.correct && isSelected
                            ? 'bg-red-50 border-red-400'
                            : 'bg-gray-50'
                          : isSelected
                          ? 'bg-indigo-50 border-indigo-400'
                          : 'bg-gray-50';

                        return (
                          <button key={opt}
                            onClick={() => !quizResult && selectAnswer(q.id, opt)}
                            disabled={!!quizResult}
                            className={`w-full text-left px-3 py-2 rounded-lg border text-sm ${bgColor} hover:bg-gray-100 transition-colors`}>
                            {opt}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* 提交 / 结果 */}
            <div className="mt-4">
              {!quizResult ? (
                <button
                  onClick={submitQuiz}
                  disabled={Object.keys(quizAnswers).length < quizQuestions.length || submitting}
                  className="w-full bg-indigo-600 text-white py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submitting ? '提交中...' : '提交答案'}
                </button>
              ) : (
                <div className="text-center">
                  <p className={`text-lg font-bold ${quizResult.passed ? 'text-green-600' : 'text-red-600'}`}>
                    {quizResult.correct}/{quizResult.total} 正确
                    {quizResult.passed ? ' ✅ 通过！' : ' ❌ 未通过'}
                  </p>
                  <div className="flex gap-2 justify-center mt-3">
                    {quizResult.passed ? (
                      <button onClick={goToNextNode} className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700">
                        继续下一节点 →
                      </button>
                    ) : (
                      <button onClick={handleComplete} className="bg-yellow-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-yellow-600">
                        🔄 重新测验
                      </button>
                    )}
                    <button onClick={() => { setQuizQuestions([]); setQuizResult(null); }} className="text-gray-500 px-4 py-2 rounded-lg text-sm hover:bg-gray-100">
                      返回学习
                    </button>
                  </div>
                </div>
              )}
            </div>
            </>)}
          </div>
        )}

        {/* 对话 */}
        <div className="flex-1 flex flex-col p-4 overflow-hidden">
          <div className="flex-1 overflow-auto space-y-3 mb-3">
            {chatMessages.length === 0 && (
              <div className="text-center py-10 text-gray-400">
                <MessageSquare size={32} className="mx-auto mb-2" />
                <p className="text-sm">AI 教师正在准备教学内容...</p>
              </div>
            )}
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-xl px-4 py-2 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white'
                    : msg.role === 'system'
                    ? 'bg-yellow-50 text-yellow-800 border border-yellow-200'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {msg.role === 'user' ? (
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  ) : (
                    <div className="markdown-content text-sm leading-relaxed">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isChatLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-xl px-4 py-2 text-sm text-gray-400">
                  <span className="animate-pulse">思考中...</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          <div className="flex gap-2 border-t border-gray-200 pt-3">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="输入你的问题..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
            {isVoiceSupported() && (
              <>
              <button
                onClick={handleVoiceToggle}
                disabled={isChatLoading || isVoiceActivationActive()}
                className={`px-3 py-2 rounded-lg border text-sm transition-colors ${
                  isRecording
                    ? 'bg-red-500 text-white border-red-500 animate-pulse'
                    : 'bg-white text-gray-500 border-gray-300 hover:bg-gray-50'
                } disabled:opacity-50`}
                title={isRecording ? 'VAD 录音中，静音自动停止' : '语音输入'}
              >
                {isRecording ? '⏹' : '🎤'}
              </button>
              <button
                onClick={handleVoiceActivationToggle}
                disabled={isChatLoading || isRecording}
                className={`px-3 py-2 rounded-lg border text-sm transition-colors ${
                  isVoiceActivationActive()
                    ? 'bg-green-500 text-white border-green-500 animate-pulse'
                    : 'bg-white text-gray-500 border-gray-300 hover:bg-gray-50'
                } disabled:opacity-50`}
                title={isVoiceActivationActive() ? '关闭语音唤醒' : '语音唤醒'}
              >
                {isVoiceActivationActive() ? '🔊' : '😴'}
              </button>
              </>
            )}
            <button
              onClick={handleSend}
              disabled={!message.trim() || isChatLoading}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* 图谱面板 */}
      {showGraph && (
        <div className="w-80 border-l border-gray-200 bg-white flex flex-col">
          <div className="flex items-center justify-between p-3 border-b border-gray-100">
            <h3 className="text-sm font-medium">知识图谱</h3>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 text-xs">
                <span className="w-2.5 h-2.5 rounded-full bg-green-500 inline-block" />
                <span className="text-gray-400">掌握</span>
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500 inline-block ml-1" />
                <span className="text-gray-400">学习中</span>
                <span className="w-2.5 h-2.5 rounded-full bg-gray-300 inline-block ml-1" />
                <span className="text-gray-400">未开始</span>
              </div>
              <button onClick={() => setShowGraph(false)} className="text-gray-400 hover:text-gray-600 text-sm">✕</button>
            </div>
          </div>
          <div className="flex-1 p-2">
            <GraphView
              nodes={graphData.nodes || []}
              edges={graphData.edges || []}
              currentNodeId={currentNode?.id}
              onNodeClick={(nid) => loadNode(nid)}
            />
          </div>
        </div>
      )}
    </div>
  );
}


