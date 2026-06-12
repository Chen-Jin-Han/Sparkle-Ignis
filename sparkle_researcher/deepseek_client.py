from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import settings


class DeepSeekClient:
    def __init__(self) -> None:
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.model = settings.deepseek_model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def chat(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.2, max_tokens: int = 1800) -> str:
        if not self.enabled:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"].get("content", "")

    def chat_json(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 1800) -> dict[str, Any]:
        content = self.chat(system_prompt, user_prompt, max_tokens=max_tokens)
        return parse_json_object(content)


def parse_json_object(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("{") and content.endswith("}"):
        return json.loads(content)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=re.S)
    if match:
        return json.loads(match.group(1))
    match = re.search(r"(\{.*\})", content, flags=re.S)
    if match:
        return json.loads(match.group(1))
    raise ValueError("Model response did not contain a JSON object")
