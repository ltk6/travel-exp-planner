"""
N11 Foursquare Places v3 normalizer.

Raw shape (per result):
    {
        "fsq_place_id": str,
        "name": str,
        "latitude": float, "longitude": float,
        "distance": int,                        # meters
        "categories": [{"name": str, "short_name": str, ...}],
        "location": {
            "locality": str, "region": str, "country": str,
            "address": str | None, "postcode": str | None,
            "formatted_address": str
        },
        "date_refreshed": "YYYY-MM-DD",
        "link": "/places/<id>"
    }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schema import build_activity


# Foursquare category name (substring match, case-insensitive) → activity_type
_FSQ_CATEGORY_KEYWORDS = [
    # nature
    ("nature preserve", "nature"), ("mountain", "nature"), ("hiking trail", "nature"),
    ("park", "nature"), ("garden", "nature"), ("waterfall", "nature"), ("lake", "nature"),
    ("beach", "nature"), ("forest", "nature"), ("scenic", "nature"), ("viewpoint", "nature"),
    # culture
    ("museum", "culture"), ("temple", "culture"), ("church", "culture"),
    ("monument", "culture"), ("historic", "culture"), ("art gallery", "culture"),
    ("cultural", "culture"), ("heritage", "culture"),
    # food
    ("restaurant", "food"), ("cafe", "food"), ("coffee", "food"), ("bakery", "food"),
    ("food", "food"), ("dessert", "food"), ("breakfast", "food"),
    # nightlife
    ("bar", "nightlife"), ("pub", "nightlife"), ("nightclub", "nightlife"),
    ("lounge", "nightlife"),
    # shopping
    ("mall", "shopping"), ("market", "shopping"), ("shop", "shopping"),
    ("boutique", "shopping"), ("store", "shopping"),
    # relaxation
    ("spa", "relaxation"), ("hotel", "relaxation"), ("resort", "relaxation"),
    ("hostel", "relaxation"), ("homestay", "relaxation"),
    # adventure
    ("adventure", "adventure"), ("climbing", "adventure"), ("rafting", "adventure"),
    ("zipline", "adventure"), ("ski", "adventure"),
]


def _map_activity_type(categories: List[Dict[str, Any]]) -> Optional[str]:
    if not categories:
        return None
    joined = " ".join((c.get("name") or "").lower() for c in categories)
    for keyword, atype in _FSQ_CATEGORY_KEYWORDS:
        if keyword in joined:
            return atype
    return None


from .shared import indoor_outdoor_by_type as _indoor_outdoor


def _extract_address(loc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "country":   loc.get("country"),
        "region":    loc.get("region"),
        "city":      loc.get("locality"),
        "street":    loc.get("address"),
        "formatted": loc.get("formatted_address"),
    }


def _extract_coords(item: Dict[str, Any]) -> Optional[Dict[str, float]]:
    lat = item.get("latitude")
    lng = item.get("longitude")
    if lat is None or lng is None:
        return None
    return {"lat": float(lat), "lng": float(lng)}


def normalize(raw_item: Dict[str, Any], ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = raw_item.get("name")
    if not name:
        return None

    fsq_id = raw_item.get("fsq_place_id")
    cats = raw_item.get("categories") or []
    activity_type = _map_activity_type(cats)
    cats_raw = [c.get("name") for c in cats if c.get("name")]

    # Foursquare đã tính sẵn distance — ưu tiên dùng để khỏi recompute,
    # nhưng schema cần coordinates để haversine vẫn đúng nếu ai đó re-derive.
    coords = _extract_coords(raw_item)

    return build_activity(
        source="foursquare",
        location_id=ctx["location_id"],
        raw_source_id=fsq_id,
        name=name,
        description=None,
        activity_type=activity_type,
        activity_subtype=(cats[0].get("short_name") if cats else None),
        categories_raw=cats_raw,
        indoor_outdoor=_indoor_outdoor(activity_type),
        coordinates=coords,
        address=_extract_address(raw_item.get("location") or {}),
        # Foursquare v3 không trả website của place trong /places/search.
        # Cần gọi /places/{id} riêng để enrich → để null ở stage này.
        source_url=f"https://foursquare.com/v/{fsq_id}" if fsq_id else None,
        raw=raw_item,
        anchor_lat=ctx.get("anchor_lat"),
        anchor_lng=ctx.get("anchor_lng"),
    )


from .shared import make_normalize_all
normalize_all = make_normalize_all(normalize)
