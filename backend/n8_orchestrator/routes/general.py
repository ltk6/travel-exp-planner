from __future__ import annotations
import os
from flask import Blueprint, request, jsonify, Response, abort
from config import GROQ_API_KEY, setup_logging
from backend.n8_orchestrator.services import IMG_CACHE_DIR, get_all_locations_cached

logger = setup_logging("N8.general")

general_bp = Blueprint("general", __name__)

# ── Routes ──

@general_bp.get("/health")
def health():
    from modules.n5_activity_generation.providers import get_llm_chain
    
    # 1. Check N1 Embedding
    try:
        from modules.n1_embedding.embedder import get_model
        n1_status = "ok" if get_model() is not None else "not_loaded"
    except Exception as e:
        logger.error("N1 embedding model failed to load: %s", e)
        n1_status = "error"

    # 2. Check N3 Database
    try:
        from n3_database.db_manager import _get_connection
        conn = _get_connection()
        conn.close()
        n3_status = "db_connected"
    except Exception:
        n3_status = "file_storage"

    # 3. Check LLMs availability
    llms_available = bool(GROQ_API_KEY)

    chain = get_llm_chain()
    return jsonify({
        "status": "ok",
        "services": {
            "n1_embedding": n1_status,
            "n3_database": n3_status,
            "llms_available": llms_available
        },
        "pipeline": ["n1", "n2", "n3", "n4", "n5", "n6"],
        "llm_chain": [{"name": p.name, "model": p.model, "rpm_limit": p.rpm_limit} for p in chain],
    })

@general_bp.get("/api/images/<path:filename>")
def serve_image(filename):
    """Serve location images from N8's local disk cache, falling back to PostgreSQL and caching on-the-fly."""
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        abort(400)
    
    file_path = os.path.join(IMG_CACHE_DIR, filename)
    
    # 1. Check local disk cache
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            return Response(img_bytes, mimetype="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
        except Exception as e:
            logger.warning(f"Failed to read image from local cache {filename}: {e}")

    # 2. Cache miss: Fetch from PostgreSQL database
    try:
        base = filename.rsplit(".", 1)[0]
        if "_" not in base:
            abort(404)
        location_id, idx_str = base.rsplit("_", 1)
        idx = int(idx_str)
        
        from backend.n3_database import get_location_image_by_index
        img_bytes = get_location_image_by_index(location_id, idx)
        if not img_bytes:
            transparent_1x1 = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
            return Response(transparent_1x1, mimetype="image/png")
            
        try:
            os.makedirs(IMG_CACHE_DIR, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(img_bytes)
        except Exception as e:
            logger.warning(f"Failed to write image to local cache {filename}: {e}")
            
        return Response(img_bytes, mimetype="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        logger.error(f"Lỗi serve ảnh lazy: {e}")
        abort(500)

@general_bp.post("/cache/reset")
def reset_cache():
    """Manual trigger to force cache refresh."""
    get_all_locations_cached(force_refresh=True)
    return jsonify({"status": "success", "message": "Cache successfully refreshed from N3"})

@general_bp.get("/cache/fingerprint")
def get_fingerprint():
    """Check current DB version fingerprint."""
    from n3_database.db_manager import get_db_fingerprint
    return jsonify({"fingerprint": get_db_fingerprint()})
