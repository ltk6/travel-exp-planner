# =============================================================================
# n5_activity_generator.py
# =============================================================================
# N5 — Activity Generation Module
#
# Entry point duy nhất: generate_activities(data: dict) -> dict
# Schema I/O theo đúng __init__.py
#
# KIẾN TRÚC:
#   ┌─────────────────────────────────────────────────────────┐
#   │  generate_activities(data)                              │
#   │       │                                                 │
#   │       ▼                                                 │
#   │  _parse_input()  → user, locations, constraints         │
#   │       │                                                 │
#   │       ▼  (per location)                                 │
#   │  _generate_for_location()                               │
#   │       ├── LLM path: generate_from_llm()  ~25 acts       │
#   │       └── Template path: _expand_templates() ~75 acts   │
#   │       │   (combine → 100/location)                      │
#   │       ▼                                                 │
#   │  _build_activity_output()  → schema theo __init__.py    │
#   │       │                                                 │
#   │       ▼                                                 │
#   │  {"activities": [...]}                                  │
#   └─────────────────────────────────────────────────────────┘
#
# SCALABILITY:
#   - TARGET_PER_LOCATION = 100 (configurable)
#   - Template expansion dùng VARIATION_MODIFIERS để biến thể templates
#   - LLM bổ sung ~25 activities với nội dung phong phú hơn
#   - Khi không có LLM: template expansion tự điền đủ 100
#
# OUTPUT: unified activity schema (xem activity_retrievals/SCHEMA.md).
# Generator nội bộ tạo legacy dict {activity_id, location_id, metadata{...}},
# sau đó qua activity_retrievals.normalizers.llm.normalize_all() → unified.
# =============================================================================

import random
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple

from .n5_activity_templates import (
    LOCATION_PROFILES,
    ACTIVITY_TYPE_BANK,
    SIGHTSEEING_BOOST_TAGS,
    VARIATION_MODIFIERS,
)

# Normalizer convert legacy n5 dict → unified schema (xem activity_retrievals/SCHEMA.md).
from ..activity_retrievals.normalizers import llm as _llm_normalizer

try:
    from .n5_llm_generator import generate_from_llm, is_llm_available
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    def is_llm_available(): return False
    def generate_from_llm(*args, **kwargs): return None

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

TARGET_PER_LOCATION = 100   # Mục tiêu số activities mỗi location
LLM_QUOTA           = 25    # LLM sinh tối đa 25/location
TEMPLATE_QUOTA      = TARGET_PER_LOCATION - LLM_QUOTA  # 75 từ template

# Sightseeing priority boost — activity types được ưu tiên
SIGHTSEEING_PRIORITY_TYPES = {"nature", "relaxation"}
SIGHTSEEING_BOOST = 0.15    # Cộng thêm vào sightseeing_priority khi location có tags phù hợp


# =============================================================================
# PUBLIC ENTRY POINT
# =============================================================================

def generate_activities(data: dict) -> dict:
    """
    N5 — Entry point chính.

    Input schema (từ N4):
    {
        "user": {
            "text": str | None,
            "image_description": str | None,
            "tags": list[str] | None
        },
        "locations": [
            {
                "location_id": str,
                "metadata": {
                    "name": str | None,
                    "description": str | None,
                    "tags": list[str] | None
                }
            }
        ],
        "constraints": {
            "budget": float | None,
            "duration": float | None,       # tổng số ngày
            "people": int | None,
            "time_of_day": str | None
        }
    }

    Output schema (sang N6):
    {
        "activities": [
            {
                "activity_id": str,
                "location_id": str,
                "metadata": { ... }         # theo __init__.py
            }
        ]
    }
    """
    user, locations, constraints = _parse_input(data)
    unified_activities: List[Dict] = []

    for loc in locations:
        loc_id   = loc["location_id"]
        loc_name = loc["metadata"].get("name") or ""
        loc_desc = loc["metadata"].get("description") or ""
        loc_tags = loc["metadata"].get("tags") or []

        # Enrich từ LOCATION_PROFILES nếu có
        profile = _get_profile(loc_name, loc_tags, loc_desc)

        legacy_activities = _generate_for_location(
            location_id   = loc_id,
            location_name = loc_name,
            profile       = profile,
            user          = user,
            constraints   = constraints,
        )

        # Convert legacy {activity_id, location_id, metadata{...}} → unified schema
        # (xem backend/modules/activity_retrievals/SCHEMA.md).
        coords = loc["metadata"].get("coordinates")
        ctx = {
            "location_id":    loc_id,
            "anchor_lat":     (coords or {}).get("lat") if coords else None,
            "anchor_lng":     (coords or {}).get("lng") if coords else None,
            "anchor_address": loc["metadata"].get("address"),
        }
        unified = _llm_normalizer.normalize_all(legacy_activities, ctx)

        unified_activities.extend(unified)
        logger.info(
            "Location '%s' (%s): generated %d activities (unified)",
            loc_name, loc_id, len(unified)
        )

    return {"activities": unified_activities}


