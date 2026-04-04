@echo off
chcp 65001 >nul 2>&1
title MindJournal AI - Launcher
cd /d "%~dp0"

echo ========================================
echo    MindJournal AI - One-Click Launcher
echo ========================================
echo.

REM ---- Step 1: Check prerequisites ----
echo [Step 1] Checking prerequisites...

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js is not installed. Please install from https://nodejs.org
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed. Please install from https://www.python.org
    pause
    exit /b 1
)

REM ---- Step 2: Backend setup ----
echo [Step 2] Setting up backend...
cd /d "%~dp0..\backend"

if not exist ".venv" (
    echo   Creating Python virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat >nul 2>&1

REM Check if dependencies are installed
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo   Installing Python dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install Python dependencies.
        pause
        exit /b 1
    )
)

REM ---- Step 3: Frontend setup ----
echo [Step 3] Setting up frontend...
cd /d "%~dp0..\frontend"

if not exist "node_modules" (
    echo   Installing npm dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install npm dependencies.
        pause
        exit /b 1
    )
)

REM ---- Step 4: Start servers ----
echo [Step 4] Starting servers...
echo.
echo   Starting backend server...
start "MindJournal-Backend" cmd /k "cd /d "%~dp0..\backend" && call .venv\Scripts\activate.bat >nul 2>&1 && python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1"

echo   Waiting for backend to start (5 seconds)...
timeout /t 5 /nobreak >nul

REM Check if backend is ready
powershell -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] Backend may not be ready yet. Please check the "MindJournal-Backend" window.
)

echo   Starting frontend server...
start "MindJournal-Frontend" cmd /k "cd /d "%~dp0..\frontend" && npm run dev"

echo.
echo ========================================
echo    MindJournal AI is starting!
echo ========================================
echo.
echo    Backend:  http://127.0.0.1:8000
echo    Frontend: http://127.0.0.1:5173
echo.
echo    Please open http://127.0.0.1:5173 in Chrome or Edge
echo    (NOT in Cursor's built-in preview)
echo.
echo    Keep both terminal windows open!
echo ========================================
echo.
pause
