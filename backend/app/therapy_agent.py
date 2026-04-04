# backend/app/therapy_agent.py
from pathlib import Path
from typing import Dict, Any, Optional
from .llm_client import openrouter_client
from .services.language_utils import detect_language, build_language_instruction
from .llm_schemas import (
    ROLE_SELECTION_SCHEMA,
    EMOTION_CLASSIFICATION_SCHEMA,
    CRISIS_SCHEMA,
    B1_SCHEMA,
    B2_SCHEMA,
    B3_SCHEMA,
    INSIGHTS_SCHEMA,
    GATING_B1_B2_SCHEMA,
    GATING_B2_B3_SCHEMA,
)

PROMPTS_DIR = Path(__file__).parent / "prompts"

FOLLOWUP_GUIDANCE = {
    "情緒承接": "用溫柔的語言再次確認使用者的情緒，讓他感到被理解，不要急於進入下一個問題",
    "聚焦痛點": "溫和地邀請使用者深入具體的刺痛點，例如『這件事中哪個部分最讓你難受？』",
    "邀請具體化": "邀請使用者舉出具體例子或詳細描述，幫助把抽象的感受具象化",
    "澄清自動想法": "幫助使用者更清晰地描述腦中自動冒出來的念頭或解讀",
    "探索證據": "邀請使用者檢視支撐或反駁某個想法的證據",
    "聚焦內在拉扯": "幫助使用者看見自己內心的矛盾或掙扎",
}


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


