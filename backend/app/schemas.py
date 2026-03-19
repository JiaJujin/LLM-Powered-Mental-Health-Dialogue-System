from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PrecheckRequest(BaseModel):
    anon_id: str
    body_feeling: str
    need: str
    emotion: str


class PrecheckResponse(BaseModel):
    role: str
    confidence: float
    reasons: str


class JournalRequest(BaseModel):
    anon_id: str
    content: str = Field(min_length=5)
    title: Optional[str] = None
    mood: Optional[str] = None
    weather: Optional[str] = None
    entry_date: Optional[str] = None  # Format: YYYY-MM-DD


class CrisisResult(BaseModel):
    risk_level: int
    trigger: str
    evidence: List[str]
    confidence: float


class TherapyRound(BaseModel):
    text: str
    raw_json: Dict[str, Any]


class JournalResponse(BaseModel):
    risk: CrisisResult
    rounds: Dict[str, TherapyRound]
    session_id: Optional[str] = None
    round_index: Optional[int] = 1


# ========== Therapy Session Schemas ==========

class TherapySessionCreate(BaseModel):
    """Schema for creating a therapy session"""
    session_id: str
    user_id: int
    journal_entry_id: Optional[int] = None
    journal_text: str
    precheck_context: str  # JSON string
    selected_role: str
    risk_level: int
    emotion_label: str


class TherapySessionResponse(BaseModel):
    """Schema for returning therapy session info"""
    session_id: str
    entry_id: int
    assistant_message: str
    round_index: int
    risk: CrisisResult
    emotion_label: str
    selected_role: str
    status: str


class ChatContinueRequest(BaseModel):
    """Schema for continuing a therapy chat"""
    session_id: str
    user_message: str


class GatingDecision(BaseModel):
    """Schema for gating decision output"""
    decision: str  # "READY_FOR_B2" | "STAY_IN_B1" | "READY_FOR_B3" | "STAY_IN_B2"
    reason: str
    evidence: List[str]
    followup_style: str


class ChatContinueResponse(BaseModel):
    """Schema for continuing therapy chat response"""
    assistant_message: str
    round_index: int
    status: str  # "active" | "completed"
    gating_decision: Optional[GatingDecision] = None


class InsightItem(BaseModel):
    date: str
    emotion_label: Optional[str] = None
    risk_level: Optional[int] = None
    summary: str


class InsightsRequest(BaseModel):
    anon_id: str


class InsightsResponse(BaseModel):
    total_entries: int
    current_streak: int
    top_mood: str
    emotion_distribution: Dict[str, int]
    risk_distribution: Dict[str, int]
    timeline: List[InsightItem]

    llm_summary: str
    emotional_patterns: str
    common_themes: str
    growth_observations: str
    recommendations: str
    affirmation: str
    focus_points: List[str]

    analysis_history: List[str]


# ========== History Schemas ==========

class JournalHistoryItem(BaseModel):
    """Schema for a history list item"""
    entry_id: int
    entry_date: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    mood: Optional[str] = None
    weather: Optional[str] = None
    preview: str  # First 100 characters of content


class JournalHistoryResponse(BaseModel):
    """Response for history list"""
    entries: List[JournalHistoryItem]
    total: int


class JournalEntryResponse(BaseModel):
    """Full journal entry for viewing"""
    entry_id: int
    entry_date: Optional[str] = None
    title: Optional[str] = None
    content: str
    mood: Optional[str] = None
    weather: Optional[str] = None
    emotion_label: Optional[str] = None
    risk_level: Optional[int] = None
    created_at: datetime
