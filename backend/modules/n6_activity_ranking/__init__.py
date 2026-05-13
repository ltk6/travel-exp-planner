"""
─────────────────────────────────────────────
N6 — ACTIVITY RANKING MODULE
─────────────────────────────────────────────

─────────────────────────────────────────────
INPUT
─────────────────────────────────────────────
{
    "text_k": int,
    "tags_k": int,

    "user_vectors": {
        "text":     list[float] | None,
        "aug_text": list[float] | None,
        "aug_tags": list[float] | None,
        "img_desc": list[float] | None
    },

    "activities": [
        {
            "activity_id": str,
            "location_id": str,
            "metadata": {
                "name": str,
                "description": str,
                "tags": list[str],

                "activity_type": str,

                "intensity": float,
                "physical_level": float | None,
                "social_level": float | None,
            },
            "vectors": {
                "text":     list[float] | None,
                "aug_tags": list[float] | None
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