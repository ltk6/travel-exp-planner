"""
groq_provider.py — Groq (Llama-4-Scout) provider.

Port từ call_groq_api cũ trong n5_llm_generator.py, tuân theo LLMProvider base:
  - _call raise RetryableError cho 429/503/timeout
  - Không tự sleep — base class lo backoff
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Optional

from .base import LLMProvider, RetryableError

from config import setup_logging
logger = setup_logging("N5.provider.groq")


from config import GROQ_MODEL_NAME, GROQ_API_URL, USER_AGENT

DEFAULT_SYSTEM = (
    "You are a travel expert. Always respond with pure JSON only — "
    "no markdown, no code blocks, no explanation. Start your response directly with ["
)


class GroqProvider(LLMProvider):
    name = "groq"
    model = GROQ_MODEL_NAME
    rpm_limit = 30  # Groq free tier tham khảo

    def __init__(self, model: Optional[str] = None, timeout: int = 60):
        if model:
            self.model = model
        self.timeout = timeout

    def _api_key(self) -> Optional[str]:
        # Import lazy để tránh circular và cho phép reload env
        from config import GROQ_API_KEY
        return GROQ_API_KEY

    def _call(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 4096,
    ) -> Optional[str]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system or DEFAULT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            GROQ_API_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key()}",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                raise RetryableError(f"Groq HTTP {e.code}", status=e.code) from e
            try:
                body = e.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                body = ""
            logger.error("Groq HTTP %s non-retryable: %s", e.code, body)
            return None
        except (urllib.error.URLError, TimeoutError) as e:
            raise RetryableError(f"Groq network error: {e}") from e

        choices = result.get("choices", [])
        usage = result.get("usage", {})
        if usage:
            p_tokens = usage.get("prompt_tokens", 0)
            c_tokens = usage.get("completion_tokens", 0)
            self.last_usage = {"prompt_tokens": p_tokens, "completion_tokens": c_tokens}
            logger.info("Groq usage: %d prompt, %d completion tokens", p_tokens, c_tokens)

        if choices:
            return choices[0].get("message", {}).get("content", "")

        logger.warning("Groq response format unexpected: %s", str(result)[:200])
        return None
