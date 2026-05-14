import base64
from config import (
    TOP_K_LOCATIONS, TOP_K_ACTIVITIES, LLM_N5_TARGET_COUNT, setup_logging, API_DEBUG
)
from .utils import _safe_vec

logger = setup_logging("N8.services")

from n3_database import get_all_locations
from modules.n1_embedding import embed, embed_batch
from modules.n2_image_processing import process_image
from modules.n4_location_ranking import rank_locations
from modules.n5_activity_generation.n5_activity_generator import generate_activities
from modules.n6_activity_ranking.rank_activities import rank_activities
from shared.weights import get_weights

# ── Location Caching ──
import os
import json
import base64
from n3_database.db_manager import get_db_fingerprint

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
            # Tách header data:image/jpeg;base64, nếu có
            if "," in b64_data:
                b64_data = b64_data.split(",")[1]
            
            file_name = f"{location_id}_{i+1}.jpg"
            file_path = os.path.join(IMG_CACHE_DIR, file_name)
            
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(b64_data))
            saved_paths.append(file_path)
        except Exception as e:
            logger.error(f"Lỗi lưu ảnh cache cho {location_id}: {e}")
    return saved_paths

def get_all_locations_cached(force_refresh=False):
    """
    Hybrid Caching với Image Persistence:
    1. Check Fingerprint.
    2. Nếu Miss: Fetch từ N3 (kèm ảnh) -> Lưu ảnh ra File -> Lưu Metadata ra JSON.
    3. Nếu Hit: Load Metadata từ JSON -> Trả về (Ảnh sẽ được load từ File khi cần).
    """
    global _CACHED_LOCATIONS_DATA, _CACHED_FINGERPRINT
    current_fp = get_db_fingerprint()
    
    if _CACHED_LOCATIONS_DATA is not None and current_fp == _CACHED_FINGERPRINT and not force_refresh:
        return _CACHED_LOCATIONS_DATA

    if os.path.exists(CACHE_FILE) and not force_refresh:
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                obj = json.load(f)
                if obj.get("fingerprint") == current_fp:
                    logger.info("✅ N8 Cache Hit: Loading metadata from local file...")
                    _CACHED_LOCATIONS_DATA = obj.get("data", [])
                    _CACHED_FINGERPRINT = current_fp
                    return _CACHED_LOCATIONS_DATA
        except: pass

    # SYNC MỚI: Lấy cả ảnh từ N3
    logger.info(f"🔄 N8 Syncing from N3 (Remote Simulation)... Fingerprint: {current_fp}")
    db_result = get_all_locations(include_images=True) # Lấy ảnh qua "Service"
    raw_data = db_result.get("data", [])
    
    processed_data = []
    for loc in raw_data:
        loc_id = loc.get("location_id")
        imgs = loc.get("images", [])
        
        # Tự N8 lưu ảnh vào "kho" riêng của mình
        _save_images_to_local_cache(loc_id, imgs)
        
        # Metadata trong RAM không giữ Base64 để tiết kiệm bộ nhớ
        loc_copy = loc.copy()
        if "images" in loc_copy: del loc_copy["images"] 
        processed_data.append(loc_copy)

    # Cập nhật Cache
    _CACHED_LOCATIONS_DATA = processed_data
    _CACHED_FINGERPRINT = current_fp
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"fingerprint": current_fp, "data": processed_data}, f, ensure_ascii=False)
        
    return _CACHED_LOCATIONS_DATA

def _get_images_from_local_cache(location_id):
    """Đọc ảnh từ kho cache riêng của N8 và chuyển thành Base64."""
    encoded_images = []
    for i in range(1, 4):
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

