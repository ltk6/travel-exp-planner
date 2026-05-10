import os
import json
import logging
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
import base64

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("N3")

from config.settings import PG_URI
def _get_connection():
    """Tạo kết nối DB và đăng ký kiểu vector."""
    conn = psycopg2.connect(PG_URI, cursor_factory=RealDictCursor)
    conn.autocommit = True
    register_vector(conn) # Chỉ đăng ký, không CREATE EXTENSION ở đây nữa
    return conn

def init_db():
    """Khởi tạo cấu trúc Database ban đầu."""
    conn = _get_connection()
    cur = conn.cursor()
    
    # Chuyển CREATE EXTENSION vào đây (chỉ chạy 1 lần)
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    cur.execute("DROP TABLE IF EXISTS users;")
    cur.execute("DROP TABLE IF EXISTS locations;")
    
    # ── USERS ────────────────────────────────
    cur.execute("""
        CREATE TABLE users (
            user_id VARCHAR(255) PRIMARY KEY,

            text vector(1024),
            aug_text vector(1024),
            aug_tags vector(1024),
            img_desc vector(1024),

            metadata JSONB,
            constraints JSONB
        );
    """)

    # ── LOCATIONS ────────────────────────────
    cur.execute("""
        CREATE TABLE locations (
            location_id VARCHAR(255) PRIMARY KEY,

            text vector(1024),
            aug_text vector(1024),
            aug_tags vector(1024),
            img_desc vector(1024),

            metadata JSONB,
            geo JSONB
        );
    """)

    cur.close()
    conn.close()
    logger.info("✨ Khởi tạo DB thành công.")

def _format_vectors(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert flat DB columns → unified vectors dict."""
    return {
        "text": row.get("text"),
        "aug_text": row.get("aug_text"),
        "aug_tags": row.get("aug_tags"),
        "img_desc": row.get("img_desc")
    }

def _attach_image(location_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Hàm nội bộ gắn actual image (base64) thay vì path."""
    loc_id = location_dict.get("location_id")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    encoded_images = []
    
    for i in range(1, 4):
        img_path = os.path.join(current_dir, "images", f"{loc_id}_{i}.jpg")
        if os.path.exists(img_path):
            try:
                with open(img_path, "rb") as f:
                    b64_str = base64.b64encode(f.read()).decode("utf-8")
                    encoded_images.append(f"data:image/jpeg;base64,{b64_str}")
            except Exception as e:
                logger.warning(f"Lỗi đọc ảnh {img_path}: {e}")
        else:
            # Fallback path if we want to keep structure but file is missing
            pass

    if encoded_images:
        location_dict["images"] = encoded_images
    else:
        location_dict["images"] = []

    return location_dict

def save_location(location_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lưu dữ liệu địa điểm vào Database.
    Input: dict chứa location_id, vector, metadata, geo.
    Output: dict chứa status và location_id.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()

        vectors = location_data.get("vectors", {})

        cur.execute("""
            INSERT INTO locations (
                location_id,
                text,
                aug_text,
                aug_tags,
                img_desc,
                metadata,
                geo
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (location_id)
            DO UPDATE SET
                text = EXCLUDED.text,
                aug_text = EXCLUDED.aug_text,
                aug_tags = EXCLUDED.aug_tags,
                img_desc = EXCLUDED.img_desc,
                metadata = EXCLUDED.metadata,
                geo = EXCLUDED.geo;
        """,
        (
            location_data.get("location_id"),

            vectors.get("text"),
            vectors.get("aug_text"),
            vectors.get("aug_tags"),
            vectors.get("img_desc"),

            json.dumps(location_data.get("metadata", {})),
            json.dumps(location_data.get("geo", {})),
        ))

        conn.close()

        return {
            "status": "success",
            "location_id": location_data.get("location_id")
        }

    except Exception as e:
        logger.error(f"Lỗi lưu Location: {e}")
        return {"status": "error", "message": str(e)}

def get_all_locations() -> Dict[str, Any]:
    """
    Lấy toàn bộ danh sách địa điểm.
    Input: Không có (hoặc dict rỗng).
    Output: dict chứa status, total và danh sách data.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()

        # KHÔNG DÙNG vector::text nữa, lấy trực tiếp vector
        cur.execute("""
            SELECT
                location_id,
                text,
                aug_text,
                aug_tags,
                img_desc,
                metadata,
                geo
            FROM locations;
        """)

        rows = cur.fetchall()
        conn.close()

        results = []
        for row in rows:
            row_dict = dict(row)

            formatted = {
                "location_id": row_dict["location_id"],
                "vectors": _format_vectors(row_dict),   # 🔥 FIXED
                "metadata": row_dict.get("metadata"),
                "geo": row_dict.get("geo"),
            }

            results.append(_attach_image(formatted))

        # Trả về Dict chuẩn ý sếp Khanh
        return {
            "status": "success",
            "total": len(results),
            "data": results
        }

    except Exception as e:
        logger.error(f"Lỗi truy vấn DB: {e}. Đang chuyển sang chế độ Fallback JSON...")
        
        # FALLBACK: Đọc từ file JSON seeds nếu DB lỗi
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            fallback_path = os.path.join(current_dir, "seeds", "locations_with_vectors.json")
            
            if os.path.exists(fallback_path):
                with open(fallback_path, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                
                results = []
                for item in json_data:
                    # Gắn ảnh nếu chưa có
                    if "images" not in item or not item["images"]:
                        item = _attach_image(item)
                    results.append(item)
                
                logger.info(f"✅ Fallback thành công: Load {len(results)} locations từ JSON.")
                return {
                    "status": "success",
                    "total": len(results),
                    "data": results,
                    "is_fallback": True
                }
            else:
                logger.error(f"❌ Không tìm thấy file fallback: {fallback_path}")
        except Exception as fallback_err:
            logger.error(f"❌ Fallback JSON cũng thất bại: {fallback_err}")

        return {"status": "error", "message": str(e), "data": []}

def save_user_profile(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lưu thông tin người dùng.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users (
                user_id,
                text,
                aug_text,
                aug_tags,
                img_desc,
                metadata,
                constraints
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET
                text = EXCLUDED.text,
                aug_text = EXCLUDED.aug_text,
                aug_tags = EXCLUDED.aug_tags,
                img_desc = EXCLUDED.img_desc,
                metadata = EXCLUDED.metadata,
                constraints = EXCLUDED.constraints;
        """,
        (
            user_data.get("user_id"),
            user_data.get("text"),
            user_data.get("aug_text"),
            user_data.get("aug_tags"),
            user_data.get("img_desc"),
            json.dumps(user_data.get("metadata", {})),
            json.dumps(user_data.get("constraints", {})),
        ))

        conn.close()
        return {
            "status": "success",
            "user_id": user_data.get("user_id")
        }

    except Exception as e:
        logger.error(f"Lỗi lưu User: {e}")
        return {"status": "error", "message": str(e)}