# =============================================================================
# INPUT PARSING
# =============================================================================

def _parse_input(data: dict) -> Tuple[Dict, List[Dict], Dict]:
    """Validate và extract user, locations, constraints từ input dict."""
    user        = data.get("user", {}) or {}
    locations   = data.get("locations", []) or []
    constraints = data.get("constraints", {}) or {}

    # Normalize user tags
    user_tags = user.get("tags") or []
    if isinstance(user_tags, str):
        user_tags = [t.strip() for t in user_tags.split(",") if t.strip()]
    user["tags"] = [t.lower() for t in user_tags]

    # Normalize constraints với defaults
    constraints = {
        "budget":                float(constraints.get("budget") or 10_000_000),
        "duration":              float(constraints.get("duration") or 3),
        "people":                int(constraints.get("people") or 2),
        "time_of_day":           constraints.get("time_of_day") or "anytime",
        # Derived
        "budget_per_activity":   None,   # tính bên dưới
        "max_time_per_activity": 360,    # phút
    }
    # Budget per activity: tối đa 25% tổng budget
    constraints["budget_per_activity"] = int(constraints["budget"] * 0.25)

    # Normalize locations.
    # `coordinates` và `address` được giữ optional để truyền sang unified schema:
    # nếu N4 cung cấp → llm.normalize fill được `place.coordinates` + distance,
    # nếu không → place.coordinates = null (schema vẫn valid).
    normalized_locs = []
    for loc in locations:
        if not isinstance(loc, dict):
            continue
        loc_id   = str(loc.get("location_id", ""))
        metadata = loc.get("metadata", {}) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        normalized_locs.append({
            "location_id": loc_id,
            "metadata": {
                "name":        metadata.get("name") or loc_id,
                "description": metadata.get("description") or "",
                "tags":        [t.lower() for t in (metadata.get("tags") or [])],
                "coordinates": metadata.get("coordinates"),   # optional {lat, lng}
                "address":     metadata.get("address"),       # optional dict
            }
        })

    return user, normalized_locs, constraints


# =============================================================================
# LOCATION PROFILE ENRICHMENT
# =============================================================================

def _get_profile(loc_name: str, loc_tags: List[str], loc_desc: str) -> Dict:
    """
    Lấy profile từ LOCATION_PROFILES hoặc tự xây dựng từ metadata.
    Profile cung cấp thông tin phong phú hơn về location để sinh activities đúng ngữ cảnh.
    """
    # Tìm exact match hoặc partial match
    for key, profile in LOCATION_PROFILES.items():
        if key.lower() in loc_name.lower() or loc_name.lower() in key.lower():
            # Merge với metadata được truyền vào (metadata từ N4 có thể cụ thể hơn)
            merged_tags = list(set(profile["tags"] + loc_tags))
            return {
                **profile,
                "tags": merged_tags,
                "description": loc_desc or profile["description"],
                "name": loc_name or key,
            }

    # Không tìm thấy profile → tự build từ tags
    return {
        "name":         loc_name,
        "tags":         loc_tags,
        "description":  loc_desc or f"Địa điểm du lịch {loc_name} tại Việt Nam",
        "best_season":  [],
        "indoor_ratio": 0.3,
        "price_range":  (0, 500_000),
        "region":       "unknown",
    }


# =============================================================================
# PER-LOCATION GENERATION
# =============================================================================

