"""
cache.py — TTL cache cho LLM activity generation.

Mục đích:
  - Giảm số lần gọi LLM khi cùng (location, user preferences) lặp lại
  - Giảm nguy cơ 429 rate limit, giảm latency rõ rệt cho hit
  - Không cần external store (Redis) — in-memory đủ cho đồ án

Key components:
  - provider config (LLM_PROVIDER + LLM_FALLBACK)
  - location identity (name + sorted tags)
  - user preferences (sorted tags + trimmed text)
  - constraints (budget, max_time, num_activities, schema_v2)

TTL mặc định 1 giờ, LRU cap 500 entry. Thống kê hit/miss có sẵn cho log.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Dict, List, Optional

from cachetools import TTLCache

logger = logging.getLogger(__name__)

CACHE_MAXSIZE = 500
CACHE_TTL_SECONDS = 3600  # 1 giờ

_cache: TTLCache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=CACHE_TTL_SECONDS)

# Thống kê — dùng cho benchmark / trace
_stats = {"hits": 0, "misses": 0, "stores": 0}


def _provider_key(override: Optional[str] = None) -> str:
    """
    Cache key cần bao gồm cấu hình provider:
    khi user đổi LLM_PROVIDER, phải cache miss chứ không lấy kết quả của provider cũ.

    Nếu caller truyền `override` (UI chọn provider cụ thể), key dùng override
    thay vì env — để chọn "gemini" và "groq" có cache riêng.
    """
    if override:
        return f"override:{override.strip().lower()}"
    primary  = os.getenv("LLM_PROVIDER", "gemini")
    fallback = os.getenv("LLM_FALLBACK", "")
    return f"{primary}|{fallback}"


def make_key(
    location_name: str,
    location_tags: List[str],
    user_tags: List[str],
    user_text: str,
    num_activities: int,
    schema_v2: bool,
    provider_override: Optional[str] = None,
) -> str:
    """Tạo cache key ổn định theo nội dung — deterministic trên cùng input."""
    payload = {
        "provider":      _provider_key(provider_override),
        "location":      location_name.strip().lower(),
        "location_tags": sorted(t.lower().strip() for t in (location_tags or [])),
        "user_tags":     sorted(t.lower().strip() for t in (user_tags or [])),
        "user_text":     (user_text or "").strip().lower(),
        "num":           int(num_activities or 0),
        "schema_v2":     bool(schema_v2),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def get(key: str) -> Optional[List[Dict]]:
    """Trả về kết quả cached hoặc None. Ghi stats."""
    value = _cache.get(key)
    if value is not None:
        _stats["hits"] += 1
        logger.info("LLM cache HIT key=%s... hits=%d misses=%d",
                    key[:12], _stats["hits"], _stats["misses"])
        return value
    _stats["misses"] += 1
    return None


def put(key: str, value: List[Dict]) -> None:
    """Lưu vào cache. Không lưu nếu value rỗng (tránh cache failure)."""
    if not value:
        return
    _cache[key] = value
    _stats["stores"] += 1
    logger.info("LLM cache STORE key=%s... size=%d", key[:12], len(_cache))


def stats() -> Dict:
    """Snapshot stats hiện tại — dùng để log / hiển thị trace."""
    total = _stats["hits"] + _stats["misses"]
    hit_rate = (_stats["hits"] / total) if total else 0.0
    return {
        **_stats,
        "size": len(_cache),
        "maxsize": CACHE_MAXSIZE,
        "hit_rate": round(hit_rate, 3),
    }


def clear() -> None:
    """Xóa toàn bộ cache — dùng trong test."""
    _cache.clear()
    _stats["hits"] = 0
    _stats["misses"] = 0
    _stats["stores"] = 0
