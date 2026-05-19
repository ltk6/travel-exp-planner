from flask import request, jsonify, abort, Blueprint, g, send_from_directory, Response
import time
from config import INTERNAL_API_KEY, PROTECTED_ROUTES, setup_logging
from .utils import _err, _get_json
from .services import (
    recommend_service,
    activities_service,
    activities_v2_service,
    feedback_recommend_service,
    feedback_activities_service,
    explore_locations_service,
    IMG_CACHE_DIR,
)

logger = setup_logging("N8.routes")

import hashlib
import json
from threading import Lock

_active_requests = set()
_active_requests_lock = Lock()

bp = Blueprint("n8_routes", __name__)

@bp.before_request
def _before():
    g.start_time = time.time()
    
    # Idempotency / Request Deduplication for POST methods (skip cache reset etc.)
    if request.method == "POST" and request.path not in ["/cache/reset", "/feedback/recommend", "/feedback/activities"]:
        try:
            body = request.get_json(silent=True) or {}
            # Ignore volatile or very large fields if needed, but standard payload works perfectly
            serialized = json.dumps(body, sort_keys=True)
            val = f"{request.path}:{serialized}".encode("utf-8")
            fp = hashlib.sha256(val).hexdigest()
            g.request_fingerprint = fp
            
            with _active_requests_lock:
                if fp in _active_requests:
                    logger.warning(f"⚠️ Duplicate request detected! Path: {request.path} (Fingerprint: {fp[:12]})")
                    return jsonify({"error": "Duplicate request in progress"}), 409
                _active_requests.add(fp)
        except Exception as e:
            logger.warning(f"Failed to calculate request fingerprint: {e}")

@bp.after_request
def _after(response):
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        logger.info(f"[{request.method}] {request.path} took {duration:.4f}s")
    return response

@bp.teardown_request
def _teardown(exception=None):
    fp = getattr(g, "request_fingerprint", None)
    if fp:
        with _active_requests_lock:
            _active_requests.discard(fp)

@bp.before_app_request
def _check_internal_key():
    import hmac
    if request.path in PROTECTED_ROUTES:
        provided = request.headers.get("X-Internal-Key") or ""
        if not hmac.compare_digest(provided, INTERNAL_API_KEY):
            abort(401)

@bp.get("/health")
def health():
    from modules.n5_activity_generation.providers import get_llm_chain
    from config import GROQ_API_KEY
    
    # 1. Check N1 Embedding
    try:
        from modules.n1_embedding.embedder import get_model
        n1_status = "ok" if get_model() is not None else "not_loaded"
    except Exception as e:
        n1_status = f"error: {str(e)}"

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

@bp.post("/recommend")
def recommend():
    body, err = _get_json()
    if err: return err

    if not body.get("text") and not body.get("tags") and not body.get("image") and not body.get("images") and not body.get("img_desc"):
        return _err("Provide text, tags, or image")

    try:
        result = recommend_service(body)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Recommend service failed: {e}")
        return _err(f"Internal error: {str(e)}", 500)

@bp.post("/activities")
def get_activities():
    body = request.get_json() or {}
    if not body.get("location"):
        return _err("Missing location data")

    try:
        result = activities_service(body)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Activities service failed: {e}")
        return _err(f"Internal error: {str(e)}", 500)

@bp.post("/activities/v2")
def get_activities_v2():
    """v2: N9-N14 processor (real map sources) instead of N5 LLM gen.
    Same request/response contract as /activities for drop-in A/B testing."""
    body = request.get_json() or {}
    if not body.get("location"):
        return _err("Missing location data")
    try:
        result = activities_v2_service(body)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Activities v2 service failed: {e}")
        return _err(f"Internal error: {str(e)}", 500)


@bp.post("/locations")
def list_locations():
    """Slim list of all locations for Explore mode — không có vectors, mỗi loc kèm 1 ảnh đại diện."""
    try:
        result = explore_locations_service()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Explore locations failed: {e}")
        return _err(f"Internal error: {str(e)}", 500)

@bp.get("/api/images/<path:filename>")
def serve_image(filename):
    """Serve location images directly from PostgreSQL on demand (lazy-fetch).
    Public (not in PROTECTED_ROUTES) so <img src=...> works without auth header.
    Browser caches via max_age. Returns transparent pixel fallback if not found."""
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        abort(400)
    try:
        base = filename.rsplit(".", 1)[0]
        if "_" not in base:
            abort(404)
        location_id, idx_str = base.rsplit("_", 1)
        idx = int(idx_str)
        
        from backend.n3_database import get_location_image_by_index
        img_bytes = get_location_image_by_index(location_id, idx)
        if not img_bytes:
            # 1x1 transparent PNG fallback
            transparent_1x1 = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
            return Response(transparent_1x1, mimetype="image/png")
            
        return Response(img_bytes, mimetype="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        logger.error(f"Lỗi serve ảnh lazy: {e}")
        abort(500)


@bp.post("/cache/reset")
def reset_cache():
    """Manual trigger to force cache refresh."""
    from .services import get_all_locations_cached
    get_all_locations_cached(force_refresh=True)
    return jsonify({"status": "success", "message": "Cache successfully refreshed from N3"})

@bp.get("/cache/fingerprint")
def get_fingerprint():
    """Check current DB version fingerprint."""
    from n3_database.db_manager import get_db_fingerprint
    return jsonify({"fingerprint": get_db_fingerprint()})

@bp.post("/feedback/recommend")
def feedback_recommend():
    body, err = _get_json()
    if err: return err
    if not body.get("feedback"): return _err("Missing feedback text")
    try:
        result = feedback_recommend_service(body)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Feedback recommend failed: {e}")
        return _err(f"Internal error: {str(e)}", 500)

@bp.post("/feedback/activities")
def feedback_activities():
    body, err = _get_json()
    if err: return err
    if not body.get("feedback"): return _err("Missing feedback text")
    try:
        result = feedback_activities_service(body)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Feedback activities failed: {e}")
        return _err(f"Internal error: {str(e)}", 500)
