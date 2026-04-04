@echo off
chcp 65001 >nul 2>&1
title MindJournal Server
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 请从 https://www.python.org/downloads/ 下载安装
    pause
    exit /b 1
)

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [OK] 虚拟环境已激活
) else (
    echo [警告] 未找到 .venv，将使用系统 Python
    echo 建议先运行: python -m venv .venv
)

echo.
echo ========================================
echo    MindJournal AI - Backend Server
echo ========================================
echo.
echo    Backend:  http://127.0.0.1:8000
echo    Swagger:  http://127.0.0.1:8000/docs
echo    Health:   http://127.0.0.1:8000/api/health
echo.
echo    保持本窗口打开！
echo ========================================
echo.

python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1

echo.
echo [退出] 服务器已停止。
pause
