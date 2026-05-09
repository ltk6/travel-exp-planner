from flask import jsonify, request

def err(msg: str, code: int = 400):
    """Return a JSON error response."""
    return jsonify({"error": msg}), code

def get_json():
    """Safely parse JSON from the request."""
    data = request.get_json(silent=True)
    if not data:
        return None, err("Invalid JSON body")
    return data, None

def safe_vec(v):
    """Ensure value is a Python list. Handles numpy arrays from pgvector."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    # Handle numpy-like objects
    if hasattr(v, 'tolist'):
        return v.tolist()
    try:
        return list(v)
    except (TypeError, ValueError):
        return []
