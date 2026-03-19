# backend/app/therapy_agent.py
from pathlib import Path
from typing import Dict, Any, Optional
from .llm_client import openrouter_client
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

# Follow-up style guidance
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

        # Gating prompts
        self.prompt_gating_b1_b2 = load_prompt("prompt_gating_b1_b2.txt")
        self.prompt_gating_b2_b3 = load_prompt("prompt_gating_b2_b3.txt")

        # Follow-up prompts
        self.prompt_b1_followup = load_prompt("prompt_b1_followup.txt")
        self.prompt_b2_followup = load_prompt("prompt_b2_followup.txt")

    async def select_role(self, body: str, need: str, emotion: str) -> Dict[str, Any]:
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_a,
            user_prompt=f"body={body}, need={need}, emotion={emotion}",
            schema_name="role_selection",
            schema=ROLE_SELECTION_SCHEMA,
            temperature=0.2,
            max_tokens=250,
        )

    async def classify_emotion(self, text: str) -> Dict[str, Any]:
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_e,
            user_prompt=text,
            schema_name="emotion_classification",
            schema=EMOTION_CLASSIFICATION_SCHEMA,
            temperature=0.1,
            max_tokens=180,
        )

    async def detect_crisis(self, text: str) -> Dict[str, Any]:
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_c,
            user_prompt=text,
            schema_name="crisis_detection",
            schema=CRISIS_SCHEMA,
            temperature=0.1,
            max_tokens=280,
        )

    async def run_b1(self, context: Dict[str, Any], journal: str) -> Dict[str, Any]:
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_b1.format(**context),
            user_prompt=journal,
            schema_name="therapy_b1",
            schema=B1_SCHEMA,
            temperature=0.5,
            max_tokens=420,
        )

    async def run_b2(
        self,
        context: Dict[str, Any],
        conversation_history: str,
        user_msg: str
    ) -> Dict[str, Any]:
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_b2.format(
                conversation_history=conversation_history,
                **context
            ),
            user_prompt=user_msg,
            schema_name="therapy_b2",
            schema=B2_SCHEMA,
            temperature=0.5,
            max_tokens=420,
        )

    async def run_b3(
        self,
        context: Dict[str, Any],
        conversation_history: str,
        user_msg: str
    ) -> Dict[str, Any]:
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_b3.format(
                conversation_history=conversation_history,
                **context
            ),
            user_prompt=user_msg,
            schema_name="therapy_b3",
            schema=B3_SCHEMA,
            temperature=0.5,
            max_tokens=500,
        )

    async def generate_insights(self, llm_user_input: str) -> Dict[str, Any]:
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_d,
            user_prompt=llm_user_input,
            schema_name="insights_summary",
            schema=INSIGHTS_SCHEMA,
            temperature=0.4,
            max_tokens=900,
        )

    # ========== Gating Methods ==========

    async def gate_b1_to_b2(
        self,
        journal_text: str,
        assistant_b1: str,
        user_reply: str
    ) -> Dict[str, Any]:
        """Gate decision: should we proceed from B1 to B2?"""
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_gating_b1_b2,
            user_prompt=f"原始日记：{journal_text}\n\nAI 第一轮回应（B1）：{assistant_b1}\n\n使用者最新回复：{user_reply}",
            schema_name="gating_b1_b2",
            schema=GATING_B1_B2_SCHEMA,
            temperature=0.2,
            max_tokens=300,
        )

    async def gate_b2_to_b3(
        self,
        journal_text: str,
        assistant_b2: str,
        user_reply: str
    ) -> Dict[str, Any]:
        """Gate decision: should we proceed from B2 to B3?"""
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_gating_b2_b3,
            user_prompt=f"原始日记：{journal_text}\n\nAI 第二轮回应（B2）：{assistant_b2}\n\n使用者最新回复：{user_reply}",
            schema_name="gating_b2_b3",
            schema=GATING_B2_B3_SCHEMA,
            temperature=0.2,
            max_tokens=300,
        )

    # ========== Follow-up Methods ==========

    async def run_b1_followup(
        self,
        context: Dict[str, Any],
        journal_text: str,
        previous_b1: str,
        user_reply: str,
        followup_style: str
    ) -> Dict[str, Any]:
        """Generate a follow-up in B1 style when gating says STAY_IN_B1"""
        guidance = FOLLOWUP_GUIDANCE.get(followup_style, FOLLOWUP_GUIDANCE["情緒承接"])
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_b1_followup.format(
                assigned_role=context.get("assigned_role", "Emotional Support"),
                journal_text=journal_text,
                previous_b1=previous_b1,
                user_reply=user_reply,
                followup_style=followup_style,
                followup_guidance=guidance,
            ),
            user_prompt=user_reply,
            schema_name="b1_followup",
            schema=B1_SCHEMA,
            temperature=0.5,
            max_tokens=350,
        )

    async def run_b2_followup(
        self,
        context: Dict[str, Any],
        journal_text: str,
        previous_b2: str,
        user_reply: str,
        followup_style: str
    ) -> Dict[str, Any]:
        """Generate a follow-up in B2 style when gating says STAY_IN_B2"""
        guidance = FOLLOWUP_GUIDANCE.get(followup_style, FOLLOWUP_GUIDANCE["澄清自動想法"])
        return await openrouter_client.chat_structured(
            system_prompt=self.prompt_b2_followup.format(
                assigned_role=context.get("assigned_role", "Clarify Thinking"),
                journal_text=journal_text,
                previous_b2=previous_b2,
                user_reply=user_reply,
                followup_style=followup_style,
                followup_guidance=guidance,
            ),
            user_prompt=user_reply,
            schema_name="b2_followup",
            schema=B2_SCHEMA,
            temperature=0.5,
            max_tokens=350,
        )


agent = TherapyAgent()
