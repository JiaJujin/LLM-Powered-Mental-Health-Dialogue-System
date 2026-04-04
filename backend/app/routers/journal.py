from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from datetime import datetime, timedelta
from collections import Counter
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


# =============================================================================
# Background analysis refresh — triggered after journal create / delete / update
# =============================================================================
async def _refresh_insights_background(anon_id: str) -> None:
    """
    Background task: regenerate insights for a user after their journal changes.
    This runs asynchronously so it doesn't block the journal submission response.
    """
    print(f"[BG_ANALYSIS] starting background refresh for anon_id={anon_id}")
    db_gen = SessionLocal()
    try:
        user = db_gen.query(models.User).filter_by(anon_id=anon_id).first()
        if not user:
            print(f"[BG_ANALYSIS] user not found: {anon_id}")
            return

        fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
        all_entries = (
            db_gen.query(models.JournalEntry)
            .filter(models.JournalEntry.user_id == user.id)
            .filter(
                (models.JournalEntry.created_at >= fourteen_days_ago)
                | (models.JournalEntry.entry_date.is_(None))
                | (models.JournalEntry.entry_date >= fourteen_days_ago.date().isoformat())
            )
            .order_by(models.JournalEntry.created_at.asc())
            .all()
        )

        if not all_entries:
            print(f"[BG_ANALYSIS] no entries in window — skipping analysis refresh")
            return

        # Build stats and journal text
        mood_counter = Counter()
        risk_counter = Counter()
        for e in all_entries:
            raw_mood = getattr(e, "mood", "") or ""
            mood_label = raw_mood.strip() if raw_mood.strip() else (e.emotion_label or "Unknown")
            risk_label = f"Level {e.risk_level}" if e.risk_level is not None else "Unknown"
            mood_counter[mood_label] += 1
            risk_counter[risk_label] += 1

        journal_lines = []
        for e in all_entries:
            summary = (e.content or "").strip().replace("\n", " ")[:140]
            journal_lines.append(
                f"Date: {e.created_at.strftime('%Y-%m-%d')} | Mood: {e.emotion_label or 'Unknown'} | Risk: {e.risk_level} | {summary}"
            )
        journal_text = "\n".join(journal_lines)
        journal_sample = " ".join(e.content or "" for e in all_entries if e.content)[:200]

        llm_user_input = (
            f"Analyze all diary entries from the last 14 days. There are {len(all_entries)} entries.\n\n"
            f"Diary entries:\n{journal_text}\n\n"
            f"Emotion distribution: {', '.join(f'{k}: {v}' for k, v in mood_counter.items()) or 'None recorded'}\n"
            f"Risk distribution: {', '.join(f'{k}: {v}' for k, v in risk_counter.items()) or 'None recorded'}"
        )

        try:
            raw_result = await agent.generate_insights(llm_user_input, journal_content_sample=journal_sample)
            print(f"[BG_ANALYSIS] generate_insights returned, keys={list(raw_result.keys())}")
        except Exception as ex:
            print(f"[BG_ANALYSIS] generate_insights failed: {ex}")
            raw_result = {}

        def _extract(r: dict) -> dict:
            return {
                "llm_summary": r.get("summary") or r.get("llm_summary") or "",
                "emotional_patterns": r.get("emotional_patterns") or r.get("emotion_patterns") or "",
                "common_themes": r.get("common_themes") or r.get("themes") or "",
                "growth_observations": r.get("growth_observations") or r.get("growth") or "",
                "recommendations": r.get("recommendations") or "",
                "affirmation": r.get("affirmation") or "",
                "focus_points": r.get("focus_points") or [],
            }

        llm = _extract(raw_result)
        latest_entry = (
            db_gen.query(models.JournalEntry)
            .filter(models.JournalEntry.user_id == user.id)
            .order_by(models.JournalEntry.created_at.desc())
            .first()
        )

        new_history = models.AnalysisHistory(
            user_id=user.id,
            llm_summary=llm["llm_summary"],
            emotional_patterns=llm["emotional_patterns"],
            common_themes=llm["common_themes"],
            growth_observations=llm["growth_observations"],
            recommendations=llm["recommendations"],
        )
        # Only set cache-tracking fields if the columns exist in the DB.
        # This allows the refresh to succeed even if the old SQLite file
        # was not patched before this background task ran.
        try:
            new_history.source_entry_count = len(all_entries)
            new_history.latest_entry_id = latest_entry.id if latest_entry else None
            new_history.latest_entry_created_at = latest_entry.created_at if latest_entry else None
            new_history.total_entries_at_time = len(all_entries)
        except AttributeError:
            print("[BG_ANALYSIS] source_entry_count/latest_entry_id columns not found in DB — skipping cache fields")
        db_gen.add(new_history)
        db_gen.commit()
        print(f"[BG_ANALYSIS] saved new analysis  id={new_history.id}  entries={len(all_entries)}")
    except Exception as ex:
        print(f"[BG_ANALYSIS] unexpected error: {ex}")
        db_gen.rollback()
    finally:
        db_gen.close()


