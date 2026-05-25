"""
preferences.py — Rule-based inference of user activity preferences.

Receives user_input from N6 (tags + text + img_desc) and returns 3 preference scores
in [0, 1] corresponding to the 3 attribute axes of activity metadata:
    - intensity: preference for excitement / adventure
    - physical:  preference for physical activity
    - social:    preference for social / crowd interaction

Approach: lookup table from tags (highest weight) + keyword scan over text+img_desc
(small bonus). Deterministic — the same input always produces the same output, easy
to trace in reports without needing to mock an LLM.

Returns None for any axis that has no signal at all → scoring skips that axis
so activities are not unfairly penalised (neutral).
"""

from typing import Dict, List, Optional

from backend.shared.maps.tags import ALL_TAGS

_ALL_TAGS_KEYS = set(ALL_TAGS.keys())

# Score added per axis when a tag is present. Positive = pulls preference up,
# negative = pulls it down (meaning the user does NOT want that axis).
#
# Values: ±1 = strong, ±0.5 = medium, ±0.3 = mild. After aggregation
# through sigmoid, a few aligned tags push the score toward 0.8–0.95,
# while opposing tags pull it toward 0.05–0.2.
_TAG_WEIGHTS: Dict[str, Dict[str, float]] = {
    # ── Adventure / excitement ────────────────────────────────────────────
    "adventure":           {"intensity":  1.0, "physical":  0.8},
    "trekking":            {"intensity":  0.8, "physical":  1.0},
    "motorbiking":         {"intensity":  0.8, "physical":  0.5},
    "cycling":             {"intensity":  0.3, "physical":  0.8},
    "surfing":             {"intensity":  0.8, "physical":  0.8},
    "scuba diving":        {"intensity":  0.5, "physical":  0.5},
    "kayaking":            {"intensity":  0.5, "physical":  0.7},
    "camping":             {"intensity":  0.5, "physical":  0.5},
    "off the beaten path": {"intensity":  0.5, "social":   -0.3},

    # ── Relaxation / gentle ────────────────────────────────────────────
    "peaceful":  {"intensity": -0.8, "physical": -0.5, "social": -0.3},
    "cozy":      {"intensity": -0.5, "physical": -0.3, "social": -0.2},
    "spa":       {"intensity": -0.8, "physical": -0.8},
    "boat cruise": {"intensity": -0.3, "physical": -0.5},
    "homestay":  {"intensity": -0.3, "social":    0.3},

    # ── Social axis: group / crowds ─────────────────────────────────
    "family":       {"social":  0.8, "intensity": -0.3},
    "group":        {"social":  1.0},
    "friends trip": {"social":  0.8},
    "vibrant":      {"social":  0.8, "intensity":  0.3},
    "couple":       {"social": -0.2},
    "solo":         {"social": -1.0},
    "romantic":     {"social": -0.3, "intensity": -0.3},

    # ── Sightseeing / photography (neutral on primary axis) ────────────────
    "photography":   {"physical":  0.2},
    "cooking class": {"social":    0.3, "physical": -0.2},
}

assert set(_TAG_WEIGHTS.keys()).issubset(_ALL_TAGS_KEYS), f"Fabricated tags in _TAG_WEIGHTS: {set(_TAG_WEIGHTS.keys()) - _ALL_TAGS_KEYS}"

# Keywords in user free-text, used only as a bonus (lower weight than tags).
_KEYWORD_WEIGHTS: Dict[str, Dict[str, float]] = {
    # Vietnamese
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

    # English (img_desc from N2 is usually in English)
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

# Neutral 0.5; each axis score lands in [0,1] after sigmoid. If total signal < NEUTRAL_THRESHOLD
# the user is considered to have expressed no preference for that axis → return None.
NEUTRAL_THRESHOLD = 0.10


def _sigmoid(x: float) -> float:
    """Map raw signal ℝ → [0, 1]. x=0 → 0.5, x=±2 → ~0.88/0.12."""
    import math
    return 1.0 / (1.0 + math.exp(-x))


def infer_user_preferences(user_input: Dict) -> Dict[str, Optional[float]]:
    """
    Analyse user_input → preference on the 3 axes: intensity / physical / social.

    Args:
        user_input: {"text": str?, "img_desc": str?, "tags": [str]?}

    Returns:
        {"intensity": float|None, "physical": float|None, "social": float|None}
        - float in [0,1]: 1.0 = strongly prefers this axis, 0.0 = strongly opposed.
        - None: user did not express a clear preference → scoring will skip this axis.
    """
    raw = {axis: 0.0 for axis in _AXES}
    signal_count = {axis: 0 for axis in _AXES}

    # 1. Tags (highest weight)
    tags = [t.lower().strip() for t in (user_input.get("tags") or [])]
    for tag in tags:
        weights = _TAG_WEIGHTS.get(tag)
        if not weights:
            continue
        for axis, w in weights.items():
            raw[axis] += w
            signal_count[axis] += 1

    # 2. Keywords in text + img_desc (bonus, weight = 0.5 × tag weight)
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

    # 3. Sigmoid + threshold: axes with little/no signal → None
    result: Dict[str, Optional[float]] = {}
    for axis in _AXES:
        if signal_count[axis] == 0 or abs(raw[axis]) < NEUTRAL_THRESHOLD:
            result[axis] = None
        else:
            result[axis] = round(_sigmoid(raw[axis]), 3)

    return result
