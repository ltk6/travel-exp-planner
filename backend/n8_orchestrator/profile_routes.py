from flask import Blueprint, request, jsonify
from backend.n3_database.db_manager import save_user_profile, get_user_profile, init_profile_db

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/api/profile", methods=["POST"])
def api_save_profile():
    """Endpoint để lưu hoặc cập nhật profile"""
    data = request.json
    if not data or not data.get("user_id"):
        return jsonify({"status": "error", "message": "Thiếu user_id rồi ông ơi!"}), 400
        
    result = save_user_profile(data)
    return jsonify(result)

@profile_bp.route("/api/profile/<user_id>", methods=["GET"])
def api_get_profile(user_id):
    """Endpoint để tải thông tin profile lên frontend"""
    result = get_user_profile(user_id)
    if result["status"] == "error":
        return jsonify(result), 404
    return jsonify(result)