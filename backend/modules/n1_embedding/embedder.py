"""
Loads the sentence embedding model and converts text channels into normalized vectors.
Model: BAAI/bge-m3 (568M params, 1024-dim, 100+ languages, top VN-MTEB score).
"""

from __future__ import annotations
from typing import List, Optional
import torch

MODEL_NAME = "BAAI/bge-m3"

try:
    from sentence_transformers import SentenceTransformer
    print(f"[Embedding] Loading '{MODEL_NAME}' onto GPU...")
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    _MODEL = SentenceTransformer(MODEL_NAME, device=_device)
    print(f"[Embedding] Ready. Device: {_MODEL.device}")
except ImportError:
    raise RuntimeError("sentence-transformers or torch not installed")
except Exception as e:
    raise RuntimeError(f"Failed to load embedding model: {e}")


def get_model():
    """Return the globally loaded model."""
    return _MODEL


def embed_texts(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Encode strings into normalized embeddings. Empty strings yield None.
    """
    if not texts:
        return []

    model = get_model()

    # Separate non-empty texts, track original positions
    valid = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
    if not valid:
        return [None] * len(texts)

    indices, strings = zip(*valid)
    vectors = model.encode(
        list(strings),
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=False,
    ).tolist()

    # Reconstruct with None for empty slots
    output: List[Optional[List[float]]] = [None] * len(texts)
    for idx, vec in zip(indices, vectors):
        output[idx] = vec

    return output