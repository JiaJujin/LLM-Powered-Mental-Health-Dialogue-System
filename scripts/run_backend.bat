@echo off
chcp 65001 >nul 2>&1
title MindJournal AI - Backend Server
cd /d "%~dp0..\backend"

echo ========================================
echo    MindJournal AI - Backend Server
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo [Step 1] Creating Python virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Make sure Python 3.10+ is installed.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [Step 2] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check Python
python --version

REM Install dependencies if needed
echo [Step 3] Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [Step 3] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies. Check your internet connection.
        pause
        exit /b 1
    )
)

echo [Step 4] Starting FastAPI server...
echo.
echo    Backend:  http://127.0.0.1:8000
echo    Swagger:  http://127.0.0.1:8000/docs
echo    Health:   http://127.0.0.1:8000/api/health
echo.
echo    Press Ctrl+C to stop the server.
echo ========================================
echo.

python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1

echo.
echo Server stopped. Press any key to close this window...
pause >nul
