"""
─────────────────────────────────────────────
N6 — ACTIVITY RANKING MODULE (MULTI-SIGNAL SCORING ENGINE)
─────────────────────────────────────────────

This module ranks generated activities (from N5) using precomputed
embeddings and simple metadata processing.

PURPOSE:
- Rank candidate activities based on user intent
- Combine semantic similarity + simple level processing
- Return top-k most relevant activities per user query

IMPORTANT:
- NO embedding generation
- NO activity creation
- ONLY scoring + ranking logic

─────────────────────────────────────────────
INPUT
─────────────────────────────────────────────
{
    "text_k": int,
    "tags_k": int,

    # ───────── USER VECTORS ─────────
    "user_vectors": {
        "text": list[float] | None,
        "aug_text": list[float] | None,
        "aug_tags": list[float] | None,
        "img_desc": list[float] | None
    },

    # ───────── ACTIVITIES ─────────
    "activities": [
        {
            "activity_id": str,
            "location_id": str,

            "metadata": {
                "intensity":      float,
                "physical_level": float | None,
                "social_level":   float | None
            },

            "vectors": {
                "text": list[float] | None,
                "aug_tags": list[float] | None,
            }
        }
    ],

    "top_k": int
}

─────────────────────────────────────────────
OUTPUT
─────────────────────────────────────────────
{
    "activities": [
        {
            "activity_id": str,
            "location_id": str,
            "score": float,
            "reason": str
        }
    ]
}

─────────────────────────────────────────────
SCORING DESIGN (HIGH LEVEL)
─────────────────────────────────────────────
Semantic Matching:
- user_vectors ↔ activity_vectors (text/tag/intent)
- weighted cosine similarity fusion

Activity Levels Scoring:
- intensity / physical_level / social_level combined to influence the score slightly

─────────────────────────────────────────────
DESIGN PRINCIPLES
─────────────────────────────────────────────
- Fully deterministic scoring
- Missing vectors must be safely ignored (no failure propagation)
- No generation or embedding logic
- Explainable output via reason field
- Shared scoring architecture with N4
─────────────────────────────────────────────
"""

from .rank_activities import rank_activities

__all__ = ["rank_activities"]