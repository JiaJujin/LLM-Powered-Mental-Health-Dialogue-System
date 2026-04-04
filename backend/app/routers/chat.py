import json

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from ..config import settings
from ..llm_client import openrouter_client
from ..services.language_utils import detect_language, build_language_instruction

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    anon_id: str
    message: str
    history: List[ChatMessage] = []
    diary_content: Optional[str] = None  # passed when a diary entry exists
    # Pre-check assigned role, injected into the system prompt
    assigned_role: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str


# =============================================================================
# SHARED CONSTANTS — can be imported by other modules
# =============================================================================

_CRISIS_BLOCK = """
## 危机响应规则（最高优先级 — 必须执行）

如果用户表达了自杀想法、自伤意图，或任何直接或间接的结束生命意愿，你必须**立即、直截了当**地回应。不要给出泛泛的共情或转移话题。

### 第一句话必须直接回应用户说的内容
不要用"谢谢分享"、"我理解"、"你能告诉我更多吗"这类开场白。直接承认他们说的话。

### 必须按以下顺序执行：

1. **真诚承认**：用一句话直接回应他们所说的内容（不要说"我理解你的感受"这种泛泛的话）
2. **直接询问**：问"你现在安全吗？"或"你身边有人吗？"
3. **提供危机资源**（在同一条回复中，不要等后续消息）：
   - 香港撒玛利亚防止自杀会：2382 0000（24小时）
   - 生命热线：2382 0000
   - 紧急服务：999

### 语言规则（强制）
- 用户用中文输入 → 用**中文**回复
- 用户用英文输入 → 用**英文**回复
- 绝对不要混合语言

### 示例（中文输入 "我想自殺"）：
好的回应：
"聽到你說想結束生命，我很擔心你。你現在安全嗎？你身邊有沒有人可以陪你？請記住，你不用獨自承受這些。如果你想找人聊聊，可以撥打撒瑪利亞防止自殺會的24小時熱線：2382 0000。"

不好的回应（禁止）：
"謝謝你告訴我這些。每件事中，你最在意的是什麼呢？"

### 示例（英文输入 "I want to kill myself"）：
好的回应：
"I hear you saying you want to end your life, and that worries me. Are you safe right now? Is there someone with you? If you're in crisis, please reach out now — you can call the 24-hour Samaritans hotline: 2382 0000."

不好的回应（禁止）：
"Thank you for sharing that. What do you think is the most important part of what you just described?"

### 禁止行为
- 不要在危机回应后继续追问无关问题
- 不要将危机内容变成治疗对话
- 不要用"听起来"、"我理解"等泛泛表达作为开头
- 不要忽略用户说的危机内容或假装没看到
"""


# =============================================================================
# CHAT PAGE — free-form emotional support, no diary
# =============================================================================
_CHAT_CORE = """
你是 MindJournal AI，一个温暖、情商高的陪伴者。用户来聊天——没有日记、没有议程、不需要任何结构。
你的工作是让他们感受到真正的被倾听。

## 规则

- 永远只回应用户刚说的具体内容。不要给出任何人都适用的回复。
- 每条回复最多一个问题。不要堆叠问题。
- 不要每次都以"谢谢你分享"或类似的开场白开头。开场白要有变化，或者直接省略。
- 与用户的情绪能量匹配。如果他们在发泄，不要表现得太开心。如果他们轻松，不要沉重。
- 如果用户发了一条短小或轻松的消息，自然地回应，Stay in context。
- 可以温和地反映情绪，但不要过度标签化。让用户自己定义感受。
- 以 Rogers 来访者中心取向为基础：无条件积极关注、共情、真诚。
- 在适当的地方，自然地在对话中引入 CBT 或 ACT 技巧——不要作为正式练习，除非用户主动要求。
- **语言一致**：回复语言与用户输入语言完全一致。
"""


