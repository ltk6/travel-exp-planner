"""N1: Unified multi-channel embedding API."""

from __future__ import annotations

from typing import Any

from .embedder import embed_strings
from .preprocessor import preprocess

from config import EMBEDDING_MODEL_NAME, setup_logging

logger = setup_logging("N1")


def embed(data: dict[str, Any]) -> dict[str, Any]:
    """
    Entry point to embed a single multi-channel input.
    """
    results = embed_batch([data])
    return results[0]


def embed_batch(data_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Entry point to embed multiple multi-channel inputs efficiently.
    Performs exactly one forward pass through the model.
    """
    if not data_list:
        return []

    import time

    t0 = time.time()

    # 1. Preprocess all inputs
    logger.info(f"Preprocessing {len(data_list)} inputs...")
    all_preprocessed = []
    for data in data_list:
        p = preprocess(
            text=data.get("text", ""),
            tags=data.get("tags", []),
            img_desc=data.get("img_desc", ""),
        )
        all_preprocessed.append(p)

    # 2. Flatten channels into one massive list
    channels = ["text", "aug_text", "aug_tags", "img_desc"]
    flat_strings = []
    for p in all_preprocessed:
        for ch in channels:
            flat_strings.append(p[ch])

    # 3. Batch encode (SentenceTransformer natively handles batching optimally)
    logger.info(
        f"Batch encoding {len(flat_strings)} strings "
        f"({len(data_list)} items * {len(channels)} channels)..."
    )
    flat_vectors = embed_strings(flat_strings)

    # 4. Unflatten back into per-item outputs
    logger.info("Unflattening vectors back to items...")
    results = []
    num_channels = len(channels)
    for i, p in enumerate(all_preprocessed):
        start_idx = i * num_channels
        item_vecs = flat_vectors[start_idx : start_idx + num_channels]

        results.append(
            {
                "text_k": p["text_k"],
                "tags_k": p["tags_k"],
                "preprocessed": {
                    "text": p["text"],
                    "aug_text": p["aug_text"],
                    "aug_tags": p["aug_tags"],
                    "img_desc": p["img_desc"],
                },
                "vectors": {
                    "text": item_vecs[0],
                    "aug_text": item_vecs[1],
                    "aug_tags": item_vecs[2],
                    "img_desc": item_vecs[3],
                },
            }
        )

    elapsed_ms = int((time.time() - t0) * 1000)
    logger.info(f"N1 embedding completed in {elapsed_ms}ms for {len(data_list)} items.")

    # 5. Add metadata to each result
    from .embedder import get_model

    model_instance = get_model()
    device = str(model_instance.device) if hasattr(model_instance, "device") else "unknown"

    for res in results:
        res["metadata"] = {
            "model": EMBEDDING_MODEL_NAME,
            "device": device,
            "latency_ms": elapsed_ms / len(data_list) if data_list else 0,
        }

    return results


__all__ = ["embed", "embed_batch"]
