# backend/app/routers/insights.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from datetime import datetime, timedelta
from collections import Counter
from typing import Optional

from ..database import SessionLocal
from .. import models, schemas
from ..therapy_agent import agent
from ..services.language_utils import detect_language

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


def build_insights_response(
    all_entries: list,
    emotion_counter: Counter,
    risk_counter: Counter,
    timeline: list,
    llm_result: dict,
    history_rows: list,
    cached_history: Optional[models.AnalysisHistory] = None,
) -> schemas.InsightsResponse:
    """Construct an InsightsResponse, including cache freshness fields."""
    llm_summary = llm_result.get("llm_summary") or llm_result.get("summary") or ""
    emotional_patterns = llm_result.get("emotional_patterns") or llm_result.get("emotion_patterns") or ""
    common_themes = llm_result.get("common_themes") or llm_result.get("themes") or ""
    growth_observations = llm_result.get("growth_observations") or llm_result.get("growth") or ""
    recommendations = llm_result.get("recommendations") or ""
    affirmation = llm_result.get("affirmation") or ""
    focus_points = llm_result.get("focus_points") or []

    top_mood = emotion_counter.most_common(1)[0][0] if emotion_counter else "Unknown"
    current_streak = compute_current_streak(all_entries)

    is_from_cache = cached_history is not None
    cached_at = cached_history.generated_at.isoformat() if cached_history else None
    source_entry_count = cached_history.source_entry_count if cached_history else len(all_entries)
    latest_entry_id = cached_history.latest_entry_id if cached_history else None

    return schemas.InsightsResponse(
        total_entries=len(all_entries),
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
            h.generated_at.strftime("%B %d, %Y") for h in history_rows
        ],
        is_from_cache=is_from_cache,
        cached_at=cached_at,
        source_entry_count=source_entry_count,
        latest_entry_id=latest_entry_id,
        is_fresh=is_from_cache,
    )


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
        ],
        is_from_cache=False,
        cached_at=None,
        source_entry_count=0,
        latest_entry_id=None,
        is_fresh=False,
    )


def _extract_fields(result: dict) -> dict:
    """Extract analysis fields, accepting both 'summary' and 'llm_summary' keys."""
    return {
        "llm_summary": result.get("summary") or result.get("llm_summary") or "",
        "emotional_patterns": result.get("emotional_patterns") or result.get("emotion_patterns") or "",
        "common_themes": result.get("common_themes") or result.get("themes") or "",
        "growth_observations": result.get("growth_observations") or result.get("growth") or "",
        "recommendations": result.get("recommendations") or "",
        "affirmation": result.get("affirmation") or "",
        "focus_points": result.get("focus_points") or [],
    }


def _build_stats(
    all_entries: list,
    use_raw_mood: bool = True,
) -> tuple[Counter, Counter, list, str]:
    """
    Build emotion/risk counters, timeline, and journal digest from journal entries.

    use_raw_mood=True: count the user's raw 'mood' field (e.g., sad, anxious, excited)
                       before falling back to emotion_label. This gives more specific
                       mood categories in the distribution chart.
    use_raw_mood=False: only use emotion_label (LLM-classified, coarser categories).
    """
    mood_counter = Counter()
    risk_counter = Counter()
    timeline = []
    journal_digest = []

    for e in all_entries:
        # Mood source: user raw 'mood' field if available and non-empty,
        # otherwise fall back to LLM-classified 'emotion_label'.
        # This ensures the distribution chart shows specific user-selected moods.
        raw_mood = getattr(e, "mood", "") or ""
        if use_raw_mood and raw_mood.strip():
            mood_label = raw_mood.strip()
        else:
            mood_label = e.emotion_label or "Unknown"

        risk = f"Level {e.risk_level}" if e.risk_level is not None else "Unknown"
        mood_counter[mood_label] += 1
        risk_counter[risk] += 1

        summary = (e.content or "").strip().replace("\n", " ")
        if len(summary) > 100:
            summary = summary[:100] + "..."

        timeline.append(
            schemas.InsightItem(
                date=e.created_at.strftime("%Y-%m-%d"),
                emotion_label=e.emotion_label,
                risk_level=e.risk_level,
                summary=summary,
            )
        )

        digest_summary = summary
        journal_digest.append({
            "date": e.created_at.strftime("%Y-%m-%d"),
            "emotion_label": e.emotion_label or "Unknown",
            "risk_level": e.risk_level,
            "summary": digest_summary,
        })

    emotion_distribution_text = ", ".join(
        f"{k}: {v}" for k, v in mood_counter.items()
    ) or "无"
    risk_distribution_text = ", ".join(
        f"{k}: {v}" for k, v in risk_counter.items()
    ) or "无"

    journal_text = "\n".join(
        f"Date: {d['date']} | Mood: {d['emotion_label']} | Risk: {d['risk_level']} | Content: {d['summary']}"
        for d in journal_digest
    )

    return mood_counter, risk_counter, timeline, journal_text


