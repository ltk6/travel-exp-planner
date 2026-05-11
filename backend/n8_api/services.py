import base64
from config.settings import (
    TOP_K_LOCATIONS, TOP_K_ACTIVITIES, LLM_N5_TARGET_COUNT, setup_logging
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
_CACHED_LOCATIONS_DATA = None

def get_all_locations_cached():
    """Fetch locations once and cache them in memory for the life of the process."""
    global _CACHED_LOCATIONS_DATA
    if _CACHED_LOCATIONS_DATA is None:
        logger.info("First request: Fetching and caching locations from N3...")
        db_result = get_all_locations()
        _CACHED_LOCATIONS_DATA = db_result.get("data", []) if isinstance(db_result, dict) else []
    return _CACHED_LOCATIONS_DATA

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

        loc_map[loc_id] = {
            "vectors": db_vectors,
            "metadata": loc.get("metadata", {}),
            "geo": loc.get("geo", {}),
            "images": loc.get("images", [])[:3],
        }

    # ── N4 — Rank locations ────────────────────
    n4_result = rank_locations({
        "text_k": text_k,
        "tags_k": tags_k,
        "user_vectors": user_vectors,
        "locations": n4_locations,
        "top_k": top_k,
    })

    ranked = n4_result.get("locations", [])
    
    return {
        "locations": [
            {
                "location_id": r["location_id"],
                "score": r.get("score", 0),
                "reason": r.get("reason", ""),
                "metadata": loc_map.get(r["location_id"], {}).get("metadata", {}),
                "geo": loc_map.get(r["location_id"], {}).get("geo", {}),
                "images": loc_map.get(r["location_id"], {}).get("images", []),
            }
            for r in ranked
        ],
        "trace": {
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
    }

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
