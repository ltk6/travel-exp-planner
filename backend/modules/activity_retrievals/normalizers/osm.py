"""
N9 OSM (Overpass) normalizer.

Raw shape (per element):
    {
        "type": "node" | "way",
        "id":   int,
        "lat":  float, "lon": float,            # node
        "center": {"lat": ..., "lon": ...},     # way (sau out center)
        "tags": {
            "name": str,
            "tourism": str | None,
            "amenity": str | None,
            "historic": str | None,
            "leisure": str | None,
            "shop":    str | None,
            ...
        }
    }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schema import build_activity


# Mapping OSM tag → activity_type (7-class taxonomy)
_TOURISM_MAP = {
    "museum":      "culture",
    "gallery":     "culture",
    "artwork":     "culture",
    "attraction":  "culture",
    "viewpoint":   "nature",
    "theme_park":  "adventure",
    "zoo":         "nature",
    "aquarium":    "nature",
    "hotel":       "relaxation",
    "hostel":      "relaxation",
    "guest_house": "relaxation",
    "motel":       "relaxation",
    "resort":      "relaxation",
}

_AMENITY_MAP = {
    "restaurant":  "food",
    "cafe":        "food",
    "fast_food":   "food",
    "food_court":  "food",
    "bar":         "nightlife",
    "pub":         "nightlife",
    "nightclub":   "nightlife",
}

_LEISURE_MAP = {
    "park":          "nature",
    "garden":        "nature",
    "nature_reserve":"nature",
    "beach_resort":  "relaxation",
    "spa":           "relaxation",
    "sports_centre": "adventure",
    "fitness_centre":"adventure",
}


def _map_activity_type(tags: Dict[str, Any]) -> Optional[str]:
    if "historic" in tags:
        return "culture"
    t = tags.get("tourism")
    if t and t in _TOURISM_MAP:
        return _TOURISM_MAP[t]
    a = tags.get("amenity")
    if a and a in _AMENITY_MAP:
        return _AMENITY_MAP[a]
    l = tags.get("leisure")
    if l and l in _LEISURE_MAP:
        return _LEISURE_MAP[l]
    if "shop" in tags:
        return "shopping"
    if t:  # tourism nhưng không khớp map → coi là culture (điểm thăm thú)
        return "culture"
    return None


def _indoor_outdoor(tags: Dict[str, Any]) -> Optional[str]:
    if tags.get("tourism") in {"museum", "gallery", "aquarium"}:
        return "indoor"
    if tags.get("historic"):
        return "outdoor"
    if tags.get("leisure") in {"park", "garden", "nature_reserve"}:
        return "outdoor"
    if tags.get("amenity") in {"restaurant", "cafe", "bar", "pub", "nightclub"}:
        return "indoor"
    if tags.get("shop"):
        return "indoor"
    return None


def _categories_raw(tags: Dict[str, Any]) -> List[str]:
    """Flatten các tag phân loại thành list 'key=value'."""
    keys = ("tourism", "amenity", "historic", "leisure", "shop")
    return [f"{k}={tags[k]}" for k in keys if k in tags]


def _extract_coords(item: Dict[str, Any]) -> Optional[Dict[str, float]]:
    # node: lat/lon ở root; way: trong center
    if "lat" in item and "lon" in item:
        return {"lat": float(item["lat"]), "lng": float(item["lon"])}
    center = item.get("center") or {}
    if "lat" in center and "lon" in center:
        return {"lat": float(center["lat"]), "lng": float(center["lon"])}
    return None


def _extract_address(tags: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "country":   tags.get("addr:country"),
        "region":    tags.get("addr:state") or tags.get("addr:province"),
        "city":      tags.get("addr:city"),
        "street":    tags.get("addr:street"),
        "formatted": None,
    }


def normalize(raw_item: Dict[str, Any], ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tags = raw_item.get("tags") or {}
    name = tags.get("name:vi") or tags.get("name") or tags.get("name:en")
    if not name:
        return None

    raw_id = f"{raw_item.get('type', 'node')}/{raw_item.get('id')}"

    return build_activity(
        source="osm",
        location_id=ctx["location_id"],
        raw_source_id=raw_id,
        name=name,
        description=None,
        activity_type=_map_activity_type(tags),
        activity_subtype=tags.get("tourism") or tags.get("amenity") or tags.get("historic")
                         or tags.get("leisure") or tags.get("shop"),
        categories_raw=_categories_raw(tags),
        indoor_outdoor=_indoor_outdoor(tags),
        coordinates=_extract_coords(raw_item),
        address=_extract_address(tags),
        website=tags.get("website") or tags.get("contact:website"),
        opening_hours=tags.get("opening_hours"),
        phone=tags.get("phone") or tags.get("contact:phone"),
        source_url=f"https://www.openstreetmap.org/{raw_id}",
        raw=raw_item,
        anchor_lat=ctx.get("anchor_lat"),
        anchor_lng=ctx.get("anchor_lng"),
    )


from .shared import make_normalize_all
normalize_all = make_normalize_all(normalize)
