import base64
import os
import json
from config import (
    TOP_K_LOCATIONS, TOP_K_ACTIVITIES, LLM_N5_TARGET_COUNT, setup_logging, API_DEBUG
)
from .utils import _safe_vec

logger = setup_logging("N8.services")

logger.info("N8 — Loading heavy modules...")
logger.info("N8 — Loading Database (N3)...")
from n3_database import get_all_locations
from n3_database.db_manager import get_db_fingerprint

logger.info("N8 — Loading Embedding Model (N1)...")
from modules.n1_embedding import embed, embed_batch

logger.info("N8 — Loading Image Processor (N2)...")
from modules.n2_image_processing import process_image

logger.info("N8 — Loading Ranking Engines (N4, N6)...")
from modules.n4_location_ranking import rank_locations
from modules.n6_activity_ranking.rank_activities import rank_activities

logger.info("N8 — Loading Activity Generator (N5)...")
from modules.n5_activity_generation.n5_activity_generator import generate_activities

logger.info("N8 — Loading Feedback Processor (N17)...")
from modules.n17_feedback_processing import process_feedback

logger.info("N8 — Loading Shared Weights & Utils...")
from shared.weights import get_weights
logger.info("N8 — All modules loaded successfully.")

# ── Location Caching ──
_CACHED_LOCATIONS_DATA = None
_CACHED_FINGERPRINT = None
CACHE_DIR = os.path.dirname(__file__)
CACHE_FILE = os.path.join(CACHE_DIR, "location_cache.json")
IMG_CACHE_DIR = os.path.join(CACHE_DIR, "image_cache")

# Đảm bảo thư mục cache ảnh tồn tại
os.makedirs(IMG_CACHE_DIR, exist_ok=True)

def _save_images_to_local_cache(location_id, images_b64):
    """Lưu danh sách ảnh Base64 từ N3 thành file cục bộ của N8."""
    saved_paths = []
    for i, b64_data in enumerate(images_b64):
        try:
            if "," in b64_data:
                b64_data = b64_data.split(",")[1]
            img_bytes = base64.b64decode(b64_data)
            file_name = f"{location_id}_{i}.jpg"
            file_path = os.path.join(IMG_CACHE_DIR, file_name)
            with open(file_path, "wb") as f:
                f.write(img_bytes)
            saved_paths.append(file_path)
        except Exception as e:
            logger.warning(f"Lỗi lưu ảnh cache cho {location_id}: {e}")
    return saved_paths

def _get_images_from_local_cache(location_id):
    """Đọc ảnh từ file cục bộ và trả về dạng Base64 (data URI)."""
    encoded_images = []
    # Tìm các file có dạng location_id_*.jpg
    for i in range(10): # Giả định tối đa 10 ảnh
        file_path = os.path.join(IMG_CACHE_DIR, f"{location_id}_{i}.jpg")
        if os.path.exists(file_path):
            try:
                with open(file_path, "rb") as f:
                    b64_str = base64.b64encode(f.read()).decode("utf-8")
                    encoded_images.append(f"data:image/jpeg;base64,{b64_str}")
            except Exception as e:
                logger.warning(f"Lỗi đọc ảnh cache {file_path}: {e}")
    return encoded_images

# ── Core Services ──

def get_all_locations_cached(force_refresh=False):
    """
    Hybrid Caching for N3 data.
    1. Check Memory (RAM)
    2. Check Fingerprint (DB version)
    3. Check Disk (location_cache.json)
    """
    global _CACHED_LOCATIONS_DATA, _CACHED_FINGERPRINT
    current_fp = get_db_fingerprint()
    
    if not force_refresh:
        # RAM Hit?
        if _CACHED_LOCATIONS_DATA and _CACHED_FINGERPRINT == current_fp:
            return _CACHED_LOCATIONS_DATA
        
        # Disk Hit?
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if cached.get("fingerprint") == current_fp:
                        _CACHED_LOCATIONS_DATA = cached.get("data", [])
                        _CACHED_FINGERPRINT = current_fp
                        logger.info(f"Cache Hit (Disk): Loaded {len(_CACHED_LOCATIONS_DATA)} locations")
                        return _CACHED_LOCATIONS_DATA
            except Exception as e:
                logger.warning(f"Lỗi đọc Disk Cache: {e}")

    # Miss: Fetch from N3
    logger.info("Cache Miss: Fetching fresh data from N3...")
    raw_data = get_all_locations(include_images=True)
    if raw_data.get("status") != "success":
        return []

    locations = raw_data.get("data", [])
    
    # Process images (Save to local files)
    for loc in locations:
        loc_id = loc.get("location_id")
        imgs = loc.get("images", [])
        if imgs:
            _save_images_to_local_cache(loc_id, imgs)
            loc["images"] = [] # Don't store large images in JSON/RAM

    # Update RAM
    _CACHED_LOCATIONS_DATA = locations
    _CACHED_FINGERPRINT = current_fp

    # Update Disk
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "fingerprint": current_fp,
                "data": _CACHED_LOCATIONS_DATA
            }, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Lỗi lưu Disk Cache: {e}")

    return _CACHED_LOCATIONS_DATA

