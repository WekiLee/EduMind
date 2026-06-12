# EduMind MVP 测试框架

> 本文档定义 MVP 阶段的测试策略：测试层次、覆盖率目标、场景用例、运行方式。
> 所有测试基于 pytest（后端）和 vitest + Playwright（前端），可在 Windows 开发环境直接运行。

---

## 一、测试金字塔

```
         ╱  E2E  ╲           ← 2-3 条关键流程
        ╱─────────╲
       ╱  集成测试  ╲         ← API 端点全覆盖
      ╱─────────────╲
     ╱    单元测试     ╲       ← Service 层核心逻辑
    ╱───────────────────╲
   ╱    静态分析 + 类型检查  ╲  ← mypy / ruff / tsc
```

### 每层目标

| 层 | 框架 | 覆盖率目标 | 运行时间 |
|----|------|-----------|---------|
| **单元测试** | pytest | Service 层 ≥ 85% | <30s |
| **集成测试** | pytest + httpx.AsyncClient | API 端点 100% | <2min |
| **E2E 测试** | Playwright（可选） | 3 条关键流程 | <5min |
| **静态分析** | mypy + ruff + tsc | — | <30s |

---

## 二、测试目录结构

```
backend/
├── tests/
│   ├── conftest.py              # 共享 fixtures（DB session、client、LLM mock）
│   ├── factories.py             # 测试数据工厂（UserFactory、PathFactory...）
│   ├── mock_llm.py              # LLM 返回 mock 数据
│   │
│   ├── unit/                    # 单元测试
│   │   ├── test_content_pipeline.py
│   │   ├── test_syllabus.py
│   │   ├── test_teaching_engine.py
│   │   ├── test_knowledge_graph.py
│   │   ├── test_assessment.py
│   │   └── test_security.py     # JWT / 密码哈希
│   │
│   ├── integration/             # 集成测试
│   │   ├── test_auth.py
│   │   ├── test_users.py
│   │   ├── test_learning_paths.py
│   │   ├── test_nodes.py
│   │   ├── test_progress.py
│   │   ├── test_quiz.py
│   │   └── test_chat_ws.py      # WebSocket
│   │
│   └── e2e/                     # 端到端测试（可选，依赖前端）
│       └── test_full_flow.py
│
├── pytest.ini
└── .coveragerc

frontend/
├── src/
│   └── __tests__/
│       ├── components/           # 组件测试（vitest + testing-library）
│       ├── hooks/                # Hook 测试
│       ├── stores/               # Store 测试
│       └── utils/                # 工具函数测试
├── e2e/                          # Playwright E2E
│   └── specs/
└── vitest.config.ts
```

---

## 三、Fixtures 设计（conftest.py）

### 3.1 数据库 Fixtures

```python
# backend/tests/conftest.py

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.database import get_db
from app.main import app

# ── 测试数据库 ──
TEST_DATABASE_URL = "postgresql+asyncpg://edumind:edumind_dev@localhost:5432/edumind_test"

@pytest.fixture(scope="session")
def event_loop():
    """每个测试 session 一个事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session():
    """每个测试独立的事务，测试结束后回滚"""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        async with AsyncSession(conn) as session:
            yield session
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def client(db_session):
    """FastAPI 测试客户端，使用测试 DB"""
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

# ── Neo4j 测试容器（可选，需安装 testcontainers）──
# MVP 阶段可以用 Mock 替代 Neo4j 操作

@pytest.fixture
async def neo4j_mock(mocker):
    """Mock Neo4j 驱动"""
    mock = mocker.patch("app.services.knowledge_graph.Neo4jDriver")
    mock.return_value.run.return_value = []
    return mock
```

### 3.2 LLM Mock

