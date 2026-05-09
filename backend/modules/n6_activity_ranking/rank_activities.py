"""
rank_activities.py
=================
N6 — Activity Ranking Module

Ranks activities by computing weighted cosine similarity between
user vectors and activity vectors, plus simple logic for activity levels.

Scoring channels (user → activity):
    text      → text     : raw intent match
    aug_text  → text     : expanded semantic match
    aug_tags  → aug_tags : tag-based anchor
    img_desc  → text     : visual alignment
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger("N6")

from backend.shared.weights import get_weights

# ── Helpers ───────────────────────────────────────────────────

def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _cosine(a: list[float] | None, b: list[float] | None) -> float:
    """Return cosine similarity in [-1, 1], or 0.0 if either vector is None/empty."""
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        logger.warning(f"[N6] Vector length mismatch: {len(a)} vs {len(b)}")
        return 0.0
    na, nb = _norm(a), _norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _dot(a, b) / (na * nb)

# ── Scoring ───────────────────────────────────────────────────

def _score_activity(
    user_vectors: dict[str, Any],
    act_vectors: dict[str, Any],
    metadata: dict[str, Any],
    weights: dict[str, float],
) -> tuple[float, str]:
    """
    Compute the weighted similarity score for one activity.

    user_vectors keys expected  : text, aug_text, aug_tags, img_desc
    act_vectors  keys expected  : text, tag

    Returns (score: float, reason: str).
    """
    u_text     = user_vectors.get("text")
    u_aug_text = user_vectors.get("aug_text")
    u_aug_tags = user_vectors.get("aug_tags")
    u_img_desc = user_vectors.get("img_desc")

    act_text = act_vectors.get("text")
    act_aug_tags = act_vectors.get("aug_tags")

    # ── similarities ─────────────────────────────
    sim_text     = _cosine(u_text,     act_text)
    sim_aug_text = _cosine(u_aug_text, act_text)
    sim_aug_tags = _cosine(u_aug_tags, act_aug_tags)
    sim_img_desc = _cosine(u_img_desc, act_text)

    sem_score = (
        weights["text"]     * sim_text
        + weights["aug_text"] * sim_aug_text
        + weights["aug_tags"] * sim_aug_tags
        + weights["img_desc"] * sim_img_desc
    )
    score = max(0.0, sem_score)

    # ── simple logic processing (reason only) ──
    intensity = metadata.get("intensity")
    physical_level = metadata.get("physical_level")
    social_level = metadata.get("social_level")
    
    levels = []
    if intensity is not None: levels.append(float(intensity))
    if physical_level is not None: levels.append(float(physical_level))
    if social_level is not None: levels.append(float(social_level))
        
    avg_level = sum(levels) / len(levels) if levels else None

    # Build reason from signals that are active (weight > 0) and match well (sim >= 0.3)
    parts: list[str] = []
    
    text_sims = []
    if weights["text"] > 0 and sim_text >= 0.3:
        text_sims.append(sim_text)
    if weights["aug_text"] > 0 and sim_aug_text >= 0.3:
        text_sims.append(sim_aug_text)
    
    if text_sims:
        max_text_sim = max(text_sims)
        parts.append(f"phù hợp yêu cầu ({max_text_sim:.2f})")
    if weights["aug_tags"] > 0 and sim_aug_tags >= 0.3:
        parts.append(f"phù hợp sở thích ({sim_aug_tags:.2f})")
    if weights["img_desc"] > 0 and sim_img_desc >= 0.3:
        parts.append(f"hình ảnh tương đồng ({sim_img_desc:.2f})")
        
    if avg_level is not None:
        if avg_level >= 0.7:
            parts.append("cường độ cao")
        elif avg_level <= 0.3:
            parts.append("nhẹ nhàng thư giãn")
    
    reason = " · ".join(parts) if parts else "Hoạt động đề xuất"

    return round(float(score), 4), reason


# ── Public API ────────────────────────────────────────────────

def rank_activities(data: dict) -> dict:
    """
    N6 — Activity Ranking
    """
    text_k       = int(data.get("text_k", 0))
    tags_k       = int(data.get("tags_k", 0))
    user_vectors = data.get("user_vectors", {})
    activities   = data.get("activities", [])
    top_k        = max(1, int(data.get("top_k", 5)))

    if not activities:
        logger.warning("[N6] Không có hoạt động nào để xếp hạng")
        return {"activities": []}

    # ── resolve weights from text_k & tags_k ──────────────────
    weights = get_weights(text_k, tags_k)
    logger.info(f"Ranking {len(activities)} activities (signals: text_k={text_k}, tags_k={tags_k})")
    logger.info(f"Resolved weights: {weights}")

    scored: list[dict] = []
    for act in activities:
        act_id      = act.get("activity_id", "unknown")
        loc_id      = act.get("location_id", "unknown")
        act_vectors = act.get("vectors", {})
        metadata    = act.get("metadata", {})

        try:
            score, reason = _score_activity(user_vectors, act_vectors, metadata, weights)
        except Exception as exc:
            logger.warning("[N6] Lỗi tính điểm cho %s: %s", act_id, exc)
            score, reason = 0.0, "Lỗi tính điểm"

        scored.append({
            "activity_id": act_id,
            "location_id": loc_id,
            "score":       score,
            "reason":      reason,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    result = scored[:top_k]

    # ── normalize scores to 1.0 based on the top result ──
    if result and result[0]["score"] > 0:
        max_s = result[0]["score"]
        for r in result:
            r["score"] = round(r["score"] / max_s, 4)

    logger.info("[N6] Đã xếp hạng %d hoạt động → top %d (normalized)", len(activities), len(result))
    return {"activities": result}