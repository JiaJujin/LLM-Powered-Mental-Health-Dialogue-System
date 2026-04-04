"""
Vercel Serverless Entry Point for MindJournal AI Backend
适配 Vercel 无服务器环境（无状态、无持久化文件系统）

注意：Vercel Serverless 环境下 SQLite 数据库不会持久化！
如需持久化，请使用 Railway（已配置好 railway.json）或云数据库。
"""
import sys
import os
from pathlib import Path

# Ensure backend/app is on the Python path
_backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_backend_dir.parent))

# Set environment variable to indicate serverless mode
os.environ["VERCEL_SERVERLESS"] = "1"

# Patch database to use in-memory SQLite for serverless
os.environ.setdefault("DATABASE_URL", "sqlite:///./:memory:")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import mimetypes

# Windows mimetypes fix
mimetypes.init()
for strict in (True, False):
    mimetypes.add_type("application/javascript", ".js", strict=strict)
    mimetypes.add_type("application/javascript", ".mjs", strict=strict)
    mimetypes.add_type("text/css", ".css", strict=strict)

from app.database import Base, engine
from app.routers import precheck, journal, insights, chat, chat_continue, multimodal, crisis, chat_sessions

app = FastAPI(title="MindJournal AI (Vercel Serverless)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(precheck.router, prefix="/api")
app.include_router(journal.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(chat_continue.router, prefix="/api")
app.include_router(multimodal.router, prefix="/api")
app.include_router(crisis.router)
app.include_router(chat_sessions.router)


@app.get("/api/health")
async def health_check():
    from app.config import settings
    api_key_ok = bool(settings.zhipu_api_key and settings.zhipu_api_key.strip())
    return JSONResponse({
        "status": "ok",
        "vercel_serverless": True,
        "api_key_configured": api_key_ok,
        "model": settings.zhipu_model,
        "warning": "Vercel serverless mode - database is IN-MEMORY and will NOT persist data!",
    })


@app.get("/")
async def root():
    return JSONResponse({
        "name": "MindJournal AI Backend",
        "version": "1.0.0",
        "mode": "vercel-serverless",
        "docs": "/api/health",
        "warning": "Database does not persist in Vercel serverless. Use Railway for production.",
    })


# Vercel serverless handler
_handler = None


def handler(event, context):
    """
    Vercel Python runtime handler.
    Receives AWS Lambda-compatible event/context objects.
    """
    global _handler
    if _handler is None:
        # Create table schemas on first cold start
        try:
            Base.metadata.create_all(bind=engine)
            print("[Vercel] Database tables initialized")
        except Exception as e:
            print(f"[Vercel] Database init warning: {e}")

        # Import and wrap with mangum for ASGI->WSGI conversion
        from mangum import Mangum
        _handler = Mangum(app, lifespan="auto")
        print("[Vercel] Mangum handler initialized")

    return _handler(event, context)
