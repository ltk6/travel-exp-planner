# =============================================================================
# rank_activities.py (OPTIMIZED VERSION)
# =============================================================================
from __future__ import annotations

import hashlib
import math
import heapq
from typing import Any, Dict, List, Optional, Tuple, Union
from backend.shared.contracts.n6_contracts import N6RankInput

from backend.shared.weights import get_weights
from .preferences import infer_user_preferences

W_SEMANTIC     = 0.30
W_TAG          = 0.15
W_ATTRIBUTE    = 0.15
W_COMPLETENESS = 0.15
W_DISTANCE     = 0.25

# Reference radius for distance score — seed pipeline caps the pool at 8km, so we use
# the same value: act at the anchor → 1.0, act at the 8km pool edge → 0.0.
DISTANCE_DECAY_M = 8000.0

# =============================================================================
# SEMANTIC SCORE
# =============================================================================

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1  = math.sqrt(sum(a * a for a in v1))
    n2  = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)

def _semantic_score(user_vectors: Dict, act_vectors: Dict, weights: Dict[str, float]) -> Tuple[float, bool]:
    sum_score, total_weight = 0.0, 0.0
    
    for ch_user, ch_act, w_key in [("aug_tags", "aug_tags", "aug_tags"),
                                   ("aug_text", "text", "aug_text"),
                                   ("text",     "text", "text")]:
        w = weights.get(w_key, 0.0)
        if w == 0.0:
            continue
        v_user = user_vectors.get(ch_user)
        v_act  = act_vectors.get(ch_act)
        
        # ── Graceful Fallback: if activity has no tag vector, compare user's tag against activity text! ──
        if not v_act and ch_act == "aug_tags":
            v_act = act_vectors.get("text")
            
        if v_user and v_act:
            sim = cosine_similarity(v_user, v_act)
            sum_score    += ((sim + 1.0) / 2.0) * w
            total_weight += w
            
    if total_weight > 0:
        return sum_score / total_weight, True
    return 0.5, False

# =============================================================================
# TAG OVERLAP SCORE
# =============================================================================

def _tag_overlap_score(user_tags: List[str], act_tags: List[str]) -> float:
    """Fraction of user tags covered by activity tags. Neutral 0.5 when no user tags."""
    if not user_tags:
        return 0.5
    u = set(user_tags)  # already lowercased by caller
    a = set(t.lower().strip() for t in (act_tags or []))
    return len(u & a) / len(u)

# =============================================================================
# ATTRIBUTE SCORE
# =============================================================================

_COMPLETENESS_WEIGHTS = {
    "description":     0.45,
    "tags":            0.30,
    "image_url":       0.10,
    "rating":          0.10,
    "opening_hours":   0.05,
}


def _completeness_score(activity: Dict) -> float:
    """0.0 → 1.0 — prioritises acts that have a full desc + tags to display to the user.

    desc + tags account for 75% of the weight; signals (image, rating, opening hours) share the rest.
    """
    md = activity.get("metadata") or {}
    sg = activity.get("signals") or {}
    score = 0.0

    desc = md.get("description")
    if desc and str(desc).strip():
        score += _COMPLETENESS_WEIGHTS["description"]

    tags = md.get("tags") or []
    cats = md.get("categories_raw") or []
    if (tags and len(tags) > 0) or (cats and len(cats) > 0):
        score += _COMPLETENESS_WEIGHTS["tags"]

    if sg.get("image_url"):
        score += _COMPLETENESS_WEIGHTS["image_url"]
    if sg.get("rating") is not None:
        score += _COMPLETENESS_WEIGHTS["rating"]
    if sg.get("opening_hours"):
        score += _COMPLETENESS_WEIGHTS["opening_hours"]

    return score


