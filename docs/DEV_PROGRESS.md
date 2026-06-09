# EduMind 开发进度记录

> 最后更新: 2025-06-05
> 总提交数: 47 次

---

## 一、项目概况

| 项目 | 内容 |
|------|------|
| **项目名** | EduMind — 智能导师系统 |
| **架构** | Python FastAPI 后端 + React 18 + TypeScript 前端 |
| **数据库** | PostgreSQL 15+ (pgvector) + Neo4j 5 + Redis 7 |
| **AI** | LiteLLM (DeepSeek / Ollama / OpenAI) |
| **文档设计** | `docs/DESIGN.md` V2.0-FINAL |
| **工作目录** | `workspace-dir/` |

### 关键文件索引

| 文件 | 用途 |
|------|------|
| `docs/DESIGN.md` | 完整方案设计书（含路线图） |
| `docs/DEV_PROGRESS.md` | **本文件 — 开发进度记录** |
| `AGENTS.md` | AI 编码助手行为规范 |
| `CLAUDE.md` | 项目规范指南 |
| `docker-compose.yml` | 一键启动全栈服务 |
| `Makefile` | 通用开发命令 |

---

## 二、全部 47 次提交历史

```
21c5a2c Kokoro TTS 集成 — ONNX 本地语音合成
d3df351 MCP Client 集成 — 内置工具 + 外部 Server + LLM 工具调用
6d000a6 pgvector 语义搜索 — 双模式嵌入引擎 + 向量 API
5860dbb KnowledgeCard 域感知多模板 + dark模式适配
5f80f86 深色模式切换 — ThemeProvider + 深色/浅色开关
622f463 KaTeX LaTeX 公式渲染 — math/physics 域支持
f67c70f 后端 API 集成测试框架 + 3个测试模块
b392ac8 恢复 ConfigPage API Key placeholder 掩码提示
da66fa1 前端体验改进 — Toast集成/加载态统一/ConfigPage重构
63275ec 移除 Toast 未定义的 animate-slide-in Tailwind 类
f58e484 前端体验优化 — Toast通知/加载态/大纲自动跳转/测验自动滚动
3212525 消除 learning_paths.py 函数体内 import
83e80c3 消除函数体内 import — delete_user 导入提升
6bbbb4e 复查修复 — delete 404/path验证/死代码/Pydantic v2
56056e4 管理员知识图谱管理界面
209e211 复查修复 — QuizAttempt 提升至文件顶部
e3c9a05 导出复查修复 — 空f-string/文件名安全/导出UX反馈
3f2b0fa 导出报告测验次数修正
a1f5de1 学习报告导出 — Markdown 格式下载
640a544 复查修复 — 薄弱节点并发查询 + timedelta 去重
62316c1 学习报告 UI 补全 — 薄弱节点标题/概览卡片/指标双进度条
7c39cbe CI 前端编译修复 — 类型注解不匹配
22ec8be CI 修复 — cross_validation.py SearchResult 导入
9bfd67b 复查修复 — 弹窗错误遮挡 + 全完成节点复习加载
9298096 移除 DashboardPage 死导入 BookOpen
a37f796 前端体验优化 — 登录注册/Dashboard/导航/通用组件
549df58 间隔重复复习系统完善 — 闭环修复 + 复习模式 UI
08bdcef _learner_to_instruction 消除 O(n²) 冗余 normalize 调用
eb95504 Learner Profile 审查修复 — 死代码/import 位置/前端映射
53b7a42 Learner Profile 系统完善 — 嵌套结构 + 前端 5 组分段 UI
b8a5fd0 搜索/交叉验证测试修复 — async def + 空查询短路
4183c89 搜索编排审查修复 — 死代码/数据链/API 端点/分配逻辑
1ae5ad8 AI 搜索编排 + 交叉验证 — 多源搜索、置信评分、内容增强
150ca30 全模块审查修复 — 异步阻塞/上传安全/代码冗余/测试覆盖
67aa27b 语音模块单元测试 — ASR/TTS 可用性、大小限制、边界条件
f6db877 语音模块 — ASR + TTS 语音教学对话
eebfff2 扫尾阶段完成 — 拖拽上传/大纲排序/多题型/CLAUD.md 规范
099cce2 完善 8 项偏差修复 + Markdown 渲染 + Logo 集成
405aac8 修复 mypy 类型错误
d5fd66c CI 修复 mypy 命令行参数
cea905c CI 修复 datetime.UTC 兼容
697880b 修复 ruff 197 项错误
2ce7213 CI GitHub Actions 修复
eee51a7 CI PostgreSQL 健康检查修复
c069a8d tier-1 核心功能实现
b6d8085 英文 README + Docker 部署指南
d485af2 初始发布 v0.1.0
```

