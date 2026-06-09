import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../stores/useAuthStore';
import { Save, KeyRound, BookText, Timer, MessageCircle, ClipboardCheck, Monitor } from 'lucide-react';
import { showToast } from '../components/common';

interface LearnerProfile {
  content: { abstraction_level: number; analogy_density: number; example_style: number };
  pace: { teaching_speed: number; session_duration_min: number; repetition_preference: number };
  interaction: { feedback_tone: number; error_handling: number; interrupt_policy: string };
  assessment: { quiz_style: number; tolerance: number; review_frequency: number };
  ui: { font_size: string; color_scheme: string; layout_density: string; enable_tts: boolean };
}

const DEFAULT_PROFILE: LearnerProfile = {
  content: { abstraction_level: 0.5, analogy_density: 0.5, example_style: 0.5 },
  pace: { teaching_speed: 0.5, session_duration_min: 25, repetition_preference: 0.5 },
  interaction: { feedback_tone: 0.5, error_handling: 0.5, interrupt_policy: 'anytime' },
  assessment: { quiz_style: 0.5, tolerance: 0.7, review_frequency: 0.5 },
  ui: { font_size: 'medium', color_scheme: 'standard', layout_density: 'standard', enable_tts: false },
};

const PRESETS: Record<string, Partial<LearnerProfile>> = {
  '儿童友好': {
    content: { abstraction_level: 0.2, analogy_density: 0.9, example_style: 0.1 },
    pace: { teaching_speed: 0.2, session_duration_min: 15, repetition_preference: 0.8 },
    interaction: { feedback_tone: 0.1, error_handling: 0.1, interrupt_policy: 'anytime' },
    assessment: { quiz_style: 0.1, tolerance: 0.9, review_frequency: 0.7 },
    ui: { font_size: 'large', color_scheme: 'soft', layout_density: 'standard', enable_tts: true },
  },
  '青少年探索': {
    content: { abstraction_level: 0.5, analogy_density: 0.6, example_style: 0.4 },
    pace: { teaching_speed: 0.4, session_duration_min: 25, repetition_preference: 0.5 },
    interaction: { feedback_tone: 0.3, error_handling: 0.3, interrupt_policy: 'anytime' },
    assessment: { quiz_style: 0.4, tolerance: 0.7, review_frequency: 0.5 },
  },
  '成人高效': {
    content: { abstraction_level: 0.7, analogy_density: 0.4, example_style: 0.8 },
    pace: { teaching_speed: 0.7, session_duration_min: 40, repetition_preference: 0.3 },
    interaction: { feedback_tone: 0.6, error_handling: 0.7, interrupt_policy: 'after_segment' },
    assessment: { quiz_style: 0.7, tolerance: 0.6, review_frequency: 0.4 },
  },
  '长辈关怀': {
    content: { abstraction_level: 0.2, analogy_density: 0.7, example_style: 0.1 },
    pace: { teaching_speed: 0.1, session_duration_min: 20, repetition_preference: 0.9 },
    interaction: { feedback_tone: 0.1, error_handling: 0.1, interrupt_policy: 'anytime' },
    assessment: { quiz_style: 0.2, tolerance: 0.8, review_frequency: 0.8 },
    ui: { font_size: 'xlarge', color_scheme: 'high-contrast', layout_density: 'comfortable', enable_tts: true },
  },
};

/** 将旧版扁平 profile（或空）归一化为嵌套结构 */
function normalizeProfile(raw: any): LearnerProfile {
  if (!raw) return JSON.parse(JSON.stringify(DEFAULT_PROFILE));
  const hasGroups = ['content', 'pace', 'interaction', 'assessment', 'ui'].some((k) => k in raw);
  if (hasGroups) {
    const out = JSON.parse(JSON.stringify(DEFAULT_PROFILE));
    for (const group of Object.keys(out)) {
      if (raw[group] && typeof raw[group] === 'object') Object.assign(out[group], raw[group]);
    }
    return out;
  }
  // 扁平兼容：将旧版字段映射到嵌套结构
  const flatMap: Record<string, [string, string]> = {
    abstraction_level: ['content', 'abstraction_level'],
    analogy_density: ['content', 'analogy_density'],
    example_style: ['content', 'example_style'],
    teaching_speed: ['pace', 'teaching_speed'],
    session_duration: ['pace', 'session_duration_min'],
    session_duration_min: ['pace', 'session_duration_min'],
    repetition_preference: ['pace', 'repetition_preference'],
    feedback_tone: ['interaction', 'feedback_tone'],
    error_handling: ['interaction', 'error_handling'],
    quiz_style: ['assessment', 'quiz_style'],
    tolerance: ['assessment', 'tolerance'],
    review_frequency: ['assessment', 'review_frequency'],
  };
  const out = JSON.parse(JSON.stringify(DEFAULT_PROFILE));
  for (const [key, value] of Object.entries(raw)) {
    const mapping = flatMap[key];
    if (mapping && typeof value === 'number') (out[mapping[0]] as any)[mapping[1]] = value;
  }
  return out;
}