def _distance_score(activity: Dict) -> Tuple[float, bool]:
    """0.0 → 1.0 — prioritises acts closest to the anchor.

    Linear decay from 1.0 (at anchor, 0m) down to 0.0 (≥ DISTANCE_DECAY_M).
    Returns (score, matched). matched=False when no distance data is available — the caller
    drops this branch from dynamic weighting instead of assigning a neutral 0.5.
    """
    place = activity.get("place") or {}
    d = place.get("distance_from_anchor_m")
    if d is None:
        return 0.5, False
    try:
        d = float(d)
    except (TypeError, ValueError):
        return 0.5, False
    if d <= 0:
        return 1.0, True
    if d >= DISTANCE_DECAY_M:
        return 0.0, True
    return 1.0 - (d / DISTANCE_DECAY_M), True


def _attribute_score(activity: Dict, user_prefs: Dict[str, Optional[float]]) -> float:
    metadata = activity.get("metadata", {}) or {}
    signals  = activity.get("signals", {}) or {}
    axis_fits = []
    
    # Check signals (DB cached), then metadata (N5 LLM dynamic), then root activity
    for axis, meta_key in [("intensity", "intensity"), ("physical", "physical_level"), ("social", "social_level")]:
        u_pref = user_prefs.get(axis)
        
        m_val = signals.get(meta_key)
        if m_val is None:
            m_val = metadata.get(meta_key)
        if m_val is None:
            m_val = activity.get(meta_key)
        
        if u_pref is not None and m_val is not None:
            axis_fits.append(max(0.0, 1.0 - abs(float(u_pref) - float(m_val))))

    if not axis_fits:
        return 0.5
    return sum(axis_fits) / len(axis_fits)

# =============================================================================
# REASON BUILDER
# =============================================================================

_REASON_BY_TYPE = {
    "nature":      ["Khám phá cảnh quan tuyệt đẹp", "Hòa mình vào thiên nhiên {intensity_hint}đậm chất địa phương"],
    "adventure":   ["Thử thách bản thân với hoạt động {intensity_hint}đầy phấn khích", "Trải nghiệm cảm giác mạnh {intensity_hint}giữa thiên nhiên"],
    "food":        ["Thưởng thức tinh túy ẩm thực đặc trưng", "Khám phá hương vị địa phương độc đáo"],
    "culture":     ["Tìm hiểu chiều sâu văn hóa bản địa", "Trải nghiệm di sản và phong tục truyền thống"],
    "relaxation":  ["Phút giây thư giãn nhẹ nhàng", "Tìm lại sự cân bằng trong không gian yên bình"],
    "nightlife":   ["Sôi động và lung linh về đêm", "Khám phá nhịp sống về đêm đầy sắc màu"],
    "shopping":    ["Săn tìm những món quà lưu niệm độc bản", "Ghé thăm không gian mua sắm đậm chất địa phương"],
    "photography": ["Ghi lại những khoảnh khắc {intensity_hint}tuyệt đẹp", "Lưu giữ kỷ niệm qua những khung hình nghệ thuật"],
    "experience":  ["Kết nối sâu sắc với nhịp sống địa phương", "Trải nghiệm thực tế {intensity_hint}đầy chân thực và gần gũi"],
}
_REASON_DEFAULT = ["Lựa chọn tuyệt vời cho hành trình của bạn", "Trải nghiệm thú vị không nên bỏ lỡ"]
_INTENSITY_LABELS = [(0.7, "mạnh mẽ"), (0.4, "vừa sức"), (0.0, "nhẹ nhàng")]

def _build_reason(activity: Dict, sem_score: float, tag_score: float, attr_score: float) -> str:
    metadata = activity.get("metadata", {}) or {}
    signals  = activity.get("signals", {}) or {}
    
    activity_type = metadata.get("activity_type") or activity.get("activity_type") or "nature"
    name_act = metadata.get("name") or activity.get("name") or "Trải nghiệm"
    
    intensity_val = signals.get("intensity")
    if intensity_val is None:
        intensity_val = metadata.get("intensity")
    if intensity_val is None:
        intensity_val = activity.get("intensity")
    intensity = float(intensity_val or 0.5)

    intensity_hint = next((label for threshold, label in _INTENSITY_LABELS if intensity >= threshold), "nhẹ nhàng") + " "

    templates = _REASON_BY_TYPE.get(activity_type, _REASON_DEFAULT)
    idx = int(hashlib.md5(name_act.encode()).hexdigest(), 16) % len(templates)
    body = templates[idx].format(intensity_hint=intensity_hint)

    highlights = []
    if attr_score >= 0.8:               highlights.append("rất hợp sở thích")
    if max(sem_score, tag_score) >= 0.8: highlights.append("đúng ý bạn tìm")

    suffix = f" ({', '.join(highlights)})" if highlights else ""
    return f"{body}{suffix}."

