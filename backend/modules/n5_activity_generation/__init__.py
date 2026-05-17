"""
─────────────────────────────────────────────
N5 — ACTIVITY GENERATION MODULE
─────────────────────────────────────────────

This module generates structured travel activities based on
selected locations and user preferences.

PURPOSE:
- Transform ranked locations into actionable activity suggestions
- Produce structured, constraint-aware activity plans
- Prepare downstream input for embedding (N6) and ranking systems

─────────────────────────────────────────────
INPUT (ASSUMED)
─────────────────────────────────────────────
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
                "tags": list[str] | None,
                "coordinates": {"lat": float, "lng": float} | None,  # optional
                "address": dict | None                                # optional
            }
        }
    ],

    "constraints": {
        "budget": float | None,
        "duration": float | None,
        "people": int | None,
        "time_of_day": str | None
    }
}

─────────────────────────────────────────────
OUTPUT — Unified Activity Schema
─────────────────────────────────────────────
Output tuân thủ schema chung tại:
    backend/modules/activity_retrievals/SCHEMA.md

Mỗi activity có cấu trúc:
{
    "activity_id":  "llm_{location_id}_{hash6}",
    "location_id":  str,
    "source":       "llm",
    "retrieved_at": "YYYY-MM-DDTHH:MM:SSZ",

    "metadata": {
        "name": str, "description": str,
        "activity_type":    "adventure|relaxation|food|culture|nightlife|nature|shopping",
        "activity_subtype": str | None,
        "categories_raw":   [],
        "estimated_duration":  float | None,    # minutes
        "price_level":         float | None,    # 0.0 → 1.0
        "indoor_outdoor":      "indoor|outdoor|mixed" | None,
        "weather_dependent":   bool | None,
        "time_of_day_suitable":"morning|afternoon|night|anytime" | None
    },

    "place":      { coordinates, distance_from_anchor_m, address },  # kế thừa anchor location
    "signals":    { rating, popularity, image_url, website, opening_hours, phone },  # all null cho LLM
    "provenance": { raw_source_id=None, source_url=None, raw={legacy_activity_id, metadata} }
}

─────────────────────────────────────────────
DESIGN NOTES:
- Activities are derived from locations, not independent entities.
- Constraint-aware (budget, duration, group size).
- Output đã pass `activity_retrievals.schema.validate()`.
- No embedding logic or ranking logic here (generation only).
─────────────────────────────────────────────
"""

from .n5_activity_generator import generate_activities
 
__all__ = ["generate_activities"]
 