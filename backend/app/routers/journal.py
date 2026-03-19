from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
import uuid
import re

from ..database import SessionLocal
from .. import models, schemas
from ..therapy_agent import agent

router = APIRouter(tags=["journal"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_emotion_congruence(user_text: str, b1_json: dict, emotion_direction: str) -> bool:
    """
    Validate that the generated response is emotionally congruent with user input.
    Returns True if validation passes, False if there's a mismatch.
    """
    b1_text = render_b1_text(b1_json).lower()
    user_text_lower = user_text.lower()
    
    # Keywords that indicate positive content in user input (simplified Chinese)
    positive_keywords = ["开心", "快乐", "愉快", "满足", "感恩", "感谢", "幸运", "幸福", "舒服", "轻松", "好", "棒", "赞", "不错", "顺利", "温暖", "平静", "放松", "满意", "欣慰"]
    # Keywords that indicate negative content in user input (simplified Chinese)
    negative_keywords = ["难过", "伤心", "生气", "愤怒", "焦虑", "担心", "害怕", "恐惧", "压力", "沮丧", "郁闷", "绝望", "痛苦", "难受", "不舒服", "疲惫", "累", "烦", "无奈", "无助"]
    
    # Check if user is positive/neutral
    user_has_explicit_negative = any(kw in user_text_lower for kw in negative_keywords)
    user_has_explicit_positive = any(kw in user_text_lower for kw in positive_keywords)
    
    # If user explicitly positive, check that B1 doesn't introduce unsupported negative
    if user_has_explicit_positive and not user_has_explicit_negative:
        # Problematic patterns that shouldn't appear in positive-grounded responses
        problematic_patterns = [
            r"壓力", r"焦慮", r"疲憊", r"消耗", r"累積", r"委屈", r"痛苦",
            r"難受", r"不舒服", r"負擔", r"無力", r"無助", r"絕望"
        ]
        for pattern in problematic_patterns:
            if re.search(pattern, b1_text):
                return False
    
    return True


def render_b1_text(b1_json: dict) -> str:
    parts = [
        b1_json.get("reflective_paraphrase", ""),
        b1_json.get("implicit_emotion", ""),
        b1_json.get("open_question", ""),
    ]
    return "\n".join([p.strip() for p in parts if p and p.strip()])


def render_b2_text(b2_json: dict) -> str:
    parts = [
        b2_json.get("distortion_reflect", ""),
        b2_json.get("normalization", ""),
        b2_json.get("socratic_question", ""),
    ]
    return "\n".join([p.strip() for p in parts if p and p.strip()])


def render_b3_text(b3_json: dict) -> str:
    parts = [
        b3_json.get("defusion_metaphor", ""),
        b3_json.get("observed_strength", ""),
        b3_json.get("value_connection", ""),
        b3_json.get("micro_action", ""),
    ]
    return "\n".join([p.strip() for p in parts if p and p.strip()])


def render_b1_followup_text(b1_json: dict) -> str:
    parts = [
        b1_json.get("reflective_acknowledgment", ""),
        b1_json.get("followup_question", ""),
    ]
    return "\n".join([p.strip() for p in parts if p and p.strip()])


def render_b2_followup_text(b2_json: dict) -> str:
    parts = [
        b2_json.get("acknowledgment", ""),
        b2_json.get("exploration_question", ""),
    ]
    return "\n".join([p.strip() for p in parts if p and p.strip()])


def has_unsafe_flags(result: dict) -> bool:
    flags = result.get("safety_flags", {})
    return any(bool(v) for v in flags.values())


def fallback_b1(emotion_direction: str = "neutral") -> dict:
    """Fallback B1 response - emotionally neutral based on detected direction"""
    if emotion_direction == "positive":
        return {
            "reflective_paraphrase": "谢谢你分享了这个愉快的时刻。",
            "implicit_emotion": "听起来这是一件让你感到开心或满足的事情。",
            "open_question": "可以多说说这个经历中让你最印象深刻的部分吗？",
            "safety_flags": {
                "advice": False,
                "diagnosis": False,
                "moral_judgement": False,
            },
        }
    elif emotion_direction == "negative":
        return {
            "reflective_paraphrase": "我看到你把这些感受认真写了下来。",
            "implicit_emotion": "这些经历对你来说似乎不容易。",
            "open_question": "如果你愿意，可以多说说最让你在意的那部分吗？",
            "safety_flags": {
                "advice": False,
                "diagnosis": False,
                "moral_judgement": False,
            },
        }
    else:
        # Neutral
        return {
            "reflective_paraphrase": "我收到你今天记录的内容了。",
            "implicit_emotion": "谢谢你分享今天的日常。",
            "open_question": "今天有什麼事情是讓你有特別感受的嗎？",
            "safety_flags": {
                "advice": False,
                "diagnosis": False,
                "moral_judgement": False,
            },
        }


def fallback_b2() -> dict:
    return {
        "distortion_reflect": "当你把这件事总结成一个很绝对的结论时，听起来像是很多压力一下子都压到了同一个判断上。",
        "socratic_question": "如果把时间拉长一点看，有没有出现过哪怕很小的例外，说明事情不完全只有这一种解释？",
        "normalization": "人在持续受压时，很容易把眼前最痛的部分当成全部。",
        "safety_flags": {
            "advice": False,
            "diagnosis": False,
            "invalidating": False,
        },
    }


def fallback_b3() -> dict:
    return {
        "defusion_metaphor": "也许这些念头像天气一样会很真实地出现，但它们出现，并不等于它们定义了你。",
        "observed_strength": "你能把这些感受说出来，本身就说明你在认真面对自己正在经历的事。",
        "value_connection": "从你写下的内容里，能感觉到你很在乎自己是否被理解、被认真对待。",
        "micro_action": "如果你愿意，也许这会儿最重要的不是立刻解决问题，而是先允许自己停在这里一会儿。",
        "safety_flags": {
            "advice": True,
            "coercive": False,
            "diagnosis": False,
        },
    }


def fallback_b1_followup() -> dict:
    return {
        "reflective_acknowledgment": "谢谢你的分享。",
        "followup_question": "愿意再多说一点吗？",
        "safety_flags": {
            "advice": False,
            "diagnosis": False,
            "moral_judgement": False,
        },
    }


def fallback_b2_followup() -> dict:
    return {
        "acknowledgment": "感谢你的分享。",
        "exploration_question": "关于这个想法，你能再多说一些吗？",
        "safety_flags": {
            "advice": False,
            "diagnosis": False,
            "invalidating": False,
        },
    }


@router.post("/journal", response_model=schemas.JournalResponse)
async def submit_journal(req: schemas.JournalRequest, db: Session = Depends(get_db)):
    # Get or create user
    user = db.query(models.User).filter_by(anon_id=req.anon_id).first()
    if not user:
        # Create user if not exists
        user = models.User(anon_id=req.anon_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Get latest precheck (optional - use defaults if not found)
    latest_precheck = (
        db.query(models.PreCheck)
        .filter_by(user_id=user.id)
        .order_by(models.PreCheck.id.desc())
        .first()
    )

    # Use defaults if no precheck
    if latest_precheck:
        context = {
            "assigned_role": latest_precheck.assigned_role,
            "body": latest_precheck.body_feeling,
            "need": latest_precheck.need,
            "emotion": latest_precheck.emotion,
            "weekly_summary": ""
        }
        precheck_json = json.dumps({
            "body": latest_precheck.body_feeling,
            "need": latest_precheck.need,
            "emotion": latest_precheck.emotion,
            "assigned_role": latest_precheck.assigned_role
        })
    else:
        context = {
            "assigned_role": "Emotional Support",
            "body": "Unknown",
            "need": "Unknown",
            "emotion": "Unknown",
            "weekly_summary": ""
        }
        precheck_json = json.dumps({
            "body": "Unknown",
            "need": "Unknown",
            "emotion": "Unknown",
            "assigned_role": "Emotional Support"
        })

    # 1) 情绪分类 (用于锚定回复方向)
    try:
        emotion_result = await agent.classify_emotion(req.content)
        emotion_label = emotion_result.get("emotion_label", "Neutral")
        emotion_confidence = emotion_result.get("confidence", 0.5)
        emotion_reason = emotion_result.get("reason", "")
    except Exception:
        emotion_result = {
            "emotion_label": "Neutral",
            "confidence": 0.5,
            "reason": "模型分类失败，已回退到默认标签。"
        }
        emotion_label = "Neutral"
        emotion_confidence = 0.5
        emotion_reason = ""

    # Add emotion grounding to context for B1 generation
    emotion_direction = "neutral"
    if emotion_label in ["Happy", "Calm", "Grateful"]:
        emotion_direction = "positive"
    elif emotion_label in ["Sad", "Anxious", "Angry"]:
        emotion_direction = "negative"

    # Extend context with emotion grounding
    context = {**context, "emotion_direction": emotion_direction}

    # 2) 危机检测
    try:
        crisis_result_raw = await agent.detect_crisis(req.content)
        risk_level = int(crisis_result_raw.get("risk_level", 1))
    except Exception:
        crisis_result_raw = {
            "risk_level": 1,
            "trigger": "危机检测暂时失败，默认按低风险处理。",
            "evidence": [],
            "confidence": 0.5,
        }
        risk_level = 1

    # 3) 存日记
    journal_entry = models.JournalEntry(
        user_id=user.id,
        content=req.content,
        title=req.title,
        mood=req.mood or "",
        weather=req.weather or "",
        entry_date=req.entry_date,
        emotion_label=emotion_label,
        risk_level=risk_level,
    )
    db.add(journal_entry)
    db.commit()
    db.refresh(journal_entry)

    crisis_result = schemas.CrisisResult(
        risk_level=risk_level,
        trigger=crisis_result_raw.get("trigger", ""),
        evidence=crisis_result_raw.get("evidence", []),
        confidence=float(crisis_result_raw.get("confidence", 0.8)),
    )

    # 高风险直接返回，不继续治疗式生成
    if risk_level >= 3:
        return schemas.JournalResponse(
            risk=crisis_result,
            rounds={}
        )

    # 4) Generate ONLY B1 (first round) with validation
    b1_json = None
    b1_text = ""
    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            b1_json = await agent.run_b1(context, req.content)
            if has_unsafe_flags(b1_json):
                b1_json = fallback_b1(emotion_direction)
        except Exception:
            b1_json = fallback_b1(emotion_direction)
        
        # Validate emotional congruence
        if validate_emotion_congruence(req.content, b1_json, emotion_direction):
            break
        # If validation fails and we have attempts left, regenerate
        if attempt < max_attempts - 1:
            continue
    
    b1_text = render_b1_text(b1_json)

    # 5) Create therapy session
    session_id = str(uuid.uuid4())
    conversation_history = [
        {"role": "user", "content": req.content},
        {"role": "assistant", "content": b1_text, "mode": "B1"}
    ]

    therapy_session = models.TherapySession(
        session_id=session_id,
        user_id=user.id,
        journal_entry_id=journal_entry.id,
        round_index=1,
        status="active",
        last_assistant_mode="B1",
        journal_text=req.content,
        precheck_context=precheck_json,
        selected_role=context["assigned_role"],
        risk_level=risk_level,
        emotion_label=emotion_label,
        conversation_history=json.dumps(conversation_history),
    )
    db.add(therapy_session)
    db.commit()
    db.refresh(therapy_session)

    rounds = {
        "b1": schemas.TherapyRound(text=b1_text, raw_json=b1_json)
    }

    return schemas.JournalResponse(
        risk=crisis_result,
        rounds=rounds,
        session_id=session_id,
        round_index=1,
    )


# ========== History Endpoints ==========

@router.get("/journal/history", response_model=schemas.JournalHistoryResponse)
async def get_journal_history(
    anon_id: str,
    date_from: str = None,
    date_to: str = None,
    mood: str = None,
    db: Session = Depends(get_db)
):
    """Get journal history for a user with optional filters"""
    user = db.query(models.User).filter_by(anon_id=anon_id).first()
    if not user:
        return schemas.JournalHistoryResponse(entries=[], total=0)
    
    # Start with base query
    query = db.query(models.JournalEntry).filter_by(user_id=user.id)
    
    # Apply filters
    if date_from:
        query = query.filter(models.JournalEntry.entry_date >= date_from)
    if date_to:
        query = query.filter(models.JournalEntry.entry_date <= date_to)
    if mood:
        query = query.filter(models.JournalEntry.mood == mood)
    
    # Order by created_at descending
    entries = query.order_by(models.JournalEntry.created_at.desc()).all()
    
    history_items = []
    for entry in entries:
        # Strip HTML from content
        import re
        content_preview = entry.content or ""
        clean_preview = re.sub(r'<[^>]+>', '', content_preview)[:100]
        
        history_items.append(
            schemas.JournalHistoryItem(
                entry_id=entry.id,
                entry_date=entry.entry_date,
                title=entry.title,
                content=entry.content,
                mood=entry.mood,
                weather=entry.weather,
                preview=clean_preview
            )
        )
    
    return schemas.JournalHistoryResponse(entries=history_items, total=len(history_items))


@router.get("/journal/entry/{entry_id}", response_model=schemas.JournalEntryResponse)
async def get_journal_entry(
    entry_id: int,
    db: Session = Depends(get_db)
):
    """Get full journal entry by ID"""
    entry = db.query(models.JournalEntry).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return schemas.JournalEntryResponse(
        entry_id=entry.id,
        entry_date=entry.entry_date,
        title=entry.title,
        content=entry.content,
        mood=entry.mood,
        weather=entry.weather,
        emotion_label=entry.emotion_label,
        risk_level=entry.risk_level,
        created_at=entry.created_at
    )


@router.get("/journal/detail/{entry_id}")
async def get_journal_detail(
    entry_id: int,
    db: Session = Depends(get_db)
):
    """Get full journal entry with associated chat history"""
    entry = db.query(models.JournalEntry).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # Get therapy session for this journal entry
    session = db.query(models.TherapySession).filter_by(journal_entry_id=entry_id).first()
    
    chat_history = []
    if session and session.conversation_history:
        try:
            import json
            conv_history = json.loads(session.conversation_history)
            for msg in conv_history:
                chat_history.append({
                    "role": msg.get("role", "assistant"),
                    "content": msg.get("content", ""),
                    "mode": msg.get("mode")
                })
        except Exception:
            pass
    
    # Build response
    entry_response = schemas.JournalEntryResponse(
        entry_id=entry.id,
        entry_date=entry.entry_date,
        title=entry.title,
        content=entry.content,
        mood=entry.mood,
        weather=entry.weather,
        emotion_label=entry.emotion_label,
        risk_level=entry.risk_level,
        created_at=entry.created_at
    )
    
    return {
        "entry": entry_response,
        "chat_history": chat_history
    }
