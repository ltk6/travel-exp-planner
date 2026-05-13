"""
─────────────────────────────────────────────
N5 — ACTIVITY GENERATION MODULE
─────────────────────────────────────────────

─────────────────────────────────────────────
INPUT
─────────────────────────────────────────────
{
    "user": {
        "text": str | None,
        "img_desc": str | None,
        "tags": list[str] | None
    },

    "locations": [
        {
            "location_id": str,
            "metadata": {
                "name": str | None,
                "description": str | None,
                "tags": list[str] | None
            }
        }
    ],
}

─────────────────────────────────────────────
OUTPUT
─────────────────────────────────────────────
{
    "activities": [
        {
            "activity_id": str,
            "location_id": str,

            "metadata": {
                "name": str,
                "description": str,
                "tags": list[str],
                # strictly follows backend/shared/maps/tags.py

                "activity_type": str,
                # list of available activity types:
                # adventure / relaxation / food / culture / nightlife
                # nature / shopping / wellness / entertainment
                # sports / sightseeing / social / family

                "intensity": float,
                # 0.0 (very chill) → 1.0 (very active)

                "physical_level": float | None,
                # 0.0  → 1.0 (very physically demanding)
                
                "social_level": float | None,
                # 0.0 (solo) → 1.0 (group-oriented)
            }
        }
    ]
}
"""

from .n5_activity_generator import generate_activities
 
__all__ = ["generate_activities"]
 