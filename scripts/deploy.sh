#!/bin/bash
# ──────────────────────────────────────────────
# EduMind Linux 部署脚本
# 适用系统：Ubuntu 20.04+ / Debian 12+
# ──────────────────────────────────────────────
# 注意：使用 set -e 会导致网络失败时整个脚本中断，
# 我们用更精细的错误处理替代。

echo "========================================"
echo "  EduMind 部署脚本"
echo "========================================"

# ── 1. 检查系统 ──
echo ""
echo "[1/7] 检查系统环境..."

OS=$(cat /etc/os-release | grep "^ID=" | cut -d= -f2 | tr -d '"')
VER=$(cat /etc/os-release | grep "^VERSION_ID=" | cut -d= -f2 | tr -d '"' | tr -d '.')
echo "  系统: $OS $VER"

if [[ "$OS" != "ubuntu" && "$OS" != "debian" ]]; then
  echo "  ⚠️  当前系统: $OS，脚本适配 Ubuntu/Debian"
fi

# ── 2. 安装 Docker ──
echo ""
echo "[2/7] 安装 Docker..."

install_docker_manual() {
  echo "  ⚠️  自动安装失败，尝试手动安装 Docker..."
  echo "  执行以下命令安装 Docker："
  echo ""
  echo "  # 方法一：使用国内镜像（推荐国内用户）"
  echo "  curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg"
  echo '  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null'
  echo "  sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin"
  echo ""
  echo "  # 方法二：二进制安装（通用）"
  echo "  wget -O /tmp/docker.tgz https://download.docker.com/linux/static/stable/x86_64/docker-24.0.7.tgz"
  echo "  tar -xzf /tmp/docker.tgz -C /tmp/"
  echo "  sudo cp /tmp/docker/* /usr/local/bin/"
  echo "  sudo dockerd &"
  echo ""
  echo "  安装完成后重新运行本脚本即可。"
}

if ! command -v docker &> /dev/null; then
  echo "  Docker 未安装，尝试自动安装..."

  # 尝试官方脚本（可能因网络失败）
  if curl -fsSL https://get.docker.com -o /tmp/get-docker.sh 2>/dev/null; then
    sh /tmp/get-docker.sh 2>/dev/null && {
      sudo usermod -aG docker "$USER" 2>/dev/null
      echo "  ✅ Docker 已安装"
    } || {
      install_docker_manual
      exit 1
    }
  else
    # 国内网络问题，尝试阿里云镜像
    echo "  官方源不可达，尝试国内镜像..."
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg -o /tmp/docker.gpg 2>/dev/null && {
      sudo mkdir -p /etc/apt/keyrings
      sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg /tmp/docker.gpg 2>/dev/null
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
      sudo apt-get update -qq && sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin && {
        echo "  ✅ Docker 已安装（阿里云镜像）"
      } || {
        install_docker_manual
        exit 1
      }
    } || {
      install_docker_manual
      exit 1
    }
  fi
else
  echo "  ✅ Docker 已存在: $(docker --version)"
fi

# 检查 docker compose
if ! docker compose version &>/dev/null; then
  echo "  安装 docker-compose-plugin..."
  sudo apt-get install -y docker-compose-plugin 2>/dev/null || {
    echo "  ❌ 安装 docker-compose-plugin 失败"
    echo "  请手动安装：sudo apt-get install docker-compose-plugin"
    exit 1
  }
fi
echo "  ✅ Docker Compose: $(docker compose version)"

# ── 3. 准备项目文件 ──
echo ""
echo "[3/7] 准备项目文件..."

PROJECT_DIR="${1:-$(pwd)}"
if [ ! -f "$PROJECT_DIR/docker-compose.yml" ]; then
  echo "  ❌ 未找到 docker-compose.yml，请确认项目路径"
  echo "  用法: bash deploy.sh /path/to/edumind"
  exit 1
fi
cd "$PROJECT_DIR"
echo "  ✅ 项目目录: $(pwd)"

# ── 4. 创建数据目录 ──
echo ""
echo "[4/7] 创建数据目录..."
mkdir -p data
echo "  ✅ data/ 已创建"

# ── 5. 配置环境变量 ──
echo ""
echo "[5/7] 配置环境变量..."

