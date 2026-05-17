"""
N12 Overture Maps normalizer.

Raw shape (per feature):
    {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": {
            "id": str,
            "names": {"primary": str, "common": ..., "rules": ...},
            "categories": {"primary": str, "alternate": [str, ...]},
            "addresses": [{
                "freeform": str, "locality": str, "postcode": str,
                "region": str, "country": str
            }],
            "phones": [str], "websites": [str], "socials": [str], "emails": [str],
            "brand": {...},
            "confidence": float,                # [0,1]
            "sources": [{"dataset": "meta"|"osm"|..., "record_id": str, ...}]
        }
    }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schema import build_activity


# Overture primary category → activity_type
_OVERTURE_CATEGORY_MAP = {
    # food
    "restaurant":          "food",
    "fast_food_restaurant":"food",
    "cafe":                "food",
    "coffee_shop":         "food",
    "bakery":              "food",
    "food_and_beverage":   "food",
    # relaxation
    "hotel":      "relaxation",
    "hostel":     "relaxation",
    "motel":      "relaxation",
    "lodging":    "relaxation",
    "spa":        "relaxation",
    "resort":     "relaxation",
    # nightlife
    "bar":       "nightlife",
    "pub":       "nightlife",
    "nightclub": "nightlife",
    # culture
    "museum":          "culture",
    "art_gallery":     "culture",
    "tourist_attraction":"culture",
    "historical_landmark":"culture",
    "place_of_worship":"culture",
    "temple":          "culture",
    # shopping
    "shopping":   "shopping",
    "supermarket":"shopping",
    "store":      "shopping",
    "market":     "shopping",
    # nature
    "park":            "nature",
    "garden":          "nature",
    "natural_feature": "nature",
    "beach":           "nature",
    "campground":      "nature",
    # adventure
    "gym":            "adventure",
    "sports":         "adventure",
    "amusement_park": "adventure",
}


def _map_activity_type(primary: Optional[str]) -> Optional[str]:
    if not primary:
        return None
    if primary in _OVERTURE_CATEGORY_MAP:
        return _OVERTURE_CATEGORY_MAP[primary]
    # Fallback: keyword match đơn giản
    for key, atype in _OVERTURE_CATEGORY_MAP.items():
        if key in primary:
            return atype
    return None


from .shared import indoor_outdoor_by_type as _indoor_outdoor


def _extract_coords(geom: Dict[str, Any]) -> Optional[Dict[str, float]]:
    if not geom or geom.get("type") != "Point":
        return None
    c = geom.get("coordinates") or []
    if len(c) < 2:
        return None
    # GeoJSON: [lng, lat]
    return {"lat": float(c[1]), "lng": float(c[0])}


def _extract_address(addresses: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not addresses:
        return {"country": None, "region": None, "city": None, "street": None, "formatted": None}
    a = addresses[0]
    return {
        "country":   a.get("country"),
        "region":    a.get("region"),
        "city":      a.get("locality"),
        "street":    None,
        "formatted": a.get("freeform"),
    }


def normalize(raw_item: Dict[str, Any], ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    props = raw_item.get("properties") or {}
    names = props.get("names") or {}
    name = names.get("primary") or names.get("common")
    if not name:
        return None

    place_id = props.get("id")
    categories = props.get("categories") or {}
    primary_cat = categories.get("primary")
    alt_cats = categories.get("alternate") or []
    cats_raw = [c for c in [primary_cat, *alt_cats] if c]

    activity_type = _map_activity_type(primary_cat)

    phones = props.get("phones") or []
    websites = props.get("websites") or []
    # `properties.confidence` là data-quality signal (record này đáng tin không),
    # KHÔNG phải popularity → không map vào signals.popularity. Lưu trong raw.

    return build_activity(
        source="overture",
        location_id=ctx["location_id"],
        raw_source_id=place_id,
        name=name,
        description=None,
        activity_type=activity_type,
        activity_subtype=primary_cat,
        categories_raw=cats_raw,
        indoor_outdoor=_indoor_outdoor(activity_type),
        coordinates=_extract_coords(raw_item.get("geometry") or {}),
        address=_extract_address(props.get("addresses") or []),
        website=websites[0] if websites else None,
        phone=phones[0] if phones else None,
        source_url=None,
        raw=raw_item,
        anchor_lat=ctx.get("anchor_lat"),
        anchor_lng=ctx.get("anchor_lng"),
    )


from .shared import make_normalize_all
normalize_all = make_normalize_all(normalize)
