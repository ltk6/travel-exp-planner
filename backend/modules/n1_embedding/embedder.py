"""
Loads the sentence embedding model and converts text channels into normalized vectors.
Model: BAAI/bge-m3 (568M params, 1024-dim, 100+ languages).
"""

from __future__ import annotations

from typing import List, Optional

MODEL_NAME = "BAAI/bge-m3"

try:
    from sentence_transformers import SentenceTransformer
    print(f"[Embedding] Loading '{MODEL_NAME}' into memory...")
    _MODEL = SentenceTransformer(MODEL_NAME)
    print(f"[Embedding] Ready. Device: {_MODEL.device}")
except ImportError:
    raise RuntimeError("sentence-transformers not installed")
except Exception as e:
    raise RuntimeError(f"Failed to load embedding model: {e}")


def get_model():
    """Return the globally loaded model."""
    return _MODEL


def embed_strings(strings: List[str]) -> List[Optional[List[float]]]:
    """
    Converts strings into normalized vectors.
    Return None for empty strings.
    """
    if not strings:
        return []

    model = get_model()

    # Separate non-empty strings, track original positions
    valid = [(i, t) for i, t in enumerate(strings) if t and t.strip()]
    if not valid:
        return [None] * len(strings)

    indices, to_encode = zip(*valid)
    vectors = model.encode(
        list(to_encode),
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=False,
    ).tolist()

    # Reconstruct with None for empty slots
    output: List[Optional[List[float]]] = [None] * len(strings)
    for idx, vec in zip(indices, vectors):
        output[idx] = vec

    return output