# =============================================================================
# DIARY CHATBOT — diary-guided conversation
# =============================================================================
_DIARY_SECTION = """
## 日记背景（必读！）
用户在本次对话开始前写下了以下日记。请**仔细阅读**，并在回复中提及至少一个日记中的具体细节。
不要给出任何人都适用的泛泛回复，你的回复必须让人觉得你是"认真读了这篇日记"的。

---
{diary_content}
---

## 回复规则（必须遵守）

1. **必须引用日记细节**：在第一条回复中，至少用一句话直接提及日记中的某个具体内容（如事件、心情、天气、措辞）。不得使用"谢谢你分享"、"我收到了你今天的内容"这类泛泛开头。绝对禁止说"和平时差不多"、"没什么特别的事发生"、"平静的一天"这类话来描述日记——除非日记真的只写了"今天和平时一样"。
2. **每次只问一个问题**：一条回复最多一个问题。多个问题会让对话变成填表感。
3. **开头要有变化**：不要每次都从"谢谢你告诉我这些"或"谢谢你的分享"开始。可以用感叹、打趣、接话等多种方式开场。
4. **对含糊消息的回应**：如果用户只说"你猜"、"随便"、"随便聊聊"，要保持对日记内容的关注，用一种轻松好奇的语气猜一件日记里提到的事。
5. **语气**：像一个在看同一本日记、陪在旁边聊天的朋友，而不是在做心理评估。温暖、好奇、轻松，不要说教。
6. **语言一致**：回复语言与用户输入语言完全一致。
7. **情绪信号识别**：如果日记中出现了难过、焦虑、失落、疲惫、无意义感、孤独等情绪词，或表达了对生活/人际关系/学习的困惑，即使用户没有明确说"我很痛苦"，也要视为情感需求信号，在回复中温和地回应这些感受。不要若无其事地跳过去。
（危机响应规则见末尾。）
"""

_BASE_LANGUAGE_RULES = """
## 语言规则（最高优先级）
- 用户用英文 → 用英文回复
- 用户用简体中文 → 用简体中文回复
- 用户用繁体中文/粤语 → 用繁体中文/粤语回复
- 不要主动切换语言，除非用户要求。
"""


_ROLE_LINE = """
## 当前角色
你的陪伴取向是：**{assigned_role}**。让这个角色贯穿整个对话。
如果未指定角色，则以"Emotional Support companion"（情绪接纳陪伴者）为基础。
"""

# ---------------------------------------------------------------------------
# Inline crisis override — injected into the system prompt at runtime
# when the latest user message contains high-risk language.
# Language-specific so the LLM immediately knows what to do.
# ---------------------------------------------------------------------------
_INLINE_CRISIS_BLOCK_ZH = """
## 【危机响应触发 — 必须立即执行】

用户刚才说了以下内容：
{latest_message}

用户表达了自杀意念或结束生命的意愿。**立即、直截了当**地回应：

第一步（第一句话）：直接承认用户说的话，例如：
  - "聽到你說【{latest_message}】，我很擔心你。"
  - "你說了【{latest_message}】，這句話讓我很在意。"
不要說"謝謝分享"、"我理解"、"能多說說嗎"之類的話。

第二步：問"你現在安全嗎？""你身邊有沒有人可以陪你？"

第三步：立即提供危機資源（在同一條回覆裡）：
  香港撒瑪利亞防止自殺會：2382 0000（24小時）
  生命熱線：2382 0000
  緊急服務：999

禁止：
- 不要繼續一般性的治療對話
- 不要追問無關的問題
- 不要假裝沒聽到這句話
- 全程用中文回覆
"""

