# =============================================================================
# n5_activity_generator.py
# =============================================================================
# N5 — Activity Generation Module
#
# Entry point duy nhất: generate_activities(data: dict) -> dict
# Schema I/O theo đúng __init__.py
#
# KIẾN TRÚC (LLM-first):
#   ┌─────────────────────────────────────────────────────────┐
#   │  generate_activities(data)                              │
#   │       │                                                 │
#   │       ▼                                                 │
#   │  _parse_input()  → user (text+tags), locations, constraints │
#   │       │                                                 │
#   │       ▼  (per location)                                 │
#   │  _generate_for_location()                               │
#   │       ├── PRIMARY: generate_from_llm()  10 acts         │
#   │       │     └── _map_llm_v2_to_output() → N5 schema     │
#   │       └── FALLBACK: _expand_templates() nếu LLM fail    │
#   │       ▼                                                 │
#   │  _build_activity_output()  → schema theo __init__.py    │
#   │       │                                                 │
#   │       ▼                                                 │
#   │  {"activities": [...]}                                  │
#   └─────────────────────────────────────────────────────────┘
#
# LLM-FIRST STRATEGY:
#   - LLM_QUOTA = 10: xAI Grok sinh 10 activities cá nhân hóa theo user text + tags
#   - Nếu LLM trả về ≥ 5 valid → sử dụng, bù template nếu thiếu
#   - Nếu LLM fail → fall back hoàn toàn về template bank
#
# OUTPUT theo __init__.py:
#   {
#     "activities": [
#       {
#         "activity_id": str,
#         "location_id": str,
#         "metadata": {
#           "name": str,
#           "description": str,
#           "activity_type": str,
#           "activity_subtype": str | None,
#           "intensity": float,
#           "physical_level": float | None,
#           "social_level": float | None,
#           "estimated_duration": float,
#           "price_level": float,
#           "indoor_outdoor": str,
#           "weather_dependent": bool,
#           "time_of_day_suitable": str | None
#         }
#       }
#     ]
#   }
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

DEFAULT_TARGET_PER_LOCATION = 10    # LLM sinh đủ 10 activities/location
LLM_QUOTA           = 10            # LLM là primary source
TEMPLATE_QUOTA      = 0             # Template chỉ dùng khi LLM fail
TARGET_PER_LOCATION = DEFAULT_TARGET_PER_LOCATION

LLM_MIN_VALID = 5   # Ngưỡng tối thiểu — nếu LLM trả về < 5 valid thì fall back template

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
            "img_desc": str | None,
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
    user, locations, constraints, target_count = _parse_input(data)
    all_activities: List[Dict] = []

    for loc in locations:
        loc_id   = loc["location_id"]
        loc_name = loc["metadata"].get("name") or ""
        loc_desc = loc["metadata"].get("description") or ""
        loc_tags = loc["metadata"].get("tags") or []

        # Enrich từ LOCATION_PROFILES nếu có
        profile = _get_profile(loc_name, loc_tags, loc_desc)

        activities = _generate_for_location(
            location_id   = loc_id,
            location_name = loc_name,
            profile       = profile,
            user          = user,
            constraints   = constraints,
            target_count  = target_count,
        )

        all_activities.extend(activities)
        logger.info(
            "Location '%s' (%s): generated %d activities",
            loc_name, loc_id, len(activities)
        )

    return {"activities": all_activities}


# =============================================================================
# INPUT PARSING
# =============================================================================

def _parse_input(data: dict) -> Tuple[Dict, List[Dict], Dict, int]:
    """Validate và extract user, locations, constraints từ input dict."""
    user        = data.get("user", {}) or {}
    locations   = data.get("locations", []) or []
    constraints = data.get("constraints", {}) or {}
    
    target_count = data.get("target_count", DEFAULT_TARGET_PER_LOCATION)

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

    # Normalize locations
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
            }
        })

    return user, normalized_locs, constraints, target_count


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
# LLM V2 → N5 OUTPUT SCHEMA MAPPING
# =============================================================================

