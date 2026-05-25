from flask import Blueprint, request, jsonify, abort, g
import time
import hashlib
import json
from threading import Lock
from config import INTERNAL_API_KEY, PROTECTED_ROUTES, setup_logging

logger = setup_logging("N8.routes")

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

# Import sub-blueprints to register them under main bp
from .recommend import recommend_bp
from .activities import activities_bp
from .locations import locations_bp
from .general import general_bp

bp.register_blueprint(recommend_bp)
bp.register_blueprint(activities_bp)
bp.register_blueprint(locations_bp)
bp.register_blueprint(general_bp)
