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
from typing import Any, Union
from backend.shared.contracts.n4_contracts import N4RankInput

from config import setup_logging
logger = setup_logging("N4")

from backend.shared.weights import get_weights

# ── Helpers ───────────────────────────────────────────────────

from backend.shared.math import cosine as _cosine_shared


def _cosine(a: list[float] | None, b: list[float] | None) -> float:
    """Cosine similarity in [-1, 1]; returns 0.0 if either vector is None, empty, or different length."""
    if a and b and len(a) != len(b):
        logger.warning("[N4] Vector length mismatch: %d vs %d", len(a), len(b))
    return _cosine_shared(a, b)

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
    # Graceful Fallback: if location has no tag vector, compare user's tag against location text!
    safe_loc_tag = loc_tag if loc_tag else loc_text
    
    sim_text     = _cosine(u_text,     loc_text)
    sim_aug_text = _cosine(u_aug_text, loc_text)
    sim_aug_tags = _cosine(u_aug_tags, safe_loc_tag)
    sim_img_desc = _cosine(u_img_desc, loc_text)

    # ── Normalize weights based on active channels ───────────────────
    active_weights = {}
    sum_w = 0.0
    for key, vec in [("text", u_text), ("aug_text", u_aug_text), ("aug_tags", u_aug_tags), ("img_desc", u_img_desc)]:
        if vec:
            w = weights.get(key, 0.0)
            active_weights[key] = w
            sum_w += w
        else:
            active_weights[key] = 0.0

    if sum_w > 0:
        for k in active_weights:
            active_weights[k] /= sum_w
    else:
        active_weights = {"text": 1.0, "aug_text": 0.0, "aug_tags": 0.0, "img_desc": 0.0}

    score = (
        active_weights["text"]     * sim_text
        + active_weights["aug_text"] * sim_aug_text
        + active_weights["aug_tags"] * sim_aug_tags
        + active_weights["img_desc"] * sim_img_desc
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
        parts.append(f"Phù hợp văn bản tự do ({max_text_sim:.2f})")
    if weights["aug_tags"] > 0 and sim_aug_tags >= 0.3:
        parts.append(f"Phù hợp trắc nghiệm ({sim_aug_tags:.2f})")
    if weights["img_desc"] > 0 and sim_img_desc >= 0.3:
        parts.append(f"Phù hợp hình ảnh ({sim_img_desc:.2f})")
    
    reason = " · ".join(parts) if parts else "Địa điểm phổ biến"

    return round(float(score), 4), reason


# ── Public API ────────────────────────────────────────────────

def rank_locations(data: Union[N4RankInput, dict[str, Any]]) -> dict[str, Any]:
    import time
    t0 = time.time()
    
    validated = N4RankInput.model_validate(data) if isinstance(data, dict) else data
    
    text_k       = validated.text_k
    tags_k       = validated.tags_k
    user_vectors = validated.user_vectors.model_dump()
    locations    = validated.locations
    top_k        = max(1, validated.top_k)

    if not locations:
        logger.warning("[N4] No locations to rank")
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
        except (KeyError, AssertionError):
            # Programmer bug (sai schema input) — re-raise để fail loud.
            raise
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            # Runtime data issue (vector length mismatch, NaN, …) — log + score 0.
            logger.warning("[N4] Scoring error for %s: %s: %s", loc_id, type(exc).__name__, exc)
            score, reason = 0.0, "Scoring error"

        scored.append({
            "location_id": loc_id,
            "score":       score,
            "reason":      reason,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    result = scored[:top_k]

    # ── Absolute Smoothstep Dead-Zone Scaling ──
    if result:
        for r in result:
            norm = float(r["score"])  # Absolute score in [0, 1]
            # Smoothstep (3x^2 - 2x^3) adds dead-zones at 0.0 and 1.0, stretching the middle
            shaped = 3 * (norm ** 2) - 2 * (norm ** 3)
            r["score"] = round(0.65 + shaped * 0.30, 4)

    elapsed_ms = int((time.time() - t0) * 1000)
    logger.info("[N4] Ranked %d locations → top %d (normalized) in %dms", len(locations), len(result), elapsed_ms)
    
    return {
        "locations": result,
        "metadata": {
            "text_k": text_k,
            "tags_k": tags_k,
            "weights": weights,
            "latency_ms": elapsed_ms
        }
    }
