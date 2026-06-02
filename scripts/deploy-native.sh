#!/bin/bash
# ──────────────────────────────────────────────
# EduMind 原生部署脚本（不依赖 Docker 镜像）
# 适用场景：Docker Hub 无法访问时的替代方案
# ──────────────────────────────────────────────

set -e

echo "========================================"
echo "  EduMind 原生部署（无 Docker 镜像）"
echo "========================================"

# ── 1. 安装 PostgreSQL ──
echo ""
echo "[1/5] 安装 PostgreSQL..."
if ! command -v psql &>/dev/null; then
  sudo apt-get install -y postgresql postgresql-contrib
fi
sudo systemctl start postgresql 2>/dev/null || true
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='edumind'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER edumind WITH PASSWORD 'edumind_dev';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='edumind'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE edumind OWNER edumind;"
echo "  ✅ PostgreSQL 就绪"

# ── 2. 安装 Redis ──
echo ""
echo "[2/5] 安装 Redis..."
if ! command -v redis-server &>/dev/null; then
  sudo apt-get install -y redis-server
fi
sudo systemctl start redis-server 2>/dev/null || true
echo "  ✅ Redis 就绪"

# ── 3. 安装 Neo4j ──
echo ""
echo "[3/5] 安装 Neo4j..."
if ! command -v neo4j &>/dev/null && [ ! -f /usr/bin/neo4j ]; then
  # Neo4j 需要 Java 17
  sudo apt-get install -y openjdk-17-jre-headless

  # 从国内镜像下载 Neo4j（避免 docker.io 封锁）
  wget -O /tmp/neo4j.tgz "https://weixin.oss-cn-hangzhou.aliyuncs.com/neo4j-community-5.20.0-unix.tar.gz" 2>/dev/null || \
  wget -O /tmp/neo4j.tgz "https://dist.neo4j.org/neo4j-community-5.20.0-unix.tar.gz"

  sudo tar -xzf /tmp/neo4j.tgz -C /opt/
  sudo mv /opt/neo4j-community-5.20.0 /opt/neo4j
  sudo chown -R $USER:$USER /opt/neo4j

  # 配置密码
  export NEO4J_HOME=/opt/neo4j
  /opt/neo4j/bin/neo4j-admin dbms set-initial-password edumind_dev
fi

# 启动 Neo4j
if [ -f /opt/neo4j/bin/neo4j ]; then
  /opt/neo4j/bin/neo4j start 2>/dev/null || true
fi
echo "  ✅ Neo4j 就绪（http://localhost:7474, neo4j/edumind_dev）"

# ── 4. 启动后端 ──
echo ""
echo "[4/5] 启动后端..."
cd "$(dirname "$0")/../backend"

# 创建虚拟环境（如果不存在）
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

# 确保 .env 文件存在
if [ ! -f .env ]; then
  cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://edumind:edumind_dev@localhost:5432/edumind
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=edumind_dev
REDIS_URL=redis://localhost:6379/0
LLM_PROVIDER=openai-compatible
LLM_MODEL=deepseek-v4-flash
OPENAI_API_KEY=sk-your-deepseek-api-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
JWT_SECRET=edumind-native-$(date +%s | md5sum | head -c 8)
CORS_ORIGINS=http://localhost:5173
DATA_DIR=./data
EOF
  echo "  ⚠️  请编辑 backend/.env，填入你的 DeepSeek API Key"
fi

# 后台启动
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/edumind-backend.log 2>&1 &
echo "  ✅ 后端已启动 (PID: $!)"
echo "     日志: tail -f /tmp/edumind-backend.log"
echo "     API:  http://localhost:8000"

# ── 5. 启动前端 ──
echo ""
echo "[5/5] 启动前端..."
cd "$(dirname "$0")/../frontend"

if [ ! -d node_modules ]; then
  npm install
fi

nohup npm run dev -- --host 0.0.0.0 > /tmp/edumind-frontend.log 2>&1 &
echo "  ✅ 前端已启动 (PID: $!)"
echo "     日志: tail -f /tmp/edumind-frontend.log"
echo "     地址: http://localhost:5173"

echo ""
echo "========================================"
echo "  ✅ EduMind 原生部署完成！"
echo "========================================"
echo ""
echo "  访问地址:"
echo "   前端:     http://localhost:5173"
echo "   后端 API: http://localhost:8000"
echo "   Neo4j:   http://localhost:7474"
echo ""
echo "  停止服务:"
echo "    kill $(lsof -ti:8000) $(lsof -ti:5173) 2>/dev/null"
echo "    /opt/neo4j/bin/neo4j stop"
echo ""
echo "  查看日志:"
echo "    tail -f /tmp/edumind-backend.log"
echo "    tail -f /tmp/edumind-frontend.log"
echo ""
