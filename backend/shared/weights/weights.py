"""
Shared weighting logic for ranking modules.
Centralizes tier-based dynamic weight calculation using text_k and tag_k signals.
"""

def get_text_tier(text_k: int) -> int:
    """Map keyword expansion count from text to a tier 0-3."""
    if text_k == 0: return 0    # no keywords, aug_text must be 0
    if text_k <= 2: return 1    # aug_text peaks
    if text_k <= 4: return 2    # text reclaims weight from aug_text
    return 3                    # rich text

def get_tags_tier(tags_k: int) -> int:
    """Map keyword expansion count from tags to a tier 0-3."""
    if tags_k == 0: return 0    # no tags, aug_tags must be 0
    if tags_k <= 4: return 1    # sparse
    if tags_k <= 8: return 2    # solid
    return 3                    # rich

# text_tier 0–3 × tags_tier 0–3 (4×4)
WEIGHT_TABLE = {
    # ── text_tier 0: no keywords. aug_text is 0. ───────────────────────────────
    (0, 0): {"text": 1.00, "aug_text": 0.00, "aug_tags": 0.00, "img_desc": 0.20},
    (0, 1): {"text": 0.40, "aug_text": 0.00, "aug_tags": 0.60, "img_desc": 0.20},
    (0, 2): {"text": 0.30, "aug_text": 0.00, "aug_tags": 0.70, "img_desc": 0.20},
    (0, 3): {"text": 0.25, "aug_text": 0.00, "aug_tags": 0.75, "img_desc": 0.20},

    # ── text_tier 1: aug_text peaks. ───────────────────────────────────────────
    (1, 0): {"text": 0.20, "aug_text": 0.80, "aug_tags": 0.00, "img_desc": 0.20},
    (1, 1): {"text": 0.10, "aug_text": 0.60, "aug_tags": 0.30, "img_desc": 0.20},
    (1, 2): {"text": 0.10, "aug_text": 0.50, "aug_tags": 0.40, "img_desc": 0.20},
    (1, 3): {"text": 0.10, "aug_text": 0.40, "aug_tags": 0.50, "img_desc": 0.20},

    # ── text_tier 2: text reclaims weight from aug_text. ───────────────────────
    (2, 0): {"text": 0.70, "aug_text": 0.30, "aug_tags": 0.00, "img_desc": 0.20},
    (2, 1): {"text": 0.50, "aug_text": 0.20, "aug_tags": 0.30, "img_desc": 0.20},
    (2, 2): {"text": 0.45, "aug_text": 0.15, "aug_tags": 0.40, "img_desc": 0.20},
    (2, 3): {"text": 0.40, "aug_text": 0.15, "aug_tags": 0.45, "img_desc": 0.20},

    # ── text_tier 3: rich text, minimal need for aug_text. ─────────────────────
    (3, 0): {"text": 0.90, "aug_text": 0.10, "aug_tags": 0.00, "img_desc": 0.20},
    (3, 1): {"text": 0.65, "aug_text": 0.05, "aug_tags": 0.30, "img_desc": 0.20},
    (3, 2): {"text": 0.60, "aug_text": 0.05, "aug_tags": 0.35, "img_desc": 0.20},
    (3, 3): {"text": 0.55, "aug_text": 0.05, "aug_tags": 0.40, "img_desc": 0.20}
}

def get_weights(text_k: int, tags_k: int) -> dict[str, float]:
    """
    Computes normalized weights based on text and tag expansion tiers.
    
    Args:
        text_k: Number of keyword expansions from user text.
        tags_k: Number of keyword expansions from user tags.
        
    Returns:
        Dictionary of normalized weights (summing to 1.0).
    """

    text_tier = get_text_tier(text_k)
    tags_tier = get_tags_tier(tags_k)
    
    base_weights = WEIGHT_TABLE.get((text_tier, tags_tier), WEIGHT_TABLE[(0, 0)]).copy()
    
    return base_weights
