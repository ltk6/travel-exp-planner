"""
N14 Geoapify Places normalizer.

Raw shape (per feature):
    {
        "type": "Feature",
        "properties": {
            "name": str,
            "country": str, "country_code": str, "state": str,
            "city": str, "suburb": str, "postcode": str,
            "street": str, "housenumber": str,
            "lat": float, "lon": float,
            "formatted": str,
            "categories": ["catering.restaurant.vietnamese", ...],   # dot-separated path
            "website": str, "opening_hours": str,
            "contact": {"phone": str, "email": str},
            "datasource": {"raw": {...}, "sourcename": "openstreetmap"}
        },
        "geometry": {"type": "Point", "coordinates": [lng, lat]}
    }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schema import build_activity


# Geoapify root category (prefix trước dấu '.') → activity_type
_GEOAPIFY_ROOT_MAP = {
    "catering":      "food",
    "tourism":       "culture",
    "natural":       "nature",
    "leisure":       "nature",
    "entertainment": "nightlife",
    "accommodation": "relaxation",
    "commercial":    "shopping",
    "sport":         "adventure",
    "activity":      "adventure",
}


def _map_activity_type(categories: List[str]) -> Optional[str]:
    if not categories:
        return None
    # Ưu tiên category cụ thể nhất (dài nhất) trước → fallback root
    sorted_cats = sorted(categories, key=len, reverse=True)
    for c in sorted_cats:
        root = c.split(".", 1)[0]
        if root in _GEOAPIFY_ROOT_MAP:
            return _GEOAPIFY_ROOT_MAP[root]
    return None


def _indoor_outdoor(activity_type: Optional[str], categories: List[str]) -> Optional[str]:
    if any(c.startswith("natural") or c.startswith("leisure.park") for c in categories):
        return "outdoor"
    if any(c.startswith("tourism.sights") for c in categories):
        return "outdoor"
    if activity_type in {"food", "shopping", "nightlife", "relaxation"}:
        return "indoor"
    if activity_type == "culture":
        return "mixed"
    return None


def _extract_coords(item: Dict[str, Any]) -> Optional[Dict[str, float]]:
    props = item.get("properties") or {}
    lat = props.get("lat")
    lng = props.get("lon")
    if lat is None or lng is None:
        geom = item.get("geometry") or {}
        c = geom.get("coordinates") or []
        if len(c) >= 2:
            return {"lat": float(c[1]), "lng": float(c[0])}
        return None
    return {"lat": float(lat), "lng": float(lng)}


def _extract_address(props: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "country":   props.get("country_code", "").upper() or props.get("country"),
        "region":    props.get("state"),
        "city":      props.get("city") or props.get("suburb"),
        "street":    props.get("street"),
        "formatted": props.get("formatted"),
    }


def _osm_id_from_datasource(props: Dict[str, Any]) -> Optional[str]:
    ds = props.get("datasource") or {}
    raw = ds.get("raw") or {}
    osm_id = raw.get("osm_id")
    osm_type = raw.get("osm_type")
    if osm_id and osm_type:
        return f"{osm_type}/{osm_id}"
    return str(osm_id) if osm_id else None


def normalize(raw_item: Dict[str, Any], ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    props = raw_item.get("properties") or {}
    name = props.get("name") or props.get("address_line1")
    if not name:
        return None

    categories = props.get("categories") or []
    activity_type = _map_activity_type(categories)
    contact = props.get("contact") or {}

    return build_activity(
        source="geoapify",
        location_id=ctx["location_id"],
        raw_source_id=_osm_id_from_datasource(props) or props.get("place_id"),
        name=name,
        description=None,
        activity_type=activity_type,
        activity_subtype=(categories[-1] if categories else None),
        categories_raw=categories,
        indoor_outdoor=_indoor_outdoor(activity_type, categories),
        coordinates=_extract_coords(raw_item),
        address=_extract_address(props),
        website=props.get("website"),
        opening_hours=props.get("opening_hours"),
        phone=contact.get("phone") or props.get("phone"),
        source_url=None,
        raw=raw_item,
        anchor_lat=ctx.get("anchor_lat"),
        anchor_lng=ctx.get("anchor_lng"),
    )


from .shared import make_normalize_all
normalize_all = make_normalize_all(normalize)
