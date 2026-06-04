import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../stores/useAuthStore';
import { Save, KeyRound } from 'lucide-react';

export default function SettingsPage() {
  const { user, loadUser, isAdmin } = useAuthStore();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const forcePassword = searchParams.get('force_password') === '1';
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const PRESETS: Record<string, Record<string, number>> = {
    '儿童友好': { abstraction_level: 0.2, analogy_density: 0.9, teaching_speed: 0.2, feedback_tone: 0.1, session_duration: 15, tolerance: 0.9, quiz_style: 0.1 },
    '青少年探索': { abstraction_level: 0.5, analogy_density: 0.6, teaching_speed: 0.4, feedback_tone: 0.3, session_duration: 25, tolerance: 0.7, quiz_style: 0.4 },
    '成人高效': { abstraction_level: 0.7, analogy_density: 0.4, teaching_speed: 0.7, feedback_tone: 0.6, session_duration: 40, tolerance: 0.6, quiz_style: 0.7 },
    '长辈关怀': { abstraction_level: 0.2, analogy_density: 0.7, teaching_speed: 0.1, feedback_tone: 0.1, session_duration: 20, tolerance: 0.8, quiz_style: 0.2 },
  };

  const [profile, setProfile] = useState({
    abstraction_level: user?.learner_profile?.abstraction_level ?? 0.5,
    analogy_density: user?.learner_profile?.analogy_density ?? 0.5,
    teaching_speed: user?.learner_profile?.teaching_speed ?? 0.5,
    feedback_tone: user?.learner_profile?.feedback_tone ?? 0.5,
    session_duration: user?.learner_profile?.session_duration ?? 25,
    tolerance: user?.learner_profile?.tolerance ?? 0.7,
    quiz_style: user?.learner_profile?.quiz_style ?? 0.5,
  });

  const [passwordForm, setPasswordForm] = useState({ newPassword: '', confirmPassword: '' });
  const [passwordMessage, setPasswordMessage] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch('/users/me', { learner_profile: profile });
      await loadUser();
      setMessage('设置已保存');
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      setMessage('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async () => {
    if (passwordForm.newPassword.length < 6) {
      setPasswordMessage('密码长度不少于6位');
      return;
    }
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordMessage('两次输入的密码不一致');
      return;
    }
    setPasswordSaving(true);
    try {
      await api.patch('/users/me', { password: passwordForm.newPassword });
      setPasswordMessage('密码已修改');
      setPasswordForm({ newPassword: '', confirmPassword: '' });
      // 强制改密码模式 → 刷新用户信息后跳转首页（按角色自动分配）
      if (forcePassword) {
        await loadUser();
        setTimeout(() => navigate('/'), 1000);
      }
    } catch (err) {
      setPasswordMessage('修改失败');
    } finally {
      setPasswordSaving(false);
    }
  };

  const Slider = ({ label, value, onChange, left, right }: {
    label: string; value: number; onChange: (v: number) => void; left: string; right: string;
  }) => (
    <div className="mb-4">
      <div className="flex justify-between items-center mb-1">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        <span className="text-xs text-gray-400">{value.toFixed(1)}</span>
      </div>
      <input
        type="range"
        min="0"
        max="1"
        step="0.1"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full"
      />
      <div className="flex justify-between text-xs text-gray-400">
        <span>{left}</span>
        <span>{right}</span>
      </div>
    </div>
  );

  return (
    <div className="p-6 max-w-2xl mx-auto">
      {forcePassword && (
        <div className="bg-red-50 border-2 border-red-300 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-bold text-red-800 mb-2">🔒 首次登录，请先修改密码</h2>
          <p className="text-red-600 text-sm mb-4">
            使用内置管理员账号首次登录，必须修改密码后才能继续使用系统。
          </p>
        </div>
      )}

      <h1 className="text-2xl font-bold mb-6">设置</h1>

      {/* 个人信息（强制改密码模式隐藏） */}
      {!forcePassword && (
        <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
          <h2 className="font-medium mb-4">个人信息</h2>
          <div className="text-sm text-gray-600 space-y-2">
            <p>姓名：{user?.name}</p>
            <p>邮箱：{user?.email}</p>
            <p>角色：{user?.role === 'admin' ? '管理员' : '普通用户'}</p>
            {user?.organization && <p>组织：{user.organization}</p>}
          </div>
        </div>
      )}

      {/* 修改密码（所有用户、所有模式可见） */}
      <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
        <h2 className="font-medium mb-4 flex items-center gap-2">
          <KeyRound size={18} /> 修改密码
        </h2>
        <div className="space-y-3 max-w-sm">
          <input type="password" value={passwordForm.newPassword}
            onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
            placeholder="新密码" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          <input type="password" value={passwordForm.confirmPassword}
            onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
            placeholder="确认新密码" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          <button onClick={handlePasswordChange} disabled={passwordSaving}
            className="flex items-center gap-2 bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-900 disabled:opacity-50 text-sm">
            <KeyRound size={16} /> {passwordSaving ? '修改中...' : '修改密码'}
          </button>
          {passwordMessage && (
            <p className={`text-sm ${passwordMessage.includes('失败') || passwordMessage.includes('不一致') || passwordMessage.includes('不少于') ? 'text-red-500' : 'text-green-600'}`}>
              {passwordMessage}
            </p>
          )}
        </div>
      </div>

      {/* 以下内容强制改密码时隐藏 */}
      {!forcePassword && (
        <>
          {/* 学习风格（仅普通用户） */}
          {!isAdmin() && (
            <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
              <h2 className="font-medium mb-4">学习风格设置</h2>
              <p className="text-xs text-gray-400 mb-4">这些设置会影响 AI 教师的教学方式。选择一个预设或手动调整。</p>

              {/* 预设按钮 */}
              <div className="flex flex-wrap gap-2 mb-4">
                {Object.entries(PRESETS).map(([name, values]) => (
                  <button key={name} onClick={() => setProfile(values as any)}
                    className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                      Object.entries(profile).every(([k, v]) => (values as any)[k] === v)
                        ? 'bg-indigo-100 border-indigo-300 text-indigo-700'
                        : 'bg-gray-50 border-gray-200 text-gray-500 hover:border-gray-300'
                    }`}>
                    {name}
                  </button>
                ))}
              </div>

              <Slider label="抽象程度" value={profile.abstraction_level}
                onChange={(v) => setProfile({ ...profile, abstraction_level: v })}
                left="多用具体例子" right="使用专业术语" />
              <Slider label="比喻密度" value={profile.analogy_density}
                onChange={(v) => setProfile({ ...profile, analogy_density: v })}
                left="少用类比" right="多用比喻" />
              <Slider label="教学速度" value={profile.teaching_speed}
                onChange={(v) => setProfile({ ...profile, teaching_speed: v })}
                left="慢而细致" right="快而简洁" />
              <Slider label="反馈风格" value={profile.feedback_tone}
                onChange={(v) => setProfile({ ...profile, feedback_tone: v })}
                left="鼓励引导" right="直接指出" />
              <Slider label="推荐单次时长" value={(profile.session_duration - 5) / 55}
                onChange={(v) => setProfile({ ...profile, session_duration: Math.round(5 + v * 55) })}
                left="5分钟" right="60分钟" />
              <Slider label="容错率" value={profile.tolerance}
                onChange={(v) => setProfile({ ...profile, tolerance: v })}
                left="严格" right="宽松" />
              <Slider label="出题风格" value={profile.quiz_style}
                onChange={(v) => setProfile({ ...profile, quiz_style: v })}
                left="游戏化" right="传统考试" />

              <button onClick={handleSave} disabled={saving}
                className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 mt-4 disabled:opacity-50">
                <Save size={16} /> {saving ? '保存中...' : '保存设置'}
              </button>
              {message && <p className="text-sm text-green-600 mt-2">{message}</p>}
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-100 p-6">
            <h2 className="font-medium mb-4">关于 EduMind</h2>
            <p className="text-sm text-gray-500">版本 0.1.0 MVP</p>
            <p className="text-sm text-gray-500">开源智能导师系统</p>
          </div>
        </>
      )}
    </div>
  );
}
