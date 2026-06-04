# CLAUDE.md — 项目规范指南

> 本文件定义了 EduMind 项目的编码规范、工具链配置和约束条件。
> AI 助手在生成代码时应自动遵循以下规则。

---

## 一、技术栈

| 层级 | 技术 | 版本约束 |
|------|------|---------|
| 后端 | Python FastAPI | ≥3.11 |
| 前端 | React 18 + TypeScript | Node.js 20 LTS（⚠️ 不要用 Node 25） |
| 知识图谱 | Neo4j 5 + vis-network | — |
| 数据库 | PostgreSQL 15+ + Redis 7 | — |
| AI | LiteLLM (DeepSeek / Ollama / OpenAI) | — |

## 二、后端规范

### 2.1 Python 版本

- 目标版本：**Python 3.11**
- 所有代码必须兼容 Python 3.11
- `datetime.UTC` 在部分 3.11 构建中不存在，统一使用 `datetime.timezone.utc`
- 不要在 Python 3.11 代码中使用 Python 3.12+ 语法（如 `type X = ...` 类型别名语句）

### 2.2 Ruff 规则

配置见 `pyproject.toml`：

```toml
[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B"]
ignore = ["B008", "UP017"]
```

| 规则 | 含义 | 说明 |
|------|------|------|
| E501 | 行超长 | 超过 120 字符，非 100 |
| I001 | import 分组 | 标准库 → 第三方 → 本地，组间空行 |
| F401 | 未使用的 import | 不允许顶层未使用导入 |
| B008 | Depends() 默认参数 | 🔇 已忽略——FastAPI 标准写法 |
| UP017 | datetime.UTC | 🔇 已忽略——兼容 Python 3.11 |

### 2.3 Mypy 配置

```toml
[tool.mypy]
implicit_optional = true
disable_error_code = ["var-annotated", "union-attr", "return-value", "arg-type", "index", "assignment", "misc"]
```

### 2.4 Import 格式

必须按以下顺序分组，组间空行：

```python
# 标准库
import json
from datetime import datetime

# 第三方
from fastapi import APIRouter
from sqlalchemy import select

# 本地
from app.models.user import User
from app.core.database import get_db
```

### 2.5 FastAPI 路由规范

- `Depends(get_db)` 作为函数参数默认值 — ✅ 这是 FastAPI 标准写法，B008 已忽略
- 不要在 `Depends()` 外面再套函数
- 异步路由使用 `async def`

### 2.6 LLM 调用

- 默认 `max_tokens=4096`（教学和出题场景）
- 知识提取场景 `max_tokens=8192`
- `litellm.request_timeout = 30` 秒
- API Key 优先从管理员 Web UI 配置读取（`LLMAdapter.update_runtime_config()`）
- `.env` 文件作为回退

### 2.7 测试

```bash
# 运行全部测试
cd backend && python -m pytest tests/ -v

# 运行单元测试
cd backend && python -m pytest tests/unit -v
```

- 测试使用 `pytest` + `pytest-asyncio`（`asyncio_mode = auto`）
- Mock LLM 调用时使用 `pytest-mock`
- 新增功能应同步补充测试用例

---

## 三、前端规范

### 3.1 Node.js 版本

⚠️ **必须使用 Node.js 20 LTS**，Node.js 25+ 与 Vite 5 不兼容。

```bash
nvm install 20
nvm use 20
```

### 3.2 TypeScript

- 项目已配置 `strict: true`，但关闭了 `noUnusedLocals/noUnusedParameters`
- `vis-data` 的 `DataSet` 类型不兼容时使用 `as any` 断言
- 新代码尽可能加上显式类型标注
- 使用 `import type` 导入仅类型

### 3.3 组件规范

- 知识卡片组件位于 `frontend/src/components/KnowledgeCard/index.tsx`
- 知识图谱组件位于 `frontend/src/components/KnowledgeGraph/GraphView.tsx`
- 数据获取逻辑放在 `services/api.ts` 中
- 全局状态管理使用 Zustand（`stores/` 目录）
- 页面组件放在 `pages/` 目录，管理员页面在 `pages/admin/`

---

## 四、数据库规范

### 4.1 PostgreSQL

- 使用 `127.0.0.1` 而非 `localhost`（避免 IPv6 DNS 解析问题）
- 通过 `Base.metadata.create_all` 自动建表
- 迁移管理使用 Alembic（`alembic/versions/`）

### 4.2 Neo4j

- 连接使用 `bolt://127.0.0.1:7687` 而非 `bolt://localhost:7687`
- 约束通过 `scripts/init_neo4j.py` 初始化
- 异步驱动使用 `async for record in result:` 而非 `await result.fetch()`

---

## 五、自动格式化与 CI/CD

### 5.1 自动格式化

提交前运行以下命令自动修复格式问题：

```bash
ruff check --fix backend/   # 自动修复 lint
ruff format backend/        # 自动格式化代码
```

### 5.2 CI/CD

见 `.github/workflows/ci.yml`，包含三个 job：

| Job | 命令 | 说明 |
|-----|------|------|
| lint | `ruff check` + `mypy` | 代码风格和类型检查 |
| backend-test | `pytest` | 后端单元测试（含 PostgreSQL 服务容器） |
| frontend-build | `tsc` + `vite build` | 前端编译验证 |

---

## 六、关联文件

- **`AGENTS.md`** — AI 编码助手行为指南（必读）
- **`pyproject.toml`** — ruff/mypy/pytest 统一配置
- **`.github/workflows/ci.yml`** — CI/CD 完整流程

---

## 七、常见陷阱

| 问题 | 避免方式 |
|------|---------|
| `datetime.UTC` 不可用 | 用 `datetime.timezone.utc` |
| Node.js v25 与 Vite 冲突 | 强制使用 Node 20 LTS |
| Depends() 报 B008 | 已忽略，FastAPI 标准写法 |
| `result.fetch()` 参数缺失 | 用 `async for record in result:` |
| WebSocket 消息被丢弃 | `await connectChatWS()` 确保连接就绪再发消息 |
| `localhost` DNS 解析 | 用 `127.0.0.1` |
| LLM 响应被截断 | 教学/出题用 `max_tokens=4096`，提取用 `8192` |
| 字段名 `metadata` 保留字 | 用 `extra_data` 替代 |