def _cost_to_price_level(cost: int) -> float:
    """Chuyển cost VNĐ → price_level 1–5 theo mặt bằng giá Việt Nam."""
    if cost == 0:           return 1.0
    if cost < 50_000:       return 1.5
    if cost < 150_000:      return 2.0
    if cost < 500_000:      return 3.0
    if cost < 1_500_000:    return 4.0
    return 5.0


def _best_time_to_suitable(best_time: List[str]) -> str:
    """Chuyển danh sách best_time → chuỗi time_of_day_suitable."""
    if not best_time or len(best_time) >= 3:
        return "anytime"
    if best_time == ["morning"]:
        return "morning"
    if best_time == ["afternoon"]:
        return "afternoon"
    if best_time == ["evening"]:
        return "evening"
    return "anytime"


_TAG_TO_TYPE: List[Tuple[str, set]] = [
    ("food",        {"food", "cuisine", "local_food", "street_food"}),
    ("adventure",   {"adventure", "trekking", "kayak", "diving", "snorkeling", "cycling", "motorbiking", "camping", "climbing", "road_trip"}),
    ("culture",     {"culture", "history", "heritage", "temple", "architecture", "spiritual", "tradition", "ethnic", "art", "craft"}),
    ("nightlife",   {"nightlife", "music", "entertainment", "fun"}),
    ("shopping",    {"shopping", "market"}),
    ("relaxation",  {"relax", "spa", "sunset", "sunrise", "romantic"}),
    ("nature",      {"nature", "wildlife", "eco", "forest", "mountain", "waterfall", "scenic", "flower", "lake", "river", "beach", "sea", "island", "cave", "sightseeing"}),
]

_OUTDOOR_TAGS = {"nature", "beach", "sea", "trekking", "mountain", "waterfall", "cycling", "kayak", "camping", "scenic", "eco", "wildlife", "island", "cave", "river", "lake", "motorbiking", "road_trip", "snorkeling", "diving", "sunrise", "sunset"}
_INDOOR_TAGS  = {"shopping", "spa", "heritage", "architecture", "art", "craft", "education", "spiritual"}
_WEATHER_TAGS = {"beach", "sea", "diving", "snorkeling", "kayak", "trekking", "cycling", "camping", "sunrise", "sunset", "scenic", "nature", "wildlife", "outdoor"}


def _tags_to_activity_type(tags: set) -> str:
    for type_name, type_tags in _TAG_TO_TYPE:
        if tags & type_tags:
            return type_name
    return "nature"


def _tags_to_indoor_outdoor(tags: set) -> str:
    outdoor = len(tags & _OUTDOOR_TAGS)
    indoor  = len(tags & _INDOOR_TAGS)
    if outdoor > indoor:  return "outdoor"
    if indoor  > outdoor: return "indoor"
    return "both"


def _tags_to_weather_dependent(tags: set) -> bool:
    return bool(tags & _WEATHER_TAGS)


def _difficulty_to_intensity(difficulty: str) -> float:
    return {"easy": 0.25, "medium": 0.55, "hard": 0.85}.get(difficulty, 0.4)


def _map_llm_v2_to_output(act: Dict, location_id: str, idx: int) -> Dict:
    """Chuyển đổi activity schema v2 từ LLM → N5 output schema."""
    tags        = set(t.lower().strip() for t in act.get("tags", []))
    difficulty  = act.get("difficulty", "easy")
    intensity   = _difficulty_to_intensity(difficulty)
    cost        = int(act.get("cost", 0))
    best_time   = act.get("best_time", [])

    return _build_activity_output(
        activity_id          = _make_id(location_id, f"llm_{idx:03d}"),
        location_id          = location_id,
        name                 = act.get("name", ""),
        description          = act.get("description", ""),
        activity_type        = _tags_to_activity_type(tags),
        activity_subtype     = None,
        intensity            = intensity,
        physical_level       = min(1.0, intensity + 0.1),
        social_level         = 0.5,
        estimated_duration   = float(act.get("estimated_duration", 90)),
        price_level          = _cost_to_price_level(cost),
        indoor_outdoor       = _tags_to_indoor_outdoor(tags),
        weather_dependent    = _tags_to_weather_dependent(tags),
        time_of_day_suitable = _best_time_to_suitable(best_time),
    )


