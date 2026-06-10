# MVP API 契约

> FastAPI REST API + WebSocket 协议定义

---

## 一、通用约定

| 项 | 规范 |
|----|------|
| **基础路径** | `/api/v1` |
| **认证** | JWT Bearer Token（除 auth 端点外全部需要） |
| **请求体** | `application/json` |
| **响应格式** | 成功：`{"data": ...}` 失败：`{"detail": "message"}` |
| **分页** | `?page=1&size=20` → `{"data": [...], "total": 100, "page": 1, "size": 20}` |

> 兼容入口：`/health`、`/assessment`、`/analytics` 也可访问，但业务集成推荐使用 `/api/v1` 前缀。

---

## 二、Health / Assessment / Analytics

### GET /health

健康检查。兼容路径：`/api/health`。

```json
// Response 200
{ "status": "ok", "version": "0.1.0" }
```

### POST /api/v1/assessment

兼容性评估入口，要求登录用户只能提交自己的 `user_id`。该接口只统计非零答案数量，未经过题目难度、标准答案和公平性校准，不得单独用于高影响教育决策。

```json
// Request
{
  "user_id": "u_001",
  "subject": "Mathematics",
  "answers": [1, 0, 2, 1, 3, 0, 2, 1, 0, 3]
}

// Response 200
{
  "data": {
    "user_id": "u_001",
    "subject": "Mathematics",
    "score": 7,
    "total": 10,
    "percentage": 70.0,
    "difficulty_level": "intermediate",
    "timestamp": "2026-06-09T09:00:00+00:00",
    "assessment_method": "compatibility_count_positive_answers",
    "calibrated": false,
    "confidence": "low",
    "interpretation": "该兼容接口仅统计非零答案数量，不代表经过校准的真实能力评估。",
    "fairness_note": "结果不得单独用于分班、升学、奖惩等高影响教育决策。",
    "recommendation": "建议继续当前难度，并补充针对性练习。"
  }
}
```

### GET /api/v1/analytics

当前用户学习分析摘要。

```json
// Response 200
{
  "data": {
    "total_paths": 2,
    "completed_paths": 1,
    "total_nodes": 20,
    "completed_nodes": 12,
    "progress_pct": 60.0,
    "overall_mastery": 0.72,
    "total_quizzes": 8,
    "average_quiz_score": 0.76
  }
}
```

## 三、Auth

### POST /api/v1/auth/register

注册新用户。

```json
// Request
{ "name": "string", "email": "string", "password": "string" }

// Response 201
{ "data": { "id": "uuid", "name": "string", "email": "string", "created_at": "iso8601" } }
```

### POST /api/v1/auth/login

```json
// Request
{ "email": "string", "password": "string" }

// Response 200
{ "data": { "access_token": "string", "token_type": "bearer", "user": { ... } } }
```

### GET /api/v1/auth/me

```json
// Response 200
{ "data": { "id": "uuid", "name": "string", "email": "string", "learner_profile": {...}, "created_at": "iso8601" } }
```

---

## 四、Users

### PATCH /api/v1/users/me

更新用户信息（包括 learner_profile 和个人模型配置）。

```json
// Request
{
  "name": "string?",
  "learner_profile": {...}?,
  "model_config": {
    "provider": "openai-compatible?",
    "model": "deepseek-chat?",
    "api_base": "https://api.example.com/v1?",
    "api_key": "string?"
  }
}

// Response 200
{ "data": { ... } }
```

`model_config.api_key` 省略表示保留旧密钥；传入空字符串或 `null` 表示清空个人密钥。响应中只返回 `api_key_masked`，不会返回明文密钥。

---

## 五、Learning Paths

### POST /api/v1/learning-paths

创建学习路径。两种模式：

**模式 A：指定主题（LLM 生成内容）**

```json
// Request
{
  "mode": "topic",
  "topic": "Python 入门",
  "domain_id": "programming",
  "depth": "intermediate"
}

// Response 202 → 异步处理
{
  "data": {
    "id": "uuid",
    "topic": "Python 入门",
    "domain_id": "programming",
    "status": "processing",
    "created_at": "iso8601"
  }
}
```

之后通过 WebSocket 或轮询 `GET /api/v1/learning-paths/{id}` 获取进度。

**模式 B：上传文件**

```json
// Request (multipart/form-data)
{
  "mode": "upload",
  "files": [File...],
  "domain_id": "programming"
}

// Response 202 → 同上
```

### GET /api/v1/learning-paths

用户的学习路径列表。

```json
// Response
{
  "data": [
    {
      "id": "uuid",
      "topic": "Python 入门",
      "domain_id": "programming",
      "status": "active" | "processing" | "completed" | "archived",
      "progress": 0.55,
      "node_count": 20,
      "completed_count": 11,
      "created_at": "iso8601"
    }
  ],
  "total": 5
}
```

### GET /api/v1/learning-paths/{path_id}

路径详情 + 大纲。

