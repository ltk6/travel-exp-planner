"""
views/result/api.py

Fetches activity recommendations from the backend for a given location.
Errors are allowed to propagate naturally — callers handle them.
"""
import requests
import logging
import os

logger = logging.getLogger("alt_n7.result.api")

_INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "")
_BACKEND_HEADERS = {"X-Internal-Key": _INTERNAL_KEY}


def fetch_activities(
    loc_id: str,
    meta: dict,
    user_text: str,
    img_desc: str,
    tags: list,
    text_k: int,
    tags_k: int,
    user_vectors: dict,
) -> list:
    payload = {
        "text": user_text,
        "img_desc": img_desc,
        "tags": tags,
        "text_k": text_k,
        "tags_k": tags_k,
        "user_vectors": user_vectors,
        "location": {"location_id": loc_id, "metadata": meta},
    }
    logger.info(f"Requesting activities for {loc_id}")
    response = requests.post(
        "http://localhost:5000/activities",
        json=payload,
        headers=_BACKEND_HEADERS,
        timeout=120,
    )
    if response.status_code == 200:
        logger.info(f"Successfully fetched activities for {loc_id}")
    else:
        logger.error(f"Failed to fetch activities for {loc_id}: {response.status_code}")
    response.raise_for_status()
    return response.json().get("activities", [])