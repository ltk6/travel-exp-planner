from __future__ import annotations
from flask import Blueprint, jsonify
from config import setup_logging
from backend.n8_orchestrator.services import get_all_locations_cached, _get_image_urls

logger = setup_logging("N8.locations")

locations_bp = Blueprint("locations", __name__)

# ── Service logic built-in ──

def explore_locations_service():
    locations = get_all_locations_cached()
    out = []
    for loc in locations:
        loc_id = loc.get("location_id")
        imgs = _get_image_urls(loc_id) if loc_id else []
        first_img = imgs[0] if imgs else None
        out.append({
            "location_id": loc_id,
            "metadata": loc.get("metadata"),
            "geo": loc.get("geo"),
            "image": first_img,
            "images_count": len(imgs),
        })
    return {"status": "success", "total": len(out), "data": out}

# ── Routes ──

@locations_bp.post("/locations")
def list_locations():
    """Slim list of all locations for Explore mode — không có vectors, mỗi loc kèm 1 ảnh đại diện."""
    try:
        result = explore_locations_service()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Explore locations failed: {e}")
        from backend.n8_orchestrator.utils import _err
        return _err(f"Internal error: {str(e)}", 500)
