"""
n8_api/app.py
=============
N8 – API Orchestrator (Flask)

Pipeline:
N2 (image → img_desc) → N1 (embed) → N3 (db) → N4 (rank locations) → N5 (generate activities) → N6 (rank activities)

Contract summary:
─────────────────────────────────────────────
N2 input:  { image: bytes }
N2 output: { img_desc: str }

N1 input:  { text, tags, img_desc }
N1 output: { sig_k, preprocessed, vectors: { text, aug_text, aug_tags, img_desc } }

N3 output: { status, total, data: [{ location_id, vectors: { text, aug_text, aug_tags, img_desc }, metadata, geo }] }

N4 input:  { sig_k, user_vectors: { text, aug_text, aug_tags, img_desc }, locations: [{ location_id, location_vectors: { text, tag } }], top_k }
N4 output: { locations: [{ location_id, score, reason }] }
─────────────────────────────────────────────
"""

from __future__ import annotations

import sys
import os
import logging
import base64
from typing import Any

from flask import Flask, request, jsonify
from flask_cors import CORS

# ── Path setup ────────────────────────────────────────────────
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

# ── Database ──────────────────────────────────────────────────
from n3_database import get_all_locations

# ── Modules ───────────────────────────────────────────────────
from modules.n1_embedding import embed, embed_batch
from modules.n2_image_processing import process_image
from modules.n4_location_ranking import rank_locations
from modules.n5_activity_generation.n5_activity_generator import generate_activities
from modules.n6_activity_ranking.rank_activities import rank_activities

# ── Shared ────────────────────────────────────────────────────
from shared.weights import get_weights

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("N8")

# ── App ───────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)


# ═════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════

def _err(msg: str, code: int = 400):
    return jsonify({"error": msg}), code


def _get_json():
    data = request.get_json(silent=True)
    if not data:
        return None, _err("Invalid JSON body")
    return data, None


