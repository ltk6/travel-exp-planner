import base64
import os
import json
import time
from config import (
    TOP_K_LOCATIONS, TOP_K_ACTIVITIES, LLM_N5_TARGET_COUNT, setup_logging, API_DEBUG
)
from .utils import _safe_vec

logger = setup_logging("N8.services")

import threading

logger.info("N8 — Spawning background thread for heavy modules...")

def _warmup_modules():
    try:
        from n3_database import get_all_locations
        from n3_database.db_manager import get_db_fingerprint, get_activities_for_location
        from modules.n1_embedding import embed, embed_batch
        from modules.n2_image_processing import process_image
        from modules.n4_location_ranking import rank_locations
        from modules.n6_activity_ranking.rank_activities import rank_activities
        from modules.n5_activity_generation.n5_activity_generator import generate_activities
        from modules.n17_feedback_processing import process_feedback
        from shared.weights import get_weights
        
        globals()["get_all_locations"] = get_all_locations
        globals()["get_db_fingerprint"] = get_db_fingerprint
        globals()["get_activities_for_location"] = get_activities_for_location
        globals()["embed"] = embed
        globals()["embed_batch"] = embed_batch
        globals()["process_image"] = process_image
        globals()["rank_locations"] = rank_locations
        globals()["rank_activities"] = rank_activities
        globals()["generate_activities"] = generate_activities
        globals()["process_feedback"] = process_feedback
        globals()["get_weights"] = get_weights
        logger.info("N8 — All heavy modules warmed up successfully in background.")
    except Exception as e:
        logger.error(f"N8 — Background warmup failed: {e}")

threading.Thread(target=_warmup_modules, daemon=True).start()

def __getattr__(name):
    if name == "get_all_locations":
        from n3_database import get_all_locations
        globals()[name] = get_all_locations
        return get_all_locations
    if name == "get_db_fingerprint":
        from n3_database.db_manager import get_db_fingerprint
        globals()[name] = get_db_fingerprint
        return get_db_fingerprint
    if name == "get_activities_for_location":
        from n3_database.db_manager import get_activities_for_location
        globals()[name] = get_activities_for_location
        return get_activities_for_location
    if name == "embed":
        from modules.n1_embedding import embed
        globals()[name] = embed
        return embed
    if name == "embed_batch":
        from modules.n1_embedding import embed_batch
        globals()[name] = embed_batch
        return embed_batch
    if name == "process_image":
        from modules.n2_image_processing import process_image
        globals()[name] = process_image
        return process_image
    if name == "rank_locations":
        from modules.n4_location_ranking import rank_locations
        globals()[name] = rank_locations
        return rank_locations
    if name == "rank_activities":
        from modules.n6_activity_ranking.rank_activities import rank_activities
        globals()[name] = rank_activities
        return rank_activities
    if name == "generate_activities":
        from modules.n5_activity_generation.n5_activity_generator import generate_activities
        globals()[name] = generate_activities
        return generate_activities
    if name == "process_feedback":
        from modules.n17_feedback_processing import process_feedback
        globals()[name] = process_feedback
        return process_feedback
    if name == "get_weights":
        from shared.weights import get_weights
        globals()[name] = get_weights
        return get_weights
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# ── Centralized Pydantic Contracts ──
from backend.shared.contracts.n1_contracts import N1EmbedInput
from backend.shared.contracts.n2_contracts import N2ImageInput
from backend.shared.contracts.n3_contracts import N3RegisterInput, N3LoginInput, N3SaveHistoryInput, N3ActivityItem
from backend.shared.contracts.n4_contracts import N4RankInput, UserVectors
from backend.shared.contracts.n5_contracts import N5GenerateInput, N5UserInput, N5LocationItem, N5LocationMetadata
from backend.shared.contracts.n6_contracts import N6RankInput, UserInput
from backend.shared.contracts.n17_contracts import N17FeedbackInput