```python
# backend/tests/mock_llm.py

"""
LLM Mock：所有测试用固定响应替代真实模型调用。
确保测试可重复、快速、不依赖外部服务。
"""

MOCK_EXTRACT_RESPONSE = {
    "nodes": [
        {
            "title": "什么是变量",
            "summary": "变量是存储数据的容器",
            "content": "# 变量\n\n在 Python 中，变量是用于存储数据的容器。",
            "difficulty": "intro",
            "node_type": "concept",
            "examples": ["x = 10", "name = 'Alice'"]
        },
        {
            "title": "数据类型",
            "summary": "Python 有 int、float、str、bool 等基本类型",
            "content": "# 数据类型\n\nPython 有动态类型系统...",
            "difficulty": "intro",
            "node_type": "concept",
            "examples": ["isinstance(10, int)  # True"]
        },
    ],
    "relations": [
        {"from": "什么是变量", "to": "数据类型", "type": "PREREQUISITE"}
    ],
    "modules": [
        {"name": "基础概念", "order": 1, "node_titles": ["什么是变量", "数据类型"]}
    ]
}

MOCK_QUIZ_RESPONSE = {
    "questions": [
        {
            "id": "q1",
            "type": "multiple_choice",
            "question": "Python 中哪个关键字用于定义变量？",
            "options": ["A. var", "B. let", "C. 不需要关键字", "D. def"],
            "answer": "C"
        }
    ]
}

MOCK_TEACHING_RESPONSE = "变量是存储数据的容器。在 Python 中，你不需要像其他语言那样声明类型，直接赋值即可。"


@pytest.fixture
def mock_llm_extract(mocker):
    """Mock LLM 内容提取"""
    mock = mocker.patch("app.services.content_pipeline.LLMAdapter.extract_knowledge")
    mock.return_value = MOCK_EXTRACT_RESPONSE
    return mock

@pytest.fixture
def mock_llm_quiz(mocker):
    """Mock LLM 出题"""
    mock = mocker.patch("app.services.assessment.LLMAdapter.generate_quiz")
    mock.return_value = MOCK_QUIZ_RESPONSE
    return mock

@pytest.fixture
def mock_llm_teach(mocker):
    """Mock LLM 教学回答"""
    mock = mocker.patch("app.services.teaching_engine.LLMAdapter.teach")
    mock.return_value = MOCK_TEACHING_RESPONSE
    return mock
```

### 3.3 数据工厂

```python
# backend/tests/factories.py

import uuid
from datetime import datetime
from app.models.user import User
from app.models.path import LearningPath

class UserFactory:
    @staticmethod
    def create(**kwargs) -> dict:
        return {
            "id": kwargs.get("id", uuid.uuid4()),
            "name": kwargs.get("name", "测试用户"),
            "email": kwargs.get("email", f"test{uuid.uuid4().hex[:6]}@example.com"),
            "password_hash": kwargs.get("password_hash", "$2b$12$..."),
            "domain_id": kwargs.get("domain_id", "general"),
            "learner_profile": kwargs.get("learner_profile", {}),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
        }

class LearningPathFactory:
    @staticmethod
    def create(**kwargs) -> dict:
        return {
            "id": kwargs.get("id", uuid.uuid4()),
            "user_id": kwargs.get("user_id", uuid.uuid4()),
            "topic": kwargs.get("topic", "Python 入门"),
            "domain_id": kwargs.get("domain_id", "programming"),
            "syllabus": kwargs.get("syllabus", []),
            "status": kwargs.get("status", "active"),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
        }
```

---

## 四、单元测试场景

### 4.1 content_pipeline

| 测试 | 输入 | 预期 |
|------|------|------|
| `test_extract_from_text` | 一段 Python 教程文本 | 返回结构化知识节点列表 |
| `test_extract_with_relations` | 含依赖关系的文本 | 节点间含 PREREQUISITE 关系 |
| `test_extract_empty` | 空字符串 | 抛出 ValueError |
| `test_upload_file_pdf` | PDF 文件 | 提取文本成功 |
| `test_upload_file_unsupported` | .exe 文件 | 返回 400 错误 |
| `test_domain_detection` | "学微积分" | domain_id = "math" |
| `test_domain_detection_default` | 无明确领域提示 | domain_id = "general" |

### 4.2 syllabus

| 测试 | 输入 | 预期 |
|------|------|------|
| `test_topological_sort` | 带依赖的节点列表 | 输出满足所有前置约束 |
| `test_topological_sort_cycle` | 含循环依赖 | 抛出 CycleDetectedError |
| `test_module_grouping` | 排序后的节点 | 正确分入对应模块 |
| `test_syllabus_empty` | 空列表 | 返回空大纲 |
| `test_syllabus_single_node` | 1 个节点 | 单模块单节点 |

### 4.3 teaching_engine

| 测试 | 输入 | 预期 |
|------|------|------|
| `test_teach_node` | 节点 + Domain Profile | 返回教学内容文本 |
| `test_answer_question` | 学生提问 + 上下文 | 返回相关回答 |
| `test_request_extension` | 延伸请求 | 返回延伸内容 + 关联节点 |
| `test_teach_with_domain_profile` | math 领域节点 | 内容含 LaTeX 公式 |
| `test_max_context_length` | 超长对话历史 | 自动截断，无异常 |

