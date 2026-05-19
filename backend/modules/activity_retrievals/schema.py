"""
Unified activity schema cho N5 + N9-N14.

Cung cấp:
- ALLOWED_* enums
- haversine_m(): tính khoảng cách (mét) giữa hai điểm geo
- make_activity_id(): sinh ID ổn định
- build_activity(): factory tạo dict theo schema
- validate(): kiểm tra dict tuân thủ schema (raise ValueError nếu sai)
- strip_raw(): bỏ provenance.raw để giảm size khi persist
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# =============================================================================
# ENUMS
# =============================================================================

ALLOWED_SOURCES = {
    "osm", "goong", "foursquare", "overture", "wikidata", "geoapify", "llm",
}

ALLOWED_ACTIVITY_TYPES = {
    "adventure", "relaxation", "food", "culture",
    "nightlife", "nature", "shopping",
}

ALLOWED_INDOOR_OUTDOOR = {"indoor", "outdoor", "mixed"}

ALLOWED_TIME_OF_DAY = {"morning", "afternoon", "night", "anytime"}


# =============================================================================
# GEO HELPERS
# =============================================================================

_EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Khoảng cách Haversine giữa hai (lat, lng), đơn vị mét."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# =============================================================================
# ID
# =============================================================================

def make_activity_id(source: str, location_id: str, key: Optional[str]) -> str:
    """
    Sinh activity_id: {source}_{location_id}_{hash6}.

    `key` ưu tiên là raw_source_id; nếu không có thì truyền name làm fallback.
    Hash 6 ký tự md5 đủ unique trong phạm vi 1 location/source (< 100k items).
    """
    seed = key if key else "anonymous"
    digest = hashlib.md5(f"{source}|{location_id}|{seed}".encode("utf-8")).hexdigest()[:6]
    return f"{source}_{location_id}_{digest}"


# =============================================================================
# FACTORY
# =============================================================================

def build_activity(
    *,
    source: str,
    location_id: str,
    raw_source_id: Optional[str],
    name: Optional[str],
    id_seed: Optional[str] = None,
    description: Optional[str] = None,
    activity_type: Optional[str] = None,
    activity_subtype: Optional[str] = None,
    categories_raw: Optional[List[str]] = None,
    estimated_duration: Optional[float] = None,
    price_level: Optional[float] = None,
    indoor_outdoor: Optional[str] = None,
    weather_dependent: Optional[bool] = None,
    time_of_day_suitable: Optional[str] = None,
    coordinates: Optional[Dict[str, float]] = None,
    address: Optional[Dict[str, Any]] = None,
    rating: Optional[float] = None,
    popularity: Optional[float] = None,
    image_url: Optional[str] = None,
    website: Optional[str] = None,
    opening_hours: Optional[str] = None,
    phone: Optional[str] = None,
    source_url: Optional[str] = None,
    raw: Any = None,
    anchor_lat: Optional[float] = None,
    anchor_lng: Optional[float] = None,
    retrieved_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tạo dict tuân thủ unified schema.

    - Tự sinh `activity_id` từ source + location_id + (id_seed | raw_source_id | name).
      Dùng `id_seed` khi caller có một key unique riêng (ví dụ LLM normalize dùng
      legacy activity_id của n5 để bảo toàn tính unique sau khi dedup).
    - Tự tính `distance_from_anchor_m` nếu có coordinates + anchor.
    - Default `retrieved_at` = now UTC ISO.

    Raises ValueError nếu thiếu các field bắt buộc để định danh activity.
    """
    if not source or source not in ALLOWED_SOURCES:
        raise ValueError(f"build_activity: source must be one of {ALLOWED_SOURCES}, got {source!r}")
    if not location_id or not isinstance(location_id, str):
        raise ValueError(f"build_activity: location_id required, got {location_id!r}")
    if not (id_seed or raw_source_id or name):
        raise ValueError("build_activity: at least one of id_seed/raw_source_id/name required for stable activity_id")

    distance = None
    if coordinates and anchor_lat is not None and anchor_lng is not None:
        try:
            distance = round(
                haversine_m(coordinates["lat"], coordinates["lng"], anchor_lat, anchor_lng),
                1,
            )
        except (KeyError, TypeError):
            distance = None

    if retrieved_at is None:
        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    address_block = _normalize_address(address)

    return {
        "activity_id": make_activity_id(source, location_id, id_seed or raw_source_id or name),
        "location_id": location_id,
        "source": source,
        "retrieved_at": retrieved_at,
        "metadata": {
            "name": name,
            "description": description,
            "activity_type": activity_type,
            "activity_subtype": activity_subtype,
            "categories_raw": categories_raw or [],
            "estimated_duration": estimated_duration,
            "price_level": price_level,
            "indoor_outdoor": indoor_outdoor,
            "weather_dependent": weather_dependent,
            "time_of_day_suitable": time_of_day_suitable,
        },
        "place": {
            "coordinates": coordinates,
            "distance_from_anchor_m": distance,
            "address": address_block,
        },
        "signals": {
            "rating": rating,
            "popularity": popularity,
            "image_url": image_url,
            "website": website,
            "opening_hours": opening_hours,
            "phone": phone,
        },
        "provenance": {
            "raw_source_id": raw_source_id,
            "source_url": source_url,
            "raw": raw,
        },
    }