# ── Location Caching ──
_CACHED_LOCATIONS_DATA = None
_CACHED_FINGERPRINT = None
CACHE_DIR = os.path.dirname(__file__)
CACHE_FILE = os.path.join(CACHE_DIR, "location_cache.json")
IMG_CACHE_DIR = os.path.join(CACHE_DIR, "image_cache")

# Đảm bảo thư mục cache ảnh tồn tại
os.makedirs(IMG_CACHE_DIR, exist_ok=True)

# Fingerprint TTL — tránh hit DB mỗi request trong dev
_FP_TTL_SEC = 10.0
_FP_CACHE = {"value": None, "expires": 0.0}


def _fingerprint_cached() -> str:
    """Wrap get_db_fingerprint() với TTL ngắn để giảm round-trip Postgres."""
    now = time.time()
    if _FP_CACHE["value"] is not None and now < _FP_CACHE["expires"]:
        return _FP_CACHE["value"]
    fp = get_db_fingerprint()
    _FP_CACHE["value"] = fp
    _FP_CACHE["expires"] = now + _FP_TTL_SEC
    return fp

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

def _get_image_urls(location_id):
    """Trả về list URL trỏ tới /api/images/{filename}. Frontend lazy-load."""
    # Pure lazy loading: return up to 3 image URLs. If any index does not exist in DB,
    # the server will return a 1x1 transparent PNG fallback to avoid broken images.
    return [
        f"/api/images/{location_id}_0.jpg",
        f"/api/images/{location_id}_1.jpg",
        f"/api/images/{location_id}_2.jpg"
    ]

# ── Core Services ──

def get_all_locations_cached(force_refresh=False):
    """
    Hybrid Caching for N3 data.
    1. Check Memory (RAM)
    2. Check Fingerprint (DB version)
    3. Check Disk (location_cache.json)
    """
    global _CACHED_LOCATIONS_DATA, _CACHED_FINGERPRINT
    current_fp = _fingerprint_cached()
    
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
    logger.info("Cache Miss: Fetching fresh data from N3 (lazy images)...")
    raw_data = get_all_locations(include_images=False)
    if raw_data.get("status") != "success":
        return []

    locations = raw_data.get("data", [])
    
    # Ensure images list is empty to save memory/disk footprint
    for loc in locations:
        loc["images"] = []

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

