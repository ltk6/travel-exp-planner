"""
gemini_provider.py — Google Gemini provider.

Ưu tiên tốc độ: mặc định dùng gemini-2.0-flash (free tier ~15 RPM, latency thấp).
Bật response_mime_type="application/json" để Gemini tự trả JSON thuần,
giảm rủi ro parse lỗi do markdown wrapper.

Dùng REST API trực tiếp (urllib) — không cần cài thêm SDK google-genai.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional
from .base import LLMProvider, RetryableError
from config import setup_logging
logger = setup_logging("N5.provider.gemini")

from config import GEMINI_MODEL_NAME, GEMINI_API_BASE, USER_AGENT

DEFAULT_SYSTEM = (
    "You are a travel expert. Always respond with pure JSON only — "
    "no markdown, no code blocks, no explanation. Start your response directly with ["
)


class GeminiProvider(LLMProvider):
    name = "gemini"
    model = GEMINI_MODEL_NAME
    rpm_limit = 15  # Gemini free tier: 15 RPM cho 2.0-flash

    def __init__(self, model: Optional[str] = None, timeout: int = 30):
        if model:
            self.model = model
        self.timeout = timeout

    def _api_key(self) -> Optional[str]:
        from config import GEMINI_API_KEY
        return GEMINI_API_KEY

    def _call(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 4096,
    ) -> Optional[str]:
        url = f"{GEMINI_API_BASE}/{self.model}:generateContent?key={self._api_key()}"

        payload = {
            "system_instruction": {
                "parts": [{"text": system or DEFAULT_SYSTEM}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                raise RetryableError(f"Gemini HTTP {e.code}", status=e.code) from e
            try:
                body = e.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                body = ""
            logger.error("Gemini HTTPError %s non-retryable: %s", e.code, body)
            return None
        except (urllib.error.URLError, TimeoutError) as e:
            raise RetryableError(f"Gemini network error: {e}") from e

        # Gemini response: { candidates: [ { content: { parts: [ { text: "..." } ] } } ] }
        candidates = result.get("candidates", [])
        if not candidates:
            # Có thể bị safety block
            feedback = result.get("promptFeedback", {})
            logger.warning("Gemini no candidates, feedback=%s", feedback)
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            finish_reason = candidates[0].get("finishReason", "unknown")
            logger.warning("Gemini empty parts, finish_reason=%s", finish_reason)
            return None

        usage = result.get("usageMetadata", {})
        if usage:
            p_tokens = usage.get("promptTokenCount", 0)
            c_tokens = usage.get("candidatesTokenCount", 0)
            self.last_usage = {"prompt_tokens": p_tokens, "completion_tokens": c_tokens}
            logger.info("Gemini usage: %d prompt, %d completion tokens", p_tokens, c_tokens)

        return parts[0].get("text", "")
