# MVP 数据库设计

> PostgreSQL + Neo4j 完整 Schema。当前仓库未包含 Alembic 目录，MVP 阶段通过 `Base.metadata.create_all` 建表，并由 `ensure_schema_compatibility()` 执行少量启动期兼容修复。

---

## 一、PostgreSQL

### 1.1 users

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  domain_id VARCHAR(50) DEFAULT 'general',       -- 默认领域
  learner_profile JSONB DEFAULT '{
    "abstraction_level": 0.5,
    "analogy_density": 0.5,
    "teaching_speed": 0.5,
    "feedback_tone": 0.5,
    "quiz_style": 0.5
  }',
  model_config JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### 1.2 learning_paths

```sql
CREATE TABLE learning_paths (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  topic VARCHAR(500) NOT NULL,
  domain_id VARCHAR(50) NOT NULL DEFAULT 'general',
  syllabus JSONB NOT NULL DEFAULT '[]',
  -- 结构: [{"module_name": "...", "order": 1, "node_ids": ["..."]}, ...]
  status VARCHAR(20) NOT NULL DEFAULT 'active'
    CHECK (status IN ('processing', 'active', 'completed', 'archived')),
  source VARCHAR(20) DEFAULT 'topic',
    CHECK (source IN ('topic', 'upload', 'link')),
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);

CREATE INDEX idx_lp_user ON learning_paths(user_id);
CREATE INDEX idx_lp_status ON learning_paths(status);
```

### 1.3 node_progress

```sql
CREATE TABLE node_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  path_id UUID NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
  node_id VARCHAR(255) NOT NULL,              -- Neo4j 节点 ID
  status VARCHAR(20) NOT NULL DEFAULT 'not_started'
    CHECK (status IN ('not_started', 'learning', 'completed', 'reviewing')),
  mastery REAL DEFAULT 0.0 CHECK (mastery >= 0 AND mastery <= 1),
  attempt_count INT DEFAULT 0,
  quiz_scores REAL[] DEFAULT '{}',
  first_learned TIMESTAMP,
  last_reviewed TIMESTAMP,
  next_review TIMESTAMP,

  UNIQUE (user_id, path_id, node_id)
);

CREATE INDEX idx_np_user ON node_progress(user_id);
CREATE INDEX idx_np_path ON node_progress(path_id);
CREATE INDEX idx_np_review ON node_progress(next_review)
  WHERE next_review IS NOT NULL;
```

### 1.4 quiz_attempts

```sql
CREATE TABLE quiz_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  path_id UUID NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
  node_id VARCHAR(255) NOT NULL,
  score REAL NOT NULL,
  total_questions INT NOT NULL,
  correct_count INT NOT NULL,
  answers JSONB NOT NULL,
  -- [{"question_id": "...", "selected": "A", "correct": true}, ...]
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_qa_user ON quiz_attempts(user_id);
CREATE INDEX idx_qa_node ON quiz_attempts(node_id);
```

### 1.5 chat_sessions

```sql
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  path_id UUID NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
  node_id VARCHAR(255),
  started_at TIMESTAMP DEFAULT NOW(),
  ended_at TIMESTAMP,
  message_count INT DEFAULT 0
);

CREATE INDEX idx_cs_user ON chat_sessions(user_id);
```

### 1.6 chat_messages

```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cm_session ON chat_messages(session_id);
```

### 1.7 system_config

```sql
CREATE TABLE system_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  llm_provider VARCHAR(50) NOT NULL DEFAULT 'openai-compatible',
  llm_model VARCHAR(100) NOT NULL DEFAULT 'deepseek-v4-flash',
  llm_api_key TEXT,
  llm_api_base VARCHAR(500) DEFAULT 'https://api.deepseek.com/v1',
  allow_self_register BOOLEAN NOT NULL DEFAULT TRUE,
  updated_by UUID,
  updated_at TIMESTAMP DEFAULT NOW()
);
```

`llm_api_key` 只保存管理员配置的系统密钥，接口响应必须遮盖。`allow_self_register` 统一使用 Boolean；旧版 JSON/Text 列由启动期兼容逻辑转换。

### 1.8 node_embeddings

```sql
CREATE TABLE node_embeddings (
  id SERIAL PRIMARY KEY,
  node_id VARCHAR(255) NOT NULL,
  path_id UUID NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
  content_text TEXT NOT NULL,
  model_name VARCHAR(100) NOT NULL,
  dimensions INT NOT NULL,
  embedding VECTOR,
  created_at TIMESTAMP DEFAULT NOW(),

  UNIQUE (path_id, node_id, model_name)
);

CREATE INDEX idx_ne_node ON node_embeddings(node_id);
CREATE INDEX idx_ne_path ON node_embeddings(path_id);
```

