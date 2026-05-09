import logging
import base64
from flask import jsonify

from .n8_config import logger
from .utils import safe_vec
from shared.weights import get_weights

# ── Database ──────────────────────────────────────────────────
from n3_database import get_all_locations

# ── Modules ───────────────────────────────────────────────────
from modules.n1_embedding import embed, embed_batch
from modules.n2_image_processing import process_image
from modules.n4_location_ranking import rank_locations
from modules.n5_activity_generation.n5_activity_generator import generate_activities
from modules.n6_activity_ranking.rank_activities import rank_activities

# ── Global Cache ──────────────────────────────────────────────
_CACHED_LOCATIONS_DATA = None

def get_all_locations_cached():
    """Fetch locations once and cache them in memory for the life of the process."""
    global _CACHED_LOCATIONS_DATA
    if _CACHED_LOCATIONS_DATA is None:
        logger.info("First request: Fetching and caching locations from N3...")
        db_result = get_all_locations()
        _CACHED_LOCATIONS_DATA = db_result.get("data", []) if isinstance(db_result, dict) else []
    return _CACHED_LOCATIONS_DATA

def run_recommendation_pipeline(body: dict):
    """Executes the full location recommendation pipeline."""
    logger.info("--- START RECOMMENDATION PIPELINE ---")

    text = body.get("text", "").strip()
    images_b64 = body.get("images", []) or ([body.get("image")] if body.get("image") else [])
    tags = body.get("tags", [])
    context_data = body.get("context", {})
    top_k = int(body.get("top_k_locations", 5))

    # ── N2 — Image Processing ──
    img_descs = []
    if images_b64:
        logger.info(f"Stage: N2 (Image Processing) for {len(images_b64)} images")
        for i, b64_str in enumerate(images_b64):
            try:
                img_bytes = base64.b64decode(b64_str)
                n2_result = process_image({"image": img_bytes})
                desc = n2_result.get("img_desc", "")
                if desc:
                    img_descs.append(desc)
            except Exception as e:
                logger.warning(f"N2 failed for image {i+1}: {e}")
    
    img_desc = ". ".join(img_descs)

    # ── N1 — User Embedding ──
    logger.info("Stage: N1 (User Embedding)")
    n1_result = embed({
        "text": text,
        "tags": tags,
        "img_desc": img_desc
    })
    
    text_k = n1_result.get("text_k", 0)
    tags_k = n1_result.get("tags_k", 0)
    vectors = n1_result.get("vectors", {})

    user_vectors = {
        "text":     safe_vec(vectors.get("text")),
        "aug_text": safe_vec(vectors.get("aug_text")),
        "aug_tags": safe_vec(vectors.get("aug_tags")),
        "img_desc": safe_vec(vectors.get("img_desc")),
    }

    # ── N3 — Fetch Locations ──
    locations = get_all_locations_cached()
    
    # ── Build N4 Input ──
    n4_locations = []
    loc_map = {}
    for loc in locations:
        loc_id = loc.get("location_id", "unknown")
        db_vectors = loc.get("vectors", {}) or {}
        n4_locations.append({
            "location_id": loc_id,
            "location_vectors": {
                "text": safe_vec(db_vectors.get("text")),
                "aug_tags": safe_vec(db_vectors.get("aug_tags")),
            }
        })
        loc_map[loc_id] = {
            "vectors": db_vectors,
            "metadata": loc.get("metadata", {}),
            "geo": loc.get("geo", {}),
            "images": loc.get("images", []),
        }

    # ── N4 — Rank Locations ──
    logger.info(f"Stage: N4 (Location Ranking) for top_k={top_k}")
    n4_result = rank_locations({
        "text_k": text_k,
        "tags_k": tags_k,
        "user_vectors": user_vectors,
        "locations": n4_locations,
        "top_k": top_k,
    })

    ranked = n4_result.get("locations", [])
    
    # ── Format Final Response ──
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
                    "context": context_data,
                    "image_count": len(images_b64),
                },
                "n2_image": {
                    "img_descs": img_descs,
                    "combined_desc": img_desc,
                },
                "n1_embedding": {
                    "text_k": text_k,
                    "tags_k": tags_k,
                    "preprocessed": n1_result.get("preprocessed", {}),
                },
                "user_vectors": user_vectors,
                "vector_dims": {
                    k: len(v) if v else 0
                    for k, v in user_vectors.items()
                },
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
                "pipeline": {
                    "n1": "embedding",
                    "n2": "image_processing",
                    "n3": "database_cache",
                    "n4": "location_ranking"
                },
            },
        },
    }

def run_activities_pipeline(body: dict):
    """Executes the activity generation and ranking pipeline."""
    text = body.get("text", "")
    img_desc = body.get("img_desc", "")
    tags = body.get("tags", [])
    text_k = body.get("text_k", 0)
    tags_k = body.get("tags_k", 0)
    user_vectors = body.get("user_vectors", {})
    location = body.get("location", {})
    top_k_activities = int(body.get("top_k_activities", 20))
    
    loc_id = location.get("location_id", "unknown")
    logger.info(f"--- START ACTIVITIES PIPELINE for {loc_id} ---")

    # ── N5 — Generate Activities ──
    n5_result = generate_activities({
        "user": {"text": text, "img_desc": img_desc, "tags": tags},
        "locations": [location],
        "target_count": 10
    })
    activities = n5_result.get("activities", [])

    # ── Embed Activities (N1 Batch) ──
    n1_inputs = []
    for activity in activities:
        meta = activity.get("metadata", {})
        act_text = f"{meta.get('name', '')} - {meta.get('description', '')}".strip(" -")
        act_tags = [t for t in [meta.get("activity_type"), meta.get("activity_subtype")] if t]
        n1_inputs.append({"text": act_text, "tags": act_tags, "img_desc": ""})
        
    if n1_inputs:
        n1_batch_results = embed_batch(n1_inputs)
        for activity, embed_res in zip(activities, n1_batch_results):
            activity["vectors"] = {
                "text":     safe_vec(embed_res.get("vectors", {}).get("text")),
                "aug_tags": safe_vec(embed_res.get("vectors", {}).get("aug_tags"))
            }

    # ── N6 — Rank Activities ──
    n6_result = rank_activities({
        "text_k": text_k, "tags_k": tags_k,
        "user_vectors": user_vectors,
        "activities": activities,
        "top_k": top_k_activities
    })
    ranked_activities = n6_result.get("activities", [])

    # Enrich with metadata
    act_map = {act.get("activity_id"): act for act in activities}
    return {
        "status": "success",
        "location_id": loc_id,
        "activities": [
            {
                **r_act,
                "metadata": act_map.get(r_act["activity_id"], {}).get("metadata", {})
            }
            for r_act in ranked_activities
        ]
    }