def _safe_vec(v):
    """Ensure value is a Python list. Handles numpy arrays from pgvector."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    # numpy arrays from pgvector
    if hasattr(v, 'tolist'):
        return v.tolist()
    try:
        return list(v)
    except (TypeError, ValueError):
        return []


# ═════════════════════════════════════════════════════════════
# HEALTH
# ═════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "pipeline": ["n1", "n2", "n3", "n4", "n5", "n6"]
    })


# ═════════════════════════════════════════════════════════════
# FULL PIPELINE
# ═════════════════════════════════════════════════════════════

@app.post("/recommend")
def recommend():
    body, err = _get_json()
    if err:
        return err

    text = body.get("text", "").strip()
    image_b64 = body.get("image", "")
    tags = body.get("tags", [])
    constraints = body.get("constraints", {})
    context_data = body.get("context", {})
    top_k = int(body.get("top_k_locations", 5))
    top_k_activities = int(body.get("top_k_activities", 5))

    if not text and not tags:
        return _err("Provide text or tags")

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
    # N1 contract: { text, tags, img_desc } → { sig_k, preprocessed, vectors }
    n1_result = embed({
        "text": text,
        "tags": tags,
        "img_desc": img_desc
    })

    text_k = n1_result.get("text_k", 0)
    tags_k = n1_result.get("tags_k", 0)
    vectors = n1_result.get("vectors", {})

    # User vectors: text, aug_text, aug_tags, img_desc
    user_vectors = {
        "text":     _safe_vec(vectors.get("text")),
        "aug_text": _safe_vec(vectors.get("aug_text")),
        "aug_tags": _safe_vec(vectors.get("aug_tags")),
        "img_desc": _safe_vec(vectors.get("img_desc")),
    }

    # ── N3 — Fetch locations from DB ───────────
    db_result = get_all_locations()
    locations = db_result.get("data", []) if isinstance(db_result, dict) else []

    # ── Build N4 input ─────────────────────────
    n4_locations = []
    loc_map = {}

    for loc in locations:
        loc_id = loc.get("location_id", "unknown")
        db_vectors = loc.get("vectors", {}) or {}

        n4_locations.append({
            "location_id": loc_id,
            "location_vectors": {
                "text": _safe_vec(db_vectors.get("text")),
                "tag":  _safe_vec(db_vectors.get("aug_tags")),
            }
        })

        loc_map[loc_id] = {
            "vectors": db_vectors,
            "metadata": loc.get("metadata", {}),
            "geo": loc.get("geo", {}),
            "image_path": loc.get("image_path", ""),
        }

    # ── N4 — Rank locations ────────────────────
    n4_result = rank_locations({
        "text_k": text_k,
        "tags_k": tags_k,
        "user_vectors": user_vectors,
        "locations": n4_locations,
        "top_k": int(body.get("top_k_locations", 5)),
    })

    ranked = n4_result.get("locations", [])
    return jsonify({
        # ─────────────────────────────
        # MAIN CONTRACT (DO NOT CHANGE)
        # ─────────────────────────────
        "locations": [
            {
                "location_id": r["location_id"],
                "score": r.get("score", 0),
                "reason": r.get("reason", ""),

                "metadata": loc_map.get(r["location_id"], {}).get("metadata", {}),
                "geo": loc_map.get(r["location_id"], {}).get("geo", {}),
                "image_path": loc_map.get(r["location_id"], {}).get("image_path", ""),
            }
            for r in ranked
        ],
        
        # ─────────────────────────────
        # FULL TRACE (EVERYTHING)
        # ─────────────────────────────
        "trace": {
            # ─── USER SIDE ───
            "user": {
                "input": {
                    "text": text,
                    "tags": tags,
                    "constraints": constraints,
                    "context": context_data,
                    "has_image": bool(image_b64),
                },
                "n2_image": {
                    "img_desc": img_desc,
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

            # ─── LOCATION SIDE (RAW BEFORE RANKING) ───
            "locations_raw": [
                {
                    "location_id": loc.get("location_id"),
                    "metadata": loc.get("metadata", {}),
                    "geo": loc.get("geo", {}),
                }
                for loc in locations
            ],

            # ─── RANKING OUTPUT ───
            "ranking": {
                "text_k": text_k,
                "tags_k": tags_k,
                "weights_used": get_weights(text_k, tags_k),
                "top_k": int(body.get("top_k_locations", 5)),
                "ranked": ranked,
            },
            # ─── SYSTEM DEBUG ───
            "debug": {
                "total_locations": len(n4_locations),
                "pipeline": {
                    "n1": "embedding",
                    "n2": "image_processing",
                    "n3": "database_fetch",
                    "n4": "location_ranking"
                },
            },
        },
    })

# =========================================================================
# ACTIVITIES ENDPOINT (N5 -> N1 -> N6)
# =========================================================================

@app.route("/activities", methods=["POST"])
def get_activities():
    """
    Generate and rank activities for a SINGLE location.
    
    Expected body:
    {
      "text": str,
      "img_desc": str,
      "tags": list,
      "text_k": int,
      "tags_k": int,
      "user_vectors": dict,
      "constraints": dict,
      "context": dict,
      "location": { "location_id": str, "metadata": dict },
      "top_k_activities": int
    }
    """
    body = request.get_json() or {}
    text = body.get("text", "")
    img_desc = body.get("img_desc", "")
    tags = body.get("tags", [])
    text_k = body.get("text_k", 0)
    tags_k = body.get("tags_k", 0)
    user_vectors = body.get("user_vectors", {})
    constraints = body.get("constraints", {})
    context_data = body.get("context", {})
    location = body.get("location", {})
    top_k_activities = int(body.get("top_k_activities", 20))

    if not location:
        return _err("Missing location data")

    # ── N5 — Generate Activities ───────────────
    n5_input = {
        "user": {
            "text": text,
            "img_desc": img_desc,
            "tags": tags
        },
        "locations": [location],
        "constraints": constraints,
        "target_count": 10
    }
    n5_result = generate_activities(n5_input)
    activities = n5_result.get("activities", [])

    # ── Embed Activities via N1 ────────────────
    logger.info("Embedding %d activities for location '%s' via N1 (BATCH MODE)...", len(activities), location.get("location_id"))
    
    # Prepare batch
    n1_inputs = []
    for activity in activities:
        meta = activity.get("metadata", {})
        act_name = meta.get("name", "")
        act_desc = meta.get("description", "")
        act_text = f"{act_name} - {act_desc}".strip(" -")
        
        act_tags = []
        if meta.get("activity_type"):
            act_tags.append(meta.get("activity_type"))
        if meta.get("activity_subtype"):
            act_tags.append(meta.get("activity_subtype"))
            
        n1_inputs.append({
            "text": act_text,
            "tags": act_tags,
            "img_desc": ""
        })
        
    # Execute batch embedding
    if n1_inputs:
        n1_batch_results = embed_batch(n1_inputs)
        
        # Re-assign vectors to activities
        for activity, embed_res in zip(activities, n1_batch_results):
            activity["vectors"] = {
                "text": _safe_vec(embed_res.get("vectors", {}).get("text")),
                "tag":  _safe_vec(embed_res.get("vectors", {}).get("aug_tags"))
            }

    # ── N6 — Rank Activities ───────────────────
    n6_input = {
        "text_k": text_k,
        "tags_k": tags_k,
        "user_input": {
            "text": text,
            "img_desc": img_desc,
            "tags": tags
        },
        "user_vectors": user_vectors,
        "activities": activities,
        "constraints": constraints,
        "context": context_data,
        "top_k": top_k_activities
    }
    n6_result = rank_activities(n6_input)
    ranked_activities = n6_result.get("activities", [])

    # Enrich ranked activities with metadata from N5
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

    return jsonify({
        "status": "success",
        "location_id": location.get("location_id"),
        "activities": enriched_ranked_activities
    })


# ═════════════════════════════════════════════════════════════
# RUN
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)