def _generate_for_location(
    location_id:   str,
    location_name: str,
    profile:       Dict,
    user:          Dict,
    constraints:   Dict,
) -> List[Dict]:
    """
    Sinh đúng TARGET_PER_LOCATION activities cho một location.

    Pipeline (3 phase):
      A. _run_llm_path → tối đa LLM_QUOTA activities chất lượng cao (best-effort).
      B. _fill_unique_to_target → bù template + dedupe → ≥ TARGET_PER_LOCATION.
      C. _promote_sightseeing_to_front → đảm bảo ≥40% sightseeing ở top, generate
         thêm sightseeing nếu deficit, rồi sort: sightseeing → non-sightseeing.
    """
    seed = _run_llm_path(location_id, location_name, profile, user, constraints)
    pool = _fill_unique_to_target(
        seed         = seed,
        target_count = TARGET_PER_LOCATION,
        location_id  = location_id,
        location_name= location_name,
        profile      = profile,
        user_tags    = user.get("tags", []),
        constraints  = constraints,
    )
    pool = _promote_sightseeing_to_front(
        activities    = pool,
        location_id   = location_id,
        location_name = location_name,
        profile       = profile,
        target_ratio  = 0.40,
        target_total  = TARGET_PER_LOCATION,
    )
    return pool[:TARGET_PER_LOCATION]


def _run_llm_path(
    location_id:   str,
    location_name: str,
    profile:       Dict,
    user:          Dict,
    constraints:   Dict,
) -> List[Dict]:
    """Gọi LLM lấy tối đa LLM_QUOTA activities. Trả [] nếu LLM unavailable/fail."""
    if not (LLM_AVAILABLE and is_llm_available()):
        return []
    raw = generate_from_llm(
        location_name        = location_name,
        location_description = profile.get("description", ""),
        location_tags        = profile.get("tags", []),
        user_tags            = user.get("tags", []),
        budget_per_activity  = constraints["budget_per_activity"],
        max_time_per_activity= constraints["max_time_per_activity"],
        num_activities       = LLM_QUOTA,
    )
    if not raw:
        return []

    # LLM output đã được _validate_and_normalize đảm bảo đầy đủ field
    # unified-schema → truy cập trực tiếp, không cần default.
    out = [
        _build_activity_output(
            activity_id          = _make_id(location_id, f"llm_{i:03d}"),
            location_id          = location_id,
            name                 = act["name"],
            description          = act["description"],
            activity_type        = act["activity_type"],
            activity_subtype     = act["activity_subtype"],
            estimated_duration   = act["estimated_duration"],
            price_level          = act["price_level"],
            indoor_outdoor       = act["indoor_outdoor"],
            weather_dependent    = act["weather_dependent"],
            time_of_day_suitable = act["time_of_day_suitable"],
        )
        for i, act in enumerate(raw)
    ]
    logger.info("LLM generated %d activities for '%s'", len(out), location_name)
    return out


def _fill_unique_to_target(
    seed:          List[Dict],
    target_count:  int,
    location_id:   str,
    location_name: str,
    profile:       Dict,
    user_tags:     List[str],
    constraints:   Dict,
    max_rounds:    int = 3,
) -> List[Dict]:
    """
    Bổ sung template activities vào `seed` cho đến khi đủ `target_count` unique items.

    Vòng đầu dedupe rồi tính deficit; nếu vẫn thiếu sau khi expand thì lặp lại với
    `force_diverse=True` để rotate modifier mạnh hơn. Bound bởi max_rounds để tránh
    vòng vô hạn khi template pool cạn.
    """
    pool = _deduplicate(seed)
    for round_idx in range(max_rounds):
        if len(pool) >= target_count:
            break
        deficit = target_count - len(pool)
        more = _expand_templates(
            location_id   = location_id,
            location_name = location_name,
            profile       = profile,
            user_tags     = user_tags,
            constraints   = constraints,
            target_count  = deficit,
            start_index   = len(pool),
            force_diverse = round_idx > 0,
        )
        pool = _deduplicate(pool + more)
    return pool


# =============================================================================
# TEMPLATE EXPANSION ENGINE
# =============================================================================

