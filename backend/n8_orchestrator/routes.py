from flask import request, jsonify, abort, Blueprint
from config import INTERNAL_API_KEY, PROTECTED_ROUTES, setup_logging
from .utils import _err, _get_json
from .services import recommend_service, activities_service, feedback_recommend_service, feedback_activities_service

logger = setup_logging("N8.routes")

bp = Blueprint("n8_routes", __name__)

@bp.before_app_request
def _check_internal_key():
    if request.path in PROTECTED_ROUTES:
        if request.headers.get("X-Internal-Key") != INTERNAL_API_KEY:
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

    if not body.get("text") and not body.get("tags"):
        return _err("Provide text or tags")

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
