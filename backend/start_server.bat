@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1 > server.log 2>&1