"""
─────────────────────────────────────────────
N4 — LOCATION RANKING MODULE
─────────────────────────────────────────────

Ranks travel locations using weighted cosine similarity between
user vectors (from N1) and location vectors (from N3).

It combines:
- User vectors from N1 (text/aug_text/aug_tags/img_desc)
- Location embeddings (text/tag)
- sig_k-based dynamic channel weighting

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

    "locations": [
        {
            "location_id": str,

            "location_vectors": {
                "text":     list[float] | None,
                "aug_tags": list[float] | None
            },

            "metadata": {
                "name":        str | None,
                "description": str | None,
                "tags":        list[str] | None
            },

            "geo": {
                "lat": float | None,
                "lng": float | None
            }
        }
    ],
    "top_k": int
}

─────────────────────────────────────────────
OUTPUT
─────────────────────────────────────────────
{
    "locations": [
        {
            "location_id": str,
            "score":       float,           # [0.0, 1.0], đã áp penalty nếu có
            "reason":      str              # giải thích tiếng Việt
        }
    ]
}

"""

from .rank_locations import rank_locations

__all__ = ["rank_locations"]
