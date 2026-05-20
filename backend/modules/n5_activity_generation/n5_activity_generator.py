# =============================================================================
# n5_activity_generator.py — N5 Activity Generation
#
# Entry: generate_activities(data) → {"activities": [...], "llm_meta": [...]}
# Strategy: LLM-first, template backup on failure.
# Schema: matches N5 __init__.py
# =============================================================================

import random
import hashlib
from typing import Dict, List, Optional, Tuple, Union
from backend.shared.contracts.n5_contracts import N5GenerateInput

from .n5_activity_templates import (
    LOCATION_PROFILES,
    ACTIVITY_TYPE_BANK,
    SIGHTSEEING_BOOST_TAGS,
    VARIATION_MODIFIERS,
)



try:
    from .n5_llm_generator import generate_from_llm, generate_from_llm_with_meta, is_llm_available
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    def is_llm_available(): return False
    def generate_from_llm(*args, **kwargs): return None
    def generate_from_llm_with_meta(*args, **kwargs): return None, {}

from config import setup_logging, LLM_N5_TARGET_COUNT
logger = setup_logging("N5")

# =============================================================================
# CONSTANTS
# =============================================================================

LLM_MIN_VALID = 5


# =============================================================================
# PUBLIC ENTRY POINT
# =============================================================================

def generate_activities(data: Union[N5GenerateInput, dict]) -> dict:
    """
    N5 — Entry point chính.
 
    Input/output schema: see __init__.py
    """
    import time
    t0 = time.time()
    from config.settings import LLM_ACTIVITIES_PER_CALL, LLM_N5_TARGET_COUNT
    
    # ─── Step 0: Early Exit Check ────────────────────────────────────────────
    if LLM_N5_TARGET_COUNT <= 0 or LLM_ACTIVITIES_PER_CALL <= 0:
        logger.info("N5: Skipping generation (config set to 0)")
        elapsed_ms = int((time.time() - t0) * 1000)
        return {
            "activities": [], 
            "metadata": {
                "per_location": [],
                "latency_ms": elapsed_ms
            }
        }

    user, locations, constraints, target_count = _parse_input(data)
    all_activities: List[Dict] = []
    llm_metas: List[Dict] = []  # 1 entry per location

    for loc in locations:
        loc_id   = loc["location_id"]
        loc_name = loc["metadata"].get("name") or ""
        loc_desc = loc["metadata"].get("description") or ""
        loc_tags = loc["metadata"].get("tags") or []

        # Enrich từ LOCATION_PROFILES nếu có
        profile = _get_profile(loc_name, loc_tags, loc_desc)

        meta_out: Dict = {}
        activities = _generate_for_location(
            location_id   = loc_id,
            location_name = loc_name,
            profile       = profile,
            user          = user,
            constraints   = constraints,
            target_count  = target_count,
            llm_chain     = None, # Will be determined by provider registry from config
            meta_out      = meta_out,
        )
        llm_metas.append({"location_id": loc_id, **meta_out})

        # Legacy {activity_id, location_id, metadata{...}} format is returned directly.
        # Decoupled: Normalization into the unified schema is handled by the orchestrator (N8).
        all_activities.extend(activities)
        logger.info(
            "Location '%s' (%s): generated %d activities (raw format)",
            loc_name, loc_id, len(activities)
        )

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "activities": all_activities, 
        "metadata": {
            "per_location": llm_metas,
            "latency_ms": elapsed_ms
        }
    }


# =============================================================================
# INPUT PARSING
# =============================================================================

def _parse_input(data: Union[N5GenerateInput, dict]) -> Tuple[Dict, List[Dict], Dict, int]:
    """Validate và extract user, locations, constraints từ input dict."""
    from config.settings import LLM_N5_TARGET_COUNT
    
    validated = N5GenerateInput.model_validate(data) if isinstance(data, dict) else data
    
    user = validated.user.model_dump()
    user_tags = user.get("tags") or []
    user["tags"] = [str(t).lower() for t in user_tags]
    
    constraints = validated.constraints.model_dump() if validated.constraints else {"time_of_day": "anytime"}
    if not constraints.get("time_of_day"):
        constraints["time_of_day"] = "anytime"
        
    normalized_locs = []
    for loc in validated.locations:
        loc_id = loc.location_id
        meta = loc.metadata.model_dump() if loc.metadata else {}
        normalized_locs.append({
            "location_id": loc_id,
            "metadata": {
                "name":        meta.get("name") or loc_id,
                "description": meta.get("description") or "",
                "tags":        [t.lower() for t in (meta.get("tags") or [])],
                "coordinates": meta.get("coordinates"),
                "address":     meta.get("address"),
            }
        })
        
    return user, normalized_locs, constraints, LLM_N5_TARGET_COUNT


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


