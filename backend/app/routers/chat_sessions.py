"""
Chat session persistence — survives page refresh.

Routes:
  POST /api/chat/sessions                  — create a new free-form chat session
  GET  /api/chat/sessions/{anon_id}          — get all sessions for a user
  GET  /api/chat/sessions/{anon_id}/latest  — get the most recent session + messages
  GET  /api/chat/sessions/detail/{session_id} — get a specific session with messages
  POST /api/chat/sessions/{session_id}      — append a message to a session
  PATCH /api/chat/sessions/{session_id}/title — update session title

Note: These are for standalone free-form chatbot sessions.
Therapy sessions (journal-triggered) are handled by /chat/continue.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models, schemas

router = APIRouter(prefix="/api/chat", tags=["chat-sessions"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Create a new session
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=schemas.ChatSessionCreateResponse)
async def create_session(req: schemas.ChatSessionCreate, db: Session = Depends(get_db)) -> schemas.ChatSessionCreateResponse:
    """
    Create a brand-new free-form chat session for the given anon_id.
    """
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()

    session = models.ChatSession(
        session_id=session_id,
        anon_id=req.anon_id,
        type=req.type,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    print(f"[CHAT/SESSIONS] created  session_id={session_id}  anon_id={req.anon_id}  type={req.type}")

    return schemas.ChatSessionCreateResponse(
        session_id=session_id,
        created_at=session.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Get all sessions for a user
# ---------------------------------------------------------------------------

@router.get("/sessions/{anon_id}")
async def get_all_sessions(anon_id: str, type: str | None = None, db: Session = Depends(get_db)) -> dict:
    """
    Return all chat sessions for a user (newest first).
    Optionally filter by session type ("diary" | "chat").
    """
    query = db.query(models.ChatSession).filter_by(anon_id=anon_id)
    if type is not None:
        query = query.filter_by(type=type)
    sessions = (
        query
        .order_by(models.ChatSession.updated_at.desc())
        .all()
    )

    def last_preview(session: models.ChatSession) -> str | None:
        msgs = _load_messages(session)
        if not msgs:
            return None
        last = msgs[-1]
        content: str = last.get("content", "")
        return (content[:30] + "…") if len(content) > 30 else content

    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "title": s.title,
                "type": s.type,
                "last_message_preview": last_preview(s),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ]
    }


# ---------------------------------------------------------------------------
# Get the latest session (or create one if none exists)
# ---------------------------------------------------------------------------

@router.get(
    "/sessions/{anon_id}/latest",
    response_model=schemas.ChatSessionResponse | schemas.ChatSessionCreateResponse,
)
async def get_or_create_latest_session(anon_id: str, type: str | None = None, db: Session = Depends(get_db)):
    """
    Return the most recently active session with its full message history.
    If no session exists and a type is provided, create one automatically.
    Optionally filter by session type ("diary" | "chat").
    """
    query = db.query(models.ChatSession).filter_by(anon_id=anon_id)
    if type is not None:
        query = query.filter_by(type=type)
    session = (
        query
        .order_by(models.ChatSession.updated_at.desc())
        .first()
    )

    if not session:
        # Auto-create a new session for this anon_id
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        session = models.ChatSession(
            session_id=session_id,
            anon_id=anon_id,
            type=type or "chat",
            created_at=now,
            updated_at=now,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        print(f"[CHAT/SESSIONS] auto-created  session_id={session_id}  anon_id={anon_id}  type={session.type}")
        return schemas.ChatSessionCreateResponse(
            session_id=session_id,
            created_at=session.created_at.isoformat(),
        )

    # Parse messages from JSON text field
    messages = _load_messages(session)

    print(
        f"[CHAT/SESSIONS] latest  session_id={session.session_id}  "
        f"messages={len(messages)}  anon_id={anon_id}"
    )

    return schemas.ChatSessionResponse(
        session_id=session.session_id,
        anon_id=session.anon_id,
        title=session.title,
        diary_content=session.diary_content,
        messages=messages,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Append messages to a session
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}", response_model=schemas.ChatAppendResponse)
async def append_messages(
    session_id: str,
    req: schemas.ChatAppendMessage,
    db: Session = Depends(get_db),
) -> schemas.ChatAppendResponse:
    """
    Append a single message (user or assistant) to an existing session.
    Also sets the session title from the first user message.
    """
    session = (
        db.query(models.ChatSession)
        .filter_by(session_id=session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.utcnow()

    # Load existing messages
    messages = _load_messages(session)

    # Build new message
    new_msg = {
        "role": req.role,
        "content": req.content,
        "created_at": now.isoformat(),
    }
    messages.append(new_msg)

    # Set title and diary_content from first user message
    if req.role == "user":
        if session.title is None:
            session.title = req.content[:60]
        if session.diary_content is None and req.diary_content:
            session.diary_content = req.diary_content

    session.conversation_history = _save_messages(messages)
    session.updated_at = now

    db.commit()
    db.refresh(session)

    print(
        f"[CHAT/SESSIONS] appended  session_id={session_id}  "
        f"role={req.role}  total_messages={len(messages)}"
    )

    return schemas.ChatAppendResponse(messages=messages)


# ---------------------------------------------------------------------------
# Get a single session with its messages (for loading a past session)
# ---------------------------------------------------------------------------

@router.get("/sessions/detail/{session_id}", response_model=schemas.ChatSessionResponse)
async def get_session_detail(session_id: str, db: Session = Depends(get_db)) -> schemas.ChatSessionResponse:
    """
    Return a specific chat session with its full message history.
    Used by the frontend to load a session from the history sidebar.
    """
    session = (
        db.query(models.ChatSession)
        .filter_by(session_id=session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = _load_messages(session)

    print(
        f"[CHAT/SESSIONS] detail  session_id={session_id}  "
        f"messages={len(messages)}"
    )

    return schemas.ChatSessionResponse(
        session_id=session.session_id,
        anon_id=session.anon_id,
        title=session.title,
        diary_content=session.diary_content,
        messages=messages,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Update session title
# ---------------------------------------------------------------------------

@router.patch("/sessions/{session_id}/title")
async def update_session_title(
    session_id: str,
    req: schemas.ChatSessionTitleUpdate,
    db: Session = Depends(get_db),
) -> dict:
    """
    Update the title of an existing chat session.
    """
    session = (
        db.query(models.ChatSession)
        .filter_by(session_id=session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.title = req.title
    session.updated_at = datetime.utcnow()
    db.commit()

    print(f"[CHAT/SESSIONS] title updated  session_id={session_id}  title={req.title!r}")

    return {"ok": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_messages(session: models.ChatSession) -> list:
    """Load message list from session.conversation_history (JSON text column)."""
    import json
    raw = session.conversation_history or "[]"
    try:
        return json.loads(raw)
    except Exception:
        return []


def _save_messages(messages: list) -> str:
    """Serialize message list to JSON string for storage."""
    import json
    return json.dumps(messages, ensure_ascii=False)
