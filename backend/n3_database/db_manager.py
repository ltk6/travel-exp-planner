import os
import json
import logging
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
import base64

from config import setup_logging
logger = setup_logging("N3")

from config import PG_URI
def _get_connection():
    """Tạo kết nối DB và đăng ký kiểu vector."""
    conn = psycopg2.connect(PG_URI, cursor_factory=RealDictCursor)
    conn.autocommit = True
    register_vector(conn)
    return conn

def init_db():
    """Khởi tạo cấu trúc Database và ép ngắt các kết nối đang treo để tránh Lock."""
    conn = _get_connection()
    cur = conn.cursor()
    
    try:
        # Chỉ ngắt kết nối của CHÍNH MÌNH (current user) để không cần quyền Superuser
        cur.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND usename = current_user
              AND pid <> pg_backend_pid();
        """)
    except Exception as e:
        logger.warning(f"Không thể ngắt các kết nối khác: {e}")

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute("DROP TABLE IF EXISTS locations CASCADE;")
    
    cur.execute("""
        CREATE TABLE locations (
            location_id VARCHAR(255) PRIMARY KEY,
            text vector(1024),
            aug_text vector(1024),
            aug_tags vector(1024),
            img_desc vector(1024),
            metadata JSONB,
            geo JSONB,
            images BYTEA[], 
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.close()
    conn.close()
    logger.info("✨ Khởi tạo DB thành công (Đã giải phóng các kết nối cũ).")

def get_db_fingerprint() -> str:
    """Tạo dấu vân tay duy nhất cho trạng thái hiện tại của DB."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), MAX(updated_at) FROM locations;")
        row = cur.fetchone()
        conn.close()
        return f"{row['count']}:{row['max']}"
    except Exception as e:
        logger.warning(f"Lỗi lấy Fingerprint: {e}")
        return "fallback_v1"

def _format_vectors(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": row.get("text"),
        "aug_text": row.get("aug_text"),
        "aug_tags": row.get("aug_tags"),
        "img_desc": row.get("img_desc")
    }

def save_location(location_data: Dict[str, Any]) -> Dict[str, Any]:
    """Lưu dữ liệu địa điểm kèm mảng ảnh Binary vào Database."""
    try:
        conn = _get_connection()
        cur = conn.cursor()

        vectors = location_data.get("vectors", {})
        images_binary = location_data.get("images_binary", [])

        cur.execute("""
            INSERT INTO locations (
                location_id, text, aug_text, aug_tags, img_desc, metadata, geo, images, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (location_id)
            DO UPDATE SET
                text = EXCLUDED.text,
                aug_text = EXCLUDED.aug_text,
                aug_tags = EXCLUDED.aug_tags,
                img_desc = EXCLUDED.img_desc,
                metadata = EXCLUDED.metadata,
                geo = EXCLUDED.geo,
                images = CASE WHEN array_length(EXCLUDED.images, 1) > 0 THEN EXCLUDED.images ELSE locations.images END,
                updated_at = CURRENT_TIMESTAMP;
        """,
        (
            location_data.get("location_id"),
            vectors.get("text"),
            vectors.get("aug_text"),
            vectors.get("aug_tags"),
            vectors.get("img_desc"),
            json.dumps(location_data.get("metadata", {})),
            json.dumps(location_data.get("geo", {})),
            images_binary if images_binary else None,
        ))

        conn.commit()
        conn.close()
        return {"status": "success", "location_id": location_data.get("location_id")}
    except Exception as e:
        logger.error(f"Lỗi lưu Location: {e}")
        return {"status": "error", "message": str(e)}

def attach_image_to_location(location_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Giữ nguyên interface cho N8. Ảnh đã được load từ DB vào field 'images'."""
    return location_dict

def get_all_locations(include_images: bool = True) -> Dict[str, Any]:
    """Lấy toàn bộ danh sách địa điểm, giải mã Binary sang Base64 cho Frontend."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        
        query = "SELECT location_id, text, aug_text, aug_tags, img_desc, metadata, geo"
        if include_images:
            query += ", images"
        query += " FROM locations;"
        
        cur.execute(query)
        rows = cur.fetchall()
        conn.close()

        results = []
        for row in rows:
            row_dict = dict(row)
            formatted = {
                "location_id": row_dict["location_id"],
                "vectors": _format_vectors(row_dict),
                "metadata": row_dict.get("metadata"),
                "geo": row_dict.get("geo"),
            }
            
            if include_images and row_dict.get("images"):
                encoded_images = []
                for img_bytes in row_dict["images"]:
                    if img_bytes:
                        b64_str = base64.b64encode(img_bytes).decode("utf-8")
                        encoded_images.append(f"data:image/jpeg;base64,{b64_str}")
                formatted["images"] = encoded_images
            else:
                formatted["images"] = []
                
            results.append(formatted)

        return {"status": "success", "total": len(results), "data": results}

    except Exception as e:
        logger.error(f"Lỗi truy vấn DB: {e}")
        return {"status": "error", "message": str(e), "data": []}
