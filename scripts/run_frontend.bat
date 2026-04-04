@echo off
chcp 65001 >nul 2>&1
title MindJournal AI - Frontend Dev Server
cd /d "%~dp0..\frontend"

echo ========================================
echo    MindJournal AI - Frontend Server
echo ========================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js is not installed. Please install from https://nodejs.org
    pause
    exit /b 1
)

REM Install dependencies if node_modules is missing
if not exist "node_modules" (
    echo [Step 1] Installing npm dependencies (first time only)...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed. Check your internet connection.
        pause
        exit /b 1
    )
)

echo [Step 2] Starting Vite dev server...
echo.
echo    Frontend: http://127.0.0.1:5173
echo    (Backend must be running at port 8000 for full functionality)
echo.
echo    Press Ctrl+C to stop the server.
echo ========================================
echo.

call npm run dev

echo.
echo Server stopped. Press any key to close this window...
pause >nul