def explore_locations_service():
    """
    Trả về danh sách địa điểm cho chế độ Khám phá (Explore).

    Slim shape: chỉ giữ `location_id`, `metadata`, `geo` và 1 ảnh đại diện.
    Vectors (text, aug_text, aug_tags, img_desc) bị strip để giảm payload —
    UI không cần tới chúng. Ảnh được nạp lại từ disk cache (N3 cleared sau khi
    save vào IMG_CACHE_DIR).
    """
    locations = get_all_locations_cached()
    out = []
    for loc in locations:
        loc_id = loc.get("location_id")
        imgs = _get_image_urls(loc_id) if loc_id else []
        first_img = imgs[0] if imgs else None
        out.append({
            "location_id": loc_id,
            "metadata": loc.get("metadata"),
            "geo": loc.get("geo"),
            "image": first_img,
            "images_count": len(imgs),
        })
    return {"status": "success", "total": len(out), "data": out}

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
                n2_input = N2ImageInput(image=img_bytes)
                n2_result = process_image(n2_input)
                img_desc = n2_result.get("img_desc", "")
            except Exception as e:
                logger.warning(f"N2 processing failed: {e}")

    # ── N1 — Build User Vectors ────────────────
    n1_input = N1EmbedInput(
        text=text,
        tags=tags,
        img_desc=img_desc
    )
    n1_result = embed(n1_input)

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

    n4_input = N4RankInput(
        text_k=text_k,
        tags_k=tags_k,
        user_vectors=UserVectors(**user_vectors),
        locations=locations,
        top_k=top_k,
    )
    n4_result = rank_locations(n4_input)
    ranked = n4_result.get("locations", [])
    
    # ── Final Enrichment (Attach images from N8's LOCAL cache) ──
    for loc_rank in ranked:
        loc_id = loc_rank.get("location_id")
        loc_rank["images"] = _get_image_urls(loc_id)
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
    provider = body.get("provider")
    location = body.get("location", {})
    top_k_activities = int(body.get("top_k_activities", TOP_K_ACTIVITIES))

    # ── BGE-M3 — Build User Vectors ────────────
    # Use primary BGE-M3 model for activities user embedding
    logger.info("N8 — Embedding user query via BGE-M3...")
    n1_input = N1EmbedInput(
        text=text,
        tags=tags,
        img_desc=img_desc
    )
    bge_result = embed(n1_input)

    text_k = bge_result.get("text_k", 0)
    tags_k = bge_result.get("tags_k", 0)
    bge_vectors = bge_result.get("vectors", {})

    user_vectors = {
        "text":     _safe_vec(bge_vectors.get("text")),
        "aug_text": _safe_vec(bge_vectors.get("aug_text")),
        "aug_tags": _safe_vec(bge_vectors.get("aug_tags")),
        "img_desc": _safe_vec(bge_vectors.get("img_desc")),
    }

    # ── N5 — Generate Activities ───────────────
    n5_loc_meta = N5LocationMetadata(
        name=location.get("metadata", {}).get("name") or location.get("location_id"),
        description=location.get("metadata", {}).get("description"),
        tags=location.get("metadata", {}).get("tags") or [],
        coordinates=location.get("metadata", {}).get("coordinates") or location.get("geo"),
        address=location.get("metadata", {}).get("address")
    )
    n5_input = N5GenerateInput(
        user=N5UserInput(text=text, tags=tags, img_desc=img_desc),
        locations=[N5LocationItem(location_id=location["location_id"], metadata=n5_loc_meta)],
        provider_override=provider
    )

    n5_result = generate_activities(n5_input)
    raw_activities = n5_result.get("activities", [])
    
    # Decoupled Normalization: Call the normalizer here in N8 Orchestrator
    from modules.activity_retrievals.normalizers import llm as _llm_normalizer
    coords = location.get("geo") or location.get("metadata", {}).get("coordinates")
    ctx = {
        "location_id":    location["location_id"],
        "anchor_lat":     (coords or {}).get("lat") if coords else None,
        "anchor_lng":     (coords or {}).get("lng") if coords else None,
        "anchor_address": location.get("metadata", {}).get("address"),
    }
    activities = _llm_normalizer.normalize_all(raw_activities, ctx)
    
    n5_metadata = n5_result.get("metadata", {})
    per_loc_meta = n5_metadata.get("per_location", [])

    # ── BGE-M3 — Embed Generated Activities ────
    # Map N5 activities to N1 contract (text, tags, img_desc)
    n1_batch_input = []
    for act in activities:
        meta = act.get("metadata", {}) or {}
        n1_batch_input.append(N1EmbedInput(
            text=(meta.get("name") or "") + ". " + (meta.get("description") or ""),
            tags=meta.get("tags") or [],
            img_desc="",
        ))

    logger.info(f"N8 — Embedding {len(activities)} activities via BGE-M3...")
    bge_results = embed_batch(n1_batch_input)
    
    # Merge vectors back into activities for N6
    for i, act in enumerate(activities):
        act["vectors"] = bge_results[i].get("vectors")

    # ── N6 — Rank Activities ───────────────────
    n6_input = N6RankInput(
        text_k=text_k,
        tags_k=tags_k,
        user_input=UserInput(text=text, tags=tags, img_desc=img_desc),
        user_vectors=UserVectors(**user_vectors),
        activities=activities,
        top_k=top_k_activities,
    )
    n6_result = rank_activities(n6_input)
    ranked_acts = n6_result.get("activities", [])

    # Final enrichment for UI: N8 merges metadata back using its local reference
    act_map = {a["activity_id"]: a for a in activities}
    
    enriched_ranked_activities = []
    for ra in ranked_acts:
        aid = ra.get("activity_id")
        original_act = act_map.get(aid, {})
        md = original_act.get("metadata", {}) or {}
        plc = original_act.get("place", {}) or {}
        sg = original_act.get("signals", {}) or {}
        dist = plc.get("distance_from_anchor_m")
        
        enriched_ranked_activities.append({
            "activity_id": aid,
            "location_id": original_act.get("location_id") or ra.get("location_id") or location.get("location_id"),
            "score": ra.get("score", 0),
            "reason": ra.get("reason", ""),
            "metadata": {
                "name":           md.get("name") or original_act.get("name") or "Trải nghiệm",
                "description":    md.get("description") or original_act.get("description") or "",
                "activity_type":  md.get("activity_type") or original_act.get("activity_type") or "nature",
                "indoor_outdoor": md.get("indoor_outdoor") or original_act.get("indoor_outdoor"),
                "tags":           md.get("tags", []) or original_act.get("tags", []),
                "source":         original_act.get("source") or "n5_generation",
                "coordinates":    plc.get("coordinates") or original_act.get("coordinates"),
                "distance_m":     dist,
                "rating":         sg.get("rating") or original_act.get("rating"),
                "image_url":      sg.get("image_url") or original_act.get("image_url"),
                "website":        sg.get("website") or original_act.get("website"),
                "opening_hours":  sg.get("opening_hours") or original_act.get("opening_hours"),
            }
        })

    return {
        "status": "success",
        "location_id": location.get("location_id"),
        "activities": enriched_ranked_activities,
        "meta": per_loc_meta[0] if per_loc_meta else {},
        "ranking_meta": n6_result.get("metadata", {})
    }


