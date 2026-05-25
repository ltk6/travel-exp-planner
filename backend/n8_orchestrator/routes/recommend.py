from __future__ import annotations
import base64
from flask import Blueprint, request, jsonify
from backend.shared.contracts.n4_contracts import N4RankInput, UserVectors
from backend.shared.contracts.n2_contracts import N2ImageInput
from backend.shared.contracts.n1_contracts import N1EmbedInput
from backend.shared.contracts.n17_contracts import N17FeedbackInput
from config import TOP_K_LOCATIONS, TOP_K_ACTIVITIES, API_DEBUG, setup_logging
from backend.n8_orchestrator.utils import _err, _get_json
from backend.n8_orchestrator.services import (
    embed,
    rank_locations,
    process_feedback,
    get_weights,
    process_image,
    get_all_locations_cached,
    _get_image_urls,
    _safe_vec,
)

logger = setup_logging("N8.recommend")

recommend_bp = Blueprint("recommend", __name__)

# ── Service logic built-in ──

def recommend_service(body):
    text = body.get("text", "").strip()
    tags = body.get("tags", [])
    constraints = body.get("constraints", {})
    context_data = body.get("context", {})
    top_k = int(body.get("top_k_locations", TOP_K_LOCATIONS))
    top_k_activities = int(body.get("top_k_activities", TOP_K_ACTIVITIES))

    logger.info("N8 — Starting recommendation flow (text='%s', tags=%s)", text, tags)

    # ── N2 — Image → img_desc ──────────────────
    img_desc = body.get("img_desc", "")
    image_b64 = ""
    if not img_desc:
        image_b64 = body.get("image", "")
        if not image_b64 and body.get("images"):
            imgs = body.get("images", [])
            if isinstance(imgs, list) and len(imgs) > 0:
                image_b64 = imgs[0]

        if image_b64:
            try:
                logger.info("N8 — Base64 image detected. Processing via N2 (Llama Vision)...")
                b64_data = image_b64.split(",")[1] if "," in image_b64 else image_b64
                img_bytes = base64.b64decode(b64_data)
                n2_input = N2ImageInput(image=img_bytes)
                n2_result = process_image(n2_input)
                img_desc = n2_result.get("img_desc", "")
                logger.info("N8 — N2 processing complete. Generated img_desc: '%s'", img_desc)
            except Exception as e:
                logger.warning(f"N2 processing failed: {e}")

    # ── N1 — Build User Vectors ────────────────
    logger.info("N8 — Building user preferences & vector embeddings using N1 (BGE-M3)...")
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
    logger.info("N8 — Retrieved %d location candidates from N3 cache/database.", len(locations))

    # ── N4 — Rank Locations ───────────────────
    logger.info("N8 — Ranking candidate locations using N4 Ranker (text_k=%d, tags_k=%d)...", text_k, tags_k)
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
        original = next((l for l in locations if l["location_id"] == loc_id), {})
        loc_rank["metadata"] = original.get("metadata", {})
        loc_rank["geo"] = original.get("geo", {})

    top_match = ranked[0].get("location_id", "N/A") if ranked else "None"
    top_score = ranked[0].get("score", 0.0) if ranked else 0.0
    logger.info("N8 — Completed recommendation. Top location match: '%s' with score %.4f", top_match, top_score)

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

    if body.get("refined"):
        response["refined"] = body["refined"]

    return response

def feedback_recommend_service(body):
    old_text = body.get("text", "")
    old_tags = body.get("tags", [])
    old_img_desc = body.get("img_desc", "")
    feedback = body.get("feedback", "")

    if not feedback:
        logger.info("N8 — No feedback text provided. Executing standard recommendation flow.")
        return recommend_service(body)

    logger.info("N8 (N17) — Processing recommend feedback: '%s'", feedback)
    feedback_input = N17FeedbackInput(
        user_input=old_text,
        user_tags=old_tags,
        img_desc=old_img_desc,
        feedback_text=feedback
    )
    refined = process_feedback(feedback_input)
    
    new_body = body.copy()
    new_body["text"] = refined.get("refined_text", old_text)
    new_body["tags"] = refined.get("refined_tags", old_tags)
    new_body["img_desc"] = refined.get("refined_img_desc", old_img_desc)
    
    logger.info("N8 (N17) — Feedback refined successfully. New Text: '%s', New Tags: %s", new_body["text"], new_body["tags"])
    result = recommend_service(new_body)
    
    result["refined"] = {
        "text": new_body["text"],
        "tags": new_body["tags"],
        "img_desc": new_body["img_desc"],
        "explanation": refined.get("explanation", "")
    }
    
    return result

# ── Routes ──

@recommend_bp.post("/recommend")
def recommend():
    body, err = _get_json()
    if err: return err

    if not body.get("text") and not body.get("tags") and not body.get("image") and not body.get("images") and not body.get("img_desc"):
        return _err("Provide text, tags, or image")

    try:
        result = recommend_service(body)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Recommend service failed: {e}")
        return _err(f"Internal error: {str(e)}", 500)

@recommend_bp.post("/feedback/recommend")
def feedback_recommend():
    body, err = _get_json()
    if err: return err
    if not body.get("feedback"): return _err("Missing feedback text")
    try:
        result = feedback_recommend_service(body)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Feedback recommend failed: {e}")
        return _err(f"Internal error: {str(e)}", 500)
