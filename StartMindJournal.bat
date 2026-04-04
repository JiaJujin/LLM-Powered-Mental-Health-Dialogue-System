@echo off
chcp 65001 >nul
title MindJournal AI - 启动器
cd /d "%~dp0"

echo ========================================
echo        MindJournal AI 启动器
echo ========================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [1/3] 准备后端...
cd /d "%~dp0backend"
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] pip 安装失败
    pause
    exit /b 1
)

if not exist "%~dp0frontend\dist\index.html" (
    echo [2/3] 首次运行：正在构建前端...
    where node >nul 2>nul
    if %errorlevel% neq 0 (
        echo [错误] 需要 Node.js 才能生成前端页面。请安装 https://nodejs.org
        pause
        exit /b 1
    )
    cd /d "%~dp0frontend"
    call npm install
    call npm run build
    if %errorlevel% neq 0 (
        echo [错误] 前端构建失败
        pause
        exit /b 1
    )
) else (
    echo [2/3] 前端已构建 (frontend\dist)
)

echo [3/3] 启动服务并打开浏览器...
echo.
echo 正在启动服务器并检查...
start "MindJournal Server" "%~dp0backend\run_uvicorn.bat"

set /a count=0
:wait_loop
timeout /t 2 /nobreak >nul
set /a count+=2
powershell -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:8000' -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if %errorlevel% equ 0 goto server_ready
if %count% lss 30 goto wait_loop

echo.
echo [警告] 服务器可能未启动，请在 "MindJournal Server" 窗口查看错误
set /p =按回车键打开浏览器<nul
start http://127.0.0.1:8000
goto end

:server_ready
echo.
echo [OK] 服务器已就绪！
start http://127.0.0.1:8000

:end
echo.
echo ========================================
echo   已启动。地址: http://127.0.0.1:8000
echo   请保持 MindJournal Server 窗口打开
echo ========================================
pause
