"""
views/result/api.py
Fetches activity recommendations from the backend for a given location.
Errors are allowed to propagate naturally — callers handle them.
"""
import requests
import time
from config import setup_logging, INTERNAL_API_KEY, API_PORT
logger = setup_logging("N7.api")

_BACKEND_HEADERS = {"X-Internal-Key": INTERNAL_API_KEY}

def fetch_recommendations(payload: dict) -> dict:
    url = f"http://localhost:{API_PORT}/recommend"
    logger.info(f"Fetching recommendations from {url}")
    start = time.time()
    response = requests.post(
        url,
        json=payload,
        headers=_BACKEND_HEADERS,
        timeout=120,
    )
    duration = time.time() - start
    logger.info(f"POST {url} took {duration:.4f}s")
    response.raise_for_status()
    return response.json()

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
    url = f"http://localhost:{API_PORT}/activities"
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
    start = time.time()
    response = requests.post(
        url,
        json=payload,
        headers=_BACKEND_HEADERS,
        timeout=120,
    )
    duration = time.time() - start
    logger.info(f"POST {url} took {duration:.4f}s")
    response.raise_for_status()
    return response.json()

def send_feedback(endpoint: str, body: dict) -> dict:
    url = f"http://localhost:{API_PORT}/feedback/{endpoint}"
    logger.info(f"Sending feedback to {url}")
    start = time.time()
    response = requests.post(
        url,
        json=body,
        headers=_BACKEND_HEADERS,
        timeout=120,
    )
    duration = time.time() - start
    logger.info(f"POST {url} took {duration:.4f}s")
    response.raise_for_status()
    return response.json()