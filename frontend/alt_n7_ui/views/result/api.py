"""
views/result/api.py

Fetches activity recommendations from the backend for a given location.
Errors are allowed to propagate naturally — callers handle them.
"""
import requests


def fetch_activities(
    loc_id: str,
    meta: dict,
    user_text: str,
    img_desc: str,
    tags: list,
    sig_k: float,
    user_vectors: dict,
) -> list:
    payload = {
        "text": user_text,
        "img_desc": img_desc,
        "tags": tags,
        "sig_k": sig_k,
        "user_vectors": user_vectors,
        "constraints": {},
        "context": {},
        "location": {"location_id": loc_id, "metadata": meta},
    }
    response = requests.post(
        "http://localhost:5000/activities",
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("activities", [])