@echo off
chcp 65001 >nul
echo ========================================
echo   Dao-Mind v2 — 打包构建
echo ========================================
echo.

set "ROOT=%~dp0"
set "DIST=%ROOT%dist\daomind"
set "EXE_DIST=%ROOT%dist\exe"

REM 清理旧包
if exist "%DIST%" (
    echo [INFO] 清理旧构建...
    rmdir /s /q "%DIST%"
)
if exist "%EXE_DIST%" (
    rmdir /s /q "%EXE_DIST%"
)

REM 创建目录结构
echo [INFO] 创建目录结构...
mkdir "%DIST%\backend\api"
mkdir "%DIST%\backend\rag"
mkdir "%DIST%\backend\clients"
mkdir "%DIST%\backend\services"
mkdir "%DIST%\data\rag_databases"

REM 1. 构建前端
echo.
echo [1/5] 构建前端...
cd /d "%ROOT%frontend"
if exist "node_modules" (
    call npx vite build --outDir dist
) else (
    echo [WARN] node_modules 未安装，跳过前端构建
    echo       请先运行: cd frontend ^&^& npm install
)
cd /d "%ROOT%"

REM 2. 复制后端
echo [2/5] 复制后端文件...
xcopy /y /q "%ROOT%backend\*.py" "%DIST%\backend\" >nul
xcopy /y /q "%ROOT%backend\api\*.py" "%DIST%\backend\api\" >nul
xcopy /y /q "%ROOT%backend\rag\*.py" "%DIST%\backend\rag\" >nul
xcopy /y /q "%ROOT%backend\clients\*.py" "%DIST%\backend\clients\" >nul
xcopy /y /q "%ROOT%backend\services\*.py" "%DIST%\backend\services\" >nul

REM 3. 复制前端构建产物
echo [3/5] 复制前端...
if exist "%ROOT%frontend\dist" (
    xcopy /e /y /q "%ROOT%frontend\dist\*" "%DIST%\frontend\dist\" >nul
)

REM 4. 复制数据和配置文件
echo [4/5] 复制数据和配置...
if exist "%ROOT%data\rag_databases" (
    xcopy /e /y /q "%ROOT%data\rag_databases\*" "%DIST%\data\rag_databases\" >nul
)
copy /y "%ROOT%requirements.txt" "%DIST%\" >nul
copy /y "%ROOT%.env.example" "%DIST%\" >nul
copy /y "%ROOT%start.bat" "%DIST%\" >nul

REM 写入版本信息
echo Dao-Mind v2 > "%DIST%\VERSION.txt"
echo Build: %date% %time% >> "%DIST%\VERSION.txt"

REM 5. PyInstaller 打包为 exe
echo.
echo [5/5] PyInstaller 打包 exe...
if exist "%ROOT%frontend\dist" (
    mkdir "%EXE_DIST%"
    cd /d "%ROOT%backend"
    python -m PyInstaller --onefile --console --name "DaoMind" ^
        --add-data "%ROOT%frontend\dist;frontend\dist" ^
        --add-data "%ROOT%data\rag_databases;data\rag_databases" ^
        --hidden-import uvicorn ^
        --hidden-import fastapi ^
        --hidden-import numpy ^
        --hidden-import cachetools ^
        --clean ^
        --noconfirm ^
        launcher.py 2>&1
    if exist "dist\DaoMind.exe" (
        copy /y "dist\DaoMind.exe" "%EXE_DIST%\" >nul
        echo [OK] DaoMind.exe 已生成
    )
    cd /d "%ROOT%"
) else (
    echo [SKIP] 前端未构建，跳过 exe 打包
)

echo.
echo ========================================
echo   打包完成
echo ========================================
echo.
echo   便携版: %DIST%
echo     - 复制到任意机器，安装依赖后双击 start.bat
echo.
if exist "%EXE_DIST%\DaoMind.exe" (
    echo   单文件版: %EXE_DIST%\DaoMind.exe
    echo     - 单个 exe，双击即用，无需安装任何依赖
)
echo.
pause
