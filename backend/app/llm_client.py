# backend/app/llm_client.py
import json
import httpx
from typing import Dict, Any, Optional
from .config import settings


class OpenRouterClient:
    def __init__(self):
        self.base_url = settings.openrouter_base_url
        self.api_key = settings.openrouter_api_key
        self.model = settings.nemotron_model

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "MindJournal-AI",
        }

    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()

    def _extract_json_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        content = data["choices"][0]["message"]["content"]

        if isinstance(content, dict):
            return content

        if isinstance(content, str):
            stripped = content.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                return json.loads(stripped)
            raise ValueError(f"Model returned non-JSON text: {stripped[:100]}")

        raise ValueError("Model returned unsupported content format")

    async def chat_json_object(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_object"
            },
        }

        data = await self._post(payload)
        return self._extract_json_content(data)

    async def chat_json_schema(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: Dict[str, Any],
        temperature: float = 0.3,
        max_tokens: int = 512,
        strict: bool = True,
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": strict,
                    "schema": schema,
                },
            },
        }

        data = await self._post(payload)
        return self._extract_json_content(data)

    async def chat_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: Dict[str, Any],
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> Dict[str, Any]:
        try:
            return await self.chat_json_schema(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema_name=schema_name,
                schema=schema,
                temperature=temperature,
                max_tokens=max_tokens,
                strict=True,
            )
        except Exception:
            return await self.chat_json_object(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )


openrouter_client = OpenRouterClient()
