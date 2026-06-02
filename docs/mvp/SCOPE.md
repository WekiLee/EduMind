# MVP 范围定义

> 基于 DESIGN.md 的 Phase 0 规划，明确 MVP 的边界：做什么、不做什么、验收标准。

---

## 一、MVP 核心目标

用户启动系统 → 指定学习主题（文字/上传文件） → 系统自动生成知识图谱和大纲 → 用户逐节点学习（文字问答） → 完成评估 → 掌握度反馈 → 图谱可视化

**一句话**：让一个完整的学习闭环跑通，不依赖外部 AI 搜索和语音。

---

## 二、功能边界

### ✅ 包含（MVP）

| 模块 | 功能 | 说明 |
|------|------|------|
| **用户系统** | 注册 / 登录 / 个人信息 | 基础认证，JWT |
| **学习路径管理** | 创建路径 / 列表 / 查看 / 删除 | |
| **内容上传** | 上传 PDF/MD/TXT 文件 → 文本提取 | 由 LLM 提取知识点和依赖关系 |
| **知识图谱** | 节点入库 + 前置依赖关系写入 | Neo4j，MVP 不包含自动关联发现 |
| **大纲生成** | 拓扑排序 → 模块分组 → 用户确认/调整 | |
| **教学引擎** | 文字对话 + 知识卡片展示 | Domain Profile 基础版（general/math/programming） |
| **评估** | 选择题生成 + 判卷 + 掌握度计算 | |
| **进度追踪** | 节点状态 + 模块进度条 | |
| **图谱可视化** | vis-network 展示 + 按掌握度着色 | 可点击跳转到节点 |
| **模型配置** | 支持配置文件切换模型 Provider | MVP 硬编码为 Ollama/Qwen，但预留适配器 |

### ❌ 不包含（MVP 之后）

| 模块 | 原因 |
|------|------|
| AI 自动搜索编排 | 依赖 MCP + 多源交叉验证，复杂度高 |
| 语音交互（ASR + TTS） | 非核心闭环，Phase 1 |
| Learner Profile | MVP 默认成人模式，参数面板 Phase 1 |
| 完整的 Domain Profile 体系 | MVP 内置 3 个，其余 Phase 1 |
| 间隔重复复习 | Phase 1 |
| 3D 头像 | 增强体验，非必需 |
| Tauri 桌面打包 | Phase 1 |
| 多用户平台化 | Phase 2 |

---

## 三、内置 Domain Profile（MVP）

| Profile | graph_structure | card_template | 教学步骤 |
|---------|---------------|---------------|---------|
| **general** | network | default_card | 介绍 → 讲解 → 举例 → 问答 → 评估 |
| **math** | strict_dag | math_card（含 KaTeX） | 概念 → 公式 → 例题 → 练习 → 评估 |
| **programming** | lattice | programming_card（含 Monaco） | Demo → 讲解 → 动手 → Debug → 评估 |

用户创建学习路径时，系统自动检测或手动选择 Domain。

---

## 四、Learner Profile（MVP）

MVP 用固定默认值，不做参数面板：

```json
{
  "abstraction_level": 0.5,
  "analogy_density": 0.5,
  "teaching_speed": 0.5,
  "feedback_tone": 0.5,
  "quiz_style": 0.5
}
```

JSON 配置文件可改，但 UI 调节面板 Phase 1 再做。

---

## 五、验收标准

### 5.1 核心流程验收

```
1. 用户注册登录
2. 创建学习路径：
   a. 输入 "Python 入门" → 系统自动从知识库/LLM 生成内容
   b. 上传一份 Python 教程 PDF → 系统提取知识点
3. 系统生成大纲 → 展示给用户
4. 用户确认大纲 → 开始学习
5. 逐节点学习：
   a. 知识卡片展示内容
   b. 用户可打字提问
   c. AI 教学回答
6. 完成节点 → 触发选择题评估
7. 答对 >= 60% → 节点标记完成，掌握度更新
8. 图谱节点颜色变化（红→黄→绿）
9. 所有节点完成 → 路径标记完成
```

### 5.2 技术验收

| 维度 | 标准 |
|------|------|
| 启动 | `docker compose up` 一键启动 |
| API | 所有端点返回正确状态码和格式 |
| 前端 | 无白屏/崩溃，移动端布局不破裂 |
| 对话 | WebSocket 实时回复，消息顺序正确 |
| 图谱 | 力导向图渲染正常，点击跳转正常 |
| 部署 | 单机即可运行（Ollama + 数据库都在本地） |

---

## 六、技术约束

| 项 | 约束 |
|----|------|
| Python | ≥3.11 |
| Node.js | ≥18 |
| PostgreSQL | ≥15 |
| Neo4j | ≥5 |
| Redis | ≥7 |
| Ollama | ≥0.3（建议 qwen2.5:7b 或以上） |
| Docker | ≥24 + Compose v2 |

---

## 七、目录结构（MVP）

```
edumind/
├── backend/
│   ├── app/
│   │   ├── api/              # REST 路由
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── learning_paths.py
│   │   │   ├── nodes.py
│   │   │   ├── progress.py
│   │   │   └── quiz.py
│   │   ├── core/             # 配置、依赖、DB 连接
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/           # SQLAlchemy + Pydantic 模型
│   │   │   ├── user.py
│   │   │   ├── path.py
│   │   │   ├── progress.py
│   │   │   └── quiz.py
│   │   ├── services/         # 业务逻辑
│   │   │   ├── content_pipeline.py
│   │   │   ├── syllabus.py
│   │   │   ├── teaching_engine.py
│   │   │   ├── knowledge_graph.py
│   │   │   └── assessment.py
│   │   ├── ws/               # WebSocket 处理
│   │   │   └── chat.py
│   │   ├── domain_profiles/  # YAML 配置
│   │   │   ├── general.yaml
│   │   │   ├── math.yaml
│   │   │   └── programming.yaml
│   │   ├── llm/              # LLM 适配器
│   │   │   ├── adapter.py
│   │   │   └── prompts.py
│   │   └── main.py
│   ├── tests/
│   ├── alembic/              # 数据库迁移
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── KnowledgeCard/
│   │   │   ├── KnowledgeGraph/
│   │   │   ├── ChatInterface/
│   │   │   └── common/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/         # API 调用
│   │   ├── stores/           # Zustand
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── data/                     # 用户数据挂载卷
```
