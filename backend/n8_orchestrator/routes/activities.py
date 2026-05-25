from __future__ import annotations
from flask import Blueprint, request, jsonify
from backend.shared.contracts.n1_contracts import N1EmbedInput
from backend.shared.contracts.n5_contracts import N5GenerateInput, N5UserInput, N5LocationItem, N5LocationMetadata
from backend.shared.contracts.n6_contracts import N6RankInput, UserInput
from backend.shared.contracts.n4_contracts import UserVectors
from backend.shared.contracts.n17_contracts import N17FeedbackInput
from backend.shared.contracts.n3_contracts import N3ActivityItem
from config import TOP_K_ACTIVITIES, API_DEBUG, setup_logging
from backend.n8_orchestrator.utils import _err, _get_json
from backend.n8_orchestrator.services import (
    embed,
    embed_batch,
    generate_activities,
    rank_activities,
    get_activities_for_location,
    process_feedback,
    get_weights,
    _safe_vec,
)

logger = setup_logging("N8.activities")

activities_bp = Blueprint("activities", __name__)

# ── Service logic built-in ──

def activities_service(body):
    text = body.get("text", "").strip()
    img_desc = body.get("img_desc", "")
    tags = body.get("tags", [])
    provider = body.get("provider")
    location = body.get("location", {})
    top_k_activities = int(body.get("top_k_activities", TOP_K_ACTIVITIES))

    # ── BGE-M3 — Build User Vectors ────────────
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

def _n5_fallback_generate(location: dict, preferred_types: list, top_k: int) -> list:
    from backend.n8_orchestrator.services import _TYPE_HINT_TEXT
    if preferred_types:
        user_text = "; ".join(_TYPE_HINT_TEXT.get(t, t) for t in preferred_types)
    else:
        user_text = ""

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

def activities_v2_service(body):
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

    # ── 1. Read activities from DB ──
    db_acts = get_activities_for_location(loc_id, include_vectors=True)
    logger.info("activities_v2: loc=%s db_acts=%d", loc_id, len(db_acts))
    
    for a in db_acts:
        vecs = a.get("vectors") or {}
        if "tag" in vecs:
            vecs["aug_tags"] = vecs.pop("tag")

    # ── 2. N5 fallback when DB is sparse ──
    fallback_used = False
    fallback_n5_count = 0
    if len(db_acts) < 3:
        logger.info("v2 DB sparse (n_acts=%d) loc=%s — triggering N5 fallback", len(db_acts), loc_id)
        n5_acts = _n5_fallback_generate(location, preferred_types, top_k)
        from modules.activity_retrievals.processor import _drop_anchor_duplicates
        n5_acts = _drop_anchor_duplicates(n5_acts, loc_name)
        if n5_acts:
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
                "warning":       "Location not yet seeded — run seed_activities.py",
            },
            "ranking_meta": {},
        }

    # ── 2.1. Embed missing vectors ──
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
        embedded_results = embed_batch(missing_inputs)
        for idx, res in zip(missing_indices, embedded_results):
            v = res.get("vectors") or {}
            db_acts[idx]["vectors"] = {
                "text": v.get("text"),
                "aug_tags": v.get("aug_tags") or v.get("tags"),
                "aug_text": v.get("aug_text"),
                "img_desc": v.get("img_desc")
            }

    # ── 3. Embed user_input if missing ──
    if not user_vectors or not user_vectors.get("text") or len(user_vectors.get("text", [])) != 1024:
        logger.info("activities_v2: embedding user input using BGE-M3...")
        n1_input = N1EmbedInput(
            text=text,
            tags=tags,
            img_desc=img_desc
        )
        user_emb = embed(n1_input)
        text_k = user_emb.get("text_k", 0)
        tags_k = user_emb.get("tags_k", 0)
        raw_vecs = user_emb.get("vectors") or {}
        user_vectors = {
            "text":     _safe_vec(raw_vecs.get("text")),
            "aug_text": _safe_vec(raw_vecs.get("aug_text")),
            "aug_tags": _safe_vec(raw_vecs.get("aug_tags")),
            "img_desc": _safe_vec(raw_vecs.get("img_desc")),
        }

    # ── 4. N6 rank ──
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

    # ── 5. Map to Frontend shape ──
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

def feedback_activities_service(body):
    old_text = body.get("text", "")
    old_tags = body.get("tags", [])
    old_img_desc = body.get("img_desc", "")
    feedback = body.get("feedback", "")
    is_v2 = body.get("v2", False)

    if not feedback:
        return activities_v2_service(body) if is_v2 else activities_service(body)

    logger.info(f"N17 — Processing activity feedback: '{feedback}'")
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
    
    # Force re-embedding because user inputs have been altered by feedback
    if "user_vectors" in new_body:
        del new_body["user_vectors"]
        
    if is_v2:
        result = activities_v2_service(new_body)
    else:
        result = activities_service(new_body)
    
    result["refined"] = {
        "text": new_body["text"],
        "tags": new_body["tags"],
        "img_desc": new_body["img_desc"],
        "explanation": refined.get("explanation", "")
    }
    
    return result

# ── Routes ──

@activities_bp.post("/activities")
def get_activities():
    body = request.get_json() or {}
    if not body.get("location"):
        return _err("Missing location data")
    try:
        result = activities_service(body)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Activities service failed: {e}")
        return _err(f"Internal error: {str(e)}", 500)

@activities_bp.post("/activities/v2")
def get_activities_v2():
    body = request.get_json() or {}
    if not body.get("location"):
        return _err("Missing location data")
    try:
        result = activities_v2_service(body)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Activities v2 service failed: {e}")
        return _err(f"Internal error: {str(e)}", 500)

@activities_bp.post("/feedback/activities")
def feedback_activities():
    body, err = _get_json()
    if err: return err
    if not body.get("feedback"): return _err("Missing feedback text")
    try:
        result = feedback_activities_service(body)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Feedback activities failed: {e}")
        return _err(f"Internal error: {str(e)}", 500)
