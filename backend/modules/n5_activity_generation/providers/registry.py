"""
registry.py — Factory cho LLM providers.

Env vars đọc (ưu tiên):
  LLM_PROVIDER   — provider chính ("gemini" | "groq"). Default "gemini".
  LLM_FALLBACK   — chuỗi provider fallback, ngăn cách dấu phẩy.
                   Default "groq" (nếu primary là gemini) hoặc "gemini".

Fallback chain: primary trước, rồi lần lượt các fallback có API key.
Provider không có API key sẽ bị loại khỏi chain (ghi log warning).

Cách dùng:
  chain = get_fallback_chain()
  for provider in chain:
      text = provider.generate(prompt)
      if text:
          return text
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Type

from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider

logger = logging.getLogger(__name__)

# Registry tên → class
_PROVIDERS: Dict[str, Type[LLMProvider]] = {
    "gemini": GeminiProvider,
    "groq":   GroqProvider,
}

DEFAULT_PRIMARY = "gemini"


def _instance(name: str) -> Optional[LLMProvider]:
    """Tạo 1 instance provider theo tên. Return None nếu tên lạ."""
    name = name.strip().lower()
    cls = _PROVIDERS.get(name)
    if cls is None:
        logger.warning("Unknown provider '%s', skipping", name)
        return None
    return cls()


def get_provider(name: Optional[str] = None) -> Optional[LLMProvider]:
    """
    Lấy 1 provider theo tên. Nếu không truyền, đọc env LLM_PROVIDER.
    Không check availability — caller tự gọi .is_available() nếu cần.
    """
    name = name or os.getenv("LLM_PROVIDER", DEFAULT_PRIMARY)
    return _instance(name)


def get_fallback_chain(
    primary: Optional[str] = None,
    fallback: Optional[str] = None,
) -> List[LLMProvider]:
    """
    Xây dựng chain: [primary, *fallbacks], chỉ giữ lại các provider có API key.

    Args:
      primary  — tên provider chính. Default = env LLM_PROVIDER hoặc "gemini".
      fallback — chuỗi tên fallback ngăn cách dấu phẩy. Default = env LLM_FALLBACK.

    Return danh sách đã lọc; có thể rỗng nếu không provider nào có key.
    """
    primary = primary or os.getenv("LLM_PROVIDER", DEFAULT_PRIMARY)
    fallback_str = fallback if fallback is not None else os.getenv("LLM_FALLBACK", "")

    # Default fallback: nếu primary là gemini thì fallback groq, ngược lại
    if not fallback_str:
        fallback_str = "groq" if primary.lower() != "groq" else "gemini"

    names = [primary] + [n for n in fallback_str.split(",") if n.strip()]

    # Dedupe giữ thứ tự
    seen = set()
    ordered = []
    for n in names:
        key = n.strip().lower()
        if key and key not in seen:
            seen.add(key)
            ordered.append(key)

    chain: List[LLMProvider] = []
    for name in ordered:
        provider = _instance(name)
        if provider is None:
            continue
        if not provider.is_available():
            logger.info("Provider '%s' có trong chain nhưng thiếu API key — skip", name)
            continue
        chain.append(provider)

    if not chain:
        logger.error("Không có provider nào khả dụng — kiểm tra GEMINI_API_KEY / GROQ_API_KEY")

    return chain


def available_providers() -> List[str]:
    """Trả về tên các provider đã đăng ký (không kiểm tra API key)."""
    return list(_PROVIDERS.keys())
