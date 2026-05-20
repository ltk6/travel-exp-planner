from flask import Blueprint, request, jsonify
from backend.n3_database.db_manager import register_user, login_user, save_rec_turn, get_user_history
from backend.shared.contracts.n3_contracts import N3RegisterInput, N3LoginInput, N3SaveHistoryInput

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"status": "error", "message": "Thieu username hoac password"}), 400
    validated = N3RegisterInput.model_validate({"username": username, "password": password})
    res = register_user(validated.username, validated.password)
    return jsonify(res)

@profile_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"status": "error", "message": "Thieu username hoac password"}), 400
    validated = N3LoginInput.model_validate({"username": username, "password": password})
    res = login_user(validated.username, validated.password)
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

    validated = N3SaveHistoryInput.model_validate({
        "user_id": user_id,
        "input_data": input_data,
        "output_data": output_data,
    })
    res = save_rec_turn(validated.user_id, validated.input_data, validated.output_data)
    return jsonify(res)

@profile_bp.route("/api/profile/history/<int:user_id>", methods=["GET"])
def api_get_history(user_id):
    """Endpoint lay toan bo data cu, goi ra sau khi dang nhap thanh cong"""
    res = get_user_history(user_id)
    return jsonify(res)