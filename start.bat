@echo off
chcp 65001 >nul
title Dao-Mind v2

echo.
echo   ═══════════════════════════════
echo     道心 · Dao-Mind v2
echo   ═══════════════════════════════
echo.

REM 确定 Python
set "PYTHON="
where python >nul 2>&1 && set "PYTHON=python"
where python3 >nul 2>&1 && set "PYTHON=python3"
where py >nul 2>&1 && set "PYTHON=py"
if "%PYTHON%"=="" (
    echo [ERROR] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

REM 确保在项目根目录
cd /d "%~dp0"

REM 检查 .env (优先 settings.json，无需强制)
if not exist "settings.json" if not exist ".env" if exist ".env.example" (
    echo [INFO] 未配置 API Key
    echo       复制 .env.example 为 .env 编辑，或在应用内设置页面配置
    copy /y ".env.example" ".env" >nul
)

REM 安装依赖（如果需要）
pip show fastapi >nul 2>&1 || (
    echo [INFO] 安装 Python 依赖...
    %PYTHON% -m pip install -r requirements.txt -q
)

echo [INFO] 启动服务...

REM 启动后端
if exist "backend\main.py" (
    cd backend
    start "Dao-Mind" %PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8001
    cd ..
) else if exist "main.py" (
    start "Dao-Mind" %PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8001
) else (
    echo [ERROR] 找不到 main.py，请在项目根目录运行此脚本
    pause
    exit /b 1
)

REM 等待启动
echo [INFO] 等待服务启动...
timeout /t 3 /nobreak >nul

REM 打开浏览器
start http://localhost:8001

echo.
echo   ═══════════════════════════════
echo   应用: http://localhost:8001
echo   API:  http://localhost:8001/api/health
echo   文档: http://localhost:8001/docs
echo   ═══════════════════════════════
echo.
echo   关闭此窗口或后端窗口停止服务
pause
