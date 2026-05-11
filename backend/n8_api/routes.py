from flask import request, jsonify, abort, Blueprint
from config.settings import INTERNAL_API_KEY, PROTECTED_ROUTES, setup_logging
from .utils import _err, _get_json
from .services import recommend_service, activities_service

logger = setup_logging("N8.routes")

bp = Blueprint("n8_routes", __name__)

@bp.before_app_request
def _check_internal_key():
    if request.path in PROTECTED_ROUTES:
        if request.headers.get("X-Internal-Key") != INTERNAL_API_KEY:
            abort(401)

@bp.get("/health")
def health():
    # Lazy imports to prevent issues
    from modules.n5_activity_generation.providers import get_fallback_chain
    chain = get_fallback_chain()
    return jsonify({
        "status": "ok",
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