```json
// Response
{
  "data": {
    "id": "uuid",
    "topic": "Python 入门",
    "domain_id": "programming",
    "status": "active",
    "syllabus": [
      {
        "module_name": "基础概念",
        "order": 1,
        "nodes": [
          { "id": "neo4j-node-uuid", "title": "什么是变量", "difficulty": "intro", "status": "completed" },
          { "id": "...", "title": "数据类型", "difficulty": "intro", "status": "learning" }
        ]
      },
      {
        "module_name": "流程控制",
        "order": 2,
        "nodes": [...]
      }
    ],
    "created_at": "iso8601"
  }
}
```

### PATCH /api/v1/learning-paths/{path_id}

更新大纲（用户拖拽调整顺序）。

```json
// Request
{
  "syllabus": [
    { "module_name": "基础概念", "order": 1, "node_ids": ["id1", "id3", "id2"] },
    ...
  ]
}

// Response 200
{ "data": { ... } }
```

### DELETE /api/v1/learning-paths/{path_id}

```json
// Response 204
```

---

## 六、Knowledge Nodes

### GET /api/v1/nodes/{node_id}

获取节点完整内容（按 Domain Profile 渲染）。

```json
// Response
{
  "data": {
    "id": "neo4j-node-uuid",
    "title": "什么是变量",
    "summary": "变量是存储数据的容器...",
    "content": "# 变量\n\n在 Python 中，变量是...",
    "difficulty": "intro",
    "domain_id": "programming",
    "node_type": "concept",
    "examples": [
      { "title": "示例1", "content": "x = 10" }
    ],
    "code_snippets": [
      { "language": "python", "code": "x = 10\nprint(x)" }
    ],
    "ref_links": ["https://..."],
    "prerequisites": [
      { "id": "...", "title": "Python 环境安装" }
    ],
    "related_nodes": [
      { "id": "...", "title": "数据类型", "relation": "next" }
    ]
  }
}
```

### GET /api/v1/nodes/{node_id}/graph

获取以该节点为中心的图谱子图（用于卡片底部的图谱视图）。

```json
// Response 200
{
  "data": {
    "nodes": [
      { "id": "...", "title": "变量", "difficulty": "intro", "mastery": 0.8, "status": "completed" },
      { "id": "...", "title": "数据类型", "difficulty": "intro", "mastery": 0.3, "status": "learning" }
    ],
    "edges": [
      { "source": "id1", "target": "id2", "type": "prerequisite" },
      { "source": "id1", "target": "id3", "type": "related" }
    ]
  }
}
```

---

## 七、Progress

### GET /api/v1/learning-paths/{path_id}/progress

路径全局进度。

```json
// Response
{
  "data": {
    "total_nodes": 20,
    "completed_nodes": 11,
    "overall_mastery": 0.65,
    "module_progress": [
      { "module_name": "基础概念", "total": 5, "completed": 4, "mastery": 0.8 },
      { "module_name": "流程控制", "total": 8, "completed": 3, "mastery": 0.4 }
    ],
    "review_due": [
      { "node_id": "...", "title": "变量", "mastery": 0.5, "last_reviewed": "iso8601" }
    ]
  }
}
```

### POST /api/v1/nodes/{node_id}/start

开始学习节点。记录开始时间，状态改为 `learning`，必须通过查询参数传入 `path_id`。

```json
// Response 200
{ "data": { "status": "learning", "started_at": "iso8601" } }
```

### POST /api/v1/nodes/{node_id}/complete

完成节点（前端在评估通过后调用），必须通过查询参数传入 `path_id`。

```json
// Request
{ "mastery": 0.85 }

// Response 200
{
  "data": {
    "status": "completed",
    "mastery": 0.85,
    "next_node_id": "uuid",
    "unlocked_modules": [...]
  }
}
```

### GET /api/v1/learning-paths/{path_id}/report

学习报告，供前端仪表盘和报告页使用。

```json
// Response 200
{
  "data": {
    "module_mastery": [
      { "module_name": "基础概念", "total_nodes": 5, "completed": 4, "avg_mastery": 0.8 }
    ],
    "weak_nodes": [
      { "node_id": "n1", "title": "变量", "mastery": 0.4, "status": "learning" }
    ],
    "quiz_history": [
      { "node_id": "n1", "score": 0.7, "created_at": "iso8601" }
    ],
    "total_quizzes": 3,
    "overall_mastery": 0.65,
    "total_nodes": 20,
    "completed_nodes": 11,
    "in_progress_nodes": 2
  }
}
```

### GET /api/v1/learning-paths/{path_id}/report/trend

掌握度趋势快照。

```json
// Response 200
{
  "data": [
    { "recorded_at": "iso8601", "overall_mastery": 0.65, "completed_nodes": 11, "total_nodes": 20 }
  ]
}
```

---

## 八、Quiz

### POST /api/v1/nodes/{node_id}/quiz

为节点生成测验。LLM 根据节点内容 + Domain Profile 出题，推荐通过查询参数传入 `path_id` 以隔离测验缓存。

