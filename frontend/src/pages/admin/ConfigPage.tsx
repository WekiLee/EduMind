import { useEffect, useState } from 'react';
import { api } from '../../services/api';
import { Save, Info } from 'lucide-react';

export default function AdminConfigPage() {
  const [config, setConfig] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => { loadConfig(); }, []);

  const loadConfig = async () => {
    try {
      const { data } = await api.get('/admin/config');
      setConfig(data.data || {});
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      await api.put('/admin/config', {
        llm_provider: config.llm_provider,
        llm_model: config.llm_model,
        llm_api_key: config.llm_api_key || undefined,
        llm_api_base: config.llm_api_base,
        allow_self_register: config.allow_self_register,
      });
      setMessage('配置已更新');
      setTimeout(() => setMessage(''), 3000);
    } catch (err: any) {
      setMessage('保存失败: ' + (err.response?.data?.detail || '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">系统配置</h1>

      {/* LLM 配置 */}
      <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
        <h2 className="font-medium mb-4">🤖 AI 模型配置</h2>
        <p className="text-xs text-gray-400 mb-4">配置系统默认使用的大语言模型</p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">LLM Provider</label>
            <select
              value={config.llm_provider || 'openai-compatible'}
              onChange={(e) => setConfig({ ...config, llm_provider: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="openai-compatible">OpenAI 兼容 API</option>
              <option value="ollama">Ollama（本地）</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">模型名称</label>
            <input
              type="text"
              value={config.llm_model || 'deepseek-v4-flash'}
              onChange={(e) => setConfig({ ...config, llm_model: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
            <p className="text-xs text-gray-400 mt-1">例如：deepseek-chat, qwen2.5:7b, gpt-4o</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API 地址</label>
            <input
              type="text"
              value={config.llm_api_base || ''}
              onChange={(e) => setConfig({ ...config, llm_api_base: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
            <p className="text-xs text-gray-400 mt-1">例如：https://api.deepseek.com/v1</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <input
              type="password"
              value={config.llm_api_key || ''}
              onChange={(e) => setConfig({ ...config, llm_api_key: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              placeholder={config.llm_api_key_masked || '输入 API Key'}
            />
            {config.llm_api_key_masked && (
              <p className="text-xs text-gray-400 mt-1">当前密钥：{config.llm_api_key_masked}</p>
            )}
          </div>
        </div>
      </div>

      {/* 注册开关 */}
      <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
        <h2 className="font-medium mb-4">🔐 用户注册</h2>

        <label className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={config.allow_self_register !== false}
            onChange={(e) => setConfig({ ...config, allow_self_register: e.target.checked })}
            className="w-4 h-4 text-indigo-600"
          />
          <div>
            <p className="text-sm font-medium text-gray-700">允许用户自助注册</p>
            <p className="text-xs text-gray-400">关闭后，只能由管理员在后台创建账号</p>
          </div>
        </label>
      </div>

      {/* 保存 */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 bg-indigo-600 text-white px-6 py-2.5 rounded-lg hover:bg-indigo-700 disabled:opacity-50 text-sm"
        >
          <Save size={16} />
          {saving ? '保存中...' : '保存配置'}
        </button>
        {message && (
          <span className={`text-sm ${message.includes('失败') ? 'text-red-500' : 'text-green-600'}`}>
            {message}
          </span>
        )}
      </div>
    </div>
  );
}
