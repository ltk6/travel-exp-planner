"""N1: SentenceTransformer model loading and vector encoding."""

from __future__ import annotations
from typing import List, Optional
from config import EMBEDDING_MODEL_NAME, setup_logging

logger = setup_logging("N1.embedder")
_MODEL = None

def get_model():
    """Return the globally loaded model, initializing it if necessary."""
    global _MODEL
    if _MODEL is None:
        try:
            # Log first so the user knows what's taking time
            logger.info(f"N1 — Initializing Embedding Engine (Model: {EMBEDDING_MODEL_NAME})...")
            
            # Heavy imports happen here
            import torch
            from sentence_transformers import SentenceTransformer
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"N1 — Loading weights onto {device} (this may take a few seconds)...")
            
            _MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)
            logger.info(f"N1 — Embedding Model ready on {_MODEL.device}")
        except ImportError:
            logger.error("N1 — sentence-transformers or torch not installed")
            raise RuntimeError("sentence-transformers or torch not installed")
        except Exception as e:
            logger.error(f"N1 — Failed to load embedding model: {e}")
            raise RuntimeError(f"Failed to load embedding model: {e}")
    return _MODEL

# Pre-load at module level to avoid lazy-loading delays during user requests
get_model()


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