async def _generate_llm_insights(
    llm_user_input: str,
    journal_content_sample: str,
) -> dict:
    """Call agent.generate_insights (async) and extract fields, with defensive fallback."""
    try:
        raw_result = await agent.generate_insights(
            llm_user_input,
            journal_content_sample=journal_content_sample,
        )
        return _extract_fields(raw_result)
    except Exception as e:
        print(f"[ANALYSIS] generate_insights raised exception: {e}")
        detected_lang = detect_language(journal_content_sample)
        return {
            "llm_summary": "The analysis could not be generated this time. Please try again later." if detected_lang != "zh"
                           else "本次分析暂时无法生成，请稍后再试。",
            "emotional_patterns": "Not available." if detected_lang != "zh" else "暂无",
            "common_themes": "Not available." if detected_lang != "zh" else "暂无",
            "growth_observations": "Not available." if detected_lang != "zh" else "暂无",
            "recommendations": "Not available." if detected_lang != "zh" else "暂无",
            "affirmation": "",
            "focus_points": [],
        }


# =============================================================================
# GET /insights/cached — lightweight check: is there a fresh cached analysis?
# =============================================================================
@router.get("/insights/cached/{anon_id}", response_model=schemas.CachedInsightsResponse)
async def get_cached_insights(anon_id: str, db: Session = Depends(get_db)):
    """
    Lightweight endpoint for the frontend to check whether a cached (fresh) analysis
    already exists before deciding whether to trigger a full re-generation.

    Returns:
      has_cache=False  → no analysis history at all, frontend should call POST /insights
      has_cache=True, is_fresh=True  → cached analysis is up-to-date, can display directly
      has_cache=True, is_fresh=False  → cache exists but is stale, frontend should call POST /insights?force_refresh=true

    All errors are swallowed and returned as a safe empty state (never raises 500).
    """
    print(f"[CACHE] checking cached insights for anon_id={anon_id}")

    try:
        user = db.query(models.User).filter_by(anon_id=anon_id).first()
        if not user:
            print(f"[CACHE] user not found: {anon_id}")
            return schemas.CachedInsightsResponse(
                has_cache=False,
                is_fresh=False,
                source_entry_count=0,
                latest_entry_id=None,
            )

        # Get the most recent cached analysis
        latest_analysis = (
            db.query(models.AnalysisHistory)
            .filter(models.AnalysisHistory.user_id == user.id)
            .order_by(models.AnalysisHistory.generated_at.desc())
            .first()
        )

        # Count how many entries exist in the last 14 days
        fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
        current_entry_count = (
            db.query(models.JournalEntry)
            .filter(models.JournalEntry.user_id == user.id)
            .filter(
                (models.JournalEntry.created_at >= fourteen_days_ago)
                | (models.JournalEntry.entry_date.is_(None))
                | (models.JournalEntry.entry_date >= fourteen_days_ago.date().isoformat())
            )
            .count()
        )

        print(f"[CACHE] current_entry_count={current_entry_count}  "
              f"cached_source_count={latest_analysis.source_entry_count if latest_analysis else 'N/A'}  "
              f"cached_latest_id={latest_analysis.latest_entry_id if latest_analysis else 'N/A'}")

        if not latest_analysis:
            print("[CACHE] no cache found — returning has_cache=False")
            return schemas.CachedInsightsResponse(
                has_cache=False,
                is_fresh=False,
                source_entry_count=current_entry_count,
                latest_entry_id=None,
            )

        # Determine freshness: cache is fresh if:
        # 1. The cached analysis was generated from the same number of entries currently in the DB
        # 2. The latest_entry_id in the cache matches the actual latest entry ID in the DB
        # NOTE: source_entry_count and latest_entry_id may be NULL for rows created before
        # the columns were added (ALTER TABLE only adds columns, does not backfill).
        # COALESCE(NULL, X) returns X, so old rows with NULL are treated as matching,
        # meaning they are considered "fresh" (we fall back to full analysis display
        # regardless — we just need to know the row exists).
        latest_entry = (
            db.query(models.JournalEntry)
            .filter(models.JournalEntry.user_id == user.id)
            .order_by(models.JournalEntry.created_at.desc())
            .first()
        )
        latest_entry_id = latest_entry.id if latest_entry else None
        cached_source = latest_analysis.source_entry_count
        cached_latest_id = latest_analysis.latest_entry_id
        is_fresh = (
            (cached_source is None or cached_source == current_entry_count)
            and (cached_latest_id is None or cached_latest_id == latest_entry_id)
            and current_entry_count > 0
        )

        print(f"[CACHE] is_fresh={is_fresh}  "
              f"source_match={(cached_source is None or cached_source == current_entry_count)}  "
              f"cached_source={cached_source} vs current={current_entry_count}  "
              f"id_match={(cached_latest_id is None or cached_latest_id == latest_entry_id)}  "
              f"cached_latest_id={cached_latest_id} vs latest={latest_entry_id}  "
              f"cached_at={latest_analysis.generated_at}")

        return schemas.CachedInsightsResponse(
            has_cache=True,
            is_fresh=is_fresh,
            cached_at=latest_analysis.generated_at.isoformat(),
            source_entry_count=latest_analysis.source_entry_count,
            latest_entry_id=latest_entry_id,
            analysis=None,  # Full analysis is only returned when GET /insights/{anon_id} is called
        )
    except OperationalError as e:
        # Schema mismatch — analysis_history is missing new columns.
        # This should not happen after run_schema_patch() runs at startup,
        # but we protect against it in case the DB file is replaced at runtime.
        print(f"[CACHE] OperationalError reading analysis_history: {e}")
        return schemas.CachedInsightsResponse(
            has_cache=False,
            is_fresh=False,
            source_entry_count=0,
            latest_entry_id=None,
        )
    except Exception as e:
        print(f"[CACHE] unexpected error: {e}")
        return schemas.CachedInsightsResponse(
            has_cache=False,
            is_fresh=False,
            source_entry_count=0,
            latest_entry_id=None,
        )