# Gợi ý ngôn ngữ tự nhiên cho N5 LLM khi user chọn chip — tag literal như "nature"
# không gọi gợi cho prompt; cụm tiếng Việt mô tả sở thích thì có.
_TYPE_HINT_TEXT = {
    "nature":      "thích thiên nhiên, ngắm cảnh, leo núi, ngắm thác, công viên, biển",
    "culture":     "thích văn hoá, di tích, đền chùa, lịch sử, bảo tàng",
    "food":        "thích ăn uống, ẩm thực địa phương, quán cà phê, đặc sản",
    "adventure":   "thích phiêu lưu, mạo hiểm, thể thao mạo hiểm, trekking",
    "relaxation":  "thích thư giãn, spa, nghỉ dưỡng, suối nước nóng",
    "nightlife":   "thích về đêm, bar, quán đêm, chợ đêm",
    "shopping":    "thích mua sắm, chợ, làng nghề thủ công",
    "photography": "thích chụp ảnh, check-in điểm đẹp, cảnh quan",
    "experience":  "thích trải nghiệm độc đáo, văn hoá địa phương, homestay",
}


def _n5_fallback_generate(location: dict, preferred_types: list, top_k: int) -> list:
    """
    Gọi N5 LLM sinh top_k activities cho location, dùng preferred_types làm
    gợi ý tiếng Việt ('thích thiên nhiên, ngắm cảnh, ...'). Trả list activities
    theo unified schema (giống output v2).
    """
    if preferred_types:
        user_text = "; ".join(_TYPE_HINT_TEXT.get(t, t) for t in preferred_types)
    else:
        user_text = ""

    # Đảm bảo location.metadata.coordinates có lat/lng để n5 normalizer kế thừa.
    loc_for_n5 = {
        "location_id": location["location_id"],
        "metadata": {
            **(location.get("metadata") or {}),
            "name":        (location.get("metadata") or {}).get("name") or location["location_id"],
            "tags":        preferred_types or [],
            "coordinates": location.get("geo") or {"lat": None, "lng": None},
        },
    }

    n5_input = {
        "user":        {"text": user_text, "tags": preferred_types or [], "img_desc": ""},
        "locations":   [loc_for_n5],
        "constraints": {},
    }
    try:
        n5_result = generate_activities(n5_input)
        raw_activities = n5_result.get("activities", [])
        from modules.activity_retrievals.normalizers import llm as _llm_normalizer
        coords = location.get("geo") or location.get("metadata", {}).get("coordinates")
        ctx = {
            "location_id":    location["location_id"],
            "anchor_lat":     (coords or {}).get("lat") if coords else None,
            "anchor_lng":     (coords or {}).get("lng") if coords else None,
            "anchor_address": location.get("metadata", {}).get("address"),
        }
        normalized_activities = _llm_normalizer.normalize_all(raw_activities, ctx)
    except Exception as e:
        logger.warning("N5 fallback raised: %s", e)
        return []
    return normalized_activities or []