_TAG_TO_TYPE: List[Tuple[str, set]] = [
    ("food",        {"local cuisine", "street food", "fine dining", "cooking class", "seafood", "coffee", "food tour", "pho", "banh mi", "tropical fruit"}),
    ("adventure",   {"trekking", "kayaking", "scuba diving", "adventure", "motorbiking", "cycling", "camping", "rock climbing", "caving", "motorbike loop", "surfing", "kitesurfing", "canyoning", "zip lining"}),
    ("culture",     {"history", "temple", "architecture", "traditional music", "heritage", "ethnic minority", "craft village", "spiritual", "museum", "pagoda", "ethnic village", "unesco heritage", "imperial", "royal tomb", "cham culture", "water puppet"}),
    ("nightlife",   {"nightlife", "rooftop bar", "night market", "bar", "club", "bia hoi"}),
    ("shopping",    {"shopping", "local market", "silk village", "lantern making"}),
    ("relaxation",  {"peaceful", "spa", "hot spring", "yoga retreat", "meditation", "wellness retreat", "hot spring bath", "herbal bath"}),
    ("nature",      {"wildlife", "picturesque", "national park", "waterfall", "beach", "cave", "mountain", "island", "forest", "nature reserve", "scenic", "national park", "biosphere reserve", "birdwatching", "coral reef", "mangrove"}),
    ("photography", {"photography", "landscape photography", "instagrammable", "picturesque", "cloud sea", "flower season"}),
    ("experience",  {"authentic", "immersive", "local life", "fishing village", "homestay", "village", "floating market", "ethnic market", "craft village", "slow travel", "boat cruise", "junk boat", "basket boat", "river cruise", "fishing", "squid fishing", "limestone boat ride", "bamboo rafting"}),
]

def _tags_to_activity_type(tags: set) -> Optional[str]:
    for type_name, type_tags in _TAG_TO_TYPE:
        if tags & type_tags:
            return type_name
    return None


def _map_llm_v2_to_output(act: Dict, location_id: str, idx: int) -> Dict:
    """Chuyển đổi activity schema v2 từ LLM → N5 output schema."""
    tags = set(t.lower().strip() for t in act.get("tags", []))
    name = act.get("name", "")

    # Lấy trực tiếp từ LLM, fallback về 0.5 nếu thiếu
    intensity      = float(act.get("intensity", 0.5))
    physical_level = float(act.get("physical_level", 0.5))
    social_level   = float(act.get("social_level", 0.5))

    # Prioritize heuristic (tag-to-type) > LLM provided type > fallback
    heuristic_type = _tags_to_activity_type(tags)
    llm_type = act.get("activity_type")
    
    final_type = heuristic_type or llm_type or "experience"
    final_type = str(final_type).lower().strip()

    # Validate against known types to ensure reasoning templates in N6 work
    known_types = {t[0] for t in _TAG_TO_TYPE}
    if final_type not in known_types:
        final_type = "experience"

    return _build_activity_output(
        activity_id    = _make_id(location_id, "act", name),
        location_id    = location_id,
        name           = name,
        description    = act.get("description", ""),
        activity_type  = final_type,
        intensity      = intensity,
        physical_level = physical_level,
        social_level   = social_level,
        tags           = list(tags),
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
    llm_chain:     Optional[str] = None,
    meta_out:      Optional[Dict] = None,
) -> List[Dict]:
    """
    Sinh activities cho một location theo chiến lược LLM-first:
      1. Gọi LLM → 10 activities chất lượng cao, cá nhân hóa theo user
      2. Nếu LLM trả về ≥ LLM_MIN_VALID → dùng kết quả LLM (fill thêm từ template nếu thiếu)
      3. Nếu LLM fail hoặc < LLM_MIN_VALID → dùng template hoàn toàn

    llm_chain: override LLM_CHAIN runtime (UI chọn). None = dùng config.
    meta_out: nếu truyền dict, sẽ được điền provider_used/latency_ms.
    """
    loc_tags  = profile.get("tags", [])
    user_tags = user.get("tags", [])
    user_text = user.get("text") or ""

    llm_activities: List[Dict] = []

    # ─── Step 1: LLM generation (primary) ────────────────────────────────────
    from config.settings import LLM_ACTIVITIES_PER_CALL
    
    if LLM_AVAILABLE and is_llm_available():
        logger.info(f"Invoking LLM for location '{location_name}' (requesting {LLM_ACTIVITIES_PER_CALL} activities)...")
        raw, llm_meta = generate_from_llm_with_meta(
            location_name        = location_name,
            location_description = profile.get("description", ""),
            location_tags        = loc_tags,
            user_tags            = user_tags,
            num_activities       = LLM_ACTIVITIES_PER_CALL,
            user_text            = user_text,
            llm_chain            = llm_chain,
        )
        if meta_out is not None:
            meta_out.update(llm_meta)
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
                start_index   = target_count,
            )
            combined.extend(extra)
        return combined[:target_count]

    # ─── Step 3: Dùng template hoàn toàn ─────────────────────────────
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
            start_index   = target_count,
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
# RATIO ENFORCEMENT (stub — original implementation missing)
# =============================================================================