---

## 三、完成情况总表

### Phase 0：MVP（✅ 100%）

| 里程碑 | 状态 | 说明 |
|--------|------|------|
| P0.1 基础设施 | ✅ | FastAPI + PG + Neo4j + Redis + Docker Compose |
| P0.2 内容管道 | ✅ | 上传/主题 → LLM提取 → 图谱入库, 7个 Domain Profile |
| P0.3 教学引擎 | ✅ | 知识卡片 + 文字/语音对话, 按 domain_id 切换模板 |
| P0.4 评估+图谱 | ✅ | Quiz + 掌握度 + 进度追踪 + KG 可视化 |
| P0.5 整合打磨 | ✅ | 大纲拖拽 + 用户管理 + 全流程闭环 |

### Phase 1：V1.0（✅ 80%）

| 功能 | 状态 | 说明 |
|------|------|------|
| AI 搜索编排 + 交叉验证 | ✅ | duckduckgo/searxng 双 provider, 置信评分 |
| 语音交互 (ASR + TTS) | ✅ | Whisper + edge-tts/Kokoro, WebSocket 集成 |
| Learner Profile 系统 | ✅ | 嵌套结构, 5 组 UI, 4 预设, 兼容旧扁平 |
| 7 个内置 Domain Profile | ✅ | general/math/programming/language/history/physics/music |
| Tauri 桌面打包 | ⏸️ 搁置 | 下次重启后优先推进项之一 |

### Phase 2：V2.0（✅ 60%）

| 功能 | 状态 | 说明 |
|------|------|------|
| 间隔重复复习 | ✅ | 闭环修复 + 复习模式 UI |
| 学习报告 UI 补全 | ✅ | 概览卡片/双进度条/薄弱节点标题/柱状趋势图 |
| 学习报告导出 | ✅ | Markdown 下载 + 文件名安全 |
| pgvector 语义搜索 | ✅ | 双模式嵌入(local + litellm), 余弦相似度 |
| MCP Client 集成 | ✅ | 内置工具 + 外部 Server + LLM 工具调用 |
| Domain Profile 市场 | ❌ 未开始 | 社区贡献机制 |
| Web Component 发布 | ❌ 未开始 | 嵌入第三方网站 |

### Phase 3：平台化（❌ 0%）

| 功能 | 状态 |
|------|------|
| 多用户支持 | ❌ |
| 多人协作学习 | ❌ |
| 学习内容市场 | ❌ |

### 额外完成

| 功能 | 状态 | 说明 |
|------|------|------|
| 前端体验优化 | ✅ | Toast/LoadingSpinner/EmptyState/ErrorBanner |
| 深色模式切换 | ✅ | ThemeProvider + localStorage + 跟随系统 |
| KaTeX LaTeX 公式渲染 | ✅ | math/physics 域支持 $$块级 $行内 |
| KnowledgeCard 多模板 | ✅ | 语言/历史/编程域感知卡片 |
| 管理员知识图谱管理 | ✅ | 路径列表 + 节点编辑/删除 |
| Kokoro TTS | ✅ | ONNX 本地合成, 自动回退 edge-tts |
| 后端 API 集成测试 | ✅ | conftest + 3 测试模块 |
| CI 修复 | ✅ | 后端测试 + 前端编译 |

---

## 四、剩余待开发功能（按优先级排序）

### 🔴 高优先级（Phase 2 路线图）

