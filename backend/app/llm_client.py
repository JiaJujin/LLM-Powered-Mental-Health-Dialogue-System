# backend/app/llm_client.py
"""
MindJournal AI - LLM Client for 智谱官方 API (Z.ai / BigModel)

迁移说明：
- Base URL: https://open.bigmodel.cn/api/paas/v4/chat/completions
- Auth: Authorization: Bearer <ZHIPU_API_KEY>
- 智谱 API 兼容 OpenAI chat completions 接口格式
- 不支持 response_format（json_object / json_schema），
  故通过 chat_structured 的 try-except fallback 机制实现结构化输出
- SSE streaming 格式与 OpenAI 兼容，可直接复用
- 重要：glm-4.5-air 默认启用 thinking 模式，必须通过 extra_body.thinking={type:"disabled"}
  来禁用，否则 content 会被延迟到 reasoning_content 之后才返回
"""
import json
import httpx
from typing import Dict, Any, AsyncIterator, Literal
from .config import settings

# Token limits per task type
TOKEN_LIMITS = {
    "precheck": 150,
    "emotion": 120,
    "crisis": 150,
    "gating": 180,
    "chat": 280,
    "b1": 350,
    "b2": 400,
    "b3": 450,
    "b1_followup": 300,
    "b2_followup": 300,
    "insights": 800,
}