# =============================================================================
# PER-LOCATION GENERATION
# =============================================================================

def _generate_for_location(
    location_id:   str,
    location_name: str,
    profile:       Dict,
    user:          Dict,
    constraints:   Dict,
    target_count:  int,
) -> List[Dict]:
    """
    Sinh activities cho một location theo chiến lược LLM-first:
      1. Gọi LLM (xAI Grok) → 10 activities chất lượng cao, cá nhân hóa theo user
      2. Nếu LLM trả về ≥ LLM_MIN_VALID → dùng kết quả LLM (fill thêm từ template nếu thiếu)
      3. Nếu LLM fail hoặc < LLM_MIN_VALID → fall back hoàn toàn về template
    """
    loc_tags  = profile.get("tags", [])
    user_tags = user.get("tags", [])
    user_text = user.get("text") or ""

    llm_activities: List[Dict] = []

    # ─── Step 1: LLM generation (primary) ────────────────────────────────────
    if LLM_AVAILABLE and is_llm_available():
        raw = generate_from_llm(
            location_name         = location_name,
            location_description  = profile.get("description", ""),
            location_tags         = loc_tags,
            user_tags             = user_tags,
            budget_per_activity   = constraints["budget_per_activity"],
            max_time_per_activity = constraints["max_time_per_activity"],
            num_activities        = LLM_QUOTA,
            schema_v2             = True,
            user_text             = user_text,
        )
        if raw:
            for i, act in enumerate(raw):
                if not act.get("name") or not act.get("description"):
                    continue
                llm_activities.append(_map_llm_v2_to_output(act, location_id, i))
            logger.info("LLM generated %d activities for '%s'", len(llm_activities), location_name)

    # ─── Step 2: Đủ ngưỡng → dùng LLM, bù template nếu thiếu ───────────────
    if len(llm_activities) >= LLM_MIN_VALID:
        combined = _deduplicate(llm_activities)
        if len(combined) < target_count:
            extra = _expand_templates(
                location_id   = location_id,
                location_name = location_name,
                profile       = profile,
                user_tags     = user_tags,
                constraints   = constraints,
                target_count  = target_count - len(combined),
                start_index   = len(combined),
            )
            combined.extend(extra)
        return combined[:target_count]

    # ─── Step 3: Fall back hoàn toàn về template ─────────────────────────────
    logger.warning("LLM insufficient for '%s' (%d activities) — using templates", location_name, len(llm_activities))
    combined = _expand_templates(
        location_id   = location_id,
        location_name = location_name,
        profile       = profile,
        user_tags     = user_tags,
        constraints   = constraints,
        target_count  = target_count,
        start_index   = 0,
    )
    combined = _deduplicate(combined)

    if len(combined) < target_count:
        extra = _expand_templates(
            location_id   = location_id,
            location_name = location_name,
            profile       = profile,
            user_tags     = user_tags,
            constraints   = constraints,
            target_count  = target_count - len(combined),
            start_index   = len(combined),
            force_diverse = True,
        )
        combined.extend(extra)

    combined = _ensure_sightseeing_ratio(
        activities    = combined,
        location_id   = location_id,
        location_name = location_name,
        profile       = profile,
        target_ratio  = 0.40,
        target_total  = target_count,
    )
    return combined[:target_count]


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
    điều chỉnh nhẹ intensity và time_of_day.
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

    i_lo, i_hi = template["intensity_range"]
    p_lo, p_hi = template["physical_level_range"]
    s_lo, s_hi = template["social_level_range"]
    d_lo, d_hi = template["duration_range"]
    pl_lo, pl_hi = template["price_level_range"]

    intensity = rand_in(i_lo, i_hi)
    if modifier:
        intensity = max(0.0, min(1.0, intensity + modifier.get("intensity_delta", 0.0)))

    time_of_day = template.get("time_of_day_suitable", "anytime")
    if modifier and modifier.get("time_of_day_suitable"):
        time_of_day = modifier["time_of_day_suitable"]

    return _build_activity_output(
        activity_id          = _make_id(location_id, f"tmpl_{activity_idx:04d}"),
        location_id          = location_id,
        name                 = name,
        description          = description,
        activity_type        = template["activity_type"],
        activity_subtype     = template.get("activity_subtype"),
        intensity            = intensity,
        physical_level       = rand_in(p_lo, p_hi),
        social_level         = rand_in(s_lo, s_hi),
        estimated_duration   = float(random.randint(d_lo, d_hi)),
        price_level          = round(rand_in(pl_lo, pl_hi), 1),
        indoor_outdoor       = template["indoor_outdoor"],
        weather_dependent    = template["weather_dependent"],
        time_of_day_suitable = time_of_day,
    )