```json
// Response 200
{
  "data": {
    "quiz_id": "uuid",
    "questions": [
      {
        "id": "q1",
        "type": "multiple_choice",
        "question": "Python 中哪个关键字用于定义变量？",
        "options": ["A. var", "B. let", "C. x =", "D. 不需要关键字"],
        "shuffled": true
      },
      {
        "id": "q2",
        "type": "multiple_choice",
        "question": "下列哪个是合法的变量名？",
        "options": ["A. 2name", "B. my-name", "C. my_name", "D. class"]
      }
    ]
  }
}
```

### POST /api/v1/quiz/{quiz_id}/submit

提交答案。

```json
// Request
{
  "answers": [
    { "question_id": "q1", "selected": "C" },
    { "question_id": "q2", "selected": "C" }
  ]
}

// Response 200
{
  "data": {
    "score": 0.5,
    "total": 2,
    "correct": 1,
    "passed": false,
    "mastery_update": 0.6,
    "results": [
      { "question_id": "q1", "correct": true, "correct_answer": "C" },
      { "question_id": "q2", "correct": false, "correct_answer": "C" }
    ]
  }
}
```

如果答题卡缓存已过期，服务端返回 410，客户端应重新调用生成测验接口后再提交：

```json
// Response 410
{ "detail": "测验已过期，请重新生成后再提交" }
```

---

## 九、Admin

### PUT /api/v1/admin/config

更新系统配置，仅管理员可访问。

```json
// Request
{
  "llm_provider": "openai-compatible",
  "llm_model": "deepseek-v4-flash",
  "llm_api_key": "string?",
  "llm_api_base": "https://api.deepseek.com/v1",
  "allow_self_register": true
}

// Response 200
{ "data": { "llm_provider": "...", "llm_model": "...", "allow_self_register": true } }
```

`llm_api_key` 省略表示不修改系统密钥；传入空字符串或 `null` 表示清空系统密钥，并同步清除当前进程中的运行时密钥。

---

## 十、WebSocket 协议

### 连接

```
ws://host/api/v1/ws/chat?token=JWT_TOKEN
```

连接成功 → 服务端返回：

```json
{ "type": "connected", "session_id": "uuid" }
```

### 客户端 → 服务端

```json
// 发送消息
{
  "type": "message",
  "node_id": "neo4j-node-uuid",
  "path_id": "learning-path-uuid",
  "session_id": "已有会话可选",
  "content": "为什么变量不能以数字开头？"
}

> `session_id` 仅允许恢复同一用户、同一路径、同一节点的会话；跨路径或跨节点复用会被拒绝。

// 请求延伸
{
  "type": "extend",
  "node_id": "neo4j-node-uuid",
  "path_id": "learning-path-uuid",
  "direction": "related"   // prerequisite | related | next
}

// 请求评估
{
  "type": "request_quiz",
  "node_id": "neo4j-node-uuid"
}
```

### 服务端 → 客户端

```json
// 教学回复（流式）
{
  "type": "teaching_chunk",
  "session_id": "uuid",
  "content": "这是因为Python解释器在解析..."    // 每段增量
}

// 教学回复（完整，流式结束）
{
  "type": "teaching_done",
  "session_id": "uuid"
}

// 延伸响应
{
  "type": "extension",
  "session_id": "uuid",
  "content": "...",
  "related_nodes": [
    { "id": "...", "title": "命名规范", "relation": "延伸阅读" }
  ]
}

// 错误
{
  "type": "error",
  "code": "node_not_found",
  "message": "节点不存在"
}

// 内容管道进度（异步任务时推送）
{
  "type": "pipeline_progress",
  "path_id": "uuid",
  "stage": "extracting_knowledge",
  "progress": 0.6,
  "message": "正在提取知识点..."
}
```

---

## 十一、错误码

| HTTP | WS code | 含义 |
|------|---------|------|
| 400 | bad_request | 请求参数错误 |
| 401 | unauthorized | 未登录/Token 过期 |
| 403 | forbidden | 无权限 |
| 404 | not_found | 资源不存在 |
| 409 | conflict | 冲突（如重复创建） |
| 422 | validation_error | 数据校验失败 |
| 500 | internal_error | 服务器内部错误 |
| 503 | service_unavailable | 外部依赖不可用，如 LLM、Redis 答题卡缓存或 Neo4j 图谱清理失败 |

WebSocket 还会返回 `invalid_payload`（非法 JSON 或非对象消息）和 `invalid_audio`（非法 base64 音频数据）。这些错误只影响当前消息，不会主动断开连接。

---

## 十二、内容管道（异步任务）

在 MVP 中，内容管道以同步模式运行（用户等待完成），或用简单轮询：

```
POST /api/v1/learning-paths (mode=topic)
  → 后端启动后台任务 (asyncio.create_task)
  → 返回 202 + path_id
  → 前端轮询 GET /api/v1/learning-paths/{path_id}
     status: "processing" → 继续轮询
     status: "active" → 完成，显示大纲
```

全流程：

```
1. 用户请求
2. LLM 生成知识点列表（JSON）
3. 提取前置依赖关系
4. 写入 Neo4j
5. 拓扑排序 → 生成大纲
6. 状态改为 active
```