def _expand_templates(
    location_id:   str,
    location_name: str,
    profile:       Dict,
    user_tags:     List[str],
    constraints:   Dict,
    target_count:  int,
    start_index:   int = 0,
    force_diverse: bool = False,
) -> List[Dict]:
    """
    Sinh activities từ ACTIVITY_TYPE_BANK bằng cách:
    1. Lọc templates tương thích với location (dựa trên compatible_location_tags)
    2. Sắp xếp theo sightseeing_priority (ưu tiên ngắm cảnh)
    3. Tạo biến thể bằng VARIATION_MODIFIERS để đạt target_count
    
    Scalable: nếu hết template gốc → lặp lại với modifier khác nhau
    """
    loc_tags = set(profile.get("tags", []))
    results: List[Dict] = []

    # Bước 1: Thu thập tất cả templates tương thích
    compatible_templates = _get_compatible_templates(loc_tags)

    if not compatible_templates:
        # Fallback: lấy tất cả templates không lọc
        compatible_templates = _get_all_templates()

    # Bước 2: Tính sightseeing_priority sau khi boost theo location
    scored_templates = _score_templates_for_location(compatible_templates, loc_tags)

    # Bước 3: Sắp xếp — sightseeing ưu tiên cao nhất, sau đó theo user tags
    scored_templates = _sort_templates_by_relevance(scored_templates, user_tags)

    # Bước 4: Generate activities với variation
    idx = start_index
    modifier_cycle = 0

    while len(results) < target_count:
        # Mỗi vòng qua hết templates → dùng modifier mới
        modifier_offset = modifier_cycle % len(VARIATION_MODIFIERS)

        for tmpl_data in scored_templates:
            if len(results) >= target_count:
                break

            tmpl     = tmpl_data["template"]
            modifier = VARIATION_MODIFIERS[(modifier_offset + tmpl_data["index"]) % len(VARIATION_MODIFIERS)]

            # Tạo activity từ template + modifier
            activity = _instantiate_template(
                template      = tmpl,
                modifier      = modifier if (modifier_cycle > 0 or force_diverse) else None,
                location_id   = location_id,
                location_name = location_name,
                activity_idx  = idx,
                sightseeing_priority = tmpl_data["sightseeing_priority"],
            )

            results.append(activity)
            idx += 1

        modifier_cycle += 1

        # Safety: nếu không có templates nào để lặp
        if not scored_templates:
            break

    return results[:target_count]


def _get_compatible_templates(loc_tags: set) -> List[Dict]:
    """Lấy templates có compatible_location_tags overlap với loc_tags."""
    result = []
    for type_name, templates in ACTIVITY_TYPE_BANK.items():
        for i, tmpl in enumerate(templates):
            compat = set(tmpl.get("compatible_location_tags", []))
            if compat & loc_tags:  # Có ít nhất 1 tag chung
                result.append({"template": tmpl, "type": type_name, "index": i})
    return result


def _get_all_templates() -> List[Dict]:
    """Lấy tất cả templates (fallback khi không có compatible templates)."""
    result = []
    for type_name, templates in ACTIVITY_TYPE_BANK.items():
        for i, tmpl in enumerate(templates):
            result.append({"template": tmpl, "type": type_name, "index": i})
    return result


def _score_templates_for_location(templates: List[Dict], loc_tags: set) -> List[Dict]:
    """
    Tính sightseeing_priority cuối cùng cho mỗi template dựa trên:
    - Base priority từ template
    - Boost nếu location có các tags liên quan sightseeing
    """
    for t in templates:
        tmpl     = t["template"]
        base     = tmpl.get("sightseeing_priority", 0.3)
        boost    = 0.0

        for tag, tag_boost in SIGHTSEEING_BOOST_TAGS.items():
            if tag in loc_tags:
                compat = set(tmpl.get("compatible_location_tags", []))
                if tag in compat:
                    boost += tag_boost

        t["sightseeing_priority"] = min(1.0, base + boost)

    return templates


def _sort_templates_by_relevance(templates: List[Dict], user_tags: List[str]) -> List[Dict]:
    """
    Sort templates:
    1. Sightseeing priority cao → trước
    2. Nếu bằng → user tag overlap nhiều hơn → trước
    """
    user_tag_set = set(user_tags)

    def sort_key(t):
        tmpl = t["template"]
        compat = set(tmpl.get("compatible_location_tags", []))
        tag_overlap = len(compat & user_tag_set)
        return (-t["sightseeing_priority"], -tag_overlap)

    return sorted(templates, key=sort_key)