def _name_key(name: str) -> str:
    """Normalize name cho dedupe (lowercase + bỏ dấu + bỏ ký tự đặc biệt)."""
    import re, unicodedata
    if not name:
        return ""
    s = unicodedata.normalize("NFD", name.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D")
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def _merge_v2_n5(
    v2_acts: list,
    n5_acts: list,
    preferred_types: list,
    top_k: int,
) -> list:
    """
    Trộn V2 (POI thật) + N5 (LLM sinh), dedupe theo normalized name.
    Khi có preferred_types: ưu tiên N5 cho slot preferred (LLM biết địa danh,
    sinh được hoạt động cụ thể), dùng V2 cho diversity. Khi không: V2 trước
    (POI thật ưu thế), N5 chỉ lấp slot trống.
    """
    seen: set = set()
    out: list = []

    def _add(a):
        key = _name_key(a.get("metadata", {}).get("name", ""))
        if not key or key in seen:
            return False
        seen.add(key)
        out.append(a)
        return True

    if preferred_types:
        prefs = set(preferred_types)
        pref_quota = max(1, int(round(top_k * 0.7)))

        # 1. N5 acts khớp preferred (LLM context-aware → tốt cho ngữ cảnh location)
        for a in n5_acts:
            if a.get("metadata", {}).get("activity_type") in prefs and _add(a) and len(out) >= pref_quota:
                break
        # 2. V2 acts khớp preferred — lấp thêm slot preferred
        for a in v2_acts:
            if a.get("metadata", {}).get("activity_type") in prefs and _add(a) and len(out) >= pref_quota:
                break
        # 3. V2 non-preferred cho diversity
        for a in v2_acts:
            if a.get("metadata", {}).get("activity_type") not in prefs:
                if _add(a) and len(out) >= top_k:
                    break
        # 4. N5 non-preferred (last resort)
        for a in n5_acts:
            if a.get("metadata", {}).get("activity_type") not in prefs:
                if _add(a) and len(out) >= top_k:
                    break
    else:
        for a in v2_acts:
            if _add(a) and len(out) >= top_k:
                break
        for a in n5_acts:
            if _add(a) and len(out) >= top_k:
                break
    return out[:top_k]


def activities_v2_service(body):
    """
    Pipeline v2 (DB-backed): đọc activities đã seed sẵn ở N9-N14 từ Postgres,
    embed user_input qua N1 → rank qua N6 (cosine + 3 trục attribute).
    Fallback N5 LLM nếu DB sparse (chưa seed hoặc seed thất bại).

    Khác v2 cũ: KHÔNG fetch+embed runtime. Acts + vectors đã có sẵn ở DB sau
    khi chạy seed_activities.py.
    """
    import time

    t0 = time.time()
    text     = body.get("text", "").strip()
    img_desc = body.get("img_desc", "")
    tags     = body.get("tags", [])
    text_k   = int(body.get("text_k", 0))
    tags_k   = int(body.get("tags_k", 0))
    user_vectors = body.get("user_vectors", {}) or {}
    location = body.get("location", {})
    top_k    = int(body.get("top_k_activities", TOP_K_ACTIVITIES))

    loc_id   = location.get("location_id", "")
    loc_meta = location.get("metadata", {}) or {}
    loc_name = loc_meta.get("name") or loc_id

    if not loc_id:
        return {
            "status": "error",
            "error":  "location must have location_id",
            "activities": [],
        }

    pref_raw = body.get("preferred_types") or []
    preferred_types = [str(t).lower().strip() for t in pref_raw if isinstance(t, str) and t.strip()]

    # ── 1. Đọc activities từ DB (UNION 6 bảng cho 1 loc) ────────────────────
    db_acts = get_activities_for_location(loc_id, include_vectors=True)
    logger.info("activities_v2: loc=%s db_acts=%d", loc_id, len(db_acts))
    
    # Remap legacy database vector keys to align with the N6 aug_tags contract
    for a in db_acts:
        vecs = a.get("vectors") or {}
        if "tag" in vecs:
            vecs["aug_tags"] = vecs.pop("tag")

    # ── 2. Fallback N5 khi DB sparse (chưa seed hoặc seed lỗi) ─────────────
    fallback_used = False
    fallback_n5_count = 0
    if len(db_acts) < 3:
        logger.info("v2 DB sparse (n_acts=%d) loc=%s — triggering N5 fallback", len(db_acts), loc_id)
        n5_acts = _n5_fallback_generate(location, preferred_types, top_k)
        from modules.activity_retrievals.processor import _drop_anchor_duplicates
        n5_acts = _drop_anchor_duplicates(n5_acts, loc_name)
        if n5_acts:
            # N5 sinh act không có vectors → embed batch ngay
            n1_inputs = []
            for a in n5_acts:
                md = a.get("metadata", {})
                n1_inputs.append({
                    "text":     (md.get("name") or "") + ". " + (md.get("description") or ""),
                    "tags":     md.get("tags") or [],
                    "img_desc": "",
                })
            n1_results = embed_batch(n1_inputs)
            for a, r in zip(n5_acts, n1_results):
                v = r.get("vectors") or {}
                a["vectors"] = {"text": v.get("text"), "aug_tags": v.get("aug_tags")}
            # Validate N5 activities against N3ActivityItem before merging
            validated_n5 = [N3ActivityItem.model_validate(a).model_dump() for a in n5_acts]
            db_acts = db_acts + validated_n5
            fallback_used = True
            fallback_n5_count = len(n5_acts)

    if not db_acts:
        elapsed_ms = int((time.time() - t0) * 1000)
        return {
            "status":      "success",
            "location_id": loc_id,
            "activities":  [],
            "meta": {
                "provider_used": "n9-n14_db",
                "model_used":    "multi-source-cached",
                "latency_ms":    elapsed_ms,
                "fallback_used": fallback_used,
                "db_acts_count": 0,
                "warning":       "Location chưa được seed — chạy seed_activities.py",
            },
            "ranking_meta": {},
        }

    # ── 2.1. Embed any activities missing vectors (1024-dim BGE-M3) ────────
    missing_indices = []
    missing_inputs = []
    for idx, a in enumerate(db_acts):
        vecs = a.get("vectors") or {}
        if not vecs or not vecs.get("text"):
            missing_indices.append(idx)
            md = a.get("metadata", {}) or {}
            name_str = md.get("name") or "activity"
            desc_str = md.get("description") or ""
            full_text = name_str + ". " + desc_str
            act_tags = md.get("tags") or md.get("categories_raw") or []
            missing_inputs.append(N1EmbedInput(
                text=full_text,
                tags=act_tags,
                img_desc=""
            ))

    if missing_inputs:
        logger.info("activities_v2: found %d activities missing vectors — embedding them using BGE-M3...", len(missing_inputs))
        from modules.n1_embedding import embed_batch as bge_embed_batch
        embedded_results = bge_embed_batch(missing_inputs)
        for idx, res in zip(missing_indices, embedded_results):
            v = res.get("vectors") or {}
            db_acts[idx]["vectors"] = {
                "text": v.get("text"),
                "aug_tags": v.get("aug_tags") or v.get("tags"),
                "aug_text": v.get("aug_text"),
                "img_desc": v.get("img_desc")
            }

    # ── 3. Embed user_input nếu chưa có hoặc thiếu user_vectors (BGE-M3) ──
    if not user_vectors or not user_vectors.get("text") or len(user_vectors.get("text", [])) != 1024:
        logger.info("activities_v2: embedding user input using BGE-M3...")
        n1_input = N1EmbedInput(
            text=text,
            tags=tags,
            img_desc=img_desc
        )
        user_emb = embed(n1_input)
        
        # Must update text_k and tags_k from the embed result for N6 ranker!
        text_k = user_emb.get("text_k", 0)
        tags_k = user_emb.get("tags_k", 0)
        
        raw_vecs = user_emb.get("vectors") or {}
        user_vectors = {
            "text":     _safe_vec(raw_vecs.get("text")),
            "aug_text": _safe_vec(raw_vecs.get("aug_text")),
            "aug_tags": _safe_vec(raw_vecs.get("aug_tags")),
            "img_desc": _safe_vec(raw_vecs.get("img_desc")),
        }

    # ── 4. N6 rank (cosine + attribute) ─────────────────────────────────────
    n6_input = N6RankInput(
        text_k=text_k,
        tags_k=tags_k,
        user_input=UserInput(text=text, tags=tags, img_desc=img_desc),
        user_vectors=UserVectors(**user_vectors),
        activities=db_acts,
        top_k=top_k,
    )
    n6_result = rank_activities(n6_input)
    ranked = n6_result.get("activities", []) or []

    # ── 5. Map về FE ActivityResult shape ──────────────────────────────────
    act_map = {a["activity_id"]: a for a in db_acts}
    enriched = []
    for ra in ranked:
        aid  = ra.get("activity_id")
        orig = act_map.get(aid, {})
        md   = orig.get("metadata", {}) or {}
        plc  = orig.get("place", {}) or {}
        sg   = orig.get("signals", {}) or {}
        dist = plc.get("distance_from_anchor_m")

        enriched.append({
            "activity_id": aid,
            "location_id": orig.get("location_id") or loc_id,
            "score":       ra.get("score", 0),
            "reason":      ra.get("reason", ""),
            "metadata": {
                "name":           md.get("name") or orig.get("name") or "Trải nghiệm",
                "description":    md.get("description") or orig.get("description") or "",
                "activity_type":  md.get("activity_type") or orig.get("activity_type") or "nature",
                "indoor_outdoor": md.get("indoor_outdoor") or orig.get("indoor_outdoor"),
                "tags":           md.get("tags", []) or md.get("categories_raw", []) or orig.get("tags", []),
                "source":         orig.get("source") or "n9-n14_db",
                "coordinates":    plc.get("coordinates") or orig.get("coordinates"),
                "distance_m":     dist,
                "rating":         sg.get("rating") or orig.get("rating"),
                "image_url":      sg.get("image_url") or orig.get("image_url"),
                "website":        sg.get("website") or orig.get("website"),
                "opening_hours":  sg.get("opening_hours") or orig.get("opening_hours"),
            },
        })

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "status":      "success",
        "location_id": loc_id,
        "activities":  enriched,
        "meta": {
            "provider_used":     "n9-n14_db" + ("+n5_fallback" if fallback_used else ""),
            "model_used":        "bge-m3+n6-cosine" + (" + groq_compound_chain" if fallback_used else ""),
            "latency_ms":        elapsed_ms,
            "fallback_used":     fallback_used,
            "fallback_n5_count": fallback_n5_count,
            "db_acts_count":     len(db_acts),
        },
        "ranking_meta": n6_result.get("metadata", {}),
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
    feedback_input = N17FeedbackInput(
        user_input=old_text,
        user_tags=old_tags,
        img_desc=old_img_desc,
        feedback_text=feedback
    )
    refined = process_feedback(feedback_input)
    
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
    feedback_input = N17FeedbackInput(
        user_input=old_text,
        user_tags=old_tags,
        img_desc=old_img_desc,
        feedback_text=feedback
    )
    refined = process_feedback(feedback_input)
    
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
