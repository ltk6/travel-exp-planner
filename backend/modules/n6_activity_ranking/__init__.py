"""
─────────────────────────────────────────────
N6 — ACTIVITY RANKING MODULE
─────────────────────────────────────────────

Ranks activities from N5 using:
  - semantic similarity (reuse N4-style weighted cosine on user/activity vectors)
  - attribute fit (intensity / physical_level / social_level + time_of_day)

User preferences on the 3 attribute axes are inferred rule-based from
`user_input` (tags + free text + image description). See `preferences.py`.

Score = 0.5 * semantic + 0.5 * attribute

─────────────────────────────────────────────
INPUT
─────────────────────────────────────────────
{
    "text_k": int,
    "tags_k": int,

    "user_input": {
        "text": str | None,
        "img_desc": str | None,
        "tags": list[str] | None
    },

    "user_vectors": {
        "text": list[float] | None,
        "aug_text": list[float] | None,
        "aug_tags": list[float] | None,
        "img_desc": list[float] | None
    },

    "context": {
        "time_of_day": str | None        # morning / afternoon / evening / anytime
    },

    "activities": [
        {
            "activity_id": str,
            "location_id": str,
            "metadata": {
                "name": str,
                "description": str,
                "activity_type": str,
                "activity_subtype": str | None,

                # 3 trục attribute dùng để match với user_prefs
                "intensity": float,
                "physical_level": float | None,
                "social_level": float | None,

                "estimated_duration": float,
                "price_level": float,
                "indoor_outdoor": str,
                "weather_dependent": bool,
                "time_of_day_suitable": str | None
            },
            "vectors": {
                "text": list[float] | None,
                "tag":  list[float] | None
            }
        }
    ],

    "top_k": int
}

NOTE: các field budget / duration / people / weather đã bị loại bỏ.

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
    ],
    "user_prefs": {                       # debug, optional
        "intensity": float | None,
        "physical":  float | None,
        "social":    float | None
    }
}
"""

from .rank_activities import rank_activities
from .preferences import infer_user_preferences

__all__ = ["rank_activities", "infer_user_preferences"]