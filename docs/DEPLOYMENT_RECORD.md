# EduMind 部署记录

> **环境**：Ubuntu 20.04 Focal (x86_64)
> **记录日期**：2026-06-02
> **用途**：知识共享，下次部署可直接参考

---

## 一、前置准备

### 1.1 Python 环境

建议使用 **Python 3.11**（通过 conda 创建）：

```bash
conda create -n edumind python=3.11 -y
conda activate edumind
```

### 1.2 系统包

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib redis-server openjdk-17-jre-headless poppler-utils
```

---

## 二、数据库安装与配置

### 2.1 PostgreSQL

```bash
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE USER edumind WITH PASSWORD 'edumind_dev';"
sudo -u postgres psql -c "CREATE DATABASE edumind OWNER edumind;"

# 验证
PGPASSWORD=edumind_dev psql -h 127.0.0.1 -U edumind -d edumind -c "SELECT 1;"
```

> **注意**：`.env` 中的 `DATABASE_URL` 使用 `127.0.0.1` 而非 `localhost`。

### 2.2 Redis

```bash
sudo systemctl start redis-server
redis-cli ping  # 应返回 PONG
```

### 2.3 Neo4j

```bash
# 添加 Neo4j 官方 apt 源
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 5" | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt-get update
sudo apt-get install -y neo4j

# 首次启动前设置密码
sudo neo4j-admin dbms set-initial-password edumind_dev
sudo systemctl start neo4j
```

> **如果密码设置时数据库已初始化过**：
> ```bash
> sudo systemctl stop neo4j
> sudo rm -rf /var/lib/neo4j/data/*
> sudo neo4j-admin dbms set-initial-password edumind_dev
> sudo systemctl start neo4j
> ```

> **如果启动报 `AccessDeniedException`**：
> ```bash
> sudo chown -R neo4j:neo4j /var/lib/neo4j/data
> sudo systemctl restart neo4j
> ```

> **注意**：`.env` 中的 `NEO4J_URI` 使用 `bolt://127.0.0.1:7687`。

---

## 三、项目配置

### 3.1 环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `.env`，必填项（也可在管理员后台配置，优先级更高）：

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://edumind:edumind_dev@127.0.0.1:5432/edumind` |
| `NEO4J_URI` | Neo4j 连接串 | `bolt://127.0.0.1:7687` |
| `JWT_SECRET` | JWT 签名密钥 | 任意随机字符串 |

### 3.2 LLM 配置（两种方式）

**方式 A（推荐）**：后端启动后，管理员登录 Web 后台 `/admin/config` 配置 API Key。

**方式 B（备选）**：编辑 `.env` 文件：

```ini
OPENAI_API_KEY=sk-your-deepseek-api-key
```

> `.env` 中的 LLM 配置**优先级低于**管理员 Web UI 设置。
> 管理员在后台配置后，`.env` 中的对应值不再生效，且重启后不丢失。

### 3.3 安装 Python 依赖

```bash
conda activate edumind
pip install -r requirements.txt
```

> 国内网络可配置 PyPI 镜像：`pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/`

### 3.4 文件上传支持

系统支持通过文件上传创建学习路径。支持的格式及依赖：

| 格式 | 类型 | 系统依赖 | Python 依赖 |
|------|------|---------|------------|
| `.txt` | 纯文本 | 无 | 无（内置） |
| `.md` | Markdown | 无 | 无（内置） |
| `.pdf` | PDF 文档 | `poppler-utils` | `unstructured[pdf]` |
| `.docx` | Word 文档 | 无 | `unstructured[docx]` |
| `.pptx` | PPT 演示文稿 | 无 | `unstructured[pptx]` |

```bash
# 安装系统依赖（PDF 解析需要）
sudo apt-get install -y poppler-utils

# Python 依赖已包含在 requirements.txt 中
pip install -r requirements.txt
```

---

## 四、启动服务

### 4.1 启动后端

```bash
cd backend
conda activate edumind
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

验证：`curl http://127.0.0.1:8000/api/health` → `{"status":"ok"}`

### 4.2 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

### 4.3 后台运行

```bash
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/edumind-backend.log 2>&1 &
nohup npm run dev -- --host 0.0.0.0 > /tmp/edumind-frontend.log 2>&1 &
tail -f /tmp/edumind-backend.log
```

---

## 五、内置管理员

系统首次启动会自动创建内置管理员账号：

| 字段 | 值 |
|------|------|
| 邮箱 | `admin@edumind.cn` |
| 初始密码 | `admin123` |

> ⚠️ 首次登录必须修改密码。管理员账号仅用于管理，不能创建学习路径。

### 管理员功能

| 功能 | 路径 | 说明 |
|------|------|------|
| 用户管理 | `/admin/users` | 创建 / 编辑 / 禁用 / 删除普通用户 |
| 系统配置 | `/admin/config` | 配置 LLM Provider / 模型 / API Key / 注册开关 |

---

## 六、配置优先级

```
管理员 Web UI（SystemConfig 表）← 优先级最高
        ↑
.env 文件配置                  ← 回退值
        ↑
代码硬编码默认值                ← 最低优先级
```

---

## 七、验证清单

| 步骤 | 命令 | 预期 |
|------|------|------|
| PostgreSQL | `PGPASSWORD=edumind_dev psql -h 127.0.0.1 -U edumind -d edumind -c "SELECT 1;"` | 返回 `1` |
| Neo4j | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7474/` | `200` |
| Redis | `redis-cli ping` | `PONG` |
| 后端 API | `curl http://127.0.0.1:8000/api/health` | `{"status":"ok"}` |
| 管理员登录 | 浏览器 `http://localhost:5173` → admin@edumind.cn / admin123 | 进入管理后台 |
| 创建用户 | 管理后台创建普通用户 | 成功创建 |
| 普通用户学习 | 用普通账号登录→创建学习路径→问答→测验 | 全部正常 |

---

## 八、版本参考

| 组件 | 验证通过的版本 |
|------|---------------|
| Ubuntu | 20.04 LTS |
| Python | 3.11.15 |
| PostgreSQL | 12.x |
| Neo4j | 5.26.26 |
| Redis | 6.x |
| Node.js | 20.x |
| FastAPI | 0.136.3 |
| LiteLLM | 1.86.2 |
| DeepSeek API | deepseek-v4-flash |