_INLINE_CRISIS_BLOCK_EN = """
## 【CRISIS OVERRIDE — Execute Immediately】

The user just said: "{latest_message}"

This is a statement of suicidal intent. **Respond right now, directly**:

Step 1 (first sentence): Acknowledge exactly what they said. Do NOT open with "Thank you for sharing" or "Can you tell me more". Examples:
  - "Hearing you say '{latest_message}' worries me."
  - "You said '{latest_message}' — I want you to know I'm concerned about you."

Step 2: Ask "Are you safe right now?" / "Is there someone with you?"

Step 3: In the same reply, provide crisis resources:
  Samaritans (HK): 2382 0000 (24 hours)
  Emergency: 999

Do NOT:
- Continue with general therapy questions
- Ask unrelated follow-up questions
- Ignore or gloss over this statement
- Switch to any other language
"""


def build_system_prompt(
    lang_instruction: str,
    diary_content: str | None,
    assigned_role: str | None = None,
    latest_message: str | None = None,
) -> str:
    """
    Build the full system prompt for a single chat request.

    - diary_content is None on the Chat page (free-form).
      diary_content is set on the diary chatbot after journal submission.
    - assigned_role comes from Pre-check. Default to "Emotional Support companion"
      when not provided.
    - latest_message is the most recent user text. Used to detect crisis language
      so we can inject an inline override block before the general crisis block.
    """
    from ..services.language_utils import contains_crisis_language

    has_diary = bool(diary_content)

    # Language rules always come first
    prompt_parts = [_BASE_LANGUAGE_RULES]

    # ---- Inline crisis override block (highest priority — before everything else) ----
    if latest_message and contains_crisis_language(latest_message):
        detected_lang = detect_language(latest_message)
        if detected_lang == "zh":
            crisis_inline = _INLINE_CRISIS_BLOCK_ZH.format(latest_message=latest_message)
        else:
            crisis_inline = _INLINE_CRISIS_BLOCK_EN.format(latest_message=latest_message)
        prompt_parts.append(crisis_inline)
        prompt_parts.append("")

    if has_diary:
        prompt_parts.append(
            _DIARY_SECTION.format(diary_content=diary_content.strip())
        )
        prompt_parts.append(
            "\n## 当前对话\n以下是与用户的对话历史（用户的第一条消息已经在下方）："
        )
    else:
        # Chat page — free-form
        role = assigned_role or "Emotional Support companion"
        prompt_parts.append(_ROLE_LINE.format(assigned_role=role))
        prompt_parts.append(_CHAT_CORE)
        prompt_parts.append("\n## 对话历史：")

    # Crisis block always appended (also shared with diary chatbot via this function)
    prompt_parts.append(_CRISIS_BLOCK)

    # Language rules injected at the end so they take final priority
    prompt_parts.append("")
    return "\n".join(prompt_parts) + lang_instruction


def _format_stream_error(exc: BaseException) -> str:
    """User-facing Chinese message for SSE error event (also logged on server)."""
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        detail = ""
        try:
            body = exc.response.json()
            err = body.get("error") if isinstance(body.get("error"), dict) else body
            if isinstance(err, dict):
                detail = str(err.get("message") or err.get("msg") or err)[:300]
            else:
                detail = str(body)[:300]
        except Exception:
            detail = (exc.response.text or "")[:300]
        if code == 401:
            return (
                "智谱 API 鉴权失败（401）。请在 backend 目录的 .env 中设置有效的 ZHIPU_API_KEY，"
                "并重启后端。详情：" + detail
            )
        if code == 429:
            return "智谱 API 请求过于频繁（429），请稍后再试。"
        return f"智谱 API 返回错误（{code}）。详情：{detail}"
    if isinstance(exc, httpx.TimeoutException):
        return f"请求智谱 API 超时（{settings.request_timeout}s），请检查网络后重试。"
    if isinstance(exc, httpx.RequestError):
        return f"无法连接智谱 API：{exc}。请检查网络与 zhipu_base_url 配置。"
    return f"AI 服务异常：{exc}"


