#!/bin/bash
# ──────────────────────────────────────────────
# EduMind 启动脚本
# ──────────────────────────────────────────────

echo "🚀 EduMind 启动..."

# 启动 Neo4j（如果未启动）
sudo systemctl start neo4j 2>/dev/null
echo "  ✅ Neo4j"

# 检查 PostgreSQL
if ! pg_isready -q 2>/dev/null; then
    sudo systemctl start postgresql 2>/dev/null
    sleep 2
fi
echo "  ✅ PostgreSQL"

# 启动后端
cd ~/Edumind/backend
conda activate edumind 2>/dev/null || source venv/bin/activate 2>/dev/null
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/edumind-backend.log 2>&1 &
BACKEND_PID=$!
echo "  ✅ 后端 (PID: $BACKEND_PID) - http://localhost:8000"

# 启动前端
cd ~/Edumind/frontend
nohup npm run dev -- --host 0.0.0.0 > /tmp/edumind-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "  ✅ 前端 (PID: $FRONTEND_PID) - http://localhost:5173"

echo ""
echo "========================================"
echo "  EduMind 已启动！"
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:8000"
echo "  后端日志: tail -f /tmp/edumind-backend.log"
echo "  前端日志: tail -f /tmp/edumind-frontend.log"
echo "  停止: kill $BACKEND_PID $FRONTEND_PID"
echo "========================================"