function Slider({ label, value, onChange, left, right }: {
  label: string; value: number; onChange: (v: number) => void; left: string; right: string;
}) {
  return (
    <div className="mb-3">
      <div className="flex justify-between items-center mb-1">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        <span className="text-xs text-gray-400">{value.toFixed(1)}</span>
      </div>
      <input type="range" min="0" max="1" step="0.1" value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))} className="w-full" />
      <div className="flex justify-between text-xs text-gray-400">
        <span>{left}</span>
        <span>{right}</span>
      </div>
    </div>
  );
}

function SectionHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <h3 className="font-medium text-gray-800 mb-3 flex items-center gap-2 border-b border-gray-100 pb-2">
      {icon} {title}
    </h3>
  );
}

export default function SettingsPage() {
  const { user, loadUser, isAdmin } = useAuthStore();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const forcePassword = searchParams.get('force_password') === '1';
  const [saving, setSaving] = useState(false);

  const [profile, setProfile] = useState<LearnerProfile>(() => normalizeProfile(user?.learner_profile));

  useEffect(() => {
    if (user?.learner_profile) {
      setProfile(normalizeProfile(user.learner_profile));
    }
  }, [user?.learner_profile]);

  const [passwordForm, setPasswordForm] = useState({ newPassword: '', confirmPassword: '' });
  const [passwordMessage, setPasswordMessage] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);

  const update = <G extends keyof LearnerProfile>(group: G, field: keyof LearnerProfile[G], value: any) => {
    setProfile((prev) => ({
      ...prev,
      [group]: { ...prev[group], [field]: value },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch('/users/me', { learner_profile: profile });
      await loadUser();
      showToast('success', '学习风格设置已保存');
    } catch {
      showToast('error', '保存失败');
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

  return (
    <div className="p-6 max-w-2xl mx-auto">
      {forcePassword && (
        <div className="bg-red-50 border-2 border-red-300 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-bold text-red-800 mb-2">🔒 首次登录，请先修改密码</h2>
          <p className="text-red-600 text-sm mb-4">使用内置管理员账号首次登录，必须修改密码后才能继续使用系统。</p>
        </div>
      )}

      <h1 className="text-2xl font-bold mb-6">设置</h1>

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

      <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
        <h2 className="font-medium mb-4 flex items-center gap-2"><KeyRound size={18} /> 修改密码</h2>
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
            <p className={`text-sm ${passwordMessage.includes('失败') || passwordMessage.includes('不一致') || passwordMessage.includes('不少于') ? 'text-red-500' : 'text-green-600'}`}>{passwordMessage}</p>
          )}
        </div>
      </div>

      {!forcePassword && (
        <>
          {!isAdmin() && (
            <div className="bg-white rounded-xl border border-gray-100 p-6 mb-6">
              <h2 className="font-medium mb-4">学习风格设置</h2>
              <p className="text-xs text-gray-400 mb-4">这些设置会影响 AI 教师的教学方式。选择一个预设或手动调整。</p>

              <div className="flex flex-wrap gap-2 mb-6">
                {Object.entries(PRESETS).map(([name, values]) => (
                  <button key={name} onClick={() => setProfile({ ...JSON.parse(JSON.stringify(DEFAULT_PROFILE)), ...values } as LearnerProfile)}
                    className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                      Object.entries(values).every(([gk, gv]) =>
                        typeof gv === 'object'
                          ? Object.entries(gv as any).every(([fk, fv]) => (profile as any)[gk]?.[fk] === fv)
                          : (profile as any)[gk] === gv
                      )
                        ? 'bg-indigo-100 border-indigo-300 text-indigo-700'
                        : 'bg-gray-50 border-gray-200 text-gray-500 hover:border-gray-300'
                    }`}>{name}</button>
                ))}
              </div>

              <div className="space-y-6">
                {/* 内容偏好 */}
                <div>
                  <SectionHeader icon={<BookText size={16} />} title="内容偏好" />
                  <Slider label="抽象程度" value={profile.content.abstraction_level}
                    onChange={(v) => update('content', 'abstraction_level', v)} left="多用具体例子" right="使用专业术语" />
                  <Slider label="比喻密度" value={profile.content.analogy_density}
                    onChange={(v) => update('content', 'analogy_density', v)} left="少用类比" right="多用比喻" />
                  <Slider label="举例风格" value={profile.content.example_style}
                    onChange={(v) => update('content', 'example_style', v)} left="生活化例子" right="专业化例子" />
                </div>

                {/* 节奏偏好 */}
                <div>
                  <SectionHeader icon={<Timer size={16} />} title="节奏偏好" />
                  <Slider label="教学速度" value={profile.pace.teaching_speed}
                    onChange={(v) => update('pace', 'teaching_speed', v)} left="慢而细致" right="快而简洁" />
                  <div className="mb-3">
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-sm font-medium text-gray-700">单次学习时长</label>
                      <span className="text-xs text-gray-400">{profile.pace.session_duration_min} 分钟</span>
                    </div>
                    <input type="range" min="5" max="60" step="5" value={profile.pace.session_duration_min}
                      onChange={(e) => update('pace', 'session_duration_min', parseInt(e.target.value))} className="w-full" />
                    <div className="flex justify-between text-xs text-gray-400">
                      <span>5 分钟</span>
                      <span>60 分钟</span>
                    </div>
                  </div>
                  <Slider label="重复偏好" value={profile.pace.repetition_preference}
                    onChange={(v) => update('pace', 'repetition_preference', v)} left="一次即可" right="多重复" />
                </div>

                {/* 互动风格 */}
                <div>
                  <SectionHeader icon={<MessageCircle size={16} />} title="互动风格" />
                  <Slider label="反馈语气" value={profile.interaction.feedback_tone}
                    onChange={(v) => update('interaction', 'feedback_tone', v)} left="鼓励引导" right="直接指出" />
                  <Slider label="错误处理" value={profile.interaction.error_handling}
                    onChange={(v) => update('interaction', 'error_handling', v)} left="提示引导" right="直接指正" />
                  <div className="mb-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">打断策略</label>
                    <select value={profile.interaction.interrupt_policy}
                      onChange={(e) => update('interaction', 'interrupt_policy', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                      <option value="anytime">随时可以打断</option>
                      <option value="after_segment">等一段讲完再打断</option>
                    </select>
                  </div>
                </div>

                {/* 评估方式 */}
                <div>
                  <SectionHeader icon={<ClipboardCheck size={16} />} title="评估方式" />
                  <Slider label="出题风格" value={profile.assessment.quiz_style}
                    onChange={(v) => update('assessment', 'quiz_style', v)} left="游戏化" right="传统考试" />
                  <Slider label="容错率" value={profile.assessment.tolerance}
                    onChange={(v) => update('assessment', 'tolerance', v)} left="严格" right="宽松" />
                  <Slider label="复习频率" value={profile.assessment.review_frequency}
                    onChange={(v) => update('assessment', 'review_frequency', v)} left="少复习" right="多复习" />
                </div>

                {/* 界面偏好 */}
                <div>
                  <SectionHeader icon={<Monitor size={16} />} title="界面偏好" />
                  <div className="mb-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">字体大小</label>
                    <select value={profile.ui.font_size}
                      onChange={(e) => update('ui', 'font_size', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                      <option value="small">小</option>
                      <option value="medium">中</option>
                      <option value="large">大</option>
                      <option value="xlarge">超大</option>
                    </select>
                  </div>
                  <div className="mb-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">色彩模式</label>
                    <select value={profile.ui.color_scheme}
                      onChange={(e) => update('ui', 'color_scheme', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                      <option value="soft">柔和</option>
                      <option value="standard">标准</option>
                      <option value="high-contrast">高对比</option>
                    </select>
                  </div>
                  <div className="mb-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">布局密度</label>
                    <select value={profile.ui.layout_density}
                      onChange={(e) => update('ui', 'layout_density', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                      <option value="comfortable">宽松</option>
                      <option value="standard">标准</option>
                      <option value="compact">紧凑</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-2 mb-3">
                    <input type="checkbox" id="enable_tts" checked={profile.ui.enable_tts}
                      onChange={(e) => update('ui', 'enable_tts', e.target.checked)}
                      className="rounded border-gray-300" />
                    <label htmlFor="enable_tts" className="text-sm text-gray-700">开启语音播报</label>
                  </div>
                </div>
              </div>

              <button onClick={handleSave} disabled={saving}
                className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 mt-6 disabled:opacity-50">
                <Save size={16} /> {saving ? '保存中...' : '保存设置'}
              </button>
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