class TherapyAgent:
    def __init__(self):
        self.prompt_a = load_prompt("prompt_a_role.txt")
        self.prompt_b1 = load_prompt("prompt_b1.txt")
        self.prompt_b2 = load_prompt("prompt_b2.txt")
        self.prompt_b3 = load_prompt("prompt_b3.txt")
        self.prompt_c = load_prompt("prompt_c_crisis.txt")
        self.prompt_d = load_prompt("prompt_d_insights.txt")
        self.prompt_e = load_prompt("prompt_e_emotion.txt")
        self.prompt_gating_b1_b2 = load_prompt("prompt_gating_b1_b2.txt")
        self.prompt_gating_b2_b3 = load_prompt("prompt_gating_b2_b3.txt")
        self.prompt_b1_followup = load_prompt("prompt_b1_followup.txt")
        self.prompt_b2_followup = load_prompt("prompt_b2_followup.txt")

    async def select_role(self, body: str, need: str, emotion: str) -> Dict[str, Any]:
        print(f"[AGENT] select_role called  body_len={len(body)}  need={need}  emotion={emotion}")
        lang = detect_language(f"{body} {need} {emotion}")
        lang_instruction = build_language_instruction(lang)
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_a + lang_instruction,
            user_prompt=f"body={body}, need={need}, emotion={emotion}",
            schema_name="role_selection",
            schema=ROLE_SELECTION_SCHEMA,
            task="precheck",
            temperature=0.2,
            max_tokens=300,  # 调大避免截断导致 finish_reason=length
        )

    async def classify_emotion(self, text: str) -> Dict[str, Any]:
        print(f"[AGENT] classify_emotion called  text_len={len(text)}")
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_e,
            user_prompt=text,
            schema_name="emotion_classification",
            schema=EMOTION_CLASSIFICATION_SCHEMA,
            task="emotion",
            temperature=0.1,
            max_tokens=200,  # 调大避免截断
        )

    async def detect_crisis(self, text: str) -> Dict[str, Any]:
        print(f"[AGENT] detect_crisis called  text_len={len(text)}")
        lang = detect_language(text)
        lang_instruction = build_language_instruction(lang)
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_c + lang_instruction,
            user_prompt=text,
            schema_name="crisis_detection",
            schema=CRISIS_SCHEMA,
            task="crisis",
            temperature=0.1,
            max_tokens=250,  # 调大避免截断
        )

    async def run_b1(self, context: Dict[str, Any], journal: str) -> Dict[str, Any]:
        lang = detect_language(journal)
        lang_instruction = build_language_instruction(lang)
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_b1.format(**context) + lang_instruction,
            user_prompt=journal,
            schema_name="therapy_b1",
            schema=B1_SCHEMA,
            task="b1",
            temperature=0.5,
            max_tokens=350,
        )

    async def run_b2(
        self,
        context: Dict[str, Any],
        conversation_history: str,
        user_msg: str
    ) -> Dict[str, Any]:
        lang = detect_language(user_msg)
        lang_instruction = build_language_instruction(lang)
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_b2.format(
                conversation_history=conversation_history,
                **context
            ) + lang_instruction,
            user_prompt=user_msg,
            schema_name="therapy_b2",
            schema=B2_SCHEMA,
            task="b2",
            temperature=0.5,
            max_tokens=400,
        )

    async def run_b3(
        self,
        context: Dict[str, Any],
        conversation_history: str,
        user_msg: str
    ) -> Dict[str, Any]:
        lang = detect_language(user_msg)
        lang_instruction = build_language_instruction(lang)
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_b3.format(
                conversation_history=conversation_history,
                **context
            ) + lang_instruction,
            user_prompt=user_msg,
            schema_name="therapy_b3",
            schema=B3_SCHEMA,
            task="b3",
            temperature=0.5,
            max_tokens=450,
        )

    # 所有文本字段（用于 blank 判断和日志打印）
    INSIGHTS_TEXT_FIELDS = [
        "llm_summary",
        "emotional_patterns",
        "common_themes",
        "growth_observations",
        "recommendations",
        "affirmation",
    ]

    # 当所有 LLM 调用都失败时返回的安全 fallback（全英文）
    INSIGHTS_FALLBACK = {
        "summary": "It seems that journaling has been a gentle companion through some mixed emotional moments recently. "
                   "Across the recent entries, there's a sense of fluctuation — some brighter days alongside periods "
                   "that felt heavier to carry. The act of writing itself reflects a quiet willingness to stay "
                   "connected with what's happening inside.",
        "llm_summary": "It seems that journaling has been a gentle companion through some mixed emotional moments recently. "
                       "Across the recent entries, there's a sense of fluctuation — some brighter days alongside periods "
                       "that felt heavier to carry. The act of writing itself reflects a quiet willingness to stay "
                       "connected with what's happening inside.",
        "emotional_patterns": "The entries suggest some shifts between lighter and heavier emotional tones. "
                              "On some days, there seems to be moments of genuine warmth or relief, while other entries "
                              "carry a heavier quality. It might help to notice what small things tend to shift the mood "
                              "in either direction.",
        "common_themes": "Across the entries, certain themes seem to recur — perhaps related to daily pressures, "
                        "social dynamics, or the quiet effort of managing difficult feelings. These recurring threads "
                        "may offer clues about what matters most right now.",
        "growth_observations": "Continuing to write, even when it feels difficult or heavy, is itself a form of "
                              "self-awareness and resilience. The willingness to show up on the page, day after day, "
                              "is something to acknowledge quietly.",
        "recommendations": "It may help to notice whether certain times of day or particular situations tend to feel "
                           "more charged than others. If a pattern emerges, it can become a small but meaningful clue. "
                           "You might try noting one thing that felt slightly lighter today, even if everything else "
                           "felt heavy. One small observation can be enough.",
        "affirmation": "You are doing something meaningful by staying in touch with yourself through writing. "
                       "That quiet effort matters, even on days when nothing feels resolved. "
                       "Be gentle with yourself today — you're not alone in this.",
        "focus_points": [
            "Notice one small moment today that felt a little different, even if subtle.",
            "If something felt heavy, writing a few words about it can be a gentle release.",
            "Remember: the act of showing up here is already a form of self-care.",
        ],
    }

    def _is_insights_blank(self, result: Dict[str, Any]) -> bool:
        """
        判断 LLM 返回的洞察结果是否实质为空。

        判定规则（满足任一即返回 False = 不为空）：
        1. summary 非空  AND  非空字段数 >= 4  → 通过
        2. recommendations 非空 AND 非空字段数 >= 3  → 通过
        3. focus_points 非空数组（>=2条） AND 非空字段数 >= 2 → 通过

        判定为空（返回 True），触发 retry：
        - 绝大多数字段为空（即使 summary 有一点内容）
        - 所有文本字段总长度 < 100 字符
        """
        # 先统计非空字段
        non_empty = []
        for field in self.INSIGHTS_TEXT_FIELDS:
            val = result.get(field, "")
            if isinstance(val, str) and val.strip():
                non_empty.append(field)
        fp = result.get("focus_points", [])
        if isinstance(fp, list) and len([x for x in fp if str(x).strip()]) >= 2:
            non_empty.append("focus_points")
        elif isinstance(fp, list) and len([x for x in fp if str(x).strip()]) >= 1:
            non_empty.append("focus_points_partial")

        total_chars = sum(len(str(result.get(f, ""))) for f in self.INSIGHTS_TEXT_FIELDS)
        non_empty_count = len(non_empty)

        # 宽松检查：4+ 字段非空，或总长度 >= 500
        if non_empty_count >= 4 or total_chars >= 500:
            print(f"[IS_INSIGHTS_BLANK] PASS  non_empty={non_empty_count}  total_chars={total_chars}  → NOT blank")
            return False

        # 严格检查：只有 summary 单字段有内容（通常是截断），视为 blank
        if result.get("summary", "").strip() and non_empty_count == 1:
            print(f"[IS_INSIGHTS_BLANK] only summary non-empty — likely truncation  → IS blank")
            return True

        # 宽松检查：summary 或 recommendations 非空 且 总长度 >= 200
        if (result.get("summary", "").strip() or result.get("recommendations", "").strip()) and total_chars >= 200:
            print(f"[IS_INSIGHTS_BLANK] PASS (len-based)  total_chars={total_chars}  → NOT blank")
            return False

        # 总长度过短
        is_blank = total_chars < 100
        print(f"[IS_INSIGHTS_BLANK] total_chars={total_chars}  non_empty={non_empty_count}  → {'blank' if is_blank else 'NOT blank'}")
        return is_blank

    def _contains_chinese(self, text: str) -> bool:
        """检查文本中是否包含中文字符。"""
        return any("\u4e00" <= ch <= "\u9fff" for ch in text)

    def _insights_has_chinese(self, result: Dict[str, Any]) -> bool:
        """
        检查洞察结果中是否包含中文字符。
        返回 True 表示有中文输出，触发英文重试。
        """
        found = []
        for field in self.INSIGHTS_TEXT_FIELDS:
            val = result.get(field, "")
            if isinstance(val, str) and self._contains_chinese(val):
                found.append(f"{field}={val[:30]!r}")
        fp = result.get("focus_points", [])
        if isinstance(fp, list):
            for i, item in enumerate(fp):
                if isinstance(item, str) and self._contains_chinese(item):
                    found.append(f"focus_points[{i}]={str(item)[:30]!r}")
        if found:
            print(f"[HAS_CHINESE] Chinese found in fields: {found}")
            return True
        print(f"[HAS_CHINESE] No Chinese detected — English-only check PASSED")
        return False

    def _log_insights_fields(self, label: str, result: Dict[str, Any]) -> None:
        """Log the raw result object and length of each text field."""
        print(f"[INSIGHTS] {label}  result_keys={list(result.keys())}")
        for field in self.INSIGHTS_TEXT_FIELDS:
            val = result.get(field, "")
            print(f"[INSIGHTS]   {field}: len={len(val)}  preview={str(val)[:60]!r}")
        focus = result.get("focus_points", [])
        print(f"[INSIGHTS]   focus_points: len={len(focus)}  value={focus}")

    async def generate_insights(
        self,
        llm_user_input: str,
        journal_content_sample: str = "",
    ) -> Dict[str, Any]:
        """
        生成日记洞察 JSON，最多 3 次 LLM 调用：

        attempt_1 : prompt_d system prompt（英文版 prompt）
        attempt_2 : + 更强的英文约束 + 内容完整性提醒
        attempt_3 : + 柔和语气 + 防止截断的最大 token
        → fallback  : 全英文安全默认值

        每次调用后都做两项校验：
        - _is_insights_blank : 关键字段是否实质为空
        - _insights_has_chinese : 是否输出了中文（强制英文）
        """
        # 不再拼接语言指令，prompt_d 已经是纯英文
        base_system = self.prompt_d
        # 英文重试时追加的通用强化指令
        english_reminder = (
            "\n\n[CRITICAL — ENGLISH OUTPUT REQUIRED]\n"
            "Return English only. No Chinese characters. Every JSON value must be in English.\n"
            "Do NOT copy-paste Chinese diary text into JSON values.\n"
            "focus_points and affirmation must also be in English."
        )
        # 第三次重试时追加的柔和语气提醒
        soft_tone_reminder = (
            "\n\n[SOFT TONE REMINDER]\n"
            "Keep the tone warm, observational, and non-diagnostic.\n"
            "Avoid: 'You are clearly...', 'You have...', 'This proves...', 'severe crisis'.\n"
            "Prefer: 'It seems that...', 'From these entries, it appears...', 'A possible pattern is...'.\n"
            "recommendations must be specific and contextual to the diary content.\n"
            "Every field must contain meaningful English text — no placeholders."
        )

        print(f"[AGENT] generate_insights  input_len={len(llm_user_input)}")
        print(f"[AGENT] user_prompt (first 300 chars):\n{llm_user_input[:300]}")

        attempt_configs = [
            {
                "label": "attempt_1",
                "system": base_system,
                "temperature": 0.4,
                "max_tokens": 3000,
            },
            {
                "label": "attempt_2",
                "system": base_system + english_reminder,
                "temperature": 0.4,
                "max_tokens": 3000,
            },
            {
                "label": "attempt_3",
                "system": base_system + english_reminder + soft_tone_reminder,
                "temperature": 0.5,
                "max_tokens": 3000,
            },
        ]

        for cfg in attempt_configs:
            label = cfg["label"]
            system = cfg["system"]
            temperature = cfg["temperature"]
            max_tokens = cfg["max_tokens"]

            print(f"\n[AGENT] === {label} ===  temp={temperature}  max_tokens={max_tokens}")
            if label != "attempt_1":
                print(f"[AGENT] {label} appended system (last 400 chars):\n{system[-400:]}")

            result = await openrouter_client.chat_structured(
                system_prompt=system,
                user_prompt=llm_user_input,
                schema_name="insights_summary",
                schema=INSIGHTS_SCHEMA,
                task="insights",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self._log_insights_fields(f"{label} raw", result)

            # 1. English-only 校验
            has_chinese = self._insights_has_chinese(result)

            # 2. Blank 校验
            is_blank = self._is_insights_blank(result)
            print(f"[AGENT] {label}  has_chinese={has_chinese}  is_blank={is_blank}")

            if not is_blank and not has_chinese:
                print(f"[AGENT] {label} PASSED — English-only & content check OK:")
                print(f"[AGENT]   " + ", ".join(
                    f"{f}={len(str(result.get(f, '')))}chars"
                    for f in self.INSIGHTS_TEXT_FIELDS
                ) + f", focus_points={len(result.get('focus_points', []))}items")
                return result

            if has_chinese:
                print(f"[AGENT] {label} failed: Chinese output detected, moving to next attempt")
            if is_blank:
                print(f"[AGENT] {label} failed: content blank, moving to next attempt")

        # 所有 attempt 都失败
        print("[AGENT] all attempts failed — returning fallback (English)")
        print(f"[AGENT] fallback: {self.INSIGHTS_FALLBACK}")
        return self.INSIGHTS_FALLBACK

    # ========== Gating Methods ==========
    # FIX: Gate prompts use {journal_text}/{assistant_b1}/{user_reply} in the system prompt
    # and user_prompt should be minimal (just a trigger), not duplicate the content.

    async def gate_b1_to_b2(
        self,
        journal_text: str,
        assistant_b1: str,
        user_reply: str
    ) -> Dict[str, Any]:
        print(f"[GATE B1->B2] user_reply='{user_reply[:50]}'")
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_gating_b1_b2.format(
                journal_text=journal_text,
                assistant_b1=assistant_b1,
                user_reply=user_reply,
            ),
            user_prompt="请判断。",  # Minimal trigger; all context is in system_prompt
            schema_name="gating_b1_b2",
            schema=GATING_B1_B2_SCHEMA,
            task="gating",
            temperature=0.2,
            max_tokens=200,
        )

    async def gate_b2_to_b3(
        self,
        journal_text: str,
        assistant_b2: str,
        user_reply: str
    ) -> Dict[str, Any]:
        print(f"[GATE B2->B3] user_reply='{user_reply[:50]}'")
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_gating_b2_b3.format(
                journal_text=journal_text,
                assistant_b2=assistant_b2,
                user_reply=user_reply,
            ),
            user_prompt="请判断。",
            schema_name="gating_b2_b3",
            schema=GATING_B2_B3_SCHEMA,
            task="gating",
            temperature=0.2,
            max_tokens=200,
        )

    # ========== Follow-up Methods ==========
    # FIX: user_reply appears in system_prompt via {user_reply} variable,
    # so user_prompt should be minimal to avoid duplication.

    async def run_b1_followup(
        self,
        context: Dict[str, Any],
        journal_text: str,
        previous_b1: str,
        user_reply: str,
        followup_style: str
    ) -> Dict[str, Any]:
        guidance = FOLLOWUP_GUIDANCE.get(followup_style, FOLLOWUP_GUIDANCE["情緒承接"])
        lang = detect_language(user_reply)
        lang_instruction = build_language_instruction(lang)
        print(f"[B1_FOLLOWUP] user_reply='{user_reply[:50]}'")
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_b1_followup.format(
                assigned_role=context.get("assigned_role", "Emotional Support"),
                journal_text=journal_text,
                previous_b1=previous_b1,
                user_reply=user_reply,
                followup_style=followup_style,
                followup_guidance=guidance,
            ) + lang_instruction,
            user_prompt="请继续。",  # Minimal; context is already in system_prompt
            schema_name="b1_followup",
            schema=B1_SCHEMA,
            task="b1_followup",
            temperature=0.5,
            max_tokens=300,
        )

    async def run_b2_followup(
        self,
        context: Dict[str, Any],
        journal_text: str,
        previous_b2: str,
        user_reply: str,
        followup_style: str
    ) -> Dict[str, Any]:
        guidance = FOLLOWUP_GUIDANCE.get(followup_style, FOLLOWUP_GUIDANCE["澄清自動想法"])
        lang = detect_language(user_reply)
        lang_instruction = build_language_instruction(lang)
        print(f"[B2_FOLLOWUP] user_reply='{user_reply[:50]}'")
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_b2_followup.format(
                assigned_role=context.get("assigned_role", "Clarify Thinking"),
                journal_text=journal_text,
                previous_b2=previous_b2,
                user_reply=user_reply,
                followup_style=followup_style,
                followup_guidance=guidance,
            ) + lang_instruction,
            user_prompt="请继续。",
            schema_name="b2_followup",
            schema=B2_SCHEMA,
            task="b2_followup",
            temperature=0.5,
            max_tokens=300,
        )


agent = TherapyAgent()