| 编号 | 功能 | 设计文档 | 文件影响 | 预估工作量 | 说明 |
|------|------|---------|---------|-----------|------|
| **R1** | 🎙️ **VAD 语音活动检测** | §9.2-9.3 | `backend/app/services/voice.py` + `frontend/src/services/voice.ts` | ~3h | Silero VAD 自动检测语音开始/结束, 替代手动点击停止 |
| **R2** | 🔬 **Monaco 代码编辑器** | §11.1 | `frontend/src/components/KnowledgeCard/` + `package.json` | ~2-3h | Programming 域卡片内嵌代码编辑器, 可运行/修改示例代码 |
| **R3** | 📓 **掌握度快照表** | §12.2 | `backend/app/models/` + `backend/app/services/assessment.py` | ~2h | mastery_snapshots 表 + 定时快照 + 趋势 API |
| **R4** | 🛣️ **路径级 Learner Profile** | §12.2 | `backend/app/models/path.py` + `frontend/src/pages/SettingsPage.tsx` | ~1h | `learner_profile_override` 字段, 路径级覆盖全局画像 |
| **R5** | 🌐 **Web Component 发布** | §10.28 | `frontend/src/components/` + 构建配置 | ~4h | 学习卡片/进度条作为 Web Component 嵌入第三方网站 |

### 🟡 中优先级（Phase 1 搁置 + Phase 2）

| 编号 | 功能 | 预期工作量 | 说明 |
|------|------|-----------|------|
| **R6** | 🖥️ **Tauri 桌面打包** | ~4h | Tauri v2 桌面壳, 含托盘/自动更新/离线模式 |
| **R7** | 💻 **用户 model_config (用户级模型配置)** | ~2h | 允许用户单独选择自己的 LLM 模型 |

### 🟢 低优先级（Phase 3 + 增强）

| 编号 | 功能 | 预期工作量 | 说明 |
|------|------|-----------|------|
| R8 | 多用户支持/权限体系 | ~1天 | 团队空间/邀请码 |
| R9 | 多人协作学习 | ~2天 | 共享学习路径/实时进度同步 |
| R10 | 学习内容市场 | ~3天 | 发现/分享/评价学习路径 |
| R11 | Domain Profile 市场 | ~2天 | 用户上传/分享领域配置 |

---

## 五、关键技术指引

### 5.1 后端项目结构

```
backend/
├── app/
│   ├── api/             # 路由层（auth/learning_paths/nodes/quiz/progress/admin/search）
│   ├── core/            # 配置/数据库/安全
│   ├── domain_profiles/ # 7 个 YAML 领域配置
│   ├── llm/             # LLM 适配器 + 提示词管理
│   ├── models/          # SQLAlchemy 数据模型
│   ├── scripts/         # 初始化/种子数据脚本
│   ├── services/        # 业务服务层
│   │   ├── content_pipeline.py  # 内容管道
│   │   ├── cross_validation.py  # 交叉验证
│   │   ├── domain_profile.py    # 领域配置加载
│   │   ├── embedding.py         # 向量嵌入
│   │   ├── knowledge_graph.py   # Neo4j 图谱
│   │   ├── learner_profile.py   # 学习者画像归一化
│   │   ├── mcp_client.py        # MCP 客户端
│   │   ├── search_orchestrator.py # 搜索编排
│   │   ├── semantic_search.py   # 语义搜索(pgvector)
│   │   ├── syllabus.py          # 大纲生成
│   │   ├── teaching_engine.py   # 教学引擎
│   │   └── voice.py             # 语音(ASR+TTS)
│   └── ws/              # WebSocket 对话
├── tests/
│   ├── conftest.py      # 集成测试 Fixtures
│   ├── integration/     # API 集成测试
│   └── unit/            # 单元测试
└── requirements.txt
```

### 5.2 前端项目结构

```
frontend/src/
├── components/
│   ├── ChatInterface/
│   ├── KnowledgeCard/    # 多模板知识卡片
│   ├── KnowledgeGraph/   # 图谱可视化
│   └── common/           # Layout/Toast/LoadingSpinner/EmptyState/ErrorBanner
├── hooks/
│   └── useTheme.ts       # 深色模式
├── pages/
│   ├── admin/            # ConfigPage/UsersPage/KnowledgeGraphPage
│   ├── DashboardPage/LoginPage/RegisterPage/LearnPage/SettingsPage/
│   ├── ReportPage/SyllabusPage
├── services/
│   ├── api.ts            # axios + WebSocket
│   └── voice.ts          # 前端录音
└── stores/
    ├── useAuthStore.ts   # 认证状态
    └── useLearningStore.ts # 学习状态
```