def recommend_service(body):
    text = body.get("text", "").strip()
    tags = body.get("tags", [])
    constraints = body.get("constraints", {})
    context_data = body.get("context", {})
    top_k = int(body.get("top_k_locations", TOP_K_LOCATIONS))
    top_k_activities = int(body.get("top_k_activities", TOP_K_ACTIVITIES))

    # ── N2 — Image → img_desc ──────────────────
    img_desc = body.get("img_desc", "")
    if not img_desc:
        image_b64 = body.get("image", "")
        if not image_b64 and body.get("images"):
            imgs = body.get("images", [])
            if isinstance(imgs, list) and len(imgs) > 0:
                image_b64 = imgs[0]

        if image_b64:
            try:
                b64_data = image_b64.split(",")[1] if "," in image_b64 else image_b64
                img_bytes = base64.b64decode(b64_data)
                n2_result = process_image({"image": img_bytes})
                img_desc = n2_result.get("img_desc", "")
            except Exception as e:
                logger.warning(f"N2 processing failed: {e}")

    # ── N1 — Build User Vectors ────────────────
    n1_result = embed({
        "text": text,
        "tags": tags,
        "img_desc": img_desc
    })

    text_k = n1_result.get("text_k", 0)
    tags_k = n1_result.get("tags_k", 0)
    vectors = n1_result.get("vectors", {})

    user_vectors = {
        "text":     _safe_vec(vectors.get("text")),
        "aug_text": _safe_vec(vectors.get("aug_text")),
        "aug_tags": _safe_vec(vectors.get("aug_tags")),
        "img_desc": _safe_vec(vectors.get("img_desc")),
    }

    # ── N3 — Fetch locations from DB ───────────
    locations = get_all_locations_cached()

    # ── N4 — Rank Locations ───────────────────
    # Fix contract: Map 'vectors' from N3 to 'location_vectors' for N4
    for loc in locations:
        loc["location_vectors"] = loc.get("vectors")

    n4_input = {
        "text_k": text_k,
        "tags_k": tags_k,
        "user_vectors": user_vectors,
        "locations": locations,
        "top_k": top_k,
    }
    n4_result = rank_locations(n4_input)
    ranked = n4_result.get("locations", [])
    
    # ── Final Enrichment (Attach images from N8's LOCAL cache) ──
    for loc_rank in ranked:
        loc_id = loc_rank.get("location_id")
        loc_rank["images"] = _get_images_from_local_cache(loc_id)
        # Find and attach metadata from original locations list
        original = next((l for l in locations if l["location_id"] == loc_id), {})
        loc_rank["metadata"] = original.get("metadata", {})
        loc_rank["geo"] = original.get("geo", {})

    response = {
        "locations": ranked,
    }

    if API_DEBUG:
        response["trace"] = {
            "user": {
                "input": {
                    "text": text,
                    "tags": tags,
                    "constraints": constraints,
                    "context": context_data,
                    "has_image": bool(image_b64),
                },
                "n2_image": {"img_desc": img_desc},
                "n1_embedding": {
                    "text_k": text_k,
                    "tags_k": tags_k,
                    "preprocessed": n1_result.get("preprocessed", {}),
                },
                "user_vectors": user_vectors,
                "vector_dims": {k: len(v) if v else 0 for k, v in user_vectors.items()},
            },
            "ranking": {
                "text_k": text_k,
                "tags_k": tags_k,
                "weights_used": get_weights(text_k, tags_k),
                "top_k": top_k,
                "ranked": ranked,
            },
            "debug": {
                "total_locations": len(locations),
                "pipeline": {"n1": "embedding", "n2": "image_processing", "n3": "database_fetch", "n4": "location_ranking"},
            },
        }

    # Pass through refinement info if available
    if body.get("refined"):
        response["refined"] = body["refined"]

    return response

