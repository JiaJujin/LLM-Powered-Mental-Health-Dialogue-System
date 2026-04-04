from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
import mimetypes
import os
from pathlib import Path

# Windows 注册表常把 .js 映射成 text/plain，浏览器会拒绝 type=module（Strict MIME）
mimetypes.init()
for _strict in (True, False):
    mimetypes.add_type("application/javascript", ".js", strict=_strict)
    mimetypes.add_type("application/javascript", ".mjs", strict=_strict)
    mimetypes.add_type("text/css", ".css", strict=_strict)

from .database import Base, engine, run_schema_patch
from .routers import precheck, journal, insights, chat, chat_continue, multimodal, crisis, chat_sessions

run_schema_patch()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MindJournal AI (Zhipu)")

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


# ========== Health Check ==========
@app.get("/api/health")
async def health_check():
    from .config import settings
    return {
        "status": "ok",
        "api_key_configured": bool(settings.zhipu_api_key and settings.zhipu_api_key.strip()),
        "model": settings.zhipu_model,
    }


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    print(f"[MindJournal] Frontend mounted: {FRONTEND_DIST}")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(FRONTEND_DIST / "index.html"))

else:
    print(f"[MindJournal] Warning: Frontend dist not found: {FRONTEND_DIST}")
    print(f"[MindJournal] Please run: cd frontend && npm run build")
