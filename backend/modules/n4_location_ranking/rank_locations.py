"""
rank_locations.py
=================
N4 — Location Ranking Module

Ranks locations by computing weighted cosine similarity between
user vectors (from N1) and location vectors (from DB/N3).

Scoring channels (user → location):
    text      → text : raw intent match
    aug_text  → text : expanded semantic match
    aug_tags  → tag  : tag-based anchor
    img_desc  → text : visual alignment

Weights are resolved dynamically using shared/weights.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from config import setup_logging
logger = setup_logging("N4")

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
        logger.warning(f"[N4] Vector length mismatch: {len(a)} vs {len(b)}")
        return 0.0
    na, nb = _norm(a), _norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _dot(a, b) / (na * nb)

# ── Scoring ───────────────────────────────────────────────────

def _score_location(
    user_vectors: dict[str, Any],
    loc_vectors: dict[str, Any],
    weights: dict[str, float],
) -> tuple[float, str]:
    """
    Compute the weighted similarity score for one location.

    user_vectors keys expected  : text, aug_text, aug_tags, img_desc
    loc_vectors  keys expected  : text, aug_tags

    Returns (score: float, reason: str).
    """
    u_text     = user_vectors.get("text")
    u_aug_text = user_vectors.get("aug_text")
    u_aug_tags = user_vectors.get("aug_tags")
    u_img_desc = user_vectors.get("img_desc")

    loc_text = loc_vectors.get("text")
    loc_tag  = loc_vectors.get("aug_tags")

    # ── similarities ─────────────────────────────
    sim_text     = _cosine(u_text,     loc_text)
    sim_aug_text = _cosine(u_aug_text, loc_text)
    sim_aug_tags = _cosine(u_aug_tags, loc_tag)
    sim_img_desc = _cosine(u_img_desc, loc_text)

    score = (
        weights["text"]     * sim_text
        + weights["aug_text"] * sim_aug_text
        + weights["aug_tags"] * sim_aug_tags
        + weights["img_desc"] * sim_img_desc
    )
    score = max(0.0, score)

    # Build reason from signals that are active (weight > 0) and match well (sim >= 0.3)
    parts: list[str] = []
    
    # Merge text and aug_text into a single "content" reason
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
    
    reason = " · ".join(parts) if parts else "Địa điểm phổ biến"

    return round(float(score), 4), reason


# ── Public API ────────────────────────────────────────────────

def rank_locations(data: dict) -> dict:
    import time
    t0 = time.time()
    
    text_k       = int(data.get("text_k", 0))
    tags_k       = int(data.get("tags_k", 0))
    user_vectors = data.get("user_vectors", {})
    locations    = data.get("locations", [])
    top_k        = max(1, int(data.get("top_k", 5)))

    if not locations:
        logger.warning("[N4] Không có địa điểm nào để xếp hạng")
        return {"locations": [], "metadata": {"text_k": text_k, "tags_k": tags_k, "latency_ms": 0}}

    # ── resolve weights from text_k & tags_k ──────────────────
    weights = get_weights(text_k, tags_k)
    logger.info(f"Ranking {len(locations)} locations (signals: text_k={text_k}, tags_k={tags_k})")
    logger.info(f"Resolved weights: {weights}")

    scored: list[dict] = []
    for loc in locations:
        loc_id      = loc.get("location_id", "unknown")
        loc_vectors = loc.get("location_vectors", {})

        try:
            score, reason = _score_location(user_vectors, loc_vectors, weights)
        except Exception as exc:
            logger.warning("[N4] Lỗi tính điểm cho %s: %s", loc_id, exc)
            score, reason = 0.0, "Lỗi tính điểm"

        scored.append({
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

    elapsed_ms = int((time.time() - t0) * 1000)
    logger.info("[N4] Đã xếp hạng %d địa điểm → top %d (normalized) in %dms", len(locations), len(result), elapsed_ms)
    
    return {
        "locations": result,
        "metadata": {
            "text_k": text_k,
            "tags_k": tags_k,
            "weights": weights,
            "latency_ms": elapsed_ms
        }
    }
