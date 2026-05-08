"""
n1_embedding — Unified embedding API.
Preprocesses multi-channel inputs, generates vectors, and returns signal metadata.

embed(data: Dict[str, Any]) -> Dict[str, Any]
embed_batch(data_list: list[Dict[str, Any]]) -> list[Dict[str, Any]]

SINGLE DICT INPUT:
{
    "text":     str,
    "tags":     list[str],
    "img_desc": str
}

SINGLE DICT INPUT:
{
    "text_k":     int,
    "tags_k":     int,
    "vectors": {
        "text":     list[float] | None,
        "aug_text": list[float] | None,
        "aug_tags": list[float] | None,
        "img_desc": list[float] | None,
    },
    "preprocessed": {
        "text":     str,
        "aug_text": str,
        "aug_tags": str,
        "img_desc": str,
    }
}

BATCH INPUT:
[
    SINGLE DICT INPUT,
    ...
]

BATCH OUTPUT:
[
    SINGLE DICT OUTPUT,
    ...
]
"""

from __future__ import annotations

from typing import Dict, Any

from .embedder import embed_strings
from .preprocessor import preprocess

def embed(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point to embed a single multi-channel input.
    """
    results = embed_batch([data])
    return results[0]


def embed_batch(data_list: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """
    Entry point to embed multiple multi-channel inputs efficiently.
    Performs exactly one forward pass through the model.
    """
    if not data_list:
        return []

    # 1. Preprocess all inputs
    all_preprocessed = []
    for data in data_list:
        p = preprocess(
            text     = data.get("text", ""),
            tags     = data.get("tags", []),
            img_desc = data.get("img_desc", ""),
        )
        all_preprocessed.append(p)

    # 2. Flatten channels into one massive list
    channels = ["text", "aug_text", "aug_tags", "img_desc"]
    flat_strings = []
    for p in all_preprocessed:
        for ch in channels:
            flat_strings.append(p[ch])

    # 3. Batch encode (SentenceTransformer natively handles batching optimally)
    flat_vectors = embed_strings(flat_strings)

    # 4. Unflatten back into per-item outputs
    results = []
    num_channels = len(channels)
    for i, p in enumerate(all_preprocessed):
        start_idx = i * num_channels
        item_vecs = flat_vectors[start_idx : start_idx + num_channels]
        
        results.append({
            "text_k": p["text_k"],
            "tags_k": p["tags_k"],
            "preprocessed": {
                "text":     p["text"],
                "aug_text": p["aug_text"],
                "aug_tags": p["aug_tags"],
                "img_desc": p["img_desc"],
            },
            "vectors": {
                "text":     item_vecs[0],
                "aug_text": item_vecs[1],
                "aug_tags": item_vecs[2],
                "img_desc": item_vecs[3],
            },
        })

    return results

__all__ = ["embed", "embed_batch"]