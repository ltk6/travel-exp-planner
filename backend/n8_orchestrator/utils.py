from flask import jsonify, request

def _err(msg: str, code: int = 400):
    if code >= 500:
        msg = "An internal server error occurred."
    return jsonify({"error": msg}), code

def _get_json():
    data = request.get_json(silent=True)
    if not data:
        return None, _err("Invalid JSON body")
    return data, None

def _safe_vec(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if hasattr(v, 'tolist'):
        return v.tolist()
    try:
        return list(v)
    except (TypeError, ValueError):
        return []
