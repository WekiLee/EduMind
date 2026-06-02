@echo off
REM ──────────────────────────────────────────────
REM EduMind Windows 开发环境快速启动
REM ──────────────────────────────────────────────

echo ========================================
echo   EduMind Windows 开发环境设置
echo ========================================

REM 1. 检查 Python
echo.
echo [1/5] 检查 Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 请安装 Python 3.11+ https://www.python.org/downloads/
    exit /b 1
)
for /f %%i in ('python -c "import sys; print(sys.version_info[1])"') do set PY_MINOR=%%i
if %PY_MINOR% LSS 11 (
    echo ❌ Python 版本需要 3.11+，当前版本过低
    exit /b 1
)
echo ✅ Python %PY_VERSION%

REM 2. 创建 Python 虚拟环境
echo.
echo [2/5] 创建 Python 虚拟环境...
if not exist backend\venv (
    python -m venv backend\venv
    echo ✅ 虚拟环境已创建
) else (
    echo ✅ 虚拟环境已存在
)

REM 3. 安装后端依赖
echo.
echo [3/5] 安装后端依赖...
call backend\venv\Scripts\activate
pip install -r backend\requirements.txt
echo ✅ 后端依赖已安装

REM 4. 安装前端依赖
echo.
echo [4/5] 安装前端依赖...
cd frontend
if not exist node_modules (
    npm install
)
cd ..
echo ✅ 前端依赖已安装

REM 5. 配置环境变量
echo.
echo [5/5] 配置环境变量...
if not exist backend\.env (
    copy backend\.env.example backend\.env
    echo ✅ .env 已创建，请按需修改配置
) else (
    echo ✅ .env 已存在
)

echo.
echo ========================================
echo   ✅ 环境设置完成！
echo ========================================
echo.
echo   启动方式：
echo.
echo   1. 启动数据库（需要 Docker）:
echo      docker compose up -d postgres neo4j redis ollama
echo.
echo   2. 启动后端（新终端）:
echo      cd backend
echo      .\venv\Scripts\activate
echo      uvicorn app.main:app --reload --port 8000
echo.
echo   3. 启动前端（新终端）:
echo      cd frontend
echo      npm run dev
echo.
echo   4. 打开浏览器: http://localhost:5173
echo.
