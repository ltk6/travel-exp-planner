"""
Math utilities shared giữa các ranking module (N4 location ranking, N6 activity ranking).
"""

from __future__ import annotations

import math
from typing import Optional, Sequence


def cosine(a: Optional[Sequence[float]], b: Optional[Sequence[float]]) -> float:
    """
    Cosine similarity giữa hai vector. Trả về 0.0 nếu:
    - Một trong hai vector là None hoặc rỗng.
    - Hai vector khác độ dài.
    - Một trong hai vector có norm = 0 (toàn zero).

    Kết quả nằm trong [-1.0, 1.0].
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
    Cosine similarity được dịch về [0.0, 1.0]: `(cos + 1) / 2`.

    Dùng khi cần đưa similarity vào điểm tổng [0, 1] cùng các signal khác
    (constraint score, context score, …) — tránh điểm âm.
    """
    return (cosine(a, b) + 1.0) / 2.0