def _instantiate_template(
    template:             Dict,
    modifier:             Optional[Dict],
    location_id:          str,
    location_name:        str,
    activity_idx:         int,
    sightseeing_priority: float,
) -> Dict:
    """
    Tạo activity cụ thể từ template + optional modifier.

    Modifier tạo biến thể: thêm suffix vào tên, thêm prefix vào description,
    điều chỉnh time_of_day.
    """
    # ─── Name ────────────────────────────────────────────────────────────────
    base_name = template["name_template"].format(location=location_name)
    if modifier:
        name = f"{base_name} — {modifier['suffix']}"
    else:
        name = base_name

    # ─── Description ─────────────────────────────────────────────────────────
    base_desc = template["description_template"].format(
        location       = location_name,
        subtype_detail = template.get("activity_subtype", ""),
    )
    if modifier:
        description = modifier["desc_prefix"] + base_desc
    else:
        description = base_desc

    # ─── Numeric fields với slight randomization trong range ─────────────────
    def rand_in(lo: float, hi: float) -> float:
        return round(random.uniform(lo, hi), 2)

    d_lo, d_hi = template["duration_range"]
    pl_lo, pl_hi = template["price_level_range"]

    time_of_day = template.get("time_of_day_suitable", "anytime")
    if modifier and modifier.get("time_of_day_suitable"):
        time_of_day = modifier["time_of_day_suitable"]

    # Templates dùng thang 1.0-5.0; unified schema yêu cầu 0.0-1.0 → chia 5.
    price_level = round(rand_in(pl_lo, pl_hi) / 5.0, 2)

    return _build_activity_output(
        activity_id          = _make_id(location_id, f"tmpl_{activity_idx:04d}"),
        location_id          = location_id,
        name                 = name,
        description          = description,
        activity_type        = template["activity_type"],
        activity_subtype     = template.get("activity_subtype"),
        estimated_duration   = float(random.randint(d_lo, d_hi)),
        price_level          = price_level,
        indoor_outdoor       = template["indoor_outdoor"],
        weather_dependent    = template["weather_dependent"],
        time_of_day_suitable = time_of_day,
    )


# =============================================================================
# SIGHTSEEING RATIO ENFORCEMENT
# =============================================================================

def _promote_sightseeing_to_front(
    activities:    List[Dict],
    location_id:   str,
    location_name: str,
    profile:       Dict,
    target_ratio:  float = 0.40,
    target_total:  int   = TARGET_PER_LOCATION,
) -> List[Dict]:
    """
    Đảm bảo ≥ `target_ratio` × target_total activities sightseeing nằm ở đầu danh
    sách (để khi trim về `target_total`, ratio được giữ).

    Generate thêm sightseeing activities từ templates nature/sightseeing nếu thiếu.
    """
    sg     = [a for a in activities if _is_sightseeing(a)]
    non_sg = [a for a in activities if not _is_sightseeing(a)]
    sg_needed = int(target_total * target_ratio)

    if len(sg) < sg_needed:
        sg.extend(_generate_extra_sightseeing(
            count         = sg_needed - len(sg),
            base_idx      = len(activities),
            location_id   = location_id,
            location_name = location_name,
            profile       = profile,
        ))
    return sg + non_sg


def _generate_extra_sightseeing(
    count:         int,
    base_idx:      int,
    location_id:   str,
    location_name: str,
    profile:       Dict,
) -> List[Dict]:
    """Sinh thêm `count` sightseeing activities từ subset templates nature priority ≥ 0.7."""
    loc_tags = set(profile.get("tags", []))
    sg_templates = [
        t for t in ACTIVITY_TYPE_BANK.get("nature", [])
        if t.get("sightseeing_priority", 0) >= 0.7
        and (not t.get("compatible_location_tags") or set(t["compatible_location_tags"]) & loc_tags)
    ] or ACTIVITY_TYPE_BANK.get("nature", [])

    return [
        _instantiate_template(
            template             = sg_templates[i % len(sg_templates)],
            modifier             = VARIATION_MODIFIERS[(i + 3) % len(VARIATION_MODIFIERS)],
            location_id          = location_id,
            location_name        = location_name,
            activity_idx         = base_idx + i,
            sightseeing_priority = sg_templates[i % len(sg_templates)].get("sightseeing_priority", 0.8),
        )
        for i in range(count)
    ]


