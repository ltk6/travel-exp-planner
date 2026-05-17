"""
registry.py — Factory cho LLM providers.

Đọc LLM_CHAIN từ config (chuỗi ngăn cách bởi dấu phẩy).
Sử dụng duy nhất Groq models.

Cách dùng:
  chain = get_llm_chain()
  for provider in chain:
      text = provider.generate(prompt)
      if text:
          return text
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Type

from .base import LLMProvider
from .groq_provider import GroqProvider

from config import setup_logging, GROQ_MODELS, LLM_CHAIN
logger = setup_logging("N5.provider.registry")

# Registry tên → class
_PROVIDERS: Dict[str, Type[LLMProvider]] = {
    "groq":   GroqProvider,
}

def _instance(name: str) -> Optional[LLMProvider]:
    """Tạo 1 instance provider theo tên. Hỗ trợ alias đặc biệt của Groq."""
    name = name.strip().lower()
    
    # Kiểm tra alias đặc biệt trước
    if name in GROQ_MODELS:
        return GroqProvider(model=GROQ_MODELS[name])

    cls = _PROVIDERS.get(name)
    if cls is None:
        logger.warning("Unknown provider '%s', skipping", name)
        return None
    return cls()


def get_provider(name: Optional[str] = None) -> Optional[LLMProvider]:
    """
    Lấy 1 provider theo tên. 
    """
    if name:
        return _instance(name)
    
    # Nếu không truyền tên, lấy provider đầu tiên trong LLM_CHAIN
    chain_names = [n.strip() for n in LLM_CHAIN.split(",") if n.strip()]
    if chain_names:
        return _instance(chain_names[0])
    
    return _instance("groq")


def get_llm_chain(chain_str: Optional[str] = None) -> List[LLMProvider]:
    """
    Xây dựng chain từ LLM_CHAIN, chỉ giữ lại các provider có API key.

    Args:
      chain_str — chuỗi tên model ngăn cách dấu phẩy. Default = config.LLM_CHAIN.

    Return danh sách đã lọc; có thể rỗng nếu không provider nào có key.
    """
    raw_str = chain_str if chain_str is not None else LLM_CHAIN
    names = [n.strip() for n in raw_str.split(",") if n.strip()]

    # Dedupe giữ thứ tự
    seen = set()
    ordered = []
    for n in names:
        key = n.lower()
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
        logger.error("Không có provider nào khả dụng — kiểm tra GROQ_API_KEY")

    return chain


def available_providers() -> List[str]:
    """Trả về tên các provider đã đăng ký."""
    return list(_PROVIDERS.keys()) + list(GROQ_MODELS.keys())
