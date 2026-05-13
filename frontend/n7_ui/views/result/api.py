"""
views/result/api.py

Fetches activity recommendations from the backend for a given location.
Errors are allowed to propagate naturally — callers handle them.
"""
import requests
from config import setup_logging, INTERNAL_API_KEY, API_PORT
logger = setup_logging("N7.api")

_BACKEND_HEADERS = {"X-Internal-Key": INTERNAL_API_KEY}
_BACKEND_URL = f"http://localhost:{API_PORT}/activities"


def fetch_activities(
    loc_id: str,
    meta: dict,
    user_text: str,
    img_desc: str,
    tags: list,
    text_k: int,
    tags_k: int,
    user_vectors: dict,
    provider: str = None,
    top_k_activities: int = 5,
) -> dict:
    payload = {
        "text": user_text,
        "img_desc": img_desc,
        "tags": tags,
        "text_k": text_k,
        "tags_k": tags_k,
        "user_vectors": user_vectors,
        "location": {"location_id": loc_id, "metadata": meta},
        "provider": provider,
        "top_k_activities": top_k_activities,
    }
    logger.info(f"Requesting activities for {loc_id}")
    response = requests.post(
        _BACKEND_URL,
        json=payload,
        headers=_BACKEND_HEADERS,
        timeout=120,
    )
    if response.status_code == 200:
        logger.info(f"Successfully fetched activities for {loc_id}")
    else:
        logger.error(f"Failed to fetch activities for {loc_id}: {response.status_code}")
    response.raise_for_status()
    return response.json()