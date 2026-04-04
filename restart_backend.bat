@echo off
chcp 65001 >nul 2>&1
title MindJournal Backend

cd /d "%~dp0"

echo Stopping existing servers...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM uvicorn.exe 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Starting backend server...
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat >nul 2>&1
python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
