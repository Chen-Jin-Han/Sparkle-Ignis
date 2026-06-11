from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class DeepSeekClient:
    """Small OpenAI-compatible DeepSeek client using only the standard library."""

    def __init__(self, use_deepseek: bool | None = None) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        self.timeout = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "60"))
        self.use_deepseek = use_deepseek

    @property
    def enabled(self) -> bool:
        configured = os.getenv("SPARKLE_USE_DEEPSEEK", "false").lower() == "true"
        requested = configured if self.use_deepseek is None else self.use_deepseek
        return bool(self.api_key) and requested

    def polish_report(self, report: str, query: str) -> str:
        if not self.enabled:
            return report

        prompt = (
            "你是 Sparkle 的技术报告增强 Agent。请在不改变事实的前提下润色报告，"
            "保持中文、保留 Markdown 结构、保留所有火焰 Agent 名称，并让内容更适合面试讲解。\n\n"
            f"调研主题：{query}\n\n原报告：\n{report}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a concise technical report editor."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "temperature": 0.35,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return report + f"\n\n> DeepSeek enhancement skipped: {exc}"

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return report + "\n\n> DeepSeek enhancement skipped: unexpected response shape."

        return content.strip() or report
