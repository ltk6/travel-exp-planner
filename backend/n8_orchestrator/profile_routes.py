from flask import Blueprint, request, jsonify
from itsdangerous import URLSafeTimedSerializer
from config import INTERNAL_API_KEY
from backend.n3_database.db_manager import register_user, login_user, save_rec_turn, get_user_history
from backend.shared.contracts.n3_contracts import N3RegisterInput, N3LoginInput, N3SaveHistoryInput

profile_bp = Blueprint("profile", __name__)

# Use INTERNAL_API_KEY from global configs for signing tokens
SECRET_KEY = INTERNAL_API_KEY if INTERNAL_API_KEY else "default-travel-secret-key-1823901"
serializer = URLSafeTimedSerializer(SECRET_KEY)

def generate_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})

def verify_token(token: str) -> int:
    # Set max_age to 30 days
    data = serializer.loads(token, max_age=2592000)
    return int(data["user_id"])

@profile_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"status": "error", "message": "Thieu username hoac password"}), 400
    validated = N3RegisterInput.model_validate({"username": username, "password": password})
    res = register_user(validated.username, validated.password)
    if res.get("status") == "success" and "user_id" in res:
        res["token"] = generate_token(res["user_id"])
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
    if res.get("status") == "success" and "user_id" in res:
        res["token"] = generate_token(res["user_id"])
    return jsonify(res)

@profile_bp.route("/api/feedback", methods=["POST"])
def api_save_app_feedback():
    """Submit general app feedback from guests or logged in users."""
    data = request.json or {}
    name = data.get("name", "")
    email = data.get("email", "")
    content = data.get("content", "")

    if not content or not content.strip():
        return jsonify({"status": "error", "message": "Nội dung feedback không được để trống"}), 400

    from backend.n3_database.db_manager import save_app_feedback
    res = save_app_feedback(name, email, content)
    return jsonify(res)

@profile_bp.route("/api/profile/history", methods=["POST"])
def api_save_history():
    """Endpoint chi de save len database sau moi lan rec"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"status": "error", "message": "Yêu cầu đăng nhập để lưu lịch sử"}), 401
    
    token = auth_header.split(" ")[1]
    try:
        token_user_id = verify_token(token)
    except Exception:
        return jsonify({"status": "error", "message": "Token không hợp lệ hoặc đã hết hạn"}), 401

    data = request.json or {}
    user_id = data.get("user_id")
    input_data = data.get("input_data")
    output_data = data.get("output_data")
    history_id = data.get("history_id")

    if not user_id or not input_data or not output_data:
        return jsonify({"status": "error", "message": "Thieu parameters luu lich su"}), 400

    if int(user_id) != token_user_id:
        return jsonify({"status": "error", "message": "Không có quyền lưu lịch sử cho người dùng này"}), 403

    validated = N3SaveHistoryInput.model_validate({
        "user_id": user_id,
        "input_data": input_data,
        "output_data": output_data,
        "history_id": history_id,
    })
    res = save_rec_turn(validated.user_id, validated.input_data, validated.output_data, validated.history_id)
    return jsonify(res)

@profile_bp.route("/api/profile/history/<int:user_id>", methods=["GET"])
def api_get_history(user_id):
    """Endpoint lay toan bo data cu, goi ra sau khi dang nhap thanh cong"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"status": "error", "message": "Yêu cầu đăng nhập để xem lịch sử"}), 401
    
    token = auth_header.split(" ")[1]
    try:
        token_user_id = verify_token(token)
    except Exception:
        return jsonify({"status": "error", "message": "Token không hợp lệ hoặc đã hết hạn"}), 401

    if user_id != token_user_id:
        return jsonify({"status": "error", "message": "Không có quyền xem lịch sử của người dùng này"}), 403

    res = get_user_history(user_id)
    return jsonify(res)