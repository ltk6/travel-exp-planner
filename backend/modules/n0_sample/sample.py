"""Simplest possible reference implementation for a module."""
from typing import Any
import time

def run_sample(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize input and return the standard data/metadata envelope."""
    t0 = time.time()
    
    # 1. Extract & simple cleaning
    text = str(data.get("text", "")).strip()
    tags = data.get("tags", [])
    if not isinstance(tags, list): tags = []
    
    # 2. Build response
    return {
        "data": {
            "text": text,
            "tags": [str(t).strip() for t in tags if str(t).strip()],
        },
        "metadata": {
            "module": "n0_sample",
            "latency_ms": int((time.time() - t0) * 1000)
        }
    }
