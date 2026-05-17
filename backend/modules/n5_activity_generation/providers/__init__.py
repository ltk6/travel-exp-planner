"""
LLM Providers for N5 activity generation.

Kiến trúc:
  - base.LLMProvider: abstract class định nghĩa interface chung + retry/backoff
  - groq_provider.GroqProvider: concrete impls (Groq only)
  - registry.get_provider / get_llm_chain: factory + failover

Cách dùng:
  from .providers import get_llm_chain
  chain = get_llm_chain()             # theo LLM_CHAIN config
  for provider in chain:
      text = provider.generate(prompt)
      if text:
          break
"""

from .base import LLMProvider, RetryableError
from .groq_provider import GroqProvider
from .registry import get_provider, get_llm_chain, available_providers

__all__ = [
    "LLMProvider",
    "RetryableError",
    "GroqProvider",
    "get_provider",
    "get_llm_chain",
    "available_providers",
]
