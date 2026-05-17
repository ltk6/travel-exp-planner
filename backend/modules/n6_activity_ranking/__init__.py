"""
─────────────────────────────────────────────
N6 — ACTIVITY RANKING MODULE (MULTI-SIGNAL SCORING ENGINE)
─────────────────────────────────────────────

This module ranks generated activities (from N5) using precomputed
embeddings and structured metadata constraints.

PURPOSE:
- Rank candidate activities based on user intent and context
- Combine semantic similarity + constraint satisfaction
- Return top-k most relevant activities per user query

IMPORTANT:
- NO embedding generation
- NO activity creation
- ONLY scoring + ranking logic

─────────────────────────────────────────────
INPUT
─────────────────────────────────────────────
{
    # ───────── USER INPUT ─────────
    "user_input": {
        "text": str | None,
        "image_description": str | None,
        "tags": list[str] | None
    },

    # ───────── USER VECTORS ─────────
    "user_vectors": {
        "emotion": list[float] | None,
        "context": list[float] | None,
        "image": list[float] | None,
        "tag": list[float] | None
    },

    # ───────── CONTEXT ─────────
    "context": {
        "user_location": {
            "lat": float | None,
            "lng": float | None
        },
        "time_of_day": str | None
    },

    # ───────── ACTIVITIES (unified schema — xem activity_retrievals/SCHEMA.md) ─────────
    "activities": [
        {
            "activity_id": str,
            "location_id": str,
            "source": str,                                 # llm|osm|goong|foursquare|overture|wikidata|geoapify
            "retrieved_at": str,                           # ISO-8601 UTC

            "metadata": {
                "name": str,
                "description": str | None,
                "activity_type": str | None,               # adventure|relaxation|food|culture|nightlife|nature|shopping
                "activity_subtype": str | None,
                "categories_raw": list[str],
                "estimated_duration": float | None,        # minutes
                "price_level": float | None,               # 0.0 → 1.0
                "indoor_outdoor": str | None,              # indoor|outdoor|mixed
                "weather_dependent": bool | None,
                "time_of_day_suitable": str | None         # morning|afternoon|night|anytime
            },

            "place": {
                "coordinates": {"lat": float, "lng": float} | None,
                "distance_from_anchor_m": float | None,
                "address": {
                    "country": str | None, "region": str | None, "city": str | None,
                    "street": str | None, "formatted": str | None
                }
            },

            "signals": {
                "rating": float | None, "popularity": float | None,
                "image_url": str | None, "website": str | None,
                "opening_hours": str | None, "phone": str | None
            },

            "provenance": {
                "raw_source_id": str | None, "source_url": str | None, "raw": Any
            },

            # Bổ sung bởi N1 (embedding) TRƯỚC KHI vào N6 — không có trong unified
            # schema gốc của activity_retrievals. Nếu vectors=None/empty cho mọi
            # activity, semantic_score fallback 0.5 (sẽ log warning).
            "vectors": {
                "text": list[float] | None,
                "tag": list[float] | None,
                "intent": list[float] | None
            }
        }
    ],

    # ───────── CONSTRAINTS ─────────
    "constraints": {
        "budget": float | None,
        "duration": float | None,
        "people": int | None,
        "weather": str | None
    },

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

Constraint Scoring:
- budget fit penalty / boost
- duration fit alignment
- group size compatibility (if applicable)

Context Scoring:
- time_of_day match
- weather_dependency alignment
- indoor/outdoor preference alignment

Geographic influence (optional):
- derived from location layer (if propagated)

─────────────────────────────────────────────
DESIGN PRINCIPLES
─────────────────────────────────────────────
- Fully deterministic scoring
- Missing vectors must be safely ignored (no failure propagation)
- No generation or embedding logic
- Explainable output via reason field
- Shared scoring architecture with N4 but activity-specialized signals
─────────────────────────────────────────────
"""

from .rank_activities import rank_activities

__all__ = ["rank_activities"]