def validate_emotion_congruence(user_text: str, b1_json: dict, emotion_direction: str) -> bool:
    """
    检查生成回应是否与用户原文的 valence / intensity / eventfulness 一致。

    关键规则：
    1. 用户原文是 neutral + ordinary，不允许追问"特别感受"
    2. 用户说"没特别/普通/平常"，不能脑补出"压力/挣扎/不愉快"
    3. 不能出现模板式空泛开场白（"谢谢分享""我收到了你今天的内容"）
    4. reflective_paraphrase 至少要提及用户原文中的具体事实或措辞
    """
    user_text_lower = user_text.lower()

    # ---- 检测用户原文特征 ----
    ordinary_markers = [
        "平常", "普通", "没什么特别", "没特别", "没啥特别", "没什么", "没什么事",
        "没啥事", "平常一天", "就那样", "就这样", "没意思", "还好", "还行",
        "没什么大", "就那样", "一般般", "差不多", "没变化", "平平静静",
        "热", "冷", "忙", "闲", "累", "困"
    ]
    user_is_ordinary = any(m in user_text_lower for m in ordinary_markers) and len(user_text.strip()) < 100

    positive_keywords = ["开心", "快乐", "愉快", "满足", "感恩", "感谢", "幸运", "幸福", "舒服", "轻松", "好", "棒", "赞", "不错", "顺利", "温暖", "平静", "放松", "满意", "欣慰"]
    negative_keywords = ["难过", "伤心", "生气", "愤怒", "焦虑", "担心", "害怕", "恐惧", "压力", "沮丧", "郁闷", "绝望", "痛苦", "难受", "不舒服", "疲惫", "烦", "无奈", "无助"]

    user_has_explicit_negative = any(kw in user_text_lower for kw in negative_keywords)
    user_has_explicit_positive = any(kw in user_text_lower for kw in positive_keywords)
    user_is_neutral = not user_has_explicit_negative and not user_has_explicit_positive

    # ---- 渲染 B1 全文 ----
    b1_text = render_b1_text(b1_json).lower()

    # ---- 规则 1：用户说没特别，追问"特别感受"就是冲突 ----
    if user_is_ordinary and user_is_neutral:
        special_question_markers = ["特别感受", "特别的事", "特别感受", "特別的事", "什么特别", "什么事情", "有什么感触", "有感触", "有什么让你"]
        for marker in special_question_markers:
            if marker in b1_text:
                print(f"[VALIDATE] [REJECT] ordinary user asked about special feelings: {marker}")
                return False

        # 规则 2：不能在普通日记里脑补压力/负面
        implied_negative_markers = ["壓力", "焦慮", "疲憊", "消耗", "累積", "委屈", "痛苦", "難受", "不舒服", "負擔", "無力", "無助", "絕望", "挣扎", "压抑", "沉闷"]
        for marker in implied_negative_markers:
            if marker in b1_text:
                print(f"[VALIDATE] [REJECT] ordinary diary but reply introduced negative: {marker}")
                return False

    # ---- 规则 3：禁止模板式空泛开场白 ----
    template_openings = ["谢谢你的分享", "谢谢你分享", "我收到了你今天", "感谢你的", "谢谢你告诉我", "感谢分享", "谢谢告知"]
    for opening in template_openings:
        if b1_text.startswith(opening) or b1_text.startswith(opening.lower()):
            print(f"[VALIDATE] [REJECT] used template opening: {opening}")
            return False

    # ---- 规则 4：reflective_paraphrase 不能是纯空泛句 ----
    paraphrased = (b1_json.get("reflective_paraphrase") or "").lower()
    generic_paraphrase_markers = ["分享", "告诉我", "你说了", "你的内容", "今天的内容", "记录的"]
    # 如果整个 paraphrase 只有这些词，没有引用原文具体内容，视为空泛
    has_content = any(kw in paraphrased for kw in ["今天", "天", "热", "冷", "忙", "闲", "平常", "普通", "还", "好", "没", "说"])
    if all(kw in paraphrased for kw in generic_paraphrase_markers) and not has_content:
        print(f"[VALIDATE] [REJECT] reflective_paraphrase too generic, no content from original text")
        return False

    # ---- 规则 5：用户有正面情绪，回复不能引入未证实的负面 ----
    if user_has_explicit_positive and not user_has_explicit_negative:
        problematic_patterns = [
            r"壓力", r"焦慮", r"疲憊", r"消耗", r"累積", r"委屈", r"痛苦",
            r"難受", r"不舒服", r"負擔", r"無力", r"無助", r"絕望",
            r"挣扎", r"压抑", r"沉闷"
        ]
        for pattern in problematic_patterns:
            if re.search(pattern, b1_text):
                print(f"[VALIDATE] [REJECT] positive user, reply introduced pattern: {pattern}")
                return False

    print(f"[VALIDATE] [PASS] emotion_dir={emotion_direction}  ordinary={user_is_ordinary}  neutral={user_is_neutral}")
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
        # Neutral — handle both ordinary平淡日子 and active neutral
        return {
            # 不再用「谢谢分享」「我收到了」开头 — 太模板化
            "reflective_paraphrase": "你说今天和平时差不多，没什么特别的事发生。",
            # 不强行加情绪 — 原文是 neutral 就保持 neutral
            "implicit_emotion": "听起来这一天平静、没什么波澜。",
            # 不追问"特别感受" — 如果用户说没特别，就问平常状态
            "open_question": "这样的平常一天，对你来说感觉怎么样？",
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
    """Called when B1 followup LLM call fails. Use honest fallback, not template."""
    print("[FALLBACK] B1 followup failed, using fallback response")
    return {
        "reflective_acknowledgment": "谢谢你告诉我这些。",
        "followup_question": "刚才说的这件事里，你最在意的是什么呢？",
        "safety_flags": {
            "advice": False,
            "diagnosis": False,
            "moral_judgement": False,
        },
    }


def fallback_b2_followup() -> dict:
    """Called when B2 followup LLM call fails."""
    print("[FALLBACK] B2 followup failed, using fallback response")
    return {
        "acknowledgment": "感谢你的回应。",
        "exploration_question": "你刚才提到的这个想法，对你来说意味着什么？",
        "safety_flags": {
            "advice": False,
            "diagnosis": False,
            "invalidating": False,
        },
    }


@router.post("/journal", response_model=schemas.JournalResponse)
async def submit_journal(
    req: schemas.JournalRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
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

    # ---- pre-analysis: eventfulness 检测（内部使用，不暴露给前端） ----
    # 用于告知 LLM：这是普通平常日还是有具体内容的一天
    # 关键词只作为辅助，最终由模型判断是否有值得展开的内容
    ordinary_markers = ["平常", "普通", "没什么特别", "没特别", "没啥特别", "没什么",
                         "没啥事", "平常一天", "就那样", "就这样", "没意思", "还好", "还行",
                         "没什么大", "一般般", "差不多", "没变化", "平平静静", "无事发生"]
    user_text_lower_check = req.content.lower()
    # 只有同时满足：含普通关键词 AND 文本较短（<100字），才判定为 ordinary
    # 纯关键词匹配不可靠——"我今天没发生什么特别的事，但我其实很难过"不应被判定为 ordinary
    is_ordinary = (
        any(m in user_text_lower_check for m in ordinary_markers)
        and len(req.content.strip()) < 100
        # 排除句中含明确情绪词的情况（即使短也视为 notable）
        and not any(
            kw in user_text_lower_check
            for kw in ["难过", "伤心", "累", "焦虑", "害怕", "生气", "烦", "失望", "无奈",
                       "sad", "tired", "anxious", "fear", "angry", "lonely", "绝望", "无聊"]
        )
    )
    eventfulness_label = "ordinary" if is_ordinary else "notable"
    print(f"[JOURNAL] pre-analysis  emotion_label={emotion_label}  eventfulness={eventfulness_label}  text_len={len(req.content)}")

    # Extend context with emotion grounding and eventfulness
    context = {
        **context,
        "emotion_direction": emotion_direction,
        "eventfulness": eventfulness_label,  # 传给 B1 prompt 的 {emotion_direction}
    }

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
    import json as _json

    metadata_dict = req.input_metadata or {}
    metadata_dict["source_type"] = req.source_type or "text"
    if req.source_type in ("voice", "image") and req.source_file_path:
        metadata_dict["source_file_path"] = req.source_file_path

    journal_entry = models.JournalEntry(
        user_id=user.id,
        content=req.content,
        title=req.title,
        mood=req.mood or "",
        weather=req.weather or "",
        entry_date=req.entry_date,
        emotion_label=emotion_label,
        risk_level=risk_level,
        source_type=req.source_type or "text",
        original_input_text=req.original_input_text,
        final_text=req.content,
        source_file_path=req.source_file_path,
        input_metadata=_json.dumps(metadata_dict),
    )
    db.add(journal_entry)
    db.commit()
    db.refresh(journal_entry)
    print(f"[ANALYSIS] diary saved  id={journal_entry.id}  anon_id={req.anon_id}  entry_date={req.entry_date}")

    # Trigger background insights refresh
    background_tasks.add_task(_refresh_insights_background, req.anon_id)
    print(f"[ANALYSIS] background analysis refresh scheduled for anon_id={req.anon_id}")

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
                preview=clean_preview,
                source_type=entry.source_type or "text",
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
        created_at=entry.created_at,
        source_type=entry.source_type or "text",
        original_input_text=entry.original_input_text,
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
        created_at=entry.created_at,
        source_type=entry.source_type or "text",
        original_input_text=entry.original_input_text,
    )

    return {
        "entry": entry_response,
        "chat_history": chat_history
    }


@router.get("/journal/{anon_id}/{date}", response_model=schemas.JournalEntryResponse)
async def get_journal_by_date(
    anon_id: str,
    date: str,
    db: Session = Depends(get_db)
):
    """
    Get today's journal entry for a user (if one exists).
    Returns 404 if no entry exists for the given date.
    """
    user = db.query(models.User).filter_by(anon_id=anon_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="No entry for this date")

    entry = (
        db.query(models.JournalEntry)
        .filter_by(user_id=user.id, entry_date=date)
        .order_by(models.JournalEntry.created_at.desc())
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="No entry for this date")

    return schemas.JournalEntryResponse(
        entry_id=entry.id,
        entry_date=entry.entry_date,
        title=entry.title,
        content=entry.content,
        mood=entry.mood,
        weather=entry.weather,
        emotion_label=entry.emotion_label,
        risk_level=entry.risk_level,
        created_at=entry.created_at,
        source_type=entry.source_type or "text",
        original_input_text=entry.original_input_text,
    )


# =============================================================================
# PUT /journal/{entry_id} — update a journal entry, then trigger background analysis refresh
# =============================================================================
@router.put("/journal/{entry_id}", response_model=schemas.JournalEntryResponse)
async def update_journal_entry(
    entry_id: int,
    req: schemas.JournalRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Update an existing journal entry and refresh insights in the background."""
    entry = db.query(models.JournalEntry).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Get user for analysis refresh (entry has user_id)
    user = db.query(models.User).filter_by(id=entry.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    anon_id = user.anon_id

    # Re-classify emotion and crisis for the updated content
    try:
        emotion_result = await agent.classify_emotion(req.content)
        emotion_label = emotion_result.get("emotion_label", entry.emotion_label or "Neutral")
    except Exception:
        emotion_label = entry.emotion_label or "Neutral"

    try:
        crisis_result = await agent.detect_crisis(req.content)
        risk_level = int(crisis_result.get("risk_level", entry.risk_level or 1))
    except Exception:
        risk_level = entry.risk_level or 1

    metadata_dict = req.input_metadata or {}
    metadata_dict["source_type"] = req.source_type or "text"

    entry.content = req.content
    entry.title = req.title
    entry.mood = req.mood or ""
    entry.weather = req.weather or ""
    entry.entry_date = req.entry_date
    entry.emotion_label = emotion_label
    entry.risk_level = risk_level
    entry.source_type = req.source_type or entry.source_type or "text"
    entry.final_text = req.content
    entry.input_metadata = json.dumps(metadata_dict)

    db.commit()
    db.refresh(entry)
    print(f"[JOURNAL] entry updated  id={entry_id}  anon_id={anon_id}")

    # Trigger background insights refresh
    background_tasks.add_task(_refresh_insights_background, anon_id)
    print(f"[JOURNAL] background analysis refresh scheduled after update  anon_id={anon_id}")

    return schemas.JournalEntryResponse(
        entry_id=entry.id,
        entry_date=entry.entry_date,
        title=entry.title,
        content=entry.content,
        mood=entry.mood,
        weather=entry.weather,
        emotion_label=entry.emotion_label,
        risk_level=entry.risk_level,
        created_at=entry.created_at,
        source_type=entry.source_type or "text",
        original_input_text=entry.original_input_text,
    )


# =============================================================================
# DELETE /journal/{entry_id} — delete a journal entry, then trigger background analysis refresh
# =============================================================================
@router.delete("/journal/{entry_id}")
async def delete_journal_entry(
    entry_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Delete a journal entry and refresh insights in the background."""
    entry = db.query(models.JournalEntry).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Get user for analysis refresh before deleting
    user = db.query(models.User).filter_by(id=entry.user_id).first()
    anon_id = user.anon_id if user else None

    db.delete(entry)
    db.commit()
    print(f"[JOURNAL] entry deleted  id={entry_id}  anon_id={anon_id}")

    # Trigger background insights refresh after deletion
    if anon_id:
        background_tasks.add_task(_refresh_insights_background, anon_id)
        print(f"[JOURNAL] background analysis refresh scheduled after delete  anon_id={anon_id}")

    return {"ok": True, "deleted_id": entry_id}
