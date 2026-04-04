"""
Crisis intent classification + alert persistence endpoints.

Replaces keyword-based detection with semantic classification using the
existing Zhipu GLM LLM API (glm-4.5-air).
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..llm_client import zhipu_client
from ..models import CrisisAlert, User
from ..database import SessionLocal

router = APIRouter(prefix="/api/crisis", tags=["crisis"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic schemas (request / response)
# ---------------------------------------------------------------------------

class ClassifyRequest(BaseModel):
    text: str
    source: str   # "diary" | "chat"
    user_id: str


class ClassifyResponse(BaseModel):
    triggered: bool
    level: str            # "none" | "low" | "medium" | "high"
    reasoning: str
    matched_themes: list[str]


class CrisisAlertCreate(BaseModel):
    user_id: str
    source: str     # "diary" | "chat"
    text: str       # full triggering text


class CrisisAlertResponse(BaseModel):
    id: int
    source: str
    triggered_at: datetime
    status: str
    message_snippet: str

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# System prompt — instructs the LLM to classify crisis intent
# ---------------------------------------------------------------------------

CRISIS_SYSTEM_PROMPT = """你是一个专业的心理危机评估助手。你的任务是判断用户输入的文字是否含有与了结生命、自杀意念、自我伤害或严重心理危机相关的内容。

判断标准（涵盖直接和间接表达）：
- 直接：明确提到自杀、轻生、自残、跳楼、割手腕等
- 间接：表达活下去没意义、觉得自己是负担、消失会更好、不想再撑了、极度绝望感、感觉被困住没有出路等
- 隐晦：用隐喻或暗示表达对生命的放弃，例如"终于可以休息了"配合绝望语境、"送走自己"等

重要：你的所有回复必须只输出一个合法的 JSON 对象，不要输出任何其他文字。

JSON 格式：
{
  "triggered": true或false,
  "level": "none" | "low" | "medium" | "high",
  "reasoning": "简短说明判断依据（20字内）",
  "matched_themes": ["主题1", "主题2"]  // 如无则空数组[]
}

level 定义：
- none: 无任何危机信号
- low: 有轻微绝望/消极情绪但无明确危机意念
- medium: 有明显危机意念或自我伤害暗示
- high: 明确表达自杀/了结生命意图
"""

# ---------------------------------------------------------------------------
# Dependency — get a DB session
# ---------------------------------------------------------------------------

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/classify", response_model=ClassifyResponse)
async def classify_crisis(req: ClassifyRequest):
    """Classify text using the LLM — used by the frontend for real-time detection."""
    logger.info(f"[CRISIS] classify  source={req.source}  user={req.user_id}  text_len={len(req.text)}")

    if len(req.text.strip()) < 5:
        return ClassifyResponse(
            triggered=False,
            level="none",
            reasoning="内容过短",
            matched_themes=[],
        )

    try:
        result = await zhipu_client.chat_json_object(
            system_prompt=CRISIS_SYSTEM_PROMPT,
            user_prompt=req.text,
            temperature=0.1,
            max_tokens=200,
        )

        triggered = result.get("triggered", False)
        level = result.get("level", "none")

        logger.info(
            f"[CRISIS] result  triggered={triggered}  level={level}  "
            f"themes={result.get('matched_themes', [])}"
        )

        return ClassifyResponse(
            triggered=triggered,
            level=level,
            reasoning=result.get("reasoning", ""),
            matched_themes=result.get("matched_themes", []),
        )

    except Exception as e:
        logger.error(f"[CRISIS] LLM call failed: {e}  — falling back to 'none'")
        return ClassifyResponse(
            triggered=False,
            level="none",
            reasoning="检测服务暂时不可用",
            matched_themes=[],
        )


@router.post("/alerts")
async def create_crisis_alert(body: CrisisAlertCreate, db: Session = Depends(get_db)):
    """
    Detect crisis using the LLM and persist an alert record if triggered.

    Always returns {crisis_detected: true/false}.
    Fails open — any error returns crisis_detected=False so the user is never blocked.
    """
    logger.info(f"[CRISIS] /alerts  user={body.user_id}  source={body.source}  text_len={len(body.text)}")

    triggered = False
    try:
        # Use the utility function (calls Zhipu GLM with binary crisis prompt)
        from ..utils.crisis_detector import detect_crisis_with_llm
        triggered = await detect_crisis_with_llm(body.text)
    except Exception as exc:
        logger.error(f"[CRISIS] detect_crisis_with_llm failed: {exc}")

    if triggered:
        try:
            alert = CrisisAlert(
                user_id=body.user_id,
                source=body.source,
                message_snippet=body.text[:500],
                status="counselor_contacted",
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            logger.info(f"[CRISIS] alert saved  id={alert.id}  user={body.user_id}")
            return {
                "crisis_detected": True,
                "triggered_at": alert.triggered_at.isoformat(),
            }
        except Exception as exc:
            logger.error(f"[CRISIS] failed to save alert: {exc}")
            db.rollback()
            return {"crisis_detected": True}   # detected but not persisted — still notify caller

    return {"crisis_detected": False}


@router.get("/alerts/{user_id}", response_model=list[CrisisAlertResponse])
async def get_crisis_alerts(user_id: str, db: Session = Depends(get_db)):
    """
    Return all crisis alert records for a user, newest first.
    """
    alerts = (
        db.query(CrisisAlert)
          .filter(CrisisAlert.user_id == user_id)
          .order_by(CrisisAlert.triggered_at.desc())
          .all()
    )
    return alerts
