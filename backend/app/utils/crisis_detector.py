"""
Crisis detection utility — deterministic high-risk phrase gate followed by
LLM-based semantic classification via Zhipu GLM API.

Usage:
    from app.utils.crisis_detector import detect_crisis_with_llm
    is_crisis = await detect_crisis_with_llm("我不想活了")
"""

import json
import logging
from ..llm_client import zhipu_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# A. Hard phrase gate — deterministic fail-safe for explicit crisis language
# ---------------------------------------------------------------------------

HIGH_RISK_PATTERNS = [
    # Chinese — explicit crisis language (exact / near-exact)
    "想死",
    "我想死",
    "不想活",
    "不想活了",
    "不想活下去",
    "活不下去",
    "活著沒有意思",
    "活著没意思",
    "活着没有意思",
    "活着没意思",
    "自殺",
    "自杀",
    "轻生",
    "輕生",
    "了結自己",
    "结束生命",
    "結束生命",
    "消失算了",
    "死了算了",
    "撐不下去了",
    "撑不下去了",
    "我想消失",
    "大家沒有我會更好",
    "大家没有我会更好",
    # English
    "kill myself",
    "I want to kill myself",
    "want to die",
    "I want to die",
    "don't want to live",
    "don't want to live anymore",
    "end my life",
    "better off dead",
    "no reason to live",
]


def _contains_high_risk_phrase(text: str) -> bool:
    """Return True if any high-risk phrase appears in the text (case-insensitive)."""
    text_lower = text.lower()
    for phrase in HIGH_RISK_PATTERNS:
        if phrase.lower() in text_lower:
            return True
    return False


# ---------------------------------------------------------------------------
# B. Improved system prompt — conservative, covers explicit and indirect
#    expressions that must be classified as crisis=true
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a mental health crisis assessment assistant.
Your task is to determine whether the user's text expresses suicidal intent, self-harm intent, or serious hopelessness that may indicate danger to life.
Be conservative for safety: if the text expresses wanting to die, not wanting to live, wanting to disappear, ending life, being better off dead, or strong hopelessness suggesting life is not worth continuing, return true.

Examples that MUST return true:
- 我不想活了
- 想死
- 我想消失
- 活著沒有意思
- 大家沒有我會更好
- 撐不下去了
- I want to kill myself
- I don't want to live anymore
- There is no reason to live
- Everyone would be better off without me

Return ONLY valid JSON:
{"crisis": true}
or
{"crisis": false}"""


async def detect_crisis_with_llm(text: str) -> bool:
    """
    Two-layer detector:
      1. Hard phrase gate — returns True immediately for explicit crisis language.
      2. LLM semantic classification — for all other inputs.

    Fails open — any error returns False so the user is never blocked.
    Logs every decision point for traceability.
    """
    if not text or not text.strip():
        logger.info("[CRISIS] empty text — returning False")
        return False

    # ---- A. Hard phrase gate — checked first regardless of text length ----
    matched = _contains_high_risk_phrase(text)
    logger.info("[CRISIS] hard gate matched=%r text=%r", matched, text[:120])
    if matched:
        logger.info("[CRISIS] final crisis bool=%r  (hard gate)", True)
        return True

    # ---- B. LLM classification ----
    llm_raw_result = None
    try:
        logger.info("[CRISIS] calling LLM")
        llm_raw_result = await zhipu_client.chat_json_object(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=text,
            temperature=0.1,
            max_tokens=200,
        )
        logger.info("[CRISIS] raw LLM result=%r", llm_raw_result)

        # Safe boolean parsing
        if not isinstance(llm_raw_result, dict):
            logger.warning("[CRISIS] LLM result is not a dict (%s) — fail-open → False", type(llm_raw_result).__name__)
            return False

        crisis_value = llm_raw_result.get("crisis", False)
        if isinstance(crisis_value, bool):
            crisis = crisis_value
        elif isinstance(crisis_value, str):
            crisis = crisis_value.strip().lower() == "true"
        else:
            crisis = False

    except Exception:
        logger.exception("[CRISIS] LLM call failed — fail-open → False")
        return False

    logger.info("[CRISIS] final crisis bool=%r", crisis)
    return crisis
