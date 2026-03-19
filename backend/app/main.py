from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .routers import precheck, journal, insights, chat, chat_continue

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MindJournal AI (Nemotron)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(precheck.router, prefix="/api")
app.include_router(journal.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(chat_continue.router, prefix="/api")
