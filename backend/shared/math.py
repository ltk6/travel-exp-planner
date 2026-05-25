"""
Math utilities shared among the ranking modules (N4 location ranking, N6 activity ranking).
"""

from __future__ import annotations

import math
from typing import Optional, Sequence


def cosine(a: Optional[Sequence[float]], b: Optional[Sequence[float]]) -> float:
    """
    Cosine similarity between two vectors. Returns 0.0 if:
    - One of the vectors is None or empty.
    - The two vectors have different lengths.
    - One of the vectors has norm = 0 (all zeros).

    The result is in the range [-1.0, 1.0].
    """
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def cosine_normalized_unit(a: Optional[Sequence[float]], b: Optional[Sequence[float]]) -> float:
    """
    Cosine similarity shifted/scaled to [0.0, 1.0]: `(cos + 1) / 2`.

    Used when merging similarity into a total score [0, 1] along with other signals
    (constraint score, context score, etc.) — avoiding negative scores.
    """
    return (cosine(a, b) + 1.0) / 2.0
