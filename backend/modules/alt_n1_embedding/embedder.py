"""alt_n1: SentenceTransformer model loading and vector encoding for multilingual-e5-small."""

from __future__ import annotations
from typing import List, Optional
from config import ALT_EMBEDDING_MODEL_NAME, setup_logging

import os
from pathlib import Path

logger = setup_logging("alt_n1.embedder")
_MODEL = None

ALT_MODEL_NAME = ALT_EMBEDDING_MODEL_NAME



def get_model():
    """Return the globally loaded model, initializing it if necessary."""
    global _MODEL
    if _MODEL is None:
        try:
            logger.info(f"alt_n1 — Initializing Embedding Engine (Model: {ALT_MODEL_NAME})...")
            
            import torch
            from sentence_transformers import SentenceTransformer
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"alt_n1 — Loading weights onto {device} (this may take a few seconds)...")
            
            _MODEL = SentenceTransformer(ALT_MODEL_NAME, device=device)
            logger.info(f"alt_n1 — Embedding Model ready on {_MODEL.device}")
        except ImportError:
            logger.error("alt_n1 — sentence-transformers or torch not installed")
            raise RuntimeError("sentence-transformers or torch not installed")
        except Exception as e:
            logger.error(f"alt_n1 — Failed to load embedding model: {e}")
            raise RuntimeError(f"Failed to load embedding model: {e}")
    return _MODEL

# Pre-load model
get_model()

def embed_strings(strings: List[str], is_query: bool = False) -> List[Optional[List[float]]]:
    """
    Converts strings into normalized vectors using intfloat/multilingual-e5-small.
    Query/passage prefixes are automatically prepended as required by E5 models.
    """
    if not strings:
        return []

    model = get_model()

    # Separate non-empty strings, track original positions
    valid = [(i, t) for i, t in enumerate(strings) if t and t.strip()]
    if not valid:
        return [None] * len(strings)

    indices, to_encode = zip(*valid)
    
    # Prefix support for E5 multilingual models
    prefix = "query: " if is_query else "passage: "
    prefixed_to_encode = [prefix + t for t in to_encode]

    vectors = model.encode(
        prefixed_to_encode,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=False,
    ).tolist()

    # Reconstruct with None for empty slots
    output: List[Optional[List[float]]] = [None] * len(strings)
    for idx, vec in zip(indices, vectors):
        output[idx] = vec

    return output
