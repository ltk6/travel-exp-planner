"""
base.py — Abstract LLM provider interface.

Mỗi provider (Groq, Gemini, ...) subclass `LLMProvider` và implement:
  - `_api_key()` — đọc API key từ config
  - `_call(prompt, system, **opts)` — gọi HTTP thật, raise RetryableError cho
    lỗi tạm thời (429, 503, timeout) để base class tự retry

Base class lo phần chung: kiểm tra availability, exponential backoff có jitter,
logging có cấu trúc. Các subclass KHÔNG tự retry.
"""

from __future__ import annotations

import abc
import time
import random
from typing import Optional
from config import setup_logging, LLM_RETRY_WAIT_BASE
logger = setup_logging("N5.provider.base")


class RetryableError(Exception):
    """Lỗi tạm thời (429/503/timeout) — base class sẽ retry với backoff."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class LLMProvider(abc.ABC):
    """
    Giao diện chung cho mọi LLM provider.

    Thuộc tính class:
      name      — định danh ngắn ("groq", "gemini")
      model     — tên model cụ thể, để log/benchmark
      rpm_limit — rate limit tham khảo (requests/minute)
    """

    name: str = "base"
    model: str = ""
    rpm_limit: int = 0
    last_usage: Optional[dict] = None  # { "prompt_tokens": int, "completion_tokens": int }

    # ── Subclass phải implement ─────────────────────────────────────────────

    @abc.abstractmethod
    def _api_key(self) -> Optional[str]:
        """Trả về API key, hoặc None/empty nếu chưa cấu hình."""
        raise NotImplementedError

    @abc.abstractmethod
    def _call(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 4096,
    ) -> Optional[str]:
        """
        Thực hiện 1 HTTP call (không retry).

        Return: text response từ model (chưa parse JSON).
        Raise RetryableError cho: 429, 503, timeout, connection reset.
        Return None cho: lỗi không thể retry (auth, bad request, parse error).
        """
        raise NotImplementedError

    # ── Public API, dùng bởi caller ─────────────────────────────────────────

    def is_available(self) -> bool:
        """Provider sẵn sàng khi có API key."""
        key = self._api_key()
        return bool(key and key.strip())

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 4096,
        retries: int = 2,
    ) -> Optional[str]:
        """
        Gọi LLM với exponential backoff + jitter.

        wait = min(30, 2^attempt + random(0, 1)) giây.
        Ví dụ: attempt 0 → ~1.5s, attempt 1 → ~2.5s, attempt 2 → ~4.5s.

        Return text response hoặc None nếu thất bại sau mọi lần retry.
        """
        if not self.is_available():
            logger.debug("Provider %s không khả dụng (missing API key)", self.name)
            return None

        for attempt in range(retries + 1):
            t0 = time.time()
            try:
                result = self._call(
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                latency_ms = int((time.time() - t0) * 1000)
                if result:
                    logger.info(
                        "LLM call provider=%s model=%s status=ok latency_ms=%d",
                        self.name, self.model, latency_ms,
                    )
                    return result
                # _call trả None = lỗi không retry được (auth, parse, safety)
                logger.warning(
                    "LLM call provider=%s model=%s status=fail_nonretryable latency_ms=%d",
                    self.name, self.model, latency_ms,
                )
                return None

            except RetryableError as e:
                latency_ms = int((time.time() - t0) * 1000)
                if attempt < retries:
                    # Dùng cấu hình từ global settings
                    wait = min(30.0, (LLM_RETRY_WAIT_BASE * (2 ** attempt)) + random.random())
                    logger.warning(
                        "LLM call provider=%s model=%s status=retry_%s "
                        "attempt=%d/%d wait=%.2fs latency_ms=%d",
                        self.name, self.model, e.status,
                        attempt + 1, retries, wait, latency_ms,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "LLM call provider=%s model=%s status=fail_%s "
                        "attempt=%d/%d latency_ms=%d err=%s",
                        self.name, self.model, e.status,
                        attempt + 1, retries, latency_ms, e,
                    )
                    return None

            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                logger.error(
                    "LLM call provider=%s model=%s status=error latency_ms=%d err=%s",
                    self.name, self.model, latency_ms, e,
                )
                return None

        return None