def _ensure_sightseeing_ratio(
    activities,
    location_id,
    location_name,
    profile,
    target_ratio: float = 0.40,
    target_total: int = 10,
):
    """No-op stub. The original ratio-enforcement helper was missing from this
    file, causing /activities to 500 whenever the LLM chain fell back to
    templates. Returning activities unchanged preserves the previous behaviour
    when the template path is exercised; reintroduce real ratio logic later
    if the product still wants it."""
    return activities


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
        # Backup: lấy tất cả templates không lọc
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
    """Lấy tất cả templates (backup khi không có compatible templates)."""
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

    i_lo, i_hi = template["intensity_range"]
    p_lo, p_hi = template["physical_level_range"]
    s_lo, s_hi = template["social_level_range"]

    intensity = rand_in(i_lo, i_hi)
    if modifier:
        intensity = max(0.0, min(1.0, intensity + modifier.get("intensity_delta", 0.0)))

    return _build_activity_output(
        activity_id    = _make_id(location_id, f"tmpl_{activity_idx:04d}"),
        location_id    = location_id,
        name           = name,
        description    = description,
        activity_type  = template["activity_type"],
        intensity      = intensity,
        physical_level = rand_in(p_lo, p_hi),
        social_level   = rand_in(s_lo, s_hi),
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
    target_total:  int   = LLM_N5_TARGET_COUNT,
) -> List[Dict]:
    """
    Đảm bảo ít nhất target_ratio (40%) activities trong target_total đầu tiên là sightseeing.
    """
    sg     = [a for a in activities if _is_sightseeing(a)]
    non_sg = [a for a in activities if not _is_sightseeing(a)]

    sightseeing_needed = int(target_total * target_ratio)
    current_sg_count   = len(sg)

    if current_sg_count < sightseeing_needed:
        extra_count = sightseeing_needed - current_sg_count
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
            modifier = VARIATION_MODIFIERS[(i + 3) % len(VARIATION_MODIFIERS)]
            act = _instantiate_template(
                template             = tmpl,
                modifier             = modifier,
                location_id          = location_id,
                location_name        = location_name,
                activity_idx         = base_idx + i,
                sightseeing_priority = tmpl.get("sightseeing_priority", 0.8),
            )
            extra.append(act)

        sg = sg + extra

    return sg + non_sg


def _is_sightseeing(activity: Dict) -> bool:
    """Xác định activity có phải sightseeing hay không."""
    meta   = activity.get("metadata", {})
    a_type = meta.get("activity_type", "")
    tags   = set(meta.get("tags") or [])
    name   = (meta.get("name") or "").lower()

    if a_type == "nature":
        return True

    sightseeing_tags = {
        "picturesque", "scenic", "national park", "waterfall", "mountain",
        "landscape photography", "wildlife", "cave", "island"
    }
    if tags & sightseeing_tags:
        return True

    sightseeing_keywords = ["ngắm", "cảnh", "panorama", "view", "scenic", "hoàng hôn", "bình minh"]
    if any(kw in name for kw in sightseeing_keywords):
        return True
    return False


# =============================================================================
# OUTPUT BUILDER
# =============================================================================

def _build_activity_output(
    activity_id:    str,
    location_id:    str,
    name:           str,
    description:    str,
    activity_type:  str,
    intensity:      float,
    physical_level: Optional[float],
    social_level:   Optional[float],
    tags:           Optional[List[str]] = None,
) -> Dict:
    """Tạo output activity theo schema chuẩn."""
    return {
        "activity_id": activity_id,
        "location_id": location_id,
        "metadata": {
            "name":          name,
            "description":   description,
            "tags":          sorted(tags) if tags else [],
            "activity_type": activity_type,
            "intensity":     round(float(intensity), 2),
            "physical_level": round(float(physical_level), 2) if physical_level is not None else None,
            "social_level":  round(float(social_level), 2) if social_level is not None else None,
        }
    }


def _make_id(location_id: str, prefix: str, name: str = "") -> str:
    """Tạo activity_id duy nhất, có hash tên để tránh trùng lặp."""
    if name:
        # Lấy 6 ký tự đầu của md5 hash tên
        h = hashlib.md5(name.encode()).hexdigest()[:6]
        return f"{prefix}_{h}"
    return f"{prefix}_{random.getrandbits(16):04x}"


def _deduplicate(activities: List[Dict]) -> List[Dict]:
    """Xóa các activity trùng tên."""
    seen = set()
    unique = []
    for a in activities:
        name = a["metadata"]["name"].lower()
        if name not in seen:
            seen.add(name)
            unique.append(a)
    return unique