### 5.3 核心服务模块职责

| 模块 | 文件 | 核心方法 |
|------|------|---------|
| 内容管道 | `content_pipeline.py` | `process_topic()`, `process_topic_with_search()`, `process_upload()` |
| 知识图谱 | `knowledge_graph.py` | `create_node()`, `update_node()`, `delete_node()`, `get_node()`, `get_path_nodes()` |
| 教学引擎 | `teaching_engine.py` | `teach_node()`, `answer_question()`, `request_extension()` |
| LLM 适配 | `adapter.py` | `chat()`, `teach_concept()`, `answer_question()`, `answer_with_tools()`, `_extract_tool_call()` |
| 评估 | `assessment.py` | `generate_quiz()`, `grade_quiz()`, `calculate_mastery()`, `compute_next_review()` |
| 语义搜索 | `semantic_search.py` | `index_node()`, `search()`, `delete_node_embeddings()` |
| 搜索编排 | `search_orchestrator.py` | `search()`, `parallel_search()` |
| 语音服务 | `voice.py` | `synthesize_speech()`, `transcribe_audio()` |

### 5.4 API 端点总览

```
/auth/register|login|me
/users/me
/learning-paths (CRUD + upload + with-search)
/nodes/{id} (GET + graph + start + complete)
/quiz/{id} (GET + submit)
/learning-paths/{id}/progress|report|report/export
/ws/chat?token=
/admin/users|config|stats|learning-paths|nodes|mcp/tools|mcp/call
/search?q=&path_id=&top_k=
/api/health
```

### 5.5 开发规范（详见 AGENTS.md + CLAUDE.md）

1. **Python 3.11 兼容** — 不使用 3.12+ 语法
2. **Ruff 规范** — line-length=120, import 分组（标准库→第三方→本地）
3. **Import 规范** — 函数体内禁止 `from app.xxx` 导入（已全部清理）
4. **注释/文档/commit** — 简体中文
5. **变量名/函数名** — 英文
6. **新增功能** — 同步补充测试用例
7. **CI 验证** — `ruff check` + `mypy` + `pytest` + `tsc && vite build`

### 5.6 测试情况

| 类型 | 文件 | 测试数 |
|------|------|--------|
| 单元测试 | `tests/unit/test_assessment.py` | 20+ |
| 单元测试 | `tests/unit/test_security.py` | 7 |
| 单元测试 | `tests/unit/test_syllabus.py` | 10+ |
| 单元测试 | `tests/unit/test_utils.py` | 30+ |
| 单元测试 | `tests/unit/test_voice.py` | 8 |
| 集成测试 | `tests/integration/test_health.py` | 1 |
| 集成测试 | `tests/integration/test_auth.py` | 8 |
| 集成测试 | `tests/integration/test_users.py` | 3 |

---

## 六、重启后快速恢复指令

```bash
# 1. 确认工作目录
cd workspace-dir

# 2. 查看当前分支和状态
git log --oneline -5 --no-color
git status

# 3. 阅读进度文档
cat docs/DEV_PROGRESS.md

# 4. 选择下一任务（参考第四章优先级 R1-R7）
#    推荐从 R1 VAD 语音检测开始

# 5. 如需启动服务测试（在部署机器上）
docker compose up -d postgres neo4j redis
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
```

---

## 七、注意事项

1. **配置文件** — `.env.example` 中有完整配置项说明，部署时需要复制为 `.env`
2. **数据库迁移** — 开发环境自动建表 (`Base.metadata.create_all`)，pgvector 扩展在 `lifespan` 中自动初始化
3. **N+1 查询** — `admin.py` 的 `list_users()` 有 N+1（每用户查路径数），但分页限制 50 条可接受，未优化
4. **后端 Docker** — Dockerfile 在 `backend/Dockerfile`，生产部署用 `docker compose up -d`
5. **前端构建** — `cd frontend && npm run build` 输出到 `dist/`
