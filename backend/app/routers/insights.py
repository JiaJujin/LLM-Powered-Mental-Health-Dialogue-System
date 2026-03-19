# backend/app/routers/insights.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import Counter

from ..database import SessionLocal
from .. import models, schemas
from ..therapy_agent import agent

router = APIRouter(tags=["insights"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def compute_current_streak(entries):
    if not entries:
        return 0

    date_set = {e.created_at.date() for e in entries}
    if not date_set:
        return 0

    sorted_dates = sorted(date_set, reverse=True)
    today = datetime.utcnow().date()

    if sorted_dates[0] == today:
        cursor = today
    elif sorted_dates[0] == today - timedelta(days=1):
        cursor = today - timedelta(days=1)
    else:
        return 1

    streak = 0
    while cursor in date_set:
        streak += 1
        cursor = cursor - timedelta(days=1)

    return streak


def build_empty_insights(history_rows):
    return schemas.InsightsResponse(
        total_entries=0,
        current_streak=0,
        top_mood="Unknown",
        emotion_distribution={},
        risk_distribution={},
        timeline=[],
        llm_summary="最近 14 天还没有日记记录，所以暂时无法生成分析。",
        emotional_patterns="暂无分析内容。",
        common_themes="暂无分析内容。",
        growth_observations="暂无分析内容。",
        recommendations="当有更多记录后，这里会显示更完整的洞察。",
        affirmation="",
        focus_points=[],
        analysis_history=[
            h.generated_at.strftime("%B %d, %Y") for h in history_rows
        ]
    )


@router.post("/insights", response_model=schemas.InsightsResponse)
async def get_insights(req: schemas.InsightsRequest, db: Session = Depends(get_db)):
    print(f"[INSIGHTS] Processing request for anon_id: {req.anon_id}")
    
    user = db.query(models.User).filter_by(anon_id=req.anon_id).first()
    if not user:
        print(f"[INSIGHTS] User not found: {req.anon_id}")
        raise HTTPException(status_code=404, detail="User not found")

    print(f"[INSIGHTS] User ID: {user.id}")

    since = datetime.utcnow() - timedelta(days=14)

    entries = (
        db.query(models.JournalEntry)
        .filter(models.JournalEntry.user_id == user.id)
        .filter(models.JournalEntry.created_at >= since)
        .order_by(models.JournalEntry.created_at.asc())
        .all()
    )

    print(f"[INSIGHTS] Found {len(entries)} entries in last 14 days")

    history_rows = (
        db.query(models.AnalysisHistory)
        .filter(models.AnalysisHistory.user_id == user.id)
        .order_by(models.AnalysisHistory.generated_at.desc())
        .limit(5)
        .all()
    )

    if not entries:
        print(f"[INSIGHTS] No entries found, returning empty insights")
        return build_empty_insights(history_rows)

    emotion_counter = Counter()
    risk_counter = Counter()
    timeline = []

    for e in entries:
        emotion = e.emotion_label or "Unknown"
        risk = f"Level {e.risk_level}" if e.risk_level is not None else "Unknown"

        emotion_counter[emotion] += 1
        risk_counter[risk] += 1

        summary = (e.content or "").strip().replace("\n", " ")
        if len(summary) > 100:
            summary = summary[:100] + "..."

        timeline.append(
            schemas.InsightItem(
                date=e.created_at.strftime("%Y-%m-%d"),
                emotion_label=e.emotion_label,
                risk_level=e.risk_level,
                summary=summary
            )
        )

    top_mood = emotion_counter.most_common(1)[0][0] if emotion_counter else "Unknown"
    current_streak = compute_current_streak(entries)

    journal_digest = []
    for e in entries:
        digest_summary = (e.content or "").strip().replace("\n", " ")
        if len(digest_summary) > 140:
            digest_summary = digest_summary[:140] + "..."

        journal_digest.append({
            "date": e.created_at.strftime("%Y-%m-%d"),
            "emotion_label": e.emotion_label or "Unknown",
            "risk_level": e.risk_level,
            "summary": digest_summary
        })

    emotion_distribution_text = ", ".join(
        [f"{k}: {v}" for k, v in emotion_counter.items()]
    ) or "无"

    risk_distribution_text = ", ".join(
        [f"{k}: {v}" for k, v in risk_counter.items()]
    ) or "无"

    llm_user_input = f"""
最近 14 天内，共有 {len(entries)} 篇日记，请基于现有全部内容进行分析。

最近 14 天日记摘要：
{journal_digest}

最近 14 天情绪分布：
{emotion_distribution_text}

最近 14 天风险分布：
{risk_distribution_text}
""".strip()

    print(f"[INSIGHTS] Calling LLM for analysis...")
    llm_result = None
    llm_error = None
    
    try:
        llm_result = await agent.generate_insights(llm_user_input)
        print(f"[INSIGHTS] LLM call successful!")
    except Exception as e:
        llm_error = str(e)
        print(f"[INSIGHTS] LLM call failed: {llm_error}")
        llm_result = {
            "summary": "从最近 14 天的记录来看，你的情绪和关注点已经形成了一些可以被观察的模式，但当前这份分析还是比较初步，后续随着记录增加会更完整。",
            "emotional_patterns": "近期情绪有一定波动，部分记录呈现出明显的压力或低落，也有相对平稳的时候。",
            "common_themes": "目前反复出现的主题主要集中在近期让你在意的人和事，以及这些事情带来的心理负担。",
            "growth_observations": "你愿意持续记录本身就是一种觉察，这说明你已经在尝试更认真地理解自己的状态。",
            "recommendations": "如果你愿意，可以继续观察哪些情境最容易触发明显情绪，以及哪些时刻会让你稍微轻松一些。",
            "affirmation": "你愿意把自己的想法写下来，这本身就是一件很勇敢的事。请相信，你正在一步步靠近更了解自己的路上。",
            "focus_points": [
                "最近哪些情境最容易让你的情绪明显变化？",
                "有没有一些时刻会让你感觉稍微轻一点？"
            ]
        }

    llm_summary = llm_result.get("summary", "")
    emotional_patterns = llm_result.get("emotional_patterns", "")
    common_themes = llm_result.get("common_themes", "")
    growth_observations = llm_result.get("growth_observations", "")
    recommendations = llm_result.get("recommendations", "")
    affirmation = llm_result.get("affirmation", "")
    focus_points = llm_result.get("focus_points", [])

    # Save to analysis history
    try:
        new_history = models.AnalysisHistory(
            user_id=user.id,
            llm_summary=llm_summary,
            emotional_patterns=emotional_patterns,
            common_themes=common_themes,
            growth_observations=growth_observations,
            recommendations=recommendations,
        )
        db.add(new_history)
        db.commit()
        print(f"[INSIGHTS] Saved analysis to history")
    except Exception as e:
        print(f"[INSIGHTS] Failed to save analysis: {e}")
        db.rollback()

    updated_history_rows = (
        db.query(models.AnalysisHistory)
        .filter(models.AnalysisHistory.user_id == user.id)
        .order_by(models.AnalysisHistory.generated_at.desc())
        .limit(5)
        .all()
    )

    return schemas.InsightsResponse(
        total_entries=len(entries),
        current_streak=current_streak,
        top_mood=top_mood,
        emotion_distribution=dict(emotion_counter),
        risk_distribution=dict(risk_counter),
        timeline=timeline,
        llm_summary=llm_summary,
        emotional_patterns=emotional_patterns,
        common_themes=common_themes,
        growth_observations=growth_observations,
        recommendations=recommendations,
        affirmation=affirmation,
        focus_points=focus_points,
        analysis_history=[
            h.generated_at.strftime("%B %d, %Y") for h in updated_history_rows
        ]
    )
