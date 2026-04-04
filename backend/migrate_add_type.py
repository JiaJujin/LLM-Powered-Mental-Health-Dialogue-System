"""
One-time migration: backfill type='chat' for all existing ChatSession records
that have NULL in the type column.

Run once, then delete this file.
Safe to re-run (UPDATE is idempotent).
"""
from app.database import SessionLocal, engine
from app.models import Base, ChatSession
from sqlalchemy import text

def migrate():
    # Ensure the column exists (SQLAlchemy will create it on next engine start,
    # but we also need to handle existing DBs where it might not be there yet)
    with engine.connect() as conn:
        # SQLite: add column if not exists (does not raise error if column exists)
        try:
            conn.execute(text(
                "ALTER TABLE chat_sessions ADD COLUMN type VARCHAR DEFAULT 'chat'"
            ))
            conn.commit()
            print("[migration] Added 'type' column to chat_sessions table.")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[migration] 'type' column already exists, skipping ADD COLUMN.")
            else:
                raise

    # Backfill NULL type values
    db = SessionLocal()
    try:
        updated = (
            db.query(ChatSession)
            .filter(ChatSession.type == None)  # noqa: E711  (SQLAlchemy NULL check)
            .update({"type": "chat"}, synchronize_session=False)
        )
        db.commit()
        print(f"[migration] Backfilled type='chat' for {updated} existing session(s).")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