def recommend_service(body):
    text = body.get("text", "").strip()
    image_b64 = body.get("image", "")
    tags = body.get("tags", [])
    constraints = body.get("constraints", {})
    context_data = body.get("context", {})
    top_k = int(body.get("top_k_locations", TOP_K_LOCATIONS))
    top_k_activities = int(body.get("top_k_activities", TOP_K_ACTIVITIES))

    # ── N2 — Image → img_desc ──────────────────
    img_desc = ""
    if image_b64:
        try:
            img_bytes = base64.b64decode(image_b64)
            n2_result = process_image({"image": img_bytes})
            img_desc = n2_result.get("img_desc", "")
        except Exception as e:
            logger.warning(f"N2 failed: {e}")

    # ── N1 — Embed user input ──────────────────
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

    # ── Build N4 input ─────────────────────────
    n4_locations = []
    loc_map = {}

    for loc in locations:
        loc_id = loc.get("location_id", "unknown")
        db_vectors = loc.get("vectors", {}) or {}

        n4_locations.append({
            "location_id": loc_id,
            "location_vectors": {
                "text":     _safe_vec(db_vectors.get("text")),
                "aug_tags": _safe_vec(db_vectors.get("aug_tags")),
            }
        })

        loc_map[loc_id] = loc # Store ref to metadata/geo

    # ── N4 — Rank locations ────────────────────
    n4_result = rank_locations({
        "text_k": text_k,
        "tags_k": tags_k,
        "user_vectors": user_vectors,
        "locations": n4_locations,
        "top_k": top_k,
    })

    ranked = n4_result.get("locations", [])
    
    # ── Final Enrichment (Attach images from N8's LOCAL cache) ──
    final_locations = []
    for r in ranked:
        loc_id = r["location_id"]
        base_loc = loc_map.get(loc_id, {})
        
        final_locations.append({
            "location_id": loc_id,
            "score": r.get("score", 0),
            "reason": r.get("reason", ""),
            "metadata": base_loc.get("metadata", {}),
            "geo": base_loc.get("geo", {}),
            "images": _get_images_from_local_cache(loc_id) # Đọc từ cache riêng của N8
        })

    response = {
        "locations": final_locations,
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
                "total_locations": len(n4_locations),
                "pipeline": {"n1": "embedding", "n2": "image_processing", "n3": "database_fetch", "n4": "location_ranking"},
            },
        }

    return response

def activities_service(body):
    text = body.get("text", "")
    img_desc = body.get("img_desc", "")
    tags = body.get("tags", [])
    text_k = body.get("text_k", 0)
    tags_k = body.get("tags_k", 0)
    user_vectors = body.get("user_vectors", {})
    constraints = body.get("constraints", {})
    context_data = body.get("context", {})
    location = body.get("location", {})
    top_k_activities = int(body.get("top_k_activities", TOP_K_ACTIVITIES))

    # ── N5 — Generate Activities ───────────────
    n5_input = {
        "user": {"text": text, "img_desc": img_desc, "tags": tags},
        "locations": [location],
        "constraints": constraints,
        "target_count": int(body.get("target_count", LLM_N5_TARGET_COUNT)),
    }
    n5_result = generate_activities(n5_input)
    activities = n5_result.get("activities", [])
    llm_metas  = n5_result.get("llm_meta", [])

    # ── Embed Activities via N1 ────────────────
    logger.info("Embedding %d activities for location '%s' via N1 (BATCH MODE)...", len(activities), location.get("location_id"))
    n1_inputs = []
    for activity in activities:
        meta = activity.get("metadata", {})
        act_name = meta.get("name", "")
        act_desc = meta.get("description", "")
        act_tags_str = " ".join(meta.get("tags", []))
        act_text = f"{act_name}. {act_desc}. {act_tags_str}".strip(". ")

        act_tags = []
        if meta.get("activity_type"): act_tags.append(meta.get("activity_type"))
        if meta.get("activity_subtype"): act_tags.append(meta.get("activity_subtype"))

        n1_inputs.append({"text": act_text, "tags": act_tags, "img_desc": ""})

    if n1_inputs:
        n1_batch_results = embed_batch(n1_inputs)
        for activity, embed_res in zip(activities, n1_batch_results):
            activity["vectors"] = {
                "text": _safe_vec(embed_res.get("vectors", {}).get("text")),
                "tag":  _safe_vec(embed_res.get("vectors", {}).get("aug_tags")),
            }

    # ── N6 — Rank Activities ───────────────────
    n6_input = {
        "text_k": text_k,
        "tags_k": tags_k,
        "user_input": {"text": text, "img_desc": img_desc, "tags": tags},
        "user_vectors": user_vectors,
        "activities": activities,
        "context": {"time_of_day": context_data.get("time_of_day")},
        "top_k": top_k_activities
    }
    n6_result = rank_activities(n6_input)
    ranked_activities = n6_result.get("activities", [])

    # Enrich
    act_map = {act.get("activity_id"): act for act in activities}
    enriched_ranked_activities = []
    for r_act in ranked_activities:
        full_act = act_map.get(r_act["activity_id"], {})
        enriched_ranked_activities.append({
            "activity_id": r_act["activity_id"],
            "location_id": r_act["location_id"],
            "score": r_act["score"],
            "reason": r_act["reason"],
            "metadata": full_act.get("metadata", {})
        })

    return {
        "status": "success",
        "location_id": location.get("location_id"),
        "activities": enriched_ranked_activities,
        "meta": llm_metas[0] if llm_metas else {},
    }
