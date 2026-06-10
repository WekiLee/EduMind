import { useEffect, useState } from 'react';
import { api } from '../../services/api';
import { Save, Terminal } from 'lucide-react';
import { LoadingSpinner, showToast } from '../../components/common';

export default function AdminConfigPage() {
  const [config, setConfig] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [mcpTools, setMcpTools] = useState<any[]>([]);
  const [mcpResult, setMcpResult] = useState('');
  const [mcpTesting, setMcpTesting] = useState(false);
  const [apiKeyTouched, setApiKeyTouched] = useState(false);

  useEffect(() => { loadConfig(); }, []);

  const loadConfig = async () => {
    try {
      const { data } = await api.get('/admin/config');
      setConfig(data.data || {});
      setApiKeyTouched(false);
    } catch {
      showToast('error', '加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/admin/config', {
        llm_provider: config.llm_provider,
        llm_model: config.llm_model,
        llm_api_key: apiKeyTouched ? (config.llm_api_key || '') : undefined,
        llm_api_base: config.llm_api_base,
        allow_self_register: config.allow_self_register,
      });
      showToast('success', '配置已更新');
      await loadConfig();
    } catch (err: any) {
      showToast('error', '保存失败: ' + (err.response?.data?.detail || '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSpinner text="加载配置..." />;

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">系统配置</h1>

      <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
        <h2 className="font-medium mb-4">🤖 AI 模型配置</h2>
        <p className="text-xs text-gray-400 mb-4">配置系统默认使用的大语言模型</p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">LLM Provider</label>
            <select value={config.llm_provider || 'openai-compatible'}
              onChange={(e) => setConfig({ ...config, llm_provider: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
              <option value="openai-compatible">DeepSeek / OpenAI 兼容</option>
              <option value="ollama">Ollama（本地）</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">模型名称</label>
            <input type="text" value={config.llm_model || ''}
              onChange={(e) => setConfig({ ...config, llm_model: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <input type="password" value={config.llm_api_key || ''}
              onChange={(e) => {
                setApiKeyTouched(true);
                setConfig({ ...config, llm_api_key: e.target.value });
              }}
              placeholder={config.llm_api_key_masked || '输入 API Key...'} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            {config.llm_api_key_masked && !apiKeyTouched && !config.llm_api_key && (
              <div className="flex items-center justify-between gap-3 mt-1">
                <p className="text-xs text-gray-400">已配置：{config.llm_api_key_masked}</p>
                <button type="button"
                  onClick={() => {
                    setApiKeyTouched(true);
                    setConfig({ ...config, llm_api_key: '' });
                  }}
                  className="text-xs text-red-600 hover:underline">
                  清空 API Key
                </button>
              </div>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Base URL</label>
            <input type="text" value={config.llm_api_base || ''}
              onChange={(e) => setConfig({ ...config, llm_api_base: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
        </div>

        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 mt-4">
          <Save size={16} /> {saving ? '保存中...' : '保存配置'}
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
        <h2 className="font-medium mb-4">👥 注册设置</h2>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={config.allow_self_register !== false}
            onChange={(e) => setConfig({ ...config, allow_self_register: e.target.checked })}
            className="rounded border-gray-300" />
          允许用户自助注册
        </label>
        <p className="text-xs text-gray-400 mt-1">关闭后新用户只能由管理员创建</p>
      </div>

      {/* MCP 工具 */}
      <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
        <h2 className="font-medium mb-4 flex items-center gap-2"><Terminal size={18} /> MCP 工具</h2>
        <p className="text-xs text-gray-400 mb-3">MCP 协议允许 AI 在教学对话中调用外部工具</p>
        <button onClick={async () => {
          try {
            const { data } = await api.get('/admin/mcp/tools');
            setMcpTools(data.data);
            showToast('success', `加载到 ${data.data.length} 个工具`);
          } catch {
            showToast('error', '加载工具列表失败');
          }
        }} className="text-xs text-indigo-600 hover:underline mb-3 inline-block">刷新工具列表</button>

        {mcpTools.length > 0 && (
          <div className="space-y-2 mb-4">
            {mcpTools.map((t: any, i: number) => (
              <div key={i} className="bg-gray-50 rounded-lg px-3 py-2 text-sm">
                <div className="font-medium text-gray-700">{t.name}</div>
                <p className="text-xs text-gray-500 mt-0.5">{t.description}</p>
                <button onClick={async () => {
                  setMcpTesting(true);
                  setMcpResult('');
                  try {
                    const { data } = await api.post('/admin/mcp/call', { tool: t.name, args: { query: '测试', max_results: 2 } });
                    setMcpResult(data.data.result || '(无返回)');
                  } catch {
                    setMcpResult('调用失败');
                  } finally {
                    setMcpTesting(false);
                  }
                }} disabled={mcpTesting}
                  className="text-xs text-indigo-600 hover:underline mt-1 inline-block">
                  {mcpTesting ? '测试中...' : '测试调用'}
                </button>
              </div>
            ))}
          </div>
        )}
        {mcpResult && (
          <div className="bg-gray-900 text-green-400 rounded-lg p-3 text-xs font-mono max-h-40 overflow-auto">
            {mcpResult}
          </div>
        )}
      </div>
    </div>
  );
}
