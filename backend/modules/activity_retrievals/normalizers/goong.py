"""
N10 Goong (Place Autocomplete) normalizer.

Raw shape (per prediction):
    {
        "place_id": str,
        "description": str,                     # full address-like string
        "structured_formatting": {
            "main_text": str,
            "secondary_text": str
        },
        "compound": {
            "district": str,
            "commune":  str,
            "province": str
        },
        "plus_code": {"compound_code": ..., "global_code": ...},
        "terms": [...]
    }

LƯU Ý:
- Goong Autocomplete KHÔNG trả coordinates. → `coordinates = None`.
- Để enrich coords cần gọi thêm Place Detail API (chưa làm trong stage này).
- activity_type không suy ra được từ payload → null (downstream enrich).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schema import build_activity


def _extract_name(item: Dict[str, Any]) -> Optional[str]:
    sf = item.get("structured_formatting") or {}
    return sf.get("main_text") or item.get("description")


def _extract_address(item: Dict[str, Any]) -> Dict[str, Any]:
    compound = item.get("compound") or {}
    sf = item.get("structured_formatting") or {}
    return {
        "country":   "VN",  # Goong VN-only
        "region":    compound.get("province"),
        "city":      compound.get("district"),
        "street":    None,
        "formatted": sf.get("secondary_text") or item.get("description"),
    }


def normalize(raw_item: Dict[str, Any], ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = _extract_name(raw_item)
    if not name:
        return None

    place_id = raw_item.get("place_id")

    return build_activity(
        source="goong",
        location_id=ctx["location_id"],
        raw_source_id=place_id,
        name=name,
        description=raw_item.get("description"),
        activity_type=None,
        activity_subtype=None,
        categories_raw=[],
        coordinates=None,   # Autocomplete không có coords
        address=_extract_address(raw_item),
        source_url=None,
        raw=raw_item,
        anchor_lat=ctx.get("anchor_lat"),
        anchor_lng=ctx.get("anchor_lng"),
    )


from .shared import make_normalize_all
normalize_all = make_normalize_all(normalize)