# =============================================================================
# GET /insights/{anon_id} — retrieve the cached analysis (no regeneration)
# =============================================================================
@router.get("/insights/{anon_id}", response_model=schemas.InsightsResponse)
async def get_insights_cached(anon_id: str, db: Session = Depends(get_db)):
    """
    Return the most recent cached analysis without triggering regeneration.
    If the cache is stale or missing, returns a response with is_fresh=False
    and empty llm_summary — the frontend should then call POST /insights to regenerate.

    All errors are swallowed and returned as a safe empty state (never raises 500).
    """
    print(f"[CACHE_GET] retrieving cached insights for anon_id={anon_id}")

    try:
        user = db.query(models.User).filter_by(anon_id=anon_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Count current entries in the 14-day window
        fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
        all_entries = (
            db.query(models.JournalEntry)
            .filter(models.JournalEntry.user_id == user.id)
            .filter(
                (models.JournalEntry.created_at >= fourteen_days_ago)
                | (models.JournalEntry.entry_date.is_(None))
                | (models.JournalEntry.entry_date >= fourteen_days_ago.date().isoformat())
            )
            .order_by(models.JournalEntry.created_at.asc())
            .all()
        )

        latest_entry = (
            db.query(models.JournalEntry)
            .filter(models.JournalEntry.user_id == user.id)
            .order_by(models.JournalEntry.created_at.desc())
            .first()
        )

        history_rows = (
            db.query(models.AnalysisHistory)
            .filter(models.AnalysisHistory.user_id == user.id)
            .order_by(models.AnalysisHistory.generated_at.desc())
            .limit(5)
            .all()
        )

        cached = (
            db.query(models.AnalysisHistory)
            .filter(models.AnalysisHistory.user_id == user.id)
            .order_by(models.AnalysisHistory.generated_at.desc())
            .first()
        )

        if not all_entries:
            print("[CACHE_GET] no entries in window → returning empty insights")
            return build_empty_insights(history_rows)

        mood_counter, risk_counter, timeline, _ = _build_stats(all_entries, use_raw_mood=True)
        top_mood = mood_counter.most_common(1)[0][0] if mood_counter else "Unknown"
        current_streak = compute_current_streak(all_entries)

        if cached:
            latest_entry_id = latest_entry.id if latest_entry else None
            is_fresh = (
                cached.source_entry_count == len(all_entries)
                and cached.latest_entry_id == latest_entry_id
            )
        else:
            is_fresh = False

        print(f"[CACHE_GET] has_cache={cached is not None}  is_fresh={is_fresh}  "
              f"total_entries={len(all_entries)}  mood_dist={dict(mood_counter)}")

        if cached and is_fresh:
            # Return the cached analysis with current stats
            # IMPORTANT: read ALL fields from the cached DB row — not just llm_summary/emotional_patterns
            print("[CACHE_GET] returning FRESH cached analysis")
            cached_affirmation = getattr(cached, "affirmation", "") or ""
            cached_focus_points = getattr(cached, "focus_points", []) or []
            # If focus_points was not stored, default to empty list
            if not cached_focus_points:
                cached_focus_points = []
            print(f"[CACHE_GET] DB cache field lengths: "
                  f"llm_summary={len(cached.llm_summary or '')}  "
                  f"emotional_patterns={len(cached.emotional_patterns or '')}  "
                  f"common_themes={len(cached.common_themes or '')}  "
                  f"growth_observations={len(cached.growth_observations or '')}  "
                  f"recommendations={len(cached.recommendations or '')}  "
                  f"affirmation={len(cached_affirmation)}  "
                  f"focus_points={len(cached_focus_points)}")
            llm_result = {
                "llm_summary": cached.llm_summary or "",
                "emotional_patterns": cached.emotional_patterns or "",
                "common_themes": cached.common_themes or "",
                "growth_observations": cached.growth_observations or "",
                "recommendations": cached.recommendations or "",
                "affirmation": cached_affirmation,
                "focus_points": cached_focus_points,
            }
            return build_insights_response(
                all_entries, mood_counter, risk_counter, timeline,
                llm_result, history_rows, cached_history=cached,
            )

        # No fresh cache — return empty LLM fields with current stats
        print("[CACHE_GET] no fresh cache — returning empty LLM fields (frontend should regenerate)")
        empty_llm = {
            "llm_summary": "",
            "emotional_patterns": "",
            "common_themes": "",
            "growth_observations": "",
            "recommendations": "",
            "affirmation": "",
            "focus_points": [],
        }
        return build_insights_response(
            all_entries, mood_counter, risk_counter, timeline,
            empty_llm, history_rows, cached_history=None,
        )
    except HTTPException:
        raise
    except OperationalError as e:
        print(f"[CACHE_GET] OperationalError reading analysis_history: {e}")
        return build_empty_insights([])
    except Exception as e:
        print(f"[CACHE_GET] unexpected error: {e}")
        return build_empty_insights([])


# =============================================================================
# POST /insights — generate (or force-regenerate) analysis
# =============================================================================
@router.post("/insights", response_model=schemas.InsightsResponse)
async def get_insights(req: schemas.InsightsRequest, db: Session = Depends(get_db)):
    print(f"[ANALYSIS] POST received  anon_id={req.anon_id}")

    user = db.query(models.User).filter_by(anon_id=req.anon_id).first()
    if not user:
        print(f"[ANALYSIS] user not found: {req.anon_id}")
        raise HTTPException(status_code=404, detail="User not found")

    print(f"[ANALYSIS] user_id={user.id}  anon_id={req.anon_id}")

    fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
    print(f"[ANALYSIS] filtering entries >= {fourteen_days_ago.date()} (14-day window)")

    all_entries = (
        db.query(models.JournalEntry)
        .filter(models.JournalEntry.user_id == user.id)
        .filter(
            (models.JournalEntry.created_at >= fourteen_days_ago)
            | (models.JournalEntry.entry_date.is_(None))
            | (models.JournalEntry.entry_date >= fourteen_days_ago.date().isoformat())
        )
        .order_by(models.JournalEntry.created_at.asc())
        .all()
    )
    print(f"[ANALYSIS] entries after filter: {len(all_entries)}")

    # Get the latest entry ID for cache tracking
    latest_entry = (
        db.query(models.JournalEntry)
        .filter(models.JournalEntry.user_id == user.id)
        .order_by(models.JournalEntry.created_at.desc())
        .first()
    )
    latest_entry_id = latest_entry.id if latest_entry else None

    history_rows = (
        db.query(models.AnalysisHistory)
        .filter(models.AnalysisHistory.user_id == user.id)
        .order_by(models.AnalysisHistory.generated_at.desc())
        .limit(5)
        .all()
    )

    if not all_entries:
        print("[ANALYSIS] no entries in window → returning empty insights")
        return build_empty_insights(history_rows)

    # Build stats — use raw user mood for distribution
    mood_counter, risk_counter, timeline, journal_text = _build_stats(all_entries, use_raw_mood=True)
    print(f"[ANALYSIS] mood_distribution (raw mood): {dict(mood_counter)}")
    print(f"[ANALYSIS] top_mood (raw mood): {mood_counter.most_common(1)}")

    llm_user_input = f"""Analyze all diary entries from the last 14 days. There are {len(all_entries)} entries in total.

Diary entries:
{journal_text}

Emotion distribution:
{', '.join(f"{k}: {v}" for k, v in mood_counter.items()) or 'None recorded'}

Risk distribution:
{', '.join(f"{k}: {v}" for k, v in risk_counter.items()) or 'None recorded'}
""".strip()

    journal_content_sample = " ".join(e.content or "" for e in all_entries if e.content)[:200]
    print(f"[ANALYSIS] generating LLM analysis for {len(all_entries)} entries...")

    llm_result = await _generate_llm_insights(llm_user_input, journal_content_sample)
    print(f"[ANALYSIS] LLM result field lengths: "
          f"llm_summary={len(llm_result['llm_summary'])}  "
          f"emotional_patterns={len(llm_result['emotional_patterns'])}  "
          f"common_themes={len(llm_result['common_themes'])}  "
          f"growth_observations={len(llm_result['growth_observations'])}  "
          f"recommendations={len(llm_result['recommendations'])}  "
          f"affirmation={len(llm_result['affirmation'])}  "
          f"focus_points={llm_result['focus_points']}")

    # Save to analysis history with cache tracking fields
    try:
        new_history = models.AnalysisHistory(
            user_id=user.id,
            llm_summary=llm_result["llm_summary"],
            emotional_patterns=llm_result["emotional_patterns"],
            common_themes=llm_result["common_themes"],
            growth_observations=llm_result["growth_observations"],
            recommendations=llm_result["recommendations"],
            source_entry_count=len(all_entries),
            latest_entry_id=latest_entry_id,
            latest_entry_created_at=latest_entry.created_at if latest_entry else None,
            total_entries_at_time=len(all_entries),
        )
        db.add(new_history)
        db.commit()
        db.refresh(new_history)
        # Log saved field lengths — confirms all 6 fields were persisted
        print(f"[ANALYSIS] saved to analysis_history  id={new_history.id}  "
              f"source_entry_count={len(all_entries)}  latest_entry_id={latest_entry_id}")
        print(f"[ANALYSIS] saved field lengths (DB confirm): "
              f"llm_summary={len(new_history.llm_summary or '')}  "
              f"emotional_patterns={len(new_history.emotional_patterns or '')}  "
              f"common_themes={len(new_history.common_themes or '')}  "
              f"growth_observations={len(new_history.growth_observations or '')}  "
              f"recommendations={len(new_history.recommendations or '')}  "
              f"affirmation={len(getattr(new_history, 'affirmation', '') or '')}")
    except Exception as e:
        print(f"[ANALYSIS] save failed: {e}")
        db.rollback()

    updated_history_rows = (
        db.query(models.AnalysisHistory)
        .filter(models.AnalysisHistory.user_id == user.id)
        .order_by(models.AnalysisHistory.generated_at.desc())
        .limit(5)
        .all()
    )

    return build_insights_response(
        all_entries, mood_counter, risk_counter, timeline,
        llm_result, updated_history_rows, cached_history=None,
    )


# GET /insights/history/{anon_id}/{date} — fetch a specific historical analysis entry
@router.get("/insights/history/{anon_id}/{date}")
async def get_analysis_by_date(anon_id: str, date: str, db: Session = Depends(get_db)):
    """
    date: format "March 15, 2025" (matches the string returned in analysis_history)
    Returns the matching AnalysisHistory row so the UI can display past analysis.

    All errors are swallowed and return 404 (never raises 500).
    """
    print(f"[ANALYSIS] history fetch  anon_id={anon_id}  date={date}")
    try:
        user = db.query(models.User).filter_by(anon_id=anon_id).first()
        if not user:
            print(f"[ANALYSIS] user not found: {anon_id}")
            raise HTTPException(status_code=404, detail="User not found")

        entry = (
            db.query(models.AnalysisHistory)
            .filter(models.AnalysisHistory.user_id == user.id)
            .order_by(models.AnalysisHistory.generated_at.desc())
            .all()
        )

        matched = None
        for row in entry:
            if row.generated_at.strftime("%B %d, %Y") == date:
                matched = row
                break

        if matched:
            print(f"[ANALYSIS] history entry found  id={matched.id}  generated_at={matched.generated_at}")
            return {
                "id": matched.id,
                "generated_at": matched.generated_at.isoformat(),
                "llm_summary": matched.llm_summary,
                "emotional_patterns": matched.emotional_patterns,
                "common_themes": matched.common_themes,
                "growth_observations": matched.growth_observations,
                "recommendations": matched.recommendations,
                "affirmation": getattr(matched, "affirmation", "") or "",
                "focus_points": [],
            }

        print(f"[ANALYSIS] history entry NOT found for date={date}")
        raise HTTPException(status_code=404, detail="Analysis entry not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYSIS] history endpoint unexpected error: {e}")
        raise HTTPException(status_code=404, detail="Analysis entry not found")