def _is_sightseeing(activity: Dict) -> bool:
    """
    Xác định activity có phải sightseeing hay không.
    Bao gồm: nature type, các subtype ngắm cảnh, và relaxation có yếu tố cảnh quan.
    """
    meta      = activity.get("metadata", {})
    a_type    = meta.get("activity_type", "")
    a_subtype = (meta.get("activity_subtype") or "").lower()
    name      = (meta.get("name") or "").lower()

    # Tất cả nature activities đều là sightseeing
    if a_type == "nature":
        return True

    # Relaxation có yếu tố ngắm cảnh
    sightseeing_subtypes = {
        "sunrise_viewing", "sunset_viewing", "panorama_viewpoint",
        "landscape_photography", "flower_viewing", "stargazing",
        "nature_walk", "boat_sightseeing", "eco_tour",
        "nature_photography", "scenic_walk", "viewpoint",
    }
    if a_subtype in sightseeing_subtypes:
        return True

    # Keyword trong tên/subtype
    sightseeing_keywords = ["ngắm", "cảnh", "panorama", "view", "scenic", "hoàng hôn", "bình minh"]
    if any(kw in name for kw in sightseeing_keywords):
        return True
    if any(kw in a_subtype for kw in ["viewing", "panorama", "photography", "scenic"]):
        return True

    return False


# =============================================================================
# OUTPUT BUILDER
# =============================================================================

def _build_activity_output(
    activity_id:          str,
    location_id:          str,
    name:                 str,
    description:          str,
    activity_type:        str,
    activity_subtype:     Optional[str],
    estimated_duration:   float,
    price_level:          float,
    indoor_outdoor:       str,
    weather_dependent:    bool,
    time_of_day_suitable: Optional[str],
) -> Dict:
    """
    Tạo output activity theo schema chuẩn trong __init__.py.
    Đây là hàm duy nhất tạo ra activity dict → đảm bảo schema nhất quán.
    """
    return {
        "activity_id": activity_id,
        "location_id": location_id,
        "metadata": {
            # ─── CORE IDENTITY ─────────────────────────────
            "name":                 name,
            "description":          description,

            # ─── SEMANTIC CLASSIFICATION ───────────────────
            "activity_type":        activity_type,
            "activity_subtype":     activity_subtype,

            # ─── CONSTRAINT FIT ────────────────────────────
            "estimated_duration":   float(estimated_duration),
            "price_level":          round(float(price_level), 1),
            "indoor_outdoor":       indoor_outdoor,
            "weather_dependent":    bool(weather_dependent),

            # ─── CONTEXT FIT SIGNALS ───────────────────────
            "time_of_day_suitable": time_of_day_suitable,
        }
    }


# =============================================================================
# HELPERS
# =============================================================================

def _make_id(location_id: str, suffix: str) -> str:
    """
    Tạo activity_id ổn định từ location_id + suffix.
    Format: act_{location_short}_{suffix}
    Dùng hash ngắn để tránh trùng khi location_id dài.
    """
    loc_short = location_id[:8].replace(" ", "_").lower()
    h = hashlib.md5(f"{location_id}_{suffix}".encode()).hexdigest()[:6]
    return f"act_{loc_short}_{h}"


def _deduplicate(activities: List[Dict]) -> List[Dict]:
    """
    Loại bỏ duplicate dựa trên (name, activity_subtype).
    Ưu tiên giữ activity xuất hiện trước (LLM activities được ưu tiên).
    """
    seen: set = set()
    result: List[Dict] = []
    for act in activities:
        meta = act.get("metadata", {})
        key  = (
            meta.get("name", "").lower().strip(),
            meta.get("activity_subtype") or "",
        )
        if key not in seen:
            seen.add(key)
            result.append(act)
    return result


# =============================================================================
# MODULE RE-EXPORT (theo __init__.py)
# =============================================================================
__all__ = ["generate_activities"]