# =============================================================================
# ENTRY POINT
# =============================================================================

def rank_activities(data: Union[N6RankInput, Dict[str, Any]]) -> Dict[str, Any]:
    import time
    t0 = time.time()

    validated = N6RankInput.model_validate(data) if isinstance(data, dict) else data

    user_input   = validated.user_input.model_dump()
    user_vectors = validated.user_vectors.model_dump()
    activities   = validated.activities
    top_k        = max(1, validated.top_k)
    text_k       = validated.text_k
    tags_k       = validated.tags_k

    if not activities or top_k <= 0:
        return {"activities": [], "metadata": {"latency_ms": 0}}

    user_prefs = infer_user_preferences(user_input)
    user_tags  = [t.lower().strip() for t in (user_input.get("tags") or [])]
    weights    = get_weights(text_k, tags_k)

    scored_heap = []

    for activity in activities:
        metadata = activity.get("metadata", {}) or {}
        vectors  = activity.get("vectors", {}) or {}
        act_tags = metadata.get("tags") or activity.get("tags") or []

        sem_score, sem_matched = _semantic_score(user_vectors, vectors, weights)
        sem_scaled = max(0.0, min(1.0, (sem_score - 0.5) * 2.0)) if sem_matched else 0.5
        tag_score  = _tag_overlap_score(user_tags, act_tags)
        attr_score = _attribute_score(activity, user_prefs)
        comp_score = _completeness_score(activity)
        dist_score, dist_matched = _distance_score(activity)

        # ── Dynamic category weighting ──
        # Completeness + distance are always available when data exists → keep fixed weights.
        # Other branches zero out when input is missing. Distance is dropped when the act
        # has no distance_from_anchor_m (e.g. N5 fallback activities without anchor distance).
        has_attr_pref = any(v is not None for v in user_prefs.values())
        w_sem  = W_SEMANTIC if sem_matched else 0.0
        w_tag  = W_TAG if user_tags else 0.0
        w_attr = W_ATTRIBUTE if has_attr_pref else 0.0
        w_comp = W_COMPLETENESS
        w_dist = W_DISTANCE if dist_matched else 0.0

        sum_cat_w = w_sem + w_tag + w_attr + w_comp + w_dist
        if sum_cat_w > 0:
            total = (
                w_sem  * sem_scaled
                + w_tag  * tag_score
                + w_attr * attr_score
                + w_comp * comp_score
                + w_dist * dist_score
            ) / sum_cat_w
        else:
            total = 0.5

        heap_item = (total, activity.get("activity_id"), activity.get("location_id"), activity, sem_scaled, tag_score, attr_score)

        if len(scored_heap) < top_k:
            heapq.heappush(scored_heap, heap_item)
        else:
            heapq.heappushpop(scored_heap, heap_item)

    top_activities = sorted(scored_heap, key=lambda x: x[0], reverse=True)

    final_results = []
    if top_activities:
        for score, act_id, loc_id, act_item, sem_s, tag_s, attr in top_activities:
            # Absolute Smoothstep Dead-Zone Scaling
            norm = max(0.0, min(1.0, score))
            shaped = 3 * (norm ** 2) - 2 * (norm ** 3)
            scaled_score = round(0.65 + shaped * 0.30, 4)
            final_results.append({
                "activity_id": act_id,
                "location_id": loc_id,
                "score":       scaled_score,
                "reason":      _build_reason(act_item, sem_s, tag_s, attr),
            })

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "activities": final_results,
        "metadata": {
            "user_prefs": user_prefs,
            "weights":    weights,
            "text_k":     text_k,
            "tags_k":     tags_k,
            "latency_ms": elapsed_ms,
        },
    }