if [ ! -f backend/.env ]; then
  # 尝试获取有效 API Key
  read -p "  请输入 DeepSeek API Key（回车跳过，稍后手动编辑）: " api_key

  cat > backend/.env << ENVFILE
# ── 数据库 ──
DATABASE_URL=postgresql+asyncpg://edumind:edumind_dev@postgres:5432/edumind
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=edumind_dev
REDIS_URL=redis://redis:6379/0

# ── LLM（默认 DeepSeek 公开 API）──
LLM_PROVIDER=openai-compatible
LLM_MODEL=deepseek-v4-flash
OPENAI_API_KEY=${api_key:-sk-your-deepseek-api-key}
OPENAI_BASE_URL=https://api.deepseek.com/v1

# 如需本地模型，取消注释以下内容：
# LLM_PROVIDER=ollama
# LLM_MODEL=qwen2.5:7b
# OLLAMA_BASE_URL=http://ollama:11434

# ── 安全 ──
JWT_SECRET=edumind-$(date +%s | md5sum | head -c 16)
JWT_EXPIRATION_HOURS=72

CORS_ORIGINS=http://localhost:5173,http://localhost:3000
DATA_DIR=./data
ENVFILE
  echo "  ✅ backend/.env 已创建"
  if [ -z "$api_key" ]; then
    echo "  ⚠️  请编辑 backend/.env，填入你的 DeepSeek API Key"
    echo "     申请地址：https://platform.deepseek.com/api_keys"
  fi
else
  echo "  ✅ backend/.env 已存在"
fi

# ── 6. 启动服务 ──
echo ""
echo "[6/7] 启动 Docker 服务..."

# 先拉取镜像（允许失败，国内网络可能超时）
echo "  拉取镜像（如果网络慢可跳过：Ctrl+C 后手动 docker compose pull）..."
docker compose pull 2>/dev/null || {
  echo "  ⚠️  镜像拉取超时，将尝试直接启动（首次会自动拉取）"
}

# 启动（后台）
docker compose up -d 2>/dev/null || {
  echo "  ❌ Docker 启动失败"
  echo "  请检查："
  echo "    1. Docker 是否已启动：sudo systemctl status docker"
  echo "    2. 端口是否被占用：lsof -i :5432 -i :7687 -i :6379 -i :8000 -i :5173"
  exit 1
}

echo "  ⏳ 等待服务就绪（约 30 秒）..."

# 等待 PostgreSQL
PG_READY=false
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U edumind &>/dev/null; then
    echo "  ✅ PostgreSQL 就绪"
    PG_READY=true
    break
  fi
  sleep 2
done

if [ "$PG_READY" = false ]; then
  echo "  ⚠️  PostgreSQL 启动超时，请检查：docker compose logs postgres"
fi

# ── 7. 初始化数据 ──
echo ""
echo "[7/7] 初始化数据..."

if [ "$PG_READY" = true ]; then
  echo "  初始化 Neo4j 约束..."
  docker compose exec -T backend python -m app.scripts.init_neo4j 2>/dev/null || echo "  ⚠️  Neo4j 初始化跳过"

  # 可选：导入测试数据
  if [ "${SEED_DATA:-false}" = "true" ]; then
    echo "  导入测试数据..."
    docker compose exec -T backend python -m app.scripts.seed_data 2>/dev/null || echo "  ⚠️  测试数据导入跳过"
  fi
fi

echo ""
echo "========================================"
echo "  ✅ EduMind 部署完成！"
echo "========================================"
echo ""
echo "  访问地址:"
echo "   前端:     http://localhost:5173"
echo "   后端 API: http://localhost:8000"
echo "   Neo4j:   http://localhost:7474 (neo4j/edumind_dev)"
echo ""
echo "  常用命令:"
echo "   查看日志:  docker compose logs -f"
echo "   查看后端:  docker compose logs -f backend"
echo "   停止服务:  docker compose down"
echo "   重启服务:  docker compose restart"
echo ""
echo "  📌 默认使用 DeepSeek API"
echo "     - 确保 backend/.env 中 OPENAI_API_KEY 已正确填写"
echo "     - 如需切换为本地模型，请编辑 backend/.env 并取消 ollama 服务注释"
echo ""
