# EduMind 国内网络部署指南

> 针对中国大陆用户——解决 Docker 镜像拉取和 DeepSeek API 配置问题。

---

## 一、Docker 安装

### 方法 A：阿里云镜像（推荐）

```bash
# 安装依赖
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# 添加阿里云 Docker 源
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 方法 B：二进制安装（无网络依赖）

```bash
# 下载 Docker 二进制
wget -O /tmp/docker.tgz https://download.docker.com/linux/static/stable/x86_64/docker-24.0.7.tgz

# 解压并安装
tar -xzf /tmp/docker.tgz -C /tmp/
sudo cp /tmp/docker/* /usr/local/bin/

# 启动 Docker 守护进程
sudo dockerd &

# 安装 Compose 插件
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
wget -O $DOCKER_CONFIG/cli-plugins/docker-compose \
  "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)"
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
```

---

## 二、Docker 镜像加速

创建或编辑 `/etc/docker/daemon.json`：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

重启 Docker：

```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

---

## 三、手动拉取镜像

如果 `docker compose pull` 超时，可以逐个拉取：

```bash
# 使用镜像加速后手动拉取
docker pull pgvector/pgvector:pg16
docker pull neo4j:5
docker pull redis:7-alpine

# 构建后端和前端镜像
docker compose build
```

---

## 四、DeepSeek API 配置

1. 访问 https://platform.deepseek.com/api_keys 注册并创建 API Key
2. DeepSeek 新用户赠送 500 万 Token，完全够 MVP 开发使用
3. 在 `backend/.env` 中填入：

```ini
LLM_PROVIDER=openai-compatible
LLM_MODEL=deepseek-v4-flash
OPENAI_API_KEY=sk-你的密钥
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

> DeepSeek API 国内可直接访问，无需代理。

---

## 五、一键部署（国内适配版）

```bash
# 1. 安装 Docker（如果尚未安装）
bash scripts/deploy.sh
# 脚本会自动检测网络，失败时提示手动安装

# 2. 如果 docker compose pull 缓慢，手动加速：
#    - 配置镜像加速（见上文第二节）
#    - 或逐个 docker pull

# 3. 手动启动时需显式提供开发数据库密码并启用 dev profile
export POSTGRES_PASSWORD="edumind_dev"
docker compose --profile dev up -d
```

---

## 六、常见问题

### Q: curl: (35) OpenSSL SSL_connect 连接被重置
**原因**：国内网络对 Docker 官方域名的 TLS 干扰。  
**解决**：使用阿里云镜像安装（方法 A）。

### Q: docker compose pull 极慢
**原因**：Docker Hub 在国内访问缓慢。  
**解决**：配置镜像加速（见第二节）。

### Q: Neo4j 浏览器界面无法打开
```bash
# Neo4j 浏览器在 http://localhost:7474
# Neo4j 密码见项目根目录 .env 的 NEO4J_PASSWORD
docker compose logs neo4j  # 检查日志
```

### Q: 如何查看后端日志？
```bash
docker compose logs -f backend
```

### Q: 如何重置所有数据？
```bash
docker compose down -v   # 删除所有数据卷
export POSTGRES_PASSWORD="edumind_dev"
docker compose --profile dev up -d     # 重新启动
```
