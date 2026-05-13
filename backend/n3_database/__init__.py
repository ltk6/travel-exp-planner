"""
─────────────────────────────────────────────
N3 — DATABASE LAYER
─────────────────────────────────────────────

SAVE LOCATION:
Input:
{
    "location_id": str,

    "vectors": {
        "text":     list[float] | None,
        "aug_text": list[float] | None,
        "aug_tags": list[float] | None,
        "img_desc": list[float] | None
    },

    "metadata": {
        "name":        str,
        "description": str,
        "tags":        list[str]
    },
    "geo": {
        "lat": float,
        "lng": float
    }
}

Output:
{
    "status": "success" | "error",
    "message": str (optional on error)
}

GET ALL LOCATIONS:
Output:
{
    "status": "success",
    "total": int,
    "data": [
        {
            "location_id": str,

            "vectors": {
                "text":     list[float] | None,
                "aug_text": list[float] | None,
                "aug_tags": list[float] | None,
                "img_desc": list[float] | None
            },

            "metadata": {
                "name":        str,
                "description": str,
                "tags":        list[str]
            },
            "geo": {
                "lat": float,
                "lng": float
            },
            
            "images": list[str] # base64 strings
        }
    ]
}
"""

from .db_manager import (
    init_db,
    save_location,
    get_all_locations,
)