def _normalize_address(addr: Optional[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """Bảo đảm address block có đủ 5 key, mọi value đều string hoặc None."""
    addr = addr or {}
    return {
        "country":   addr.get("country"),
        "region":    addr.get("region"),
        "city":      addr.get("city"),
        "street":    addr.get("street"),
        "formatted": addr.get("formatted"),
    }


# =============================================================================
# VALIDATION
# =============================================================================

def validate(activity: Dict[str, Any]) -> None:
    """
    Kiểm tra `activity` tuân thủ schema. Raise ValueError nếu sai.
    """
    _require_keys(activity, {"activity_id", "location_id", "source", "retrieved_at",
                             "metadata", "place", "signals", "provenance"}, path="$")

    src = activity["source"]
    if src not in ALLOWED_SOURCES:
        raise ValueError(f"$.source: '{src}' not in {ALLOWED_SOURCES}")

    if not isinstance(activity["activity_id"], str) or not activity["activity_id"]:
        raise ValueError("$.activity_id: must be non-empty string")
    if not activity["activity_id"].startswith(f"{src}_"):
        raise ValueError(f"$.activity_id: must start with '{src}_'")

    meta = activity["metadata"]
    _require_keys(meta, {"name", "description", "activity_type", "activity_subtype",
                         "categories_raw", "estimated_duration", "price_level",
                         "indoor_outdoor", "weather_dependent", "time_of_day_suitable"},
                  path="$.metadata")

    if meta["activity_type"] is not None and meta["activity_type"] not in ALLOWED_ACTIVITY_TYPES:
        raise ValueError(f"$.metadata.activity_type: '{meta['activity_type']}' not in {ALLOWED_ACTIVITY_TYPES}")
    if meta["indoor_outdoor"] is not None and meta["indoor_outdoor"] not in ALLOWED_INDOOR_OUTDOOR:
        raise ValueError(f"$.metadata.indoor_outdoor: '{meta['indoor_outdoor']}' not in {ALLOWED_INDOOR_OUTDOOR}")
    if meta["time_of_day_suitable"] is not None and meta["time_of_day_suitable"] not in ALLOWED_TIME_OF_DAY:
        raise ValueError(f"$.metadata.time_of_day_suitable: '{meta['time_of_day_suitable']}' not in {ALLOWED_TIME_OF_DAY}")
    if not isinstance(meta["categories_raw"], list):
        raise ValueError("$.metadata.categories_raw: must be list")
    for i, c in enumerate(meta["categories_raw"]):
        if not isinstance(c, str):
            raise ValueError(f"$.metadata.categories_raw[{i}]: must be string, got {type(c).__name__}")

    # Strict-type cho các field N6 đọc → tránh crash khi cast float() / so sánh.
    _check_number_or_none(meta["estimated_duration"], "$.metadata.estimated_duration")
    _check_number_or_none(meta["price_level"], "$.metadata.price_level")
    if meta["weather_dependent"] is not None and not isinstance(meta["weather_dependent"], bool):
        raise ValueError(f"$.metadata.weather_dependent: must be bool or null, got {type(meta['weather_dependent']).__name__}")

    place = activity["place"]
    _require_keys(place, {"coordinates", "distance_from_anchor_m", "address"}, path="$.place")
    _check_number_or_none(place["distance_from_anchor_m"], "$.place.distance_from_anchor_m")
    if place["coordinates"] is not None:
        coords = place["coordinates"]
        if not isinstance(coords, dict) or "lat" not in coords or "lng" not in coords:
            raise ValueError("$.place.coordinates: must be {lat, lng} or null")
        _check_number_or_none(coords["lat"], "$.place.coordinates.lat", allow_none=False)
        _check_number_or_none(coords["lng"], "$.place.coordinates.lng", allow_none=False)
        if not (-90 <= coords["lat"] <= 90):
            raise ValueError(f"$.place.coordinates.lat: out of range ({coords['lat']})")
        if not (-180 <= coords["lng"] <= 180):
            raise ValueError(f"$.place.coordinates.lng: out of range ({coords['lng']})")

    _require_keys(place["address"], {"country", "region", "city", "street", "formatted"}, path="$.place.address")

    _require_keys(activity["signals"],
                  {"rating", "popularity", "image_url", "website", "opening_hours", "phone"},
                  path="$.signals")

    _require_keys(activity["provenance"], {"raw_source_id", "source_url", "raw"}, path="$.provenance")


def _check_number_or_none(v: Any, path: str, allow_none: bool = True) -> None:
    """Số (int hoặc float, NOT bool) hoặc None. Bool bị loại vì là subclass của int."""
    if v is None:
        if allow_none:
            return
        raise ValueError(f"{path}: must be number, got null")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{path}: must be number{' or null' if allow_none else ''}, got {type(v).__name__}")


def _require_keys(d: Any, required: set, path: str) -> None:
    if not isinstance(d, dict):
        raise ValueError(f"{path}: must be dict, got {type(d).__name__}")
    missing = required - set(d.keys())
    if missing:
        raise ValueError(f"{path}: missing keys {sorted(missing)}")


# =============================================================================
# UTIL
# =============================================================================

def strip_raw(activity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trả về copy của activity với `provenance.raw = None` (giảm size khi persist).

    ⚠️  SHALLOW COPY: chỉ outer dict + `provenance` được tạo mới. Các block
    `metadata`, `place`, `signals` vẫn share reference với `activity` gốc.
    Mutate `out["metadata"][...]` → mutate luôn `activity["metadata"][...]`.

    Dùng cho use case "strip rồi serialize ngay" (json.dumps/persist DB).
    Nếu cần copy độc lập hoàn toàn, dùng `copy.deepcopy()` ở caller.
    """
    out = {**activity, "provenance": {**activity["provenance"], "raw": None}}
    return out


__all__ = [
    "ALLOWED_SOURCES",
    "ALLOWED_ACTIVITY_TYPES",
    "ALLOWED_INDOOR_OUTDOOR",
    "ALLOWED_TIME_OF_DAY",
    "haversine_m",
    "make_activity_id",
    "build_activity",
    "validate",
    "strip_raw",
]
