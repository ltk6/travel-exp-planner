"""
preferences.py — Suy luận thiên hướng người dùng (rule-based).

Nhận user_input từ N6 (tags + text + img_desc), trả về 3 giá trị preference
trong [0, 1] tương ứng với 3 trục thuộc tính của activity metadata:
    - intensity: thích cảm giác kịch tính / mạo hiểm
    - physical:  thích vận động cơ thể
    - social:    thích tương tác đông người

Cách làm: lookup table từ tags (ưu tiên cao) + keyword scan trên text+img_desc
(bonus nhỏ). Deterministic — cùng input luôn ra cùng output, dễ trace trong
báo cáo mà không cần mock LLM.

Trả về None cho trục nào hoàn toàn không có tín hiệu → scoring sẽ bỏ qua trục đó
để không phạt oan activity (neutral).
"""

from __future__ import annotations

from typing import Dict, List, Optional

# Điểm add cho mỗi trục khi tag xuất hiện. Dương = kéo preference lên,
# âm = kéo xuống (nghĩa là user KHÔNG muốn trục đó).
#
# Giá trị ±1 là "mạnh", ±0.5 là "vừa", ±0.3 là "nhẹ". Sau khi tổng hợp
# qua sigmoid, vài tag cùng hướng sẽ đẩy điểm về 0.8-0.95, vài tag ngược
# hướng sẽ kéo về 0.05-0.2.
_TAG_WEIGHTS: Dict[str, Dict[str, float]] = {
    # ── Mạo hiểm / kịch tính ─────────────────────────────────────
    "adventure":           {"intensity":  1.0, "physical":  0.8},
    "trekking":            {"intensity":  0.8, "physical":  1.0},
    "motorbiking":         {"intensity":  0.8, "physical":  0.5},
    "cycling":             {"intensity":  0.3, "physical":  0.8},
    "surfing":             {"intensity":  0.8, "physical":  0.8},
    "snorkeling":          {"intensity":  0.5, "physical":  0.5},
    "kayaking":            {"intensity":  0.5, "physical":  0.7},
    "camping":             {"intensity":  0.5, "physical":  0.5},
    "off the beaten path": {"intensity":  0.5, "social":   -0.3},

    # ── Thư giãn / nhẹ nhàng ─────────────────────────────────────
    "peaceful":  {"intensity": -0.8, "physical": -0.5, "social": -0.3},
    "cozy":      {"intensity": -0.5, "physical": -0.3, "social": -0.2},
    "spa":       {"intensity": -0.8, "physical": -0.8},
    "relax":     {"intensity": -0.8, "physical": -0.5},
    "boat cruise": {"intensity": -0.3, "physical": -0.5},
    "homestay":  {"intensity": -0.3, "social":    0.3},

    # ── Social axis: nhóm / đông người ──────────────────────────
    "family":       {"social":  0.8, "intensity": -0.3},
    "group":        {"social":  1.0},
    "friends trip": {"social":  0.8},
    "vibrant":      {"social":  0.8, "intensity":  0.3},
    "couple":       {"social": -0.2},
    "solo":         {"social": -1.0},
    "romantic":     {"social": -0.3, "intensity": -0.3},

    # ── Sightseeing / photography (trung tính axis chính) ───────
    "photography":   {"physical":  0.2},
    "sightseeing":   {"intensity": -0.2, "physical": -0.2},
    "cooking class": {"social":    0.3, "physical": -0.2},
}

# Keywords trong free-text user mô tả, chỉ dùng bonus (nhẹ hơn tag weight).
_KEYWORD_WEIGHTS: Dict[str, Dict[str, float]] = {
    # Tiếng Việt
    "mạo hiểm":  {"intensity":  0.5},
    "kịch tính": {"intensity":  0.5},
    "thử thách": {"intensity":  0.4, "physical":  0.4},
    "leo núi":   {"intensity":  0.5, "physical":  0.6},
    "vận động":  {"physical":   0.5},
    "thể thao":  {"physical":   0.5, "intensity":  0.3},
    "thư giãn":  {"intensity": -0.6, "physical": -0.3},
    "yên tĩnh":  {"intensity": -0.5, "social":   -0.3},
    "yên bình":  {"intensity": -0.5, "social":   -0.3},
    "nghỉ ngơi": {"intensity": -0.5, "physical": -0.3},
    "đông vui":  {"social":     0.5},
    "bạn bè":    {"social":     0.4},
    "gia đình":  {"social":     0.5, "intensity": -0.2},
    "một mình":  {"social":    -0.8},
    "lãng mạn":  {"social":    -0.3, "intensity": -0.2},

    # Tiếng Anh (img_desc từ N2 thường là English)
    "adventure":  {"intensity":  0.5},
    "exciting":   {"intensity":  0.4},
    "hiking":     {"intensity":  0.4, "physical":  0.5},
    "climbing":   {"intensity":  0.5, "physical":  0.6},
    "active":     {"physical":   0.4},
    "peaceful":   {"intensity": -0.5, "social":   -0.2},
    "quiet":      {"intensity": -0.4, "social":   -0.3},
    "relaxing":   {"intensity": -0.5, "physical": -0.3},
    "family":     {"social":     0.4},
    "crowd":      {"social":     0.4},
    "bustling":   {"social":     0.5},
    "solo":       {"social":    -0.5},
}

_AXES = ("intensity", "physical", "social")

# Neutral 0.5, mỗi axis score rơi trong [0,1] sau sigmoid. Nếu tổng signal < NEUTRAL_THRESHOLD
# thì coi như user không nêu preference cho axis đó → trả None.
NEUTRAL_THRESHOLD = 0.25


def _sigmoid(x: float) -> float:
    """Map raw signal ℝ → [0, 1]. x=0 → 0.5, x=±2 → ~0.88/0.12."""
    import math
    return 1.0 / (1.0 + math.exp(-x))


def infer_user_preferences(user_input: Dict) -> Dict[str, Optional[float]]:
    """
    Phân tích user_input → preference trên 3 trục intensity/physical/social.

    Args:
        user_input: {"text": str?, "img_desc": str?, "tags": [str]?}

    Returns:
        {"intensity": float|None, "physical": float|None, "social": float|None}
        - float trong [0,1]: 1.0 = rất thích trục này, 0.0 = rất không muốn.
        - None: user không bày tỏ preference rõ → scoring sẽ skip trục này.
    """
    raw = {axis: 0.0 for axis in _AXES}
    signal_count = {axis: 0 for axis in _AXES}

    # 1. Tags (weight mạnh nhất)
    tags = [t.lower().strip() for t in (user_input.get("tags") or [])]
    for tag in tags:
        weights = _TAG_WEIGHTS.get(tag)
        if not weights:
            continue
        for axis, w in weights.items():
            raw[axis] += w
            signal_count[axis] += 1

    # 2. Keywords trong text + img_desc (bonus, weight = 0.5 × tag)
    haystack = " ".join(filter(None, [
        (user_input.get("text") or "").lower(),
        (user_input.get("img_desc") or "").lower(),
    ]))
    if haystack:
        for kw, weights in _KEYWORD_WEIGHTS.items():
            if kw in haystack:
                for axis, w in weights.items():
                    raw[axis] += 0.5 * w
                    signal_count[axis] += 1

    # 3. Sigmoid + threshold: axis ít/không có tín hiệu → None
    result: Dict[str, Optional[float]] = {}
    for axis in _AXES:
        if signal_count[axis] == 0 or abs(raw[axis]) < NEUTRAL_THRESHOLD:
            result[axis] = None
        else:
            result[axis] = round(_sigmoid(raw[axis]), 3)

    return result