class ZhipuClient:
    """智谱 BigModel 官方 API 客户端。"""

    CHAT_PATH = "/chat/completions"

    def __init__(self):
        base = settings.zhipu_base_url.rstrip("/")
        self.base_url = f"{base}{self.CHAT_PATH}"  # 完整端点
        self._base_for_log = base  # 用于日志（不打印完整路径藏 key）
        self.api_key = settings.zhipu_api_key
        self.model = settings.zhipu_model
        self.timeout = settings.request_timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: list,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 300,
        thinking_disabled: bool = True,
    ) -> Dict[str, Any]:
        """
        构建智谱 API 请求体。
        - thinking_disabled=True: 禁用思考过程，content 立即开始输出
        - thinking_disabled=False: 保留思考，会先输出 reasoning_content
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stream:
            payload["stream"] = True
        # 关键：禁用 thinking，确保 content 立即输出，不延迟
        if thinking_disabled:
            payload["extra_body"] = {
                "thinking": {
                    "type": "disabled",
                }
            }
        return payload

    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        model_used = payload.get("model", "unknown")
        max_toks = payload.get("max_tokens", "N/A")
        thinking = payload.get("extra_body", {}).get("thinking", "not set")
        print(f"[ZHIPU_CLIENT] POST  url={self._base_for_log}/chat/completions  model={model_used}  max_tokens={max_toks}  thinking={thinking}")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self.base_url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices")
            _ok = choices and len(choices) > 0 and isinstance(choices[0], dict)
            _msg = choices[0].get("message") if _ok else None
            _content = _msg.get("content") if _msg else None
            print(
                f"[ZHIPU_CLIENT] Response OK  "
                f"choices_exists={choices is not None}  "
                f"choices_len={len(choices) if choices is not None else 'N/A'}  "
                f"content_len={len(_content) if _content else 0}  "
                f"finish_reason={data.get('choices', [{}])[0].get('finish_reason', '')}"
            )
            print(f"[ZHIPU_CLIENT] raw_response (first 800 chars): {str(data)[:800]}")
            return data

    # ---------- 安全响应解析 ----------

    def _safe_get_content(self, data: Dict[str, Any], context: str = "") -> str:
        """
        安全地从智谱 API 响应中提取 choices[0].message.content。
        会详细日志记录每一步状态，方便排查。
        """
        ctx = f"[{context}] " if context else "[LLM] "

        choices = data.get("choices")
        if choices is None:
            print(f"{ctx}[WARN] choices field missing. keys={list(data.keys())}")
            return ""
        if not isinstance(choices, list):
            print(f"{ctx}[WARN] choices is not a list, type={type(choices)}")
            return ""
        if len(choices) == 0:
            print(f"{ctx}[WARN] choices is empty. response={str(data)[:300]}")
            return ""

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            print(f"{ctx}[WARN] choices[0] is not a dict, type={type(first_choice)}")
            return ""

        message = first_choice.get("message")
        if message is None:
            print(f"{ctx}[WARN] message is None. first_choice={first_choice}")
            return ""

        content = message.get("content")
        if content is None:
            print(f"{ctx}[WARN] content is None. message={message}")
            return ""

        if not isinstance(content, str):
            print(f"{ctx}[WARN] content is not a str, type={type(content)}, converting")
            content = str(content)

        print(f"{ctx}[OK] content extracted, len={len(content)}, preview={content[:40].replace(chr(10), ' ')!r}")
        return content

    def _strip_markdown_code_block(self, raw: str) -> str:
        """
        去掉 markdown 代码块外壳。

        如果内容形如：
            ```json
            { ... }
            ```
        则去掉首行的 ```/json 和尾行的 ```，只返回中间 JSON 内容；
        否则原样返回。
        """
        s = raw.strip()
        lines = s.splitlines()
        if len(lines) >= 2:
            first = lines[0].strip()
            last = lines[-1].strip()
            if (first.startswith("```") and last == "```") or \
               (first.startswith("```json") and last == "```"):
                inner = "\n".join(lines[1:-1])
                if inner.startswith("{"):
                    print(f"[STRIP_MARKDOWN] stripped code block, inner starts with '{{'")
                    return inner
        return raw

    def _extract_json_content(self, data: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        """
        从模型返回中提取 JSON 内容。
        支持三种格式：
          1. content is already a dict
          2. content is a valid JSON string
          3. content is free text → regex fallback extracts each field
        当 content 为空时，返回 fallback dict 而不抛异常。
        """
        ctx = f"[{context}] " if context else "[LLM] "

        content = self._safe_get_content(data, context=context)
        if not content:
            print(f"{ctx}[FALLBACK:CONTENT_EMPTY] content empty, returning empty dict")
            return {}

        if isinstance(content, dict):
            print(f"{ctx}[OK] content is already a dict")
            return content

        if isinstance(content, str):
            stripped = content.strip()

            # 统一初始化所有字段（确保返回字典一定包含每一个键）
            ALL_STRING_FIELDS = [
                "summary", "llm_summary",
                "emotional_patterns", "emotion_patterns",
                "common_themes", "themes",
                "growth_observations", "growth",
                "recommendations",
                "affirmation",
            ]
            result: Dict[str, Any] = {f: "" for f in ALL_STRING_FIELDS}
            result["focus_points"] = []

            # Attempt 1: 去掉 markdown 代码块外壳后尝试 JSON 解析
            raw_for_json = self._strip_markdown_code_block(stripped)
            if raw_for_json.startswith("{"):
                try:
                    parsed = json.loads(raw_for_json)
                    print(f"{ctx}[OK] JSON parsed (stripped markdown), keys={list(parsed.keys())}")
                    for f in ALL_STRING_FIELDS:
                        if f in parsed and parsed[f]:
                            result[f] = parsed[f]
                    if "focus_points" in parsed and isinstance(parsed["focus_points"], list):
                        result["focus_points"] = [str(x) for x in parsed["focus_points"] if str(x).strip()]
                    # 字段名标准化：summary → llm_summary（上游 insights.py 期望 llm_summary）
                    if not result.get("llm_summary") and result.get("summary"):
                        result["llm_summary"] = result["summary"]
                    return result
                except json.JSONDecodeError as e:
                    print(f"{ctx}[FALLBACK:JSON_PARSE_FAIL] JSON parse (strip) failed: {e}. raw={raw_for_json[:300]!r}")

            # Attempt 2: 原始内容直接尝试 JSON（非 markdown 格式的纯 JSON）
            if stripped.startswith("{"):
                try:
                    parsed = json.loads(stripped)
                    print(f"{ctx}[OK] JSON parsed (raw), keys={list(parsed.keys())}")
                    for f in ALL_STRING_FIELDS:
                        if f in parsed and parsed[f]:
                            result[f] = parsed[f]
                    if "focus_points" in parsed and isinstance(parsed["focus_points"], list):
                        result["focus_points"] = [str(x) for x in parsed["focus_points"] if str(x).strip()]
                    if not result.get("llm_summary") and result.get("summary"):
                        result["llm_summary"] = result["summary"]
                    return result
                except json.JSONDecodeError as e:
                    print(f"{ctx}[FALLBACK:JSON_PARSE_FAIL] JSON parse (raw) failed: {e}. raw={stripped[:300]!r}")

            # Attempt 3: regex 逐字段提取（应对截断响应）
            print(f"{ctx}[FALLBACK] attempting regex field extraction from free text")
            import re

            for field in ALL_STRING_FIELDS:
                pattern = rf'"{field}"\s*:\s*"((?:[^"\\]|\\.)*)"'
                m = re.search(pattern, stripped, re.IGNORECASE | re.DOTALL)
                if m:
                    extracted = m.group(1)
                    extracted = (extracted
                        .replace('\\"', '"')
                        .replace('\\n', '\n')
                        .replace('\\r', '\r')
                        .replace('\\\\', '\\'))
                    result[field] = extracted
                    print(f"{ctx}[REGEX] {field}={extracted[:60]!r}...")

            # focus_points — 贪婪匹配，支持截断（末尾的 ] 可能被截掉）
            fp_pattern = r'"focus_points"\s*:\s*\[(.*?)(?:\]|$)'
            m_arr = re.search(fp_pattern, stripped, re.IGNORECASE | re.DOTALL)
            if m_arr:
                arr_content = m_arr.group(1)
                items = []
                for item_m in re.finditer(r'"((?:[^"\\]|\\.)*)"', arr_content):
                    item = (item_m.group(1)
                        .replace('\\"', '"')
                        .replace('\\n', '\n')
                        .replace('\\\\', '\\'))
                    if item.strip():
                        items.append(item)
                if items:
                    result["focus_points"] = items
                    print(f"{ctx}[REGEX] focus_points={items}")
            else:
                # 兜底：跳过已知字段名，只取长度 >= 15 的描述性字符串片段
                KNOWN_FIELDS = {
                    "summary", "llm_summary", "emotional_patterns", "emotion_patterns",
                    "common_themes", "themes", "growth_observations", "growth",
                    "recommendations", "affirmation", "focus_points", "focus_point",
                }
                fp_plain = re.findall(r'"([^"]{15,120}?)"', stripped, re.IGNORECASE)
                candidates = [x.strip() for x in fp_plain
                              if x.strip() and x.strip() not in KNOWN_FIELDS
                              and not any(x.strip().startswith(k) for k in KNOWN_FIELDS)]
                if candidates:
                    result["focus_points"] = candidates[:6]
                    print(f"{ctx}[REGEX] focus_points (smart plain)={result['focus_points']}")

            non_empty = [k for k, v in result.items() if v and k != "focus_points"]
            if non_empty:
                print(f"{ctx}[REGEX] extracted fields: {non_empty}")
            else:
                print(f"{ctx}[REGEX] no fields extracted. raw preview: {stripped[:200]!r}")
            # 字段名标准化：summary → llm_summary
            if not result.get("llm_summary") and result.get("summary"):
                result["llm_summary"] = result["summary"]
            return result

        raise ValueError(f"{ctx} content 类型不支持: {type(content)}")

    # ---------- 结构化 JSON 调用 ----------

    async def chat_json_object(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> Dict[str, Any]:
        """
        调用模型，让其输出 JSON 对象。
        智谱不支持 response_format 参数，通过 prompt 要求 + 后处理实现。
        禁用 thinking 确保快速响应。
        """
        messages = [
            {"role": "system", "content": system_prompt + "\n\n重要：你的所有回复必须只输出一个合法的 JSON 对象，不要输出任何其他文字。"},
            {"role": "user", "content": user_prompt},
        ]
        payload = self._build_payload(
            messages=messages,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_disabled=True,
        )
        data = await self._post(payload)
        return self._extract_json_content(data, context="chat_json_object")

    async def chat_json_schema(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: Dict[str, Any],
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> Dict[str, Any]:
        """
        智谱不支持 response_format json_schema，fallback 到 chat_json_object，
        并在 prompt 中嵌入 schema 要求。
        """
        return await self.chat_json_object(
            system_prompt=system_prompt + f"\n\n输出格式要求：{json.dumps(schema, ensure_ascii=False)}",
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def chat_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: Dict[str, Any],
        task: str = "default",
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> Dict[str, Any]:
        """
        结构化输出：先尝试 JSON schema 方式，失败则 fallback 到 JSON object 方式。
        失败时会区分原因（content 空 / JSON 解析失败）并记录日志。
        """
        print(f"[ZHIPU_CLIENT] chat_structured  task={task}  model={self.model}  max_tokens={max_tokens}")
        try:
            return await self.chat_json_schema(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema_name=schema_name,
                schema=schema,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            failure_reason = _classify_failure(e)
            print(f"[ZHIPU_CLIENT] [FALLBACK:{failure_reason}] JSON parse failed for [{task}], trying plain JSON object: {e}")
            try:
                return await self.chat_json_object(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e2:
                failure_reason2 = _classify_failure(e2)
                print(f"[ZHIPU_CLIENT] [FATAL:{failure_reason}|{failure_reason2}] Both JSON schema and JSON object failed for [{task}]  schema={schema_name}")
                return {}

    # ---------- Streaming 支持（chatbot 实时打字） ----------
    # 关键修复：
    # 1. extra_body.thinking={type:"disabled"} 禁用思考过程，content 立即输出
    # 2. 提取 reasoning_content 并打印日志（便于调试是否还有残留 thinking）
    # 3. 只 yield content 给前端，不 yield reasoning_content（避免干扰用户）

    StreamChunk = Dict[Literal["content", "reasoning_content", "finish_reason"], str]

    async def stream_chat(
        self,
        messages: list,
        task: str = "chat",
        temperature: float = 0.7,
        max_tokens: int = 300,
        thinking_disabled: bool = True,
    ) -> AsyncIterator[str]:
        """
        智谱 streaming SSE：与 OpenAI 兼容。

        每次 yield 一个 content 文本片段（供前端实时渲染）。
        reasoning_content 会打印到后端日志（不在 SSE 中发送给前端）。

        thinking_disabled=True（默认）：
          extra_body.thinking={type:"disabled"}
          模型跳过思考过程，直接输出 content
          → 用户会在 1-3 秒内看到第一个字符

        thinking_disabled=False：
          模型先输出 reasoning_content（思考过程），再输出 content
          → reasoning_content 片段会打印到日志，content 正常 yield
        """
        payload = self._build_payload(
            messages=messages,
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_disabled=thinking_disabled,
        )
        print(
            f"[ZHIPU_CLIENT/STREAM] START  model={self.model}  "
            f"msg_count={len(messages)}  max_tokens={max_tokens}  "
            f"temperature={temperature}  thinking_disabled={thinking_disabled}  "
            f"url={self.base_url}"
        )

        total_content_chars = 0
        total_reasoning_chars = 0
        chunk_count = 0
        first_content_ts: float | None = None
        start_ts = __import__("time").time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", self.base_url, headers=self._headers(), json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            reasoning = delta.get("reasoning_content", "")

                            if reasoning:
                                r_trunc = reasoning[:500] + ("..." if len(reasoning) > 500 else "")
                                print(f"[ZHIPU_CLIENT/STREAM] reasoning_content ({len(reasoning)} chars): {r_trunc}")
                                total_reasoning_chars += len(reasoning)

                            if content:
                                if first_content_ts is None:
                                    first_content_ts = __import__("time").time()
                                    latency_ms = int((first_content_ts - start_ts) * 1000)
                                    print(
                                        f"[ZHIPU_CLIENT/STREAM] FIRST CONTENT  "
                                        f"latency={latency_ms}ms  total_reasoning_chars_so_far={total_reasoning_chars}"
                                    )
                                total_content_chars += len(content)
                                chunk_count += 1
                                yield content
                        except json.JSONDecodeError:
                            print(f"[ZHIPU_CLIENT/STREAM] JSON decode error on line: {line[:100]}")
                            continue
        except httpx.TimeoutException:
            print(f"[ZHIPU_CLIENT/STREAM] TIMEOUT after {self.timeout}s  content_sent={total_content_chars}")
            raise
        except Exception as e:
            print(f"[ZHIPU_CLIENT/STREAM] ERROR  {type(e).__name__}: {e}  content_sent={total_content_chars}")
            raise

        elapsed = __import__("time").time() - start_ts
        print(
            f"[ZHIPU_CLIENT/STREAM] DONE  elapsed={elapsed:.1f}s  "
            f"chunks={chunk_count}  content_chars={total_content_chars}  "
            f"reasoning_chars={total_reasoning_chars}"
        )


def _classify_failure(exc: Exception) -> str:
    """
    根据异常类型或消息内容，分类失败原因，供日志标签使用。
    CONTENT_EMPTY  : API 返回了空 content（模型没有输出）
    JSON_PARSE_FAIL: content 非空但不是合法 JSON
    HTTP_ERROR      : HTTP 请求本身失败
    UNKNOWN         : 其他异常
    """
    msg = str(exc).lower()
    if "content empty" in msg or "content is none" in msg or "content is empty" in msg:
        return "CONTENT_EMPTY"
    if "jsondecodeerror" in msg or "json" in msg and ("parse" in msg or "decode" in msg):
        return "JSON_PARSE_FAIL"
    if "httpx" in msg or "status_code" in msg or "request" in msg:
        return "HTTP_ERROR"
    return "UNKNOWN"


# 单例实例（保持向后兼容，旧的 import 路径不变）
zhipu_client = ZhipuClient()
# 向后兼容别名
openrouter_client = zhipu_client  # therapy_agent.py 等处 import openrouter_client
