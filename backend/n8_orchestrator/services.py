import base64
import os
import json
import time
from config import (
    TOP_K_LOCATIONS, TOP_K_ACTIVITIES, LLM_N5_TARGET_COUNT, setup_logging, API_DEBUG
)
from .utils import _safe_vec

logger = setup_logging("N8.services")

# ── Clean & Thread-Safe Lazy-Loading Proxies ──

def get_all_locations(*args, **kwargs):
    global get_all_locations
    from n3_database import get_all_locations as fn
    get_all_locations = fn
    return fn(*args, **kwargs)

def get_db_fingerprint(*args, **kwargs):
    global get_db_fingerprint
    from n3_database.db_manager import get_db_fingerprint as fn
    get_db_fingerprint = fn
    return fn(*args, **kwargs)

def get_activities_for_location(*args, **kwargs):
    global get_activities_for_location
    from n3_database.db_manager import get_activities_for_location as fn
    get_activities_for_location = fn
    return fn(*args, **kwargs)

def embed(*args, **kwargs):
    global embed
    from modules.n1_embedding import embed as fn
    embed = fn
    return fn(*args, **kwargs)

def embed_batch(*args, **kwargs):
    global embed_batch
    from modules.n1_embedding import embed_batch as fn
    embed_batch = fn
    return fn(*args, **kwargs)

def process_image(*args, **kwargs):
    global process_image
    from modules.n2_image_processing import process_image as fn
    process_image = fn
    return fn(*args, **kwargs)

def rank_locations(*args, **kwargs):
    global rank_locations
    from modules.n4_location_ranking import rank_locations as fn
    rank_locations = fn
    return fn(*args, **kwargs)

def rank_activities(*args, **kwargs):
    global rank_activities
    from modules.n6_activity_ranking.rank_activities import rank_activities as fn
    rank_activities = fn
    return fn(*args, **kwargs)

def generate_activities(*args, **kwargs):
    global generate_activities
    from modules.n5_activity_generation.n5_activity_generator import generate_activities as fn
    generate_activities = fn
    return fn(*args, **kwargs)

def process_feedback(*args, **kwargs):
    global process_feedback
    from modules.n17_feedback_processing import process_feedback as fn
    process_feedback = fn
    return fn(*args, **kwargs)

def get_weights(*args, **kwargs):
    global get_weights
    from shared.weights import get_weights as fn
    get_weights = fn
    return fn(*args, **kwargs)

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

# Ensure the image cache directory exists
os.makedirs(IMG_CACHE_DIR, exist_ok=True)

# Fingerprint TTL — avoid hitting DB on every request during development
_FP_TTL_SEC = 10.0
_FP_CACHE = {"value": None, "expires": 0.0}


def _fingerprint_cached() -> str:
    """Wrap get_db_fingerprint() with a short TTL to reduce Postgres round-trips."""
    now = time.time()
    if _FP_CACHE["value"] is not None and now < _FP_CACHE["expires"]:
        return _FP_CACHE["value"]
    fp = get_db_fingerprint()
    _FP_CACHE["value"] = fp
    _FP_CACHE["expires"] = now + _FP_TTL_SEC
    return fp

def _save_images_to_local_cache(location_id, images_b64):
    """Save a list of Base64 images from N3 as local files for N8."""
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
            logger.warning(f"Failed to save image cache for {location_id}: {e}")
    return saved_paths

def _get_image_urls(location_id):
    """Return a list of URLs pointing to /api/images/{filename}. Frontend lazy-loads these."""
    return [
        f"/api/images/{location_id}_0.jpg",
        f"/api/images/{location_id}_1.jpg",
        f"/api/images/{location_id}_2.jpg"
    ]

# Natural language hints for the N5 LLM when the user selects a chip
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
                logger.warning(f"Failed to read disk cache: {e}")

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
        logger.warning(f"Failed to write disk cache: {e}")

    return _CACHED_LOCATIONS_DATA
