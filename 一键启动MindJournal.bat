@echo off
chcp 65001 >nul 2>&1
title MindJournal AI

cd /d "%~dp0backend"

echo ================================================================
echo.
echo                       MindJournal AI
echo                   Backend Server Launcher
echo.
echo ================================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo  [错误] 未找到 Python，请先安装 Python 3.10+
    echo          https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv" (
    echo  [1/3] 首次运行：正在创建虚拟环境...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo  [2/3] 正在安装依赖（仅首次运行）...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo  [错误] pip 安装失败，请检查网络连接
    pause
    exit /b 1
)

echo.
echo ================================================================
echo.
echo  [3/3] 正在启动服务器，请稍候...
echo.
echo ================================================================
echo.

start "" cmd /c "title MindJournal Server && chcp 65001 >nul && .venv\Scripts\activate.bat >nul && python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1"

echo  等待服务器启动（最多 30 秒）...
set /a count=0
:wait_loop
timeout /t 2 /nobreak >nul
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:8000' -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if %errorlevel% equ 0 goto server_ready
set /a count+=2
if %count% lss 30 goto wait_loop

echo.
echo  [警告] 服务器可能未正常启动，请查看弹出的 "MindJournal Server" 窗口排查错误
echo.
set /p =按回车键手动打开浏览器 <nul
start http://127.0.0.1:8000
pause
exit /b 0

:server_ready
echo.
echo.
echo  ================================================================
echo.
echo   [OK] MindJournal 已启动
echo.
echo   前端页面：http://localhost:8000
echo   后端文档：http://localhost:8000/docs
echo.
echo   保持本窗口打开即可使用。
echo   关闭本窗口 = 停止服务，下次重新双击此文件即可。
echo.
echo  ================================================================
echo.
start http://127.0.0.1:8000
pause


http://localhost:8000 瀏覽器打開