# =============================================================================
# SIGHTSEEING RATIO ENFORCEMENT
# =============================================================================

def _ensure_sightseeing_ratio(
    activities:    List[Dict],
    location_id:   str,
    location_name: str,
    profile:       Dict,
    target_ratio:  float = 0.40,
    target_total:  int   = TARGET_PER_LOCATION,
) -> List[Dict]:
    """
    Đảm bảo ít nhất target_ratio (40%) activities trong target_total đầu tiên là sightseeing.
    
    Chiến lược:
    - Tách sightseeing và non-sightseeing
    - Tính số lượng sightseeing cần đạt trong target_total
    - Nếu thiếu → sinh thêm sightseeing và đưa lên đầu
    - Kết quả: sightseeing ở đầu, non-sightseeing ở sau → khi trim về target_total sẽ đúng ratio
    """
    sightseeing_pool    = [a for a in activities if _is_sightseeing(a)]
    non_sightseeing_pool = [a for a in activities if not _is_sightseeing(a)]

    sightseeing_needed = int(target_total * target_ratio)   # 40
    current_sg_count   = len(sightseeing_pool)

    if current_sg_count < sightseeing_needed:
        extra_count = sightseeing_needed - current_sg_count

        # Sinh thêm sightseeing từ nature/relaxation templates
        loc_tags = set(profile.get("tags", []))
        sg_templates = []

        for tmpl in ACTIVITY_TYPE_BANK.get("nature", []):
            if tmpl.get("sightseeing_priority", 0) >= 0.7:
                compat = set(tmpl.get("compatible_location_tags", []))
                if not compat or (compat & loc_tags):
                    sg_templates.append(tmpl)

        if not sg_templates:
            sg_templates = ACTIVITY_TYPE_BANK.get("nature", [])

        extra = []
        base_idx = len(activities)
        for i in range(extra_count):
            tmpl     = sg_templates[i % len(sg_templates)]
            modifier = VARIATION_MODIFIERS[(i + 3) % len(VARIATION_MODIFIERS)]  # offset để tránh trùng
            act = _instantiate_template(
                template             = tmpl,
                modifier             = modifier,
                location_id          = location_id,
                location_name        = location_name,
                activity_idx         = base_idx + i,
                sightseeing_priority = tmpl.get("sightseeing_priority", 0.8),
            )
            extra.append(act)

        sightseeing_pool = sightseeing_pool + extra

    # Sắp xếp: sightseeing trước, non-sightseeing sau
    # Khi trim về target_total sẽ đảm bảo đủ ratio
    return sightseeing_pool + non_sightseeing_pool


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
    intensity:            float,
    physical_level:       Optional[float],
    social_level:         Optional[float],
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

            # ─── EXPERIENCE DYNAMICS ───────────────────────
            "intensity":            round(float(intensity), 2),
            "physical_level":       round(float(physical_level), 2) if physical_level is not None else None,
            "social_level":         round(float(social_level), 2)   if social_level   is not None else None,

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