### 4.4 knowledge_graph

| 测试 | 输入 | 预期 |
|------|------|------|
| `test_create_node` | 节点数据 | Neo4j 中创建成功 |
| `test_create_relation` | 两个节点 + 关系类型 | 关系创建成功 |
| `test_get_prerequisites` | 节点 ID | 返回所有前置节点 |
| `test_get_subgraph` | 节点 ID | 返回 2 层子图 |
| `test_delete_path_graph` | path_id | 所属节点和关系全部删除 |

### 4.5 assessment

| 测试 | 输入 | 预期 |
|------|------|------|
| `test_generate_quiz` | 节点内容 | 返回合法题目列表 |
| `test_submit_quiz_all_correct` | 全对答案 | score=1.0 |
| `test_submit_quiz_all_wrong` | 全错答案 | score=0.0 |
| `test_submit_quiz_partial` | 部分正确 | 0 < score < 1 |
| `test_calculate_mastery` | 多次 quiz 成绩 | mastery 加权计算正确 |
| `test_quiz_type_by_domain` | math 领域 | 题目含计算题 |

### 4.6 security

| 测试 | 输入 | 预期 |
|------|------|------|
| `test_password_hash` | 明文密码 | 哈希值 ≠ 明文 |
| `test_password_verify_correct` | 正确密码 | 验证通过 |
| `test_password_verify_wrong` | 错误密码 | 验证失败 |
| `test_jwt_create` | user_id | 返回有效 token |
| `test_jwt_decode_valid` | 有效 token | 返回原始 user_id |
| `test_jwt_decode_expired` | 过期 token | 抛出 JWTError |
| `test_jwt_decode_tampered` | 篡改 token | 抛出 JWTError |

---

## 五、集成测试场景

### 5.1 Auth API

| 测试 | 方法 | 端点 | 预期状态码 |
|------|------|------|-----------|
| 注册成功 | POST | /auth/register | 201 |
| 重复邮箱 | POST | /auth/register | 409 |
| 密码太短 | POST | /auth/register | 422 |
| 登录成功 | POST | /auth/login | 200 |
| 密码错误 | POST | /auth/login | 401 |
| 获取当前用户 | GET | /auth/me | 200 |
| 无 Token 访问 | GET | /auth/me | 401 |

### 5.2 Learning Paths API

| 测试 | 方法 | 端点 | 预期 |
|------|------|------|------|
| 通过 Topic 创建 | POST | /learning-paths | 202（异步） |
| 通过文件上传创建 | POST | /learning-paths | 202 |
| 列出路径 | GET | /learning-paths | 200 + 分页 |
| 获取路径详情 | GET | /learning-paths/{id} | 200 |
| 更新大纲（拖拽） | PATCH | /learning-paths/{id} | 200 |
| 删除路径 | DELETE | /learning-paths/{id} | 204 |
| 访问不存在的路径 | GET | /learning-paths/invalid | 404 |
| 访问他人路径 | GET | /learning-paths/{other_id} | 403 |

### 5.3 Nodes API

| 测试 | 方法 | 端点 | 预期 |
|------|------|------|------|
| 获取节点内容 | GET | /nodes/{id} | 200 |
| 获取节点子图 | GET | /nodes/{id}/graph | 200 + nodes + edges |
| 不存在的节点 | GET | /nodes/invalid | 404 |

### 5.4 Progress API

| 测试 | 方法 | 端点 | 预期 |
|------|------|------|------|
| 获取路径进度 | GET | /learning-paths/{id}/progress | 200 |
| 开始学习节点 | POST | /nodes/{id}/start | 200 → status=learning |
| 完成节点（未开始） | POST | /nodes/{id}/complete | 400 |
| 重复完成节点 | POST | /nodes/{id}/complete | 200（幂等） |

### 5.5 Quiz API

| 测试 | 方法 | 端点 | 预期 |
|------|------|------|------|
| 生成测验 | POST | /nodes/{id}/quiz | 200 + 题目列表 |
| 提交正确答案 | POST | /quiz/{id}/submit | 200 + passed=true |
| 提交错误答案 | POST | /quiz/{id}/submit | 200 + passed=false |
| 提交不存在的 quiz | POST | /quiz/invalid/submit | 404 |

### 5.6 WebSocket Chat

