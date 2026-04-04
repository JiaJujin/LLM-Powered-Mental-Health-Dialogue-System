# Direct test of generate_insights — bypasses API, prints logs to THIS terminal
import asyncio
import sys
import os

# 确保 backend/app 在 path 里
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

# 设置 .env 加载
os.environ.setdefault("ENV_FILE", os.path.join(os.path.dirname(__file__), ".env"))

from app.therapy_agent import agent

# 模拟一段真实的日记内容，触发有效的 generate_insights
TEST_JOURNAL_DIGEST = [
    {"date": "2026-04-01", "emotion_label": "sad", "risk_level": 1, "summary": "今天心情很低落，感觉工作压力很大，晚上失眠。"},
    {"date": "2026-04-02", "emotion_label": "anxious", "risk_level": 1, "summary": "焦虑感加剧，担心下周的考试，和朋友聊了聊稍微好一点。"},
    {"date": "2026-04-03", "emotion_label": "neutral", "risk_level": 0, "summary": "今天稍微平静了一些，尝试做了冥想，感觉有点帮助。"},
]

EMOTION_DIST = "sad: 1, anxious: 1, neutral: 1"
RISK_DIST = "Level 1: 2, Level 0: 1"

llm_user_input = f"""
最近 14 天内，共有 3 篇日记，请基于现有全部内容进行分析。

最近 14 天日记摘要：
{TEST_JOURNAL_DIGEST}

最近 14 天情绪分布：
{EMOTION_DIST}

最近 14 天风险分布：
{RISK_DIST}
""".strip()

journal_content_sample = "今天心情很低落，感觉工作压力很大，晚上失眠。焦虑感加剧，担心下周的考试。"

print("=" * 70)
print("DIRECT generate_insights TEST")
print("=" * 70)
print(f"llm_user_input length: {len(llm_user_input)}")
print()

async def run():
    result = await agent.generate_insights(llm_user_input, journal_content_sample=journal_content_sample)
    print()
    print("=" * 70)
    print("FINAL RETURNED OBJECT:")
    print("=" * 70)
    for k, v in result.items():
        if isinstance(v, str):
            print(f"  {k} ({len(v)} chars): {v[:100]!r}")
        else:
            print(f"  {k}: {v}")
    return result

asyncio.run(run())
