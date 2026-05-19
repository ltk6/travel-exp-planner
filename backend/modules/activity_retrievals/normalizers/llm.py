"""
N5 LLM normalizer (plan B — kế thừa anchor location).

Raw shape: legacy dict do `n5_activity_generator._build_activity_output()` sinh ra:
    {
        "activity_id": str,
        "location_id": str,
        "metadata": {
            "name": str, "description": str,
            "activity_type": str, "activity_subtype": str | None,
            "estimated_duration": float, "price_level": float,
            "indoor_outdoor": str, "weather_dependent": bool,
            "time_of_day_suitable": str
        }
    }

Quy tắc plan B:
- LLM không có coordinates → kế thừa anchor (ctx.anchor_lat, ctx.anchor_lng).
- `distance_from_anchor_m` = 0 (build_activity tự tính).
- address kế thừa từ `ctx.anchor_address` nếu có.
- `provenance.raw_source_id` = None.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schema import build_activity


def normalize(raw_item: Dict[str, Any], ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    meta = raw_item.get("metadata") or {}
    name = meta.get("name")
    if not name:
        return None

    anchor_lat = ctx.get("anchor_lat")
    anchor_lng = ctx.get("anchor_lng")
    coords = None
    if anchor_lat is not None and anchor_lng is not None:
        coords = {"lat": float(anchor_lat), "lng": float(anchor_lng)}

    address = ctx.get("anchor_address") or {
        "country": None, "region": None, "city": None,
        "street": None, "formatted": None,
    }

    # Dùng activity_id gốc của N5 làm id_seed → activity_id unified vẫn unique
    # ngay cả khi 2 LLM activities có cùng name nhưng khác subtype.
    legacy_id = raw_item.get("activity_id")

    return build_activity(
        source="llm",
        location_id=ctx["location_id"],
        raw_source_id=None,
        id_seed=legacy_id,
        name=name,
        description=meta.get("description"),
        activity_type=meta.get("activity_type"),
        activity_subtype=meta.get("activity_subtype"),
        categories_raw=[],
        estimated_duration=_safe_float(meta.get("estimated_duration")),
        price_level=_safe_float(meta.get("price_level")),
        indoor_outdoor=meta.get("indoor_outdoor"),
        weather_dependent=_safe_bool(meta.get("weather_dependent")),
        time_of_day_suitable=meta.get("time_of_day_suitable"),
        coordinates=coords,
        address=address,
        source_url=None,
        raw={"legacy_activity_id": legacy_id, "metadata": meta},
        anchor_lat=anchor_lat,
        anchor_lng=anchor_lng,
    )


from .shared import make_normalize_all
normalize_all = make_normalize_all(normalize)


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    return bool(v)
