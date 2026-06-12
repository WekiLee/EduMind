# MVP 开发环境配置

> Docker Compose 一键启动 + 本地开发说明

---

## 一、服务拓扑

```
┌────────────────────────────────────────────────────────────┐
│                        Docker Net                           │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ FastAPI   │◄───│ React    │    │ (可选)    │              │
│  │ (8000)   │    │ (5173)   │    │ Ollama   │              │
│  └────┬─────┘    └──────────┘    │ (11434)  │              │
│       │                          └──────────┘              │
│  ┌────┼────┐                                               │
│  ▼    ▼    ▼                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ PostgreSQL│ │ Neo4j     │ │ Redis    │                    │
│  │ (5432)   │ │ (7687)   │ │ (6379)   │                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
│                                                             │
│  LLM 默认使用 DeepSeek 公开 API，无需本地模型服务              │
│  如需本地模型（Ollama），取消 docker-compose 中注释并配置 .env │
└────────────────────────────────────────────────────────────┘
```

---

## 二、docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: edumind
      POSTGRES_USER: edumind
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backend/scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U edumind"]
      interval: 5s
      timeout: 5s
      retries: 5

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-edumind_dev}
      NEO4J_PLUGINS: '["apoc"]'
    ports:
      - "7474:7474"    # HTTP (Browser UI)
      - "7687:7687"    # Bolt
    volumes:
      - neo4jdata:/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollamadata:/root/.ollama
    entrypoint: >
      sh -c "ollama serve &
             sleep 3 &&
             ollama pull qwen2.5:7b &&
             wait"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      ENVIRONMENT: development
      AUTO_MIGRATE_ON_STARTUP: ${AUTO_MIGRATE_ON_STARTUP:-true}
      DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://edumind:${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}@postgres:5432/edumind}
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: ${NEO4J_PASSWORD:-edumind_dev}
      REDIS_URL: redis://redis:6379/0
      OLLAMA_BASE_URL: http://ollama:11434
      JWT_SECRET: edumind-dev-secret-change-in-production
      CORS_ORIGINS: http://localhost:5173
      LLM_MODEL: qwen2.5:7b
    depends_on:
      postgres:
        condition: service_healthy
      neo4j:
        condition: service_started
      redis:
        condition: service_healthy
      ollama:
        condition: service_started
    volumes:
      - ./backend:/app
      - ./data:/data

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000/api/v1
      VITE_WS_URL: ws://localhost:8000/api/v1
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  pgdata:
  neo4jdata:
  ollamadata:
```

---

## 三、后端 Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
  gcc \
  libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 开发模式：挂载卷覆盖，Dockerfile 只负责基础镜像
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### requirements.txt

```txt
fastapi>=0.111,<1
uvicorn[standard]>=0.30
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29
alembic>=1.13
redis>=5.1
httpx>=0.27
pydantic>=2.8
pydantic-settings>=2.3
python-jose[cryptography]>=3.3
passlib[bcrypt]>=1.7
python-multipart>=0.0.9
neo4j>=5.22
litellm>=1.44
unstructured[pdf,docx,md]>=0.15
python-dotenv>=1.0
```

---

## 四、前端 Dockerfile（开发）

```dockerfile
# frontend/Dockerfile.dev
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

---

## 五、本地启动指令

```bash
# 一键启动全栈（首次会拉取镜像，较慢）
export POSTGRES_PASSWORD="edumind_dev"
docker compose --profile dev up -d

# 查看日志
docker compose logs -f backend

# 仅启动数据库（前端+后端本地运行）
export POSTGRES_PASSWORD="edumind_dev"
docker compose up -d postgres neo4j redis

# 本地运行后端（需要 Python 3.12+）
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 编辑配置
uvicorn app.main:app --reload --port 8000

# 本地运行前端（需要 Node.js 18+）
cd frontend
npm install
npm run dev

# 停止全部
docker compose down

# 重置数据（删除所有数据卷）
docker compose down -v
```

---

## 六、环境变量说明（backend/.env）

```bash
# 运行环境：development / production
# production 会拒绝默认 DATABASE_URL、NEO4J_PASSWORD 和 JWT_SECRET
ENVIRONMENT=development

# 数据库
DATABASE_URL=postgresql+asyncpg://edumind:edumind_dev@localhost:5432/edumind
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=edumind_dev
REDIS_URL=redis://localhost:6379/0

# LLM
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434

# JWT
JWT_SECRET=change-this-in-production
JWT_EXPIRATION_HOURS=72

# 数据库结构变更
# 开发环境默认自动建表；生产环境默认关闭，应通过迁移流程处理结构变更
# AUTO_MIGRATE_ON_STARTUP=true

# 内置管理员（可选）
# 未配置时跳过内置管理员创建，首位自助注册用户自动成为管理员
DEFAULT_ADMIN_PASSWORD=请使用强随机密码

# CORS
CORS_ORIGINS=http://localhost:5173

# 数据目录
DATA_DIR=./data
```

生产模式必须将 `ENVIRONMENT` 设置为 `production`，并通过部署环境显式提供真实密钥：

```bash
export ENVIRONMENT=production
export POSTGRES_PASSWORD="<强随机密码>"
export NEO4J_PASSWORD="<强随机密码>"
export JWT_SECRET="$(openssl rand -hex 32)"
# 生产默认不执行启动期 DDL；如需兼容旧部署，可显式设置 AUTO_MIGRATE_ON_STARTUP=true。
# 如使用外部 PostgreSQL，可额外覆盖 DATABASE_URL。
python scripts/validate_compose_config.py
docker compose --profile prod up -d
```

---

## 七、首次启动流程

```bash
# 1. 克隆仓库
git clone https://github.com/edumind/edumind.git
cd edumind

# 2. 准备 Compose 必填变量
export POSTGRES_PASSWORD="edumind_dev"

# 3. 启动全部服务
docker compose --profile dev up -d

# 4. 查看后端日志
docker compose logs -f backend

# 5. 运行数据库迁移
docker compose exec backend alembic upgrade head

# 6. 初始化 Neo4j 约束
docker compose exec backend python -m app.scripts.init_neo4j

# 7. 验证
curl http://localhost:8000/api/v1/auth/me
# → {"detail":"Not authenticated"}  ← 正常，说明服务在运行

# 8. 打开浏览器
open http://localhost:5173
```

---

## 八、测试数据

```bash
# 插入示例学习路径和节点
docker compose exec backend python -m app.scripts.seed_data

# 将创建一个 "Python 入门" 学习路径，包含：
# - 模块1：基础概念（变量、数据类型、运算符）
# - 模块2：流程控制（if、for、while）
# - 模块3：函数（定义、参数、返回值）
# 每个节点包含完整的教学内容和选择题
```
