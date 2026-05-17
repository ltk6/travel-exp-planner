"""
preprocessor.py

Transforms raw inputs into multi-channel strings for embedding.

Input:
{
    "text":      str,       # raw text
    "tags":      list[str], # list of tags
    "img_desc":  str        # image description
}

Output:
{
    "text_k":    int,     # number of expanded keywords in aug_text
    "tags_k":    int,     # number of expanded tags in aug_tags
    "text":      str,     # raw text (passed through)
    "aug_text":  str,     # text + expanded emotions + expanded contexts
    "aug_tags":  str,     # expanded tags
    "img_desc":  str      # image description (passed through)
}
"""

from __future__ import annotations

from typing import NamedTuple

from backend.shared.maps import ALL_CONTEXT, ALL_EMOTIONS, ALL_TAGS


# ────────────────────────────────────────────────────────────
# Scanner
# ────────────────────────────────────────────────────────────

class MatchResult(NamedTuple):
    """Structured result of keyword matching"""
    source:    str  # "emotion" | "context" | "tag"
    keyword:   str  # keyword(s) that matched
    expansion: str  # expansion of that keyword(s)


def _dedupe_substr(matches: list[MatchResult]) -> list[MatchResult]:
    """Keep only the longest match when one keyword is a substring of another."""
    kept: list[MatchResult] = []
    for m in sorted(matches, key=lambda m: len(m.keyword), reverse=True):
        if not any(m.keyword in k.keyword for k in kept):
            kept.append(m)
    return kept


def _scan_text(text: str) -> dict[str, list[MatchResult]]:
    """Scan text input for emotion and context matches."""
    normed = text.lower().strip()

    emotion_hits = [
        MatchResult("emotion", key, ALL_EMOTIONS[key])
        for key in ALL_EMOTIONS if key in normed
    ]
    context_hits = [
        MatchResult("context", key, ALL_CONTEXT[key])
        for key in ALL_CONTEXT if key in normed
    ]

    return {
        "emotion": _dedupe_substr(emotion_hits),
        "context": _dedupe_substr(context_hits),
    }


def _scan_tags(tags: list[str]) -> dict[str, list[MatchResult]]:
    """Scan tags input for tag matches"""
    tag_hits:    list[MatchResult] = []
    tag_unknown: list[MatchResult] = []
    for tag in tags:
        key = tag.lower().strip()
        if key in ALL_TAGS:
            tag_hits.append(MatchResult("tag", tag, ALL_TAGS[key]))
        else:
            tag_unknown.append(MatchResult("tag_unknown", tag, tag))

    return {
        "tag":          tag_hits,
        "tag_unknown":  tag_unknown,
    }


# ────────────────────────────────────────────────────────────
# Expander
# ────────────────────────────────────────────────────────────

def _dedupe(items: list[str]) -> list[str]:
    """Remove duplicates while preserving order, skip blanks."""
    seen: set[str] = set()
    return [seen.add(x) or x for x in items if x and x not in seen]


def _expansions(matches: list[MatchResult]) -> list[str]:
    """Extract expansion strings from match results."""
    return [m.expansion for m in matches]


# ────────────────────────────────────────────────────────────
# Preprocessor
# ────────────────────────────────────────────────────────────

def preprocess(
    text:     str,
    tags:     list[str],
    img_desc: str,
) -> dict:
    """Transforms raw inputs into multi-channel strings for embedding."""
    text = (text or "").strip()
    tags = tags or []
    img_desc = (img_desc or "").strip()
    text_k = 0
    tags_k = 0

    # Text → emotion + context keyword expansion
    if text:
        text_scan = _scan_text(text)
        expanded_emotions = _dedupe(_expansions(text_scan["emotion"]))
        expanded_contexts = _dedupe(_expansions(text_scan["context"]))
        text_k = len(expanded_emotions) + len(expanded_contexts)
        parts = [text, " ".join(expanded_emotions), " ".join(expanded_contexts)]
        aug_text = " ".join(p for p in parts if p)
    else:
        aug_text = ""

    # Tags → independent tag expansion
    if tags:
        tag_scan = _scan_tags(tags)
        expanded_tags = _dedupe(_expansions(tag_scan["tag"]))
        tags_k = len(expanded_tags)
        aug_tags = " ".join(expanded_tags)
    else:
        aug_tags = ""

    return {
        "text_k":   text_k,
        "tags_k":   tags_k,
        "text":     text,
        "aug_text": aug_text,
        "aug_tags": aug_tags,
        "img_desc": img_desc
    }