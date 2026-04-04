@echo off
chcp 65001 >nul
title MindJournal AI
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1

http://localhost:8000/


cd C:\Users\86136\Desktop\LLM心理\mindjournal-ai\backend; uvicorn app.main:app --reload --port 8000