"""
LLM Providers for N5 activity generation.

Kiến trúc:
  - base.LLMProvider: abstract class định nghĩa interface chung + retry/backoff
  - groq_provider.GroqProvider, gemini_provider.GeminiProvider: concrete impls
  - registry.get_provider / get_fallback_chain: factory + failover

Cách dùng:
  from .providers import get_fallback_chain
  chain = get_fallback_chain()             # theo LLM_PROVIDER env var
  for provider in chain:
      text = provider.generate(prompt)
      if text:
          break
"""

from .base import LLMProvider, RetryableError
from .groq_provider import GroqProvider
from .gemini_provider import GeminiProvider
from .registry import get_provider, get_fallback_chain, available_providers

__all__ = [
    "LLMProvider",
    "RetryableError",
    "GroqProvider",
    "GeminiProvider",
    "get_provider",
    "get_fallback_chain",
    "available_providers",
]
