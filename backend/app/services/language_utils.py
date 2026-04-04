"""
Language detection utility for MindJournal.

Detects whether user input is primarily Chinese (Mandarin, Cantonese, Traditional)
or English, based on character-level analysis. Used to ensure AI responses
match the user's language.

Also provides shared crisis detection for chatbot and journal companion.
"""

import re

# CJK Unified Ideographs range (covers Simplified, Traditional, Japanese kanji, Cantonese)
_CJK_PATTERN = re.compile(r'[\u4e00-\u9fff]')

# ---------------------------------------------------------------------------
# Crisis detection — shared by chat router and journal companion
# ---------------------------------------------------------------------------

# High-risk phrases that trigger immediate crisis response.
# Must be kept in sync with HIGH_RISK_PATTERNS in crisis_detector.py.
_CRISIS_PHRASES = [
    # Chinese
    "想死", "我想死", "不想活", "不想活了", "不想活下去",
    "活不下去", "活著沒有意思", "活着没有意思",
    "自殺", "自杀", "輕生", "轻生",
    "了結自己", "结束生命", "結束生命",
    "消失算了", "死了算了", "撐不下去了", "撑不下去了",
    "我想消失", "大家沒有我會更好",
    # English
    "kill myself", "i want to kill myself",
    "want to die", "i want to die",
    "don't want to live", "dont want to live",
    "end my life", "better off dead",
    "no reason to live",
]


def contains_crisis_language(text: str) -> bool:
    """
    Return True if the text contains any high-risk crisis phrase.
    Case-insensitive substring match.
    Used by chat router to inject a per-message crisis override block.
    """
    if not text:
        return False
    text_lower = text.lower()
    for phrase in _CRISIS_PHRASES:
        if phrase.lower() in text_lower:
            return True
    return False


def detect_language(text: str) -> str:
    """
    Detect the primary language of input text.

    Args:
        text: The user's input text.

    Returns:
        'zh' if Chinese characters make up > 30% of the text,
        'en' otherwise.

    Note:
        This is a heuristic-based detector. It covers:
        - Simplified Chinese (e.g., 今天, 你好)
        - Traditional Chinese (e.g., 今天, 學習)
        - Cantonese characters (same range as Traditional)
        - Mixed Chinese + English (falls back to 'en' if Chinese ratio <= 30%)
    """
    stripped = text.strip()
    if not stripped:
        return "en"

    chinese_chars = len(_CJK_PATTERN.findall(stripped))
    total_chars = len(stripped)

    chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
    print(f"[LANG_DETECT] text_len={total_chars}  chinese_chars={chinese_chars}  ratio={chinese_ratio:.2f}  → '{'zh' if chinese_ratio > 0.3 else 'en'}'")

    return "zh" if chinese_ratio > 0.3 else "en"


def build_language_instruction(lang: str) -> str:
    """
    Build a system-prompt instruction telling the AI to reply in a specific language.

    Args:
        lang: 'zh' or 'en' from detect_language()

    Returns:
        A short instruction string to append to the system prompt.
    """
    if lang == "zh":
        return (
            "\n\n[语言规则] 请使用与用户输入相同的语言回复。"
            "如果用户用简体中文写，就用简体中文回复。"
            "如果用户用繁体中文/粤语写，就用繁体中文/粤语回复。"
            "绝对不要切换到其他语言，除非用户明确要求。"
        )
    else:
        return (
            "\n\n[LANGUAGE RULE] Reply in English only. "
            "Do not switch to any other language (including Chinese, Cantonese, etc.) "
            "unless the user explicitly asks you to."
        )