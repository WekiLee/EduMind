# EduMind 开发进度记录

> 最后更新: 2025-06-04
> 总提交数: 59 次
> 实际 vs 文档: 已同步更新

---

## 一、项目概况

| 项目 | 内容 |
|------|------|
| **项目名** | EduMind — 智能导师系统 |
| **架构** | Python FastAPI 后端 + React 18 + TypeScript 前端 |
| **数据库** | PostgreSQL 15+ (pgvector) + Neo4j 5 + Redis 7 |
| **AI** | LiteLLM (DeepSeek / Ollama / OpenAI) |
| **文档设计** | `docs/DESIGN.md` V2.0-FINAL |
| **工作目录** | `H:\Personally.Storage\workspace-dir` |
| **总提交数** | 59 次 |

---

## 二、核心能力清单完成度 (§1.3 的 11 项)

| # | 能力 | 状态 | 备注 |
|---|------|------|------|
| 1 | 📚 混合内容采集 | ✅ | 上传 + 搜索 + 交叉验证 |
| 2 | 🧠 领域自动识别 | ✅ | LLM 推断 + 7 个 Domain Profile |
| 3 | 🗂️ 智能大纲生成 | ✅ | 拓扑排序 + 拖拽调整 |
| 4 | 📖 知识卡片教学 | ✅ | KaTeX + Monaco + 多模板 |
| 5 | 💬 双模交互 | ✅ | 文字/语音 + VAD + 唤醒 |
| 6 | 🔗 可视化知识图谱 | ✅ | vis-network + 掌握度着色 |
| 7 | 👤 学习者画像 | ✅ | 嵌套 + 5组UI + 预设 + 路径覆盖 |
| 8 | 📊 学习评估 | ✅ | 测验 + 掌握度 + 复习 + 快照 |
| 9 | 🔌 AI 自由配置 | ✅ | 系统级 + 用户级 |
| 10 | 🔧 MCP 集成 | ✅ | 内置工具 + 外部 Server |
| 11 | 📦 跨平台 | ⚠️ | Docker 完成, Tauri 搁置 |

**完成: 10.5/11 项**

---

## 三、完成情况

### Phase 0 MVP (100%)

| 里程碑 | 状态 |
|--------|------|
| P0.1 基础设施 | ✅ |
| P0.2 内容管道 | ✅ |
| P0.3 教学引擎 | ✅ |
| P0.4 评估+图谱 | ✅ |
| P0.5 整合打磨 | ✅ |

### Phase 1 V1.0 (~85%)

| 功能 | 状态 |
|------|------|
| AI 搜索编排 + 交叉验证 | ✅ |
| 语音交互 (ASR+TTS) | ✅ |
| Learner Profile 系统 | ✅ |
| 7 个 Domain Profile | ✅ |
| Tauri 桌面打包 | ⏸️ 搁置 |

### Phase 2 V2.0 (~75%)

| 功能 | 状态 |
|------|------|
| 间隔重复复习 | ✅ |
| 学习报告 UI 补全 | ✅ |
| 学习报告导出 | ✅ |
| pgvector 语义搜索 | ✅ |
| MCP Client 集成 | ✅ |
| Web Component 发布 | ❌ |
| Domain Profile 市场 | ❌ |

### Phase 3 (0%)

全部未开始: 多用户/协作/内容市场

### 额外完成

| 功能 | 状态 |
|------|------|
| VAD 语音活动检测 | ✅ |
| Monaco 代码编辑器 | ✅ |
| 掌握度快照表 + 趋势 API | ✅ |
| 路径级 Learner Profile | ✅ |
| 用户级模型配置 | ✅ |
| 语音唤醒模式 | ✅ |
| 深色模式切换 | ✅ |
| KaTeX LaTeX 渲染 | ✅ |
| 管理员知识图谱管理 | ✅ |
| Kokoro TTS | ✅ |
| API 集成测试 | ✅ |

---

## 四、剩余功能

| 功能 | 工作量 | 优先级 |
|------|--------|--------|
| Tauri 桌面打包 | ~4h | 🟡 |
| Web Component 发布 | ~4h | 🟡 |
| Domain Profile 市场 | ~2天 | 🟢 |
| 多用户/权限体系 | ~1天 | 🟢 |
| 多人协作学习 | ~2天 | 🟢 |
| 学习内容市场 | ~3天 | 🟢 |

### 设计文档中有但未跟踪

| 项目 | 位置 |
|------|------|
| KnowledgeNode.quiz_questions 字段 | §12.1 |
| chat_sessions.user_rating 字段 | §12.2 |
| MCP Python SDK 标准集成 | §11.1 |

---

## 五、项目结构

### 后端 (15 个服务)

```
backend/app/services/
  content_pipeline.py   交叉验证
  embedding.py          向量嵌入
  knowledge_graph.py    Neo4j 图谱
  learner_profile.py    画像归一化
  mcp_client.py         MCP 客户端
  search_orchestrator.py 搜索编排
  semantic_search.py    pgvector 搜索
  syllabus.py           大纲生成
  teaching_engine.py    教学引擎
  voice.py              语音 (ASR+TTS)
  assessment.py         评估引擎
  domain_profile.py     领域配置加载
```

### API 端点

```
/auth/register|login|me
/users/me
/learning-paths (CRUD + upload + with-search + profile-override)
/nodes/{id} (GET + graph + start + complete)
/quiz/{id} (GET + submit)
/learning-paths/{id}/progress|report|report/export|report/trend
/ws/chat?token=
/admin/users|config|stats|learning-paths|nodes|mcp/tools|mcp/call
/search?q=&path_id=&top_k=
/api/health
```

---

## 六、开发规范

- Python 3.11, Ruff line-length=120
- import 分组: 标准库 -> 第三方 -> 本地
- 函数体内禁止 from app.xxx 导入
- 注释/commit 用简体中文, 变量名用英文
- CI: ruff check + mypy + pytest + tsc && vite build

---

## 七、测试

| 文件 | 数量 |
|------|------|
| test_assessment.py | 14 |
| test_security.py | 7 |
| test_syllabus.py | 8 |
| test_utils.py | 30+ |
| test_voice.py | 8 |
| test_health.py (集成) | 1 |
| test_auth.py (集成) | 8 |
| test_users.py (集成) | 3 |

---

## 八、重启恢复

```bash
cd H:\Personally.Storage\workspace-dir
git log --oneline -5
type docs\DEV_PROGRESS.md
```