async def chat_stream_generator(
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 300,
    thinking_disabled: bool = True,
):
    """
    Generator that yields SSE-formatted chunks for streaming.

    - thinking_disabled=True: 禁用智谱 thinking/reasoning 过程，
      content 立即开始输出（用户 1-3 秒内看到第一个字）
    - thinking_disabled=False: 保留 thinking，content 延迟输出
    """
    print(
        f"[CHAT/STREAM] stream start  msg_count={len(messages)}  "
        f"temperature={temperature}  max_tokens={max_tokens}  "
        f"thinking_disabled={thinking_disabled}"
    )
    chunk_idx = 0
    try:
        async for chunk in openrouter_client.stream_chat(
            messages=messages,
            task="chat",
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_disabled=thinking_disabled,
        ):
            chunk_idx += 1
            if chunk_idx == 1:
                print(f"[CHAT/STREAM] first chunk received, len={len(chunk)}")
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        print(f"[CHAT/STREAM] stream complete  total_chunks={chunk_idx}")
    except Exception as e:
        msg = _format_stream_error(e)
        print(f"[CHAT/STREAM] FAILED: {type(e).__name__}: {e}  user_msg={msg!r}")
        yield f"data: {json.dumps({'error': msg})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    lang = detect_language(request.message)
    lang_instruction = build_language_instruction(lang)
    system_content = build_system_prompt(
        lang_instruction, request.diary_content, request.assigned_role,
        latest_message=request.message,
    )
    messages = [{"role": "system", "content": system_content}]
    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})
    # NOTE: request.history already contains the new message from frontend;
    # do NOT append request.message again here to avoid duplication.
    # If history is empty (fresh chat), prepend the message as user.
    if not request.history:
        messages.append({"role": "user", "content": request.message})

    print(f"[CHAT] messages count: {len(messages)}, last role: {messages[-1]['role'] if messages else 'none'}")
    print(f"[CHAT] diary_content received: {repr(request.diary_content[:80]) if request.diary_content else 'None'}")
    payload = {
        "model": openrouter_client.model,  # single model (glm-4.5-air) for all tasks
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 300,
    }
    # 禁用 thinking，确保快速响应
    payload["extra_body"] = {"thinking": {"type": "disabled"}}

    try:
        result = await openrouter_client._post(payload)
    except Exception as e:
        msg = _format_stream_error(e)
        print(f"[CHAT] LLM request failed: {type(e).__name__}: {e}")
        return ChatResponse(reply=msg)
    # 安全提取 content：不再是直接字典访问
    reply = openrouter_client._safe_get_content(result, context="CHAT")
    if not reply:
        print(f"[CHAT] [WARN] LLM content empty, returning friendly fallback")
        return ChatResponse(reply="抱歉，AI 助手暂时无法回应，请稍后重试。")

    print(f"[CHAT] [OK] reply len={len(reply)}, preview={reply[:40].replace(chr(10), ' ')!r}")
    return ChatResponse(reply=reply)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming version of /chat endpoint.
    Returns SSE stream for real-time token-by-token display on frontend.
    """
    lang = detect_language(request.message)
    lang_instruction = build_language_instruction(lang)
    system_content = build_system_prompt(
        lang_instruction, request.diary_content, request.assigned_role,
        latest_message=request.message,
    )
    messages = [{"role": "system", "content": system_content}]
    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})
    # NOTE: request.history already contains the new message from frontend;
    # do NOT append request.message again here to avoid duplication.
    if not request.history:
        messages.append({"role": "user", "content": request.message})

    print(f"[CHAT/STREAM] messages count: {len(messages)}, last role: {messages[-1]['role'] if messages else 'none'}")
    print(f"[CHAT/STREAM] diary_content received: {repr(request.diary_content[:200]) if request.diary_content else 'None'}")
    print(f"[CHAT/STREAM] system_prompt full:\n{system_content}")
    print(f"[CHAT/STREAM] system_prompt preview (first 800 chars): {system_content[:800].replace(chr(10), ' ')}")

    return StreamingResponse(
        chat_stream_generator(messages, temperature=0.7, max_tokens=300, thinking_disabled=True),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
