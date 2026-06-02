# EduMind — 智能导师系统

> 开源的 AI 驱动个人导师——像一位私人家教，从零到一帮学习者建立完整知识图谱，教、练、评、拓一体化。

---

## 核心特性

| 能力 | 说明 |
|------|------|
| **📚 混合内容采集** | 用户上传（PDF/MD/链接）+ AI 自动搜索，多源交叉验证 |
| **🧠 领域感知** | 不同学科（数学/编程/语言/历史）有不同的教学策略和内容模板 |
| **👤 学习者感知** | 抽象程度、比喻密度、节奏快慢等完全自定义，适配不同年龄段 |
| **🧩 知识图谱** | 知识点间前置依赖和关联关系可视化，掌握度着色 |
| **📋 智能大纲** | 自动拓扑排序，由浅入深生成学习路径 |
| **💬 对话教学** | 文字+语音双模交互，可随时提问和延伸 |
| **📊 评估闭环** | 每节点测验 + 掌握度量化 + 间隔重复复习 |
| **🔌 模型自由切换** | 支持 DeepSeek / Ollama / OpenAI 等任意兼容 API |
| **👑 双角色系统** | 管理员管理用户和系统配置，普通用户学习 |
| **📦 跨平台** | Web / Tauri 桌面 / Docker 部署 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      表示层 (React 18 + TS)                     │
│  知识卡片    对话界面    语音UI    知识图谱可视化                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                      业务层 (Python FastAPI)                    │
│  内容管道   大纲生成器   教学引擎   评估引擎   图谱管理器          │
│  领域管理器  Learner Profile  搜索编排  语音服务                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────┬───────────────┼──────────────┬───────────────────┐
│  PostgreSQL  │    Neo4j      │   Redis      │  pgvector          │
│  (用户/进度)  │  (知识图谱)   │  (会话缓存)  │  (语义搜索)        │
└──────────────┴───────────────┴──────────────┴───────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                      AI 层                                     │
│   DeepSeek API / Ollama / Whisper / Kokoro / MCP Client        │
└────────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Neo4j 5+
- Redis 7+

### 1. 安装数据库

```bash
# PostgreSQL
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE USER edumind WITH PASSWORD 'edumind_dev';"
sudo -u postgres psql -c "CREATE DATABASE edumind OWNER edumind;"

# Redis
sudo apt-get install -y redis-server
sudo systemctl start redis-server

# Neo4j
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 5" | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt-get update
sudo apt-get install -y neo4j
sudo neo4j-admin dbms set-initial-password edumind_dev
sudo systemctl start neo4j
```

### 2. 配置并启动后端

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入数据库连接信息
conda activate edumind  # 或 python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

### 4. 访问系统

浏览器打开 `http://localhost:5173`

---

## 默认管理员

| 邮箱 | 密码 | 说明 |
|------|------|------|
| admin@edumind.cn | admin123 | 首次登录必须修改密码 |

管理员登录后可在 `/admin/users` 创建普通用户，在 `/admin/config` 配置 LLM。

---

## LLM 配置

### 配置方式（优先级由高到低）

1. **管理员 Web UI** — 登录后 `/admin/config` 页面设置（推荐）
2. **.env 文件** — 首次启动的备选方案

### 支持的 Provider

| Provider | 配置方法 | 说明 |
|----------|---------|------|
| DeepSeek API | 后台配置 API Key + `https://api.deepseek.com/v1` | ✅ 默认，国内直接访问 |
| Ollama 本地 | 后台选择 Ollama + 本地模型名 | 离线运行，需先安装 Ollama |
| OpenAI 兼容 | 后台配置 API Key + 自定义地址 | 通义千问、智谱等 |

---

## 角色说明

| 角色 | 侧边栏 | 可操作 |
|------|--------|--------|
| **管理员** | 用户管理 + 系统配置 + 个人设置 | 管理用户、配置 LLM、修改密码 |
| **普通用户** | 我的学习 + 个人设置 | 创建学习路径、AI 教学对话、测验 |

> 管理员账号仅用于管理，无法创建学习路径。如需学习，请使用普通用户账号。

---

## 项目结构

```
edumind/
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── api/                # REST API 路由
│   │   ├── core/               # 配置/数据库/安全
│   │   ├── models/             # SQLAlchemy 数据模型
│   │   ├── services/           # 业务逻辑层
│   │   ├── llm/                # LLM 适配器
│   │   ├── ws/                 # WebSocket 教学对话
│   │   ├── domain_profiles/    # 领域配置文件
│   │   ├── scripts/            # 初始化脚本
│   │   └── main.py             # 入口
│   ├── tests/                  # 测试
│   └── requirements.txt
├── frontend/                   # React 18 + TypeScript
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   ├── components/         # 通用组件
│   │   ├── stores/             # Zustand 状态管理
│   │   ├── services/           # API 客户端
│   │   └── App.tsx             # 路由配置
│   ├── package.json
│   └── vite.config.ts
├── docs/                       # 文档
│   ├── DESIGN.md               # 完整方案设计书
│   ├── ADVANTAGES.md           # 优势分析
│   ├── DEPLOYMENT_RECORD.md    # 部署记录
│   └── mvp/                    # MVP 详细设计
└── scripts/                    # 部署脚本
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Tailwind CSS + Zustand |
| 后端 | Python FastAPI + SQLAlchemy + Neo4j + Redis |
| AI | LiteLLM (DeepSeek / Ollama / OpenAI) |
| 知识图谱 | Neo4j + vis-network |
| 语音（可选） | Whisper ASR + Kokoro TTS |
| 部署 | 原生安装 / Docker Compose |

---

## 开源协议

AGPL v3

---

## 文档导航

| 文档 | 说明 |
|------|------|
| [完整方案设计书](docs/DESIGN.md) | 系统架构、核心流程、技术选型 |
| [部署记录](docs/DEPLOYMENT_RECORD.md) | 从零到可用的完整部署流程 |
| [优势分析](docs/ADVANTAGES.md) | 与现有开源项目的对比 |
| [API 契约](docs/mvp/API.md) | REST + WebSocket 接口定义 |
| [数据库设计](docs/mvp/DATABASE.md) | PostgreSQL + Neo4j Schema |
| [测试框架](docs/mvp/TESTING.md) | 测试策略和用例 |
| [前端架构](docs/mvp/FRONTEND.md) | 组件树 + 状态管理 |
