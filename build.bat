@echo off
chcp 65001 >nul
echo ========================================
echo   道心 · Dao-Mind v2 — 桌面应用打包
echo ========================================
echo.

set "ROOT=%~dp0"
set "EXE_DIST=%ROOT%dist\exe"

REM 清理旧包
if exist "%EXE_DIST%" (
    echo [INFO] 清理旧构建...
    rmdir /s /q "%EXE_DIST%"
)

REM 1. 构建前端
echo [1/3] 构建前端...
cd /d "%ROOT%frontend"
if exist "node_modules" (
    call npx vite build --outDir dist
) else (
    echo [WARN] 先安装前端依赖: cd frontend ^&^& npm install
    pause
    exit /b 1
)
cd /d "%ROOT%"

REM 2. 同步前端到后端 static
echo [2/3] 同步前端...
if exist "backend\static" rmdir /s /q "backend\static"
xcopy /e /i /y /q "frontend\dist\*" "backend\static\" >nul

REM 3. PyInstaller 打包
echo [3/3] 打包桌面应用...
mkdir "%EXE_DIST%" 2>nul
cd /d "%ROOT%backend"

"C:\Users\金许诺\AppData\Local\Programs\Python\Python311\python.exe" -m PyInstaller --onefile --windowed --name "DaoMind" ^
    --add-data "%ROOT%frontend\dist;frontend\dist" ^
    --add-data "%ROOT%data\rag_databases;data\rag_databases" ^
    --hidden-import uvicorn ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import fastapi ^
    --hidden-import pydantic ^
    --hidden-import numpy ^
    --hidden-import cachetools ^
    --hidden-import webview ^
    --hidden-import webview.platforms.edgechromium ^
    --clean ^
    --noconfirm ^
    desktop_launcher.py 2>&1

if exist "dist\DaoMind.exe" (
    copy /y "dist\DaoMind.exe" "%EXE_DIST%\" >nul
    echo.
    echo ========================================
    echo   打包成功!
    echo ========================================
    echo.
    echo   桌面应用: %EXE_DIST%\DaoMind.exe
    echo   双击即可使用，像普通软件一样
    echo.
) else (
    echo.
    echo [ERROR] 打包失败，请检查错误信息
    echo.
)
cd /d "%ROOT%"
pause