def activities_service(body):
    """
    Pipeline chuyên biệt cho việc sinh hoạt động.
    """
    text = body.get("text", "").strip()
    img_desc = body.get("img_desc", "")
    tags = body.get("tags", [])
    text_k = int(body.get("text_k", 0))
    tags_k = int(body.get("tags_k", 0))
    user_vectors = body.get("user_vectors", {})
    provider = body.get("provider")
    location = body.get("location", {})
    top_k_activities = int(body.get("top_k_activities", TOP_K_ACTIVITIES))

    # ── N5 — Generate Activities ───────────────
    n5_input = {
        "user": {"text": text, "img_desc": img_desc, "tags": tags},
        "locations": [location],
        "config": {"target_count": LLM_N5_TARGET_COUNT},
        "provider_override": provider,
    }

    n5_result = generate_activities(n5_input)
    activities = n5_result.get("activities", [])
    n5_metadata = n5_result.get("metadata", {})
    per_loc_meta = n5_metadata.get("per_location", [])

    # ── N1 — Embed Generated Activities ────────
    # Map N5 activities to N1 contract (text, tags, img_desc)
    # We use 'name' as 'text' and 'description' as 'img_desc' for N1 preprocessing
    n1_batch_input = []
    for act in activities:
        meta = act.get("metadata", {})
        n1_batch_input.append({
            "text": meta.get("name", ""),
            "tags": meta.get("tags", []),
            "img_desc": meta.get("description", "")
        })

    logger.info(f"N8 — Embedding {len(activities)} activities via N1...")
    from modules.n1_embedding import embed_batch
    n1_results = embed_batch(n1_batch_input)
    
    # Merge vectors back into activities for N6
    for i, act in enumerate(activities):
        act["vectors"] = n1_results[i].get("vectors")

    # ── N6 — Rank Activities ───────────────────
    n6_input = {
        "text_k": text_k,
        "tags_k": tags_k,
        "user_input": {"text": text, "tags": tags, "img_desc": img_desc},
        "user_vectors": user_vectors,
        "activities": activities,
        "top_k": top_k_activities,
    }
    n6_result = rank_activities(n6_input)
    ranked_acts = n6_result.get("activities", [])

    # Final enrichment for UI: N8 merges metadata back using its local reference
    act_map = {a["activity_id"]: a for a in activities}
    
    enriched_ranked_activities = []
    for ra in ranked_acts:
        aid = ra.get("activity_id")
        original_act = act_map.get(aid, {})
        
        enriched_ranked_activities.append({
            "activity_id": aid,
            "location_id": ra.get("location_id"),
            "score": ra.get("score", 0),
            "reason": ra.get("reason", ""),
            "metadata": original_act.get("metadata", {})
        })

    return {
        "status": "success",
        "location_id": location.get("location_id"),
        "activities": enriched_ranked_activities,
        "meta": per_loc_meta[0] if per_loc_meta else {},
        "ranking_meta": n6_result.get("metadata", {})
    }

def feedback_recommend_service(body):
    """
    Xử lý phản hồi và chạy lại pipeline gợi ý địa điểm.
    Response structure matches recommend_service + 'refined' metadata.
    """
    old_text = body.get("text", "")
    old_tags = body.get("tags", [])
    old_img_desc = body.get("img_desc", "")
    feedback = body.get("feedback", "")

    if not feedback:
        return recommend_service(body)

    # 1. N17 — Phân tích phản hồi
    logger.info(f"N17 — Processing recommend feedback: '{feedback}'")
    refined = process_feedback(old_text, old_tags, old_img_desc, feedback)
    
    # 2. Cập nhật body
    new_body = body.copy()
    new_body["text"] = refined.get("refined_text", old_text)
    new_body["tags"] = refined.get("refined_tags", old_tags)
    new_body["img_desc"] = refined.get("refined_img_desc", old_img_desc)
    
    # 3. Chạy lại recommend_service
    result = recommend_service(new_body)
    
    # 4. Đính kèm thông tin tinh chỉnh để UI sử dụng
    result["refined"] = {
        "text": new_body["text"],
        "tags": new_body["tags"],
        "img_desc": new_body["img_desc"],
        "explanation": refined.get("explanation", "")
    }
    
    return result

def feedback_activities_service(body):
    """
    Xử lý phản hồi và chạy lại pipeline sinh hoạt động cho địa điểm cụ thể.
    Response structure matches activities_service + 'refined' metadata.
    """
    old_text = body.get("text", "")
    old_tags = body.get("tags", [])
    old_img_desc = body.get("img_desc", "")
    feedback = body.get("feedback", "")

    if not feedback:
        return activities_service(body)

    # 1. N17 — Phân tích phản hồi
    logger.info(f"N17 — Processing activity feedback: '{feedback}'")
    refined = process_feedback(old_text, old_tags, old_img_desc, feedback)
    
    # 2. Cập nhật body
    new_body = body.copy()
    new_body["text"] = refined.get("refined_text", old_text)
    new_body["tags"] = refined.get("refined_tags", old_tags)
    new_body["img_desc"] = refined.get("refined_img_desc", old_img_desc)
    
    # 3. Chạy lại activities_service
    result = activities_service(new_body)
    
    # 4. Đính kèm thông tin tinh chỉnh
    result["refined"] = {
        "text": new_body["text"],
        "tags": new_body["tags"],
        "img_desc": new_body["img_desc"],
        "explanation": refined.get("explanation", "")
    }
    
    return result