向量唯一性必须包含 `path_id`，避免不同学习路径复用同一 Neo4j 节点 ID 时相互覆盖。

---

## 二、Neo4j（知识图谱）

### 2.1 节点

```cypher
CREATE CONSTRAINT FOR (n:KnowledgeNode) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT FOR (m:Module) REQUIRE m.name IS UNIQUE;
CREATE INDEX node_domain_id FOR (n:KnowledgeNode) ON (n.domain_id);
CREATE INDEX node_difficulty FOR (n:KnowledgeNode) ON (n.difficulty);

// 知识点节点
(:KnowledgeNode {
  id: String,                    // UUID，与 PG 的 node_progress.node_id 对应
  title: String,
  summary: String,
  content: String,               // Markdown
  difficulty: String,            // "intro" | "intermediate" | "advanced"
  domain_id: String,             // "math" | "programming" | "general"
  node_type: String,             // "concept" | "skill" | "fact" | "procedure"
  examples: [String],            // JSON 字符串数组
  code_snippets: [String],       // JSON 字符串数组
  quiz_questions: String,        // JSON 字符串（避免复杂类型）
  ref_links: [String],
  source: String,                // "user" | "llm_generated" | "hybrid"
  confidence: Float,             // 0~1
  created_at: String             // ISO8601
})
```

### 2.2 关系

```cypher
// 前置依赖（A 必须先于 B 学习）
(:KnowledgeNode)-[:PREREQUISITE]->(:KnowledgeNode)

// 关联推荐（同级推荐）
(:KnowledgeNode)-[:RELATED {strength: Int}]->(:KnowledgeNode)
  // strength: 1=弱关联, 3=强关联

// 延伸（A 可作为 B 的深入话题）
(:KnowledgeNode)-[:EXTENDS]->(:KnowledgeNode)

// 所属模块（每个节点属于一个模块）
(:KnowledgeNode)-[:PART_OF]->(:Module {name: String, order: Int, path_id: String})
```

### 2.3 Cypher 查询示例

```cypher
// 获取路径的所有节点（按拓扑排序）
MATCH (n:KnowledgeNode)-[:PART_OF]->(m:Module {path_id: $path_id})
OPTIONAL MATCH (n)-[:PREREQUISITE]->(pre:KnowledgeNode)
WITH n, m, collect(pre.id) AS prerequisites
RETURN n, m, prerequisites
ORDER BY m.order, n.difficulty

// 获取节点的完整子图（2层）
MATCH (n:KnowledgeNode {id: $node_id})
OPTIONAL MATCH (n)-[:PREREQUISITE|RELATED|EXTENDS*1..2]-(related)
RETURN n, collect(DISTINCT related) AS related_nodes

// 获取所有前置节点（递归）
MATCH (n:KnowledgeNode {id: $node_id})
MATCH path = (pre)-[:PREREQUISITE*]->(n)
RETURN pre, length(path) AS depth
ORDER BY depth DESC
```

---

## 三、关系说明

| PG 表 | 关联的 Neo4j 实体 | 对应关系 |
|-------|-----------------|---------|
| `learning_paths.syllabus` | Module（模块名 + node_ids） | syllabus JSON 中大纲结构映射到 Neo4j 的 PART_OF 关系 |
| `node_progress.node_id` | KnowledgeNode.id | 字符串匹配，两个系统间的外键 |
| `learning_paths.domain_id` | KnowledgeNode.domain_id | 按域过滤 |

MVP 阶段不维护 PG ↔ Neo4j 的外键约束（NoSQL 图数据库没有外键概念）。数据一致性由业务层 Service 保证。

---

## 四、迁移策略

当前代码尚未引入 Alembic，启动时会执行以下兼容修复：

1. 将 `system_config.allow_self_register` 从 JSON/Text 转为 Boolean，并补齐默认值和非空约束。
2. 为 `node_embeddings` 补齐 `path_id`、清理无路径或孤儿向量、删除旧 `uq_node_model` 约束、添加 `uq_path_node_model`。
3. 在条件允许时为 `node_embeddings.path_id` 添加到 `learning_paths.id` 的外键级联。

后续进入生产部署前建议正式引入 Alembic，把上述兼容 SQL 固化为可审计迁移脚本。Neo4j 没有关系型迁移工具，图结构变更继续通过 Service 层 Cypher 语句控制。
