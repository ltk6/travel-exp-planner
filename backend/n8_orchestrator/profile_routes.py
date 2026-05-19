from flask import Blueprint, request, jsonify
from backend.n3_database.db_manager import register_user, login_user, save_rec_turn, get_user_history

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"status": "error", "message": "Thieu username hoac password"}), 400
    res = register_user(username, password)
    return jsonify(res)

@profile_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"status": "error", "message": "Thieu username hoac password"}), 400
    res = login_user(username, password)
    return jsonify(res)

@profile_bp.route("/api/profile/history", methods=["POST"])
def api_save_history():
    """Endpoint chi de save len database sau moi lan rec"""
    data = request.json or {}
    user_id = data.get("user_id")
    input_data = data.get("input_data")
    output_data = data.get("output_data")
    
    if not user_id or not input_data or not output_data:
        return jsonify({"status": "error", "message": "Thieu parameters luu lich su"}), 400
        
    res = save_rec_turn(user_id, input_data, output_data)
    return jsonify(res)

@profile_bp.route("/api/profile/history/<int:user_id>", methods=["GET"])
def api_get_history(user_id):
    """Endpoint lay toan bo data cu, goi ra sau khi dang nhap thanh cong"""
    res = get_user_history(user_id)
    return jsonify(res)