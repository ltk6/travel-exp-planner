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

Weights are dynamically set based on sig_k (keyword expansion count).
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

# ── sig_k-based dynamic weights (see vector-usage-guide.md) ──
WEIGHT_TABLE = {
    0: {"text": 0.3, "aug_text": 0.0, "aug_tags": 0.5, "img_desc": 0.2},
    1: {"text": 0.1, "aug_text": 0.3, "aug_tags": 0.4, "img_desc": 0.2},
    2: {"text": 0.2, "aug_text": 0.2, "aug_tags": 0.4, "img_desc": 0.2},
    3: {"text": 0.3, "aug_text": 0.1, "aug_tags": 0.4, "img_desc": 0.2},
}


def _get_weights(sig_k: int) -> dict[str, float]:
    """
    Dynamic weights:
    - sig_k <= 3 → base table
    - sig_k 3→10 → aug_text decays NON-LINEAR from 0.1 → 0
    """
    base = WEIGHT_TABLE.get(min(sig_k, 3), WEIGHT_TABLE[0])

    if sig_k <= 3:
        return base

    start, end = 3, 10
    t = (sig_k - start) / (end - start)
    t = max(0.0, min(1.0, t))

    return {
        "text": base["text"],
        "aug_text": 0.1 * (1 - t) ** 3,
        "aug_tags": base["aug_tags"],
        "img_desc": base["img_desc"],
    }

# ── Helpers ───────────────────────────────────────────────────

from backend.shared.math import cosine as _cosine_shared


def _cosine(a: list[float] | None, b: list[float] | None) -> float:
    """Cosine similarity in [-1, 1], 0.0 nếu vector None/rỗng/khác length."""
    if a and b and len(a) != len(b):
        logger.warning("[N4] Vector length mismatch: %d vs %d", len(a), len(b))
    return _cosine_shared(a, b)


def _compute_weights(
    preprocessed_user_input: dict[str, Any],
    user_vectors: dict[str, Any],
) -> dict[str, float]:
    """
    Compute dynamic scoring weights based on preprocessed user channels.

    Three principles:
    1. Channel richness is measured by keyword count of each preprocessed string.
    2. Missing/empty vector channel -> its weight is forced to zero.
    3. All four weights normalize to sum = 1.0.

    Falls back to WEIGHTS if every signal is zero.
    """
    emotion_text = str(preprocessed_user_input.get("emotion") or "").strip()
    context_text = str(preprocessed_user_input.get("context") or "").strip()
    tag_text = str(preprocessed_user_input.get("tag") or "").strip()
    image_text = str(preprocessed_user_input.get("image") or "").strip()

    emotion_count = len(emotion_text.split()) if emotion_text else 0
    context_count = len(context_text.split()) if context_text else 0
    tag_count = len(tag_text.split()) if tag_text else 0
    image_count = len(image_text.split()) if image_text else 0

    raw_emotion = float(emotion_count)
    raw_context = float(context_count)
    raw_tag = float(tag_count)
    raw_image = float(image_count)

    # Zero out if the corresponding vector is missing or empty (N1 could not embed it).
    # `not v` is True for both None and [] — intentional: both mean "no usable vector".
    if not user_vectors.get("emotion"):
        raw_emotion = 0.0
    if not user_vectors.get("context"):
        raw_context = 0.0
    if not user_vectors.get("tag"):
        raw_tag = 0.0
    if not user_vectors.get("image"):
        raw_image = 0.0

    total = raw_emotion + raw_context + raw_tag + raw_image

    if total < 1e-9:
        logger.warning("[N4] Tất cả tín hiệu đầu vào đều rỗng — dùng trọng số cố định")
        return WEIGHTS.copy()

    weights = {
        "emotion": round(raw_emotion / total, 4),
        "context": round(raw_context / total, 4),
        "tag": round(raw_tag / total, 4),
        "image": round(raw_image / total, 4),
    }

    logger.info(
        "[N4] Dynamic weights | "
        "emotion=%.3f  context=%.3f  tag=%.3f  image=%.3f | "
        "emotion_kw=%d  context_kw=%d  tag_kw=%d  image_kw=%d",
        weights["emotion"], weights["context"], weights["tag"], weights["image"],
        emotion_count, context_count, tag_count, image_count,
    )
    return weights


# ── Scoring ───────────────────────────────────────────────────

def _constraint_penalty(
    metadata: dict[str, Any],
    constraints: dict[str, Any],
) -> tuple[float, list[str]]:
    """
    Compute a soft penalty multiplier in (0, 1] when location exceeds constraints.
    Returns (multiplier, penalty_notes).
    Soft (not hard filter): over-budget locations are penalised, not removed.
    """
    multiplier = 1.0
    notes: list[str] = []

    budget = constraints.get("budget")
    price_level = metadata.get("price_level")
    if budget and price_level and price_level > budget:
        multiplier *= 0.6
        notes.append(f"vượt ngân sách ({int(price_level):,} > {int(budget):,} VNĐ)")

    duration = constraints.get("duration")
    estimated = metadata.get("estimated_duration")
    if duration and estimated and estimated > duration:
        multiplier *= 0.7
        notes.append(f"vượt thời gian ({int(estimated)}h > {int(duration)}h)")

    return multiplier, notes


def _score_location(
    user_vectors: dict[str, Any],
    loc_vectors: dict[str, Any],
    weights: dict[str, float],
) -> tuple[float, str]:
    """
    Compute the weighted similarity score for one location.

    user_vectors keys expected  : text, aug_text, aug_tags, img_desc
    loc_vectors  keys expected  : text, tag

    Returns (score: float, reason: str).
    """
    u_text     = user_vectors.get("text")
    u_aug_text = user_vectors.get("aug_text")
    u_aug_tags = user_vectors.get("aug_tags")
    u_img_desc = user_vectors.get("img_desc")

    loc_text = loc_vectors.get("text")
    loc_tag  = loc_vectors.get("tag")

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
    score = max(0.0, min(1.0, score))

    # Apply constraint soft penalty when metadata and constraints are provided
    penalty_notes: list[str] = []
    if metadata and constraints:
        penalty, penalty_notes = _constraint_penalty(metadata, constraints)
        score = round(score * penalty, 4)

    # Build reason from signals that are active (weight > 0) and match well (sim >= 0.3)
    parts: list[str] = []
    if sim_text >= 0.3:
        parts.append(f"ý định rõ ({sim_text:.2f})")
    if sim_aug_text >= 0.3:
        parts.append(f"ngữ cảnh phù hợp ({sim_aug_text:.2f})")
    if sim_aug_tags >= 0.3:
        parts.append(f"sở thích khớp ({sim_aug_tags:.2f})")
    if sim_img_desc >= 0.3:
        parts.append(f"hình ảnh tương đồng ({sim_img_desc:.2f})")
    reason = " · ".join(parts) if parts else "Địa điểm phổ biến"

    return round(float(score), 4), reason


# ── Public API ────────────────────────────────────────────────

def rank_locations(data: dict) -> dict:
    """
    N4 — Location Ranking

    Input:
    {
        "sig_k": int,
        "user_vectors": {
            "text":     list[float] | None,
            "aug_text": list[float] | None,
            "aug_tags": list[float] | None,
            "img_desc": list[float] | None
        },
        "locations": [
            {
                "location_id": str,
                "location_vectors": {
                    "text": list[float],
                    "tag":  list[float]
                },
                "metadata": {                # optional — enables constraint penalty
                    "price_level":        int | None,  # VNĐ
                    "estimated_duration": int | None   # giờ
                },
                "geo": {}                    # received, not used in scoring
            }
        ],
        "constraints": {                     # optional — triggers soft penalty
            "budget":   float | None,
            "duration": float | None,
            "people":   int   | None
        },
        "top_k": int
    }

    Output:
    {
        "locations": [
            {
                "location_id": str,
                "score":       float,        # [0.0, 1.0], đã áp penalty nếu có
                "reason":      str
            }
        ]
    }
    """

    sig_k        = int(data.get("sig_k", 0))
    user_vectors = data.get("user_vectors", {})
    locations    = data.get("locations", [])
    constraints  = data.get("constraints") or {}
    top_k        = max(1, int(data.get("top_k", 5)))

    if not locations:
        logger.warning("[N4] Không có địa điểm nào để xếp hạng")
        return {"locations": []}

    # ── resolve weights from sig_k ───────────────────────────
    weights = _get_weights(sig_k)

    scored: list[dict] = []
    for loc in locations:
        loc_id      = loc.get("location_id", "unknown")
        loc_vectors = loc.get("location_vectors", {})
        metadata    = loc.get("metadata", {})

        try:
            score, reason = _score_location(user_vectors, loc_vectors, weights)
        except (KeyError, AssertionError):
            # Programmer bug (sai schema input) — re-raise để fail loud.
            raise
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            # Runtime data issue (vector length mismatch, NaN, …) — log + score 0.
            logger.warning("[N4] Lỗi tính điểm cho %s: %s: %s", loc_id, type(exc).__name__, exc)
            score, reason = 0.0, "Lỗi tính điểm"

        scored.append({
            "location_id": loc_id,
            "score":       score,
            "reason":      reason,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    result = scored[:top_k]

    logger.info("[N4] Đã xếp hạng %d địa điểm → top %d", len(locations), len(result))
    return {"locations": result}
