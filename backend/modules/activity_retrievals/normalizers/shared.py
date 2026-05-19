"""
Helper dùng chung giữa các normalizer (osm, goong, foursquare, overture, wikidata, geoapify, llm).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


def make_normalize_all(
    normalize_fn: Callable[[Dict[str, Any], Dict[str, Any]], Optional[Dict[str, Any]]],
) -> Callable[[List[Dict[str, Any]], Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Factory: build a `normalize_all(raw_items, ctx)` từ một `normalize(raw_item, ctx)`.

    `normalize_fn` trả None → item bị skip. Mặc định cho phần lớn normalizer;
    wikidata cần dedupe theo Q-ID nên tự define.
    """
    def normalize_all(raw_items: List[Dict[str, Any]], ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for it in raw_items:
            norm = normalize_fn(it, ctx)
            if norm is not None:
                out.append(norm)
        return out
    return normalize_all


# Suy luận indoor/outdoor từ unified activity_type. Dùng cho các source không
# có signal raw (foursquare, overture) → fallback theo type.
_OUTDOOR_TYPES = {"nature"}
_INDOOR_TYPES  = {"food", "shopping", "culture", "nightlife", "relaxation"}


def indoor_outdoor_by_type(activity_type: Optional[str]) -> Optional[str]:
    """Trả 'outdoor' | 'indoor' | None dựa vào activity_type (sau khi đã map sang unified)."""
    if activity_type in _OUTDOOR_TYPES:
        return "outdoor"
    if activity_type in _INDOOR_TYPES:
        return "indoor"
    return None