| 测试 | 操作 | 预期 |
|------|------|------|
| 连接成功 | ws connect | 收到 `{"type": "connected"}` |
| 发送消息 | send message | 收到流式 teaching_chunk |
| 请求延伸 | send type=extend | 收到 extension 响应 |
| 请求评估 | send type=request_quiz | 收到 quiz 响应 |
| 无 Token 连接 | ws connect no token | 连接被拒绝 |
| 发送空消息 | send empty content | 收到 error 响应 |

---

## 六、E2E 场景（MVP 核心流程）

> 使用 Playwright + 真实后端（可 mock LLM）。MVP 阶段可选，建议持续集成中运行。

### 场景 1：用户通过主题创建并完成学习

```
1. 注册新用户
2. 创建学习路径（mode=topic, "Python 入门"）
3. 等待内容处理完成
4. 确认大纲
5. 进入第一个节点学习
6. 阅读知识卡片
7. 打字提问 → 收到回答
8. 完成节点 → 触发测验
9. 答题 → 通过 → 掌握度更新
10. 图谱节点变为绿色
11. 继续下一节点
12. 全部完成后路径标记完成
```

### 场景 2：用户上传文件学习

```
1. 登录已有用户
2. 上传 PDF 文件
3. 系统提取知识点
4. 展示大纲
5. 用户手动调整节点顺序
6. 确认 → 开始学习
```

### 场景 3：边界情况

```
1. 上传空文件 → 收到错误提示
2. 同时创建两个学习路径 → 互不影响
3. 学习中途刷新页面 → 状态保持
4. 所有题目答错 → 提示复习，不通过节点
5. 删除路径 → 所有数据清除
```

---

## 七、Mock 策略

| 外部依赖 | Mock 方式 | 说明 |
|---------|----------|------|
| **LLM（Ollama/OpenAI）** | pytest mock 替换 adapter 返回值 | 所有单元测试不依赖真实模型 |
| **Neo4j** | MVP 用 `testcontainers` 或在 PG 中用 JSON 字段模拟 | 完整版依赖真实 Neo4j 容器 |
| **PostgreSQL** | 独立 test 数据库 `edumind_test` | 每个测试独立事务，自动回滚 |
| **Redis** | `fakeredis` 库 | 纯 Python 实现，无需 Redis 进程 |
| **文件系统** | `tmp_path` fixture（pytest 内置） | 临时目录，测试后自动清理 |

---

## 八、测试运行方式

```bash
# ── 后端 ──

# 安装测试依赖
pip install pytest pytest-asyncio pytest-mock pytest-cov httpx fakeredis

# 运行全部测试
pytest backend/tests/ -v

# 运行某一层
pytest backend/tests/unit/ -v
pytest backend/tests/integration/ -v

# 带覆盖率报告
pytest backend/tests/ -v --cov=app --cov-report=term --cov-report=html:coverage_report

# 运行单个测试文件
pytest backend/tests/unit/test_syllabus.py -v

# 运行单个测试
pytest backend/tests/unit/test_syllabus.py::test_topological_sort -v

# 跳过需要 Neo4j 的测试
pytest backend/tests/ -v -m "not neo4j"


# ── 前端 ──

# 安装依赖
cd frontend && npm install

# 运行组件测试
npm run test

# 运行 E2E 测试（需要后端运行）
npm run test:e2e
```

---

## 九、覆盖率目标

| 模块 | 单元测试覆盖率 | 说明 |
|------|-------------|------|
| `services/content_pipeline.py` | ≥ 85% | 核心内容管线，覆盖所有分支 |
| `services/syllabus.py` | ≥ 90% | 拓扑排序必须完全覆盖，含循环检测 |
| `services/teaching_engine.py` | ≥ 80% | 对话管理 + 领域路由 |
| `services/knowledge_graph.py` | ≥ 75% | Neo4j 操作，覆盖 CRUD + 查询 |
| `services/assessment.py` | ≥ 85% | 出题 + 判卷 + 掌握度计算 |
| `core/security.py` | ≥ 95% | 密码哈希 + JWT，安全关键 |
| `api/*.py` | 100%（集成测试） | 每个端点至少一个成功 + 一个失败场景 |

---

## 十、CI 集成建议

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: edumind_test
          POSTGRES_USER: edumind
          POSTGRES_PASSWORD: edumind_dev
        ports:
          - 5432:5432
      neo4j:
        image: neo4j:5
        env:
          NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-edumind_dev}
        ports:
          - 7687:7687

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r backend/requirements.txt
      - run: pip install pytest pytest-asyncio pytest-mock pytest-cov httpx
      - run: pytest backend/tests/ -v --cov=app
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd frontend && npm install && npm run test
```
