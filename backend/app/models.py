# backend/app/models.py
import json as _json
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    anon_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PreCheck(Base):
    __tablename__ = "prechecks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    body_feeling = Column(String)
    need = Column(String)
    emotion = Column(String)
    assigned_role = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    title = Column(String, nullable=True)
    mood = Column(String)
    weather = Column(String)
    entry_date = Column(String, nullable=True)  # User-selected date for the entry
    emotion_label = Column(String, nullable=True)
    risk_level = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # --- Multimodal support fields ---
    # Input source type: "text" | "voice" | "image"
    source_type = Column(String, default="text")
    # Raw transcript / OCR result before user confirmation
    original_input_text = Column(Text, nullable=True)
    # Final text after user editing/confirmation (may differ from content)
    final_text = Column(Text, nullable=True)
    # Path to stored original audio/image file
    source_file_path = Column(String, nullable=True)
    # JSON metadata: duration_seconds, ocr_confidence, ocr_pages, detected_language, etc.
    input_metadata = Column(Text, nullable=True)

    user = relationship("User")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("journal_entries.id"))
    round = Column(Integer)
    user_msg = Column(Text)
    ai_msg = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    generated_at = Column(DateTime, default=datetime.utcnow)

    llm_summary = Column(Text)
    emotional_patterns = Column(Text)
    common_themes = Column(Text)
    growth_observations = Column(Text)
    recommendations = Column(Text)

    # --- Cache freshness tracking ---
    # How many journal entries were used to generate this analysis
    source_entry_count = Column(Integer, default=0)
    # The latest journal entry ID at the time of generation
    latest_entry_id = Column(Integer, nullable=True)
    # When the latest source entry was created (UTC)
    latest_entry_created_at = Column(DateTime, nullable=True)
    # Total entries at generation time
    total_entries_at_time = Column(Integer, default=0)

    user = relationship("User")


class TherapySession(Base):
    """Model for tracking therapy dialogue sessions"""
    __tablename__ = "therapy_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)

    # Session state
    round_index = Column(Integer, default=1)  # 1=B1, 2=B2, 3=B3
    status = Column(String, default="active")  # active, completed, stopped
    last_assistant_mode = Column(String, nullable=True)  # B1, B2, B3

    # Context from submission
    journal_text = Column(Text)
    precheck_context = Column(Text)  # JSON string of precheck data
    selected_role = Column(String)
    risk_level = Column(Integer)
    emotion_label = Column(String)

    # Conversation history stored as JSON
    conversation_history = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
    journal_entry = relationship("JournalEntry")


# ---------------------------------------------------------------------------
# Standalone free-form chat sessions (separate from therapy sessions)
# ---------------------------------------------------------------------------

class ChatSession(Base):
    """Free-form chat sessions for the chatbot tab — survives page refresh."""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)   # public UUID shown to frontend
    anon_id = Column(String, index=True)                  # matches frontend anonId
    type = Column(String, default="chat")                 # "diary" | "chat" — which page owns this session
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    title = Column(String, nullable=True)                 # optional chat title (first user message)
    conversation_history = Column(Text)                  # JSON array of {role, content, created_at}
    diary_content = Column(Text, nullable=True)          # the diary entry associated with this session


# ---------------------------------------------------------------------------
# Crisis alerts — logged whenever LLM-based crisis detection is triggered
# ---------------------------------------------------------------------------

class CrisisAlert(Base):
    """Persisted record of every LLM-classified crisis event."""
    __tablename__ = "crisis_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)                      # matches frontend anonId
    source = Column(String)                                  # "diary" | "chat"
    triggered_at = Column(DateTime, default=datetime.utcnow)
    message_snippet = Column(String(500))                    # first 500 chars of triggering text
    status = Column(String, default="counselor_contacted")  # always saved as "contacted" (mock mode)
