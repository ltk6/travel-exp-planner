# Shared Ranking — 2D Channel Weighting Guide

This guide explains how the system dynamically adjusts weights for different vector channels based on two signals: **text_k** and **tag_k**.

---

## The 4 Active Channels

| Channel    | Representation         | Role                                  |
| ---------- | ---------------------- | ------------------------------------- |
| `text`     | Raw user input         | High-precision, literal intent        |
| `aug_text` | Expanded semantic text | Contextual + emotional interpretation |
| `aug_tags` | Expanded tag strings   | Stable semantic anchor                |
| `img_desc` | Image description      | Visual alignment                      |

---

## Input Signals

The system uses two counts extracted during preprocessing in N1:

1.  **text_k**: Number of keyword expansions detected in the user's text.
2.  **tag_k**: Number of keyword expansions detected in the user's tags.

These signals are mapped into **Tiers (0-3)** to determine the weighting strategy.

### Text Tiers
| Tier | text_k | Role |
|------|--------|------|
| 0    | 0      | No keywords; `aug_text` is inactive. |
| 1    | 1-2    | Sparse keywords; `aug_text` is at its strongest. |
| 2    | 3-4    | Moderate keywords; `text` begins to reclaim weight. |
| 3    | 5+     | Rich keywords; `aug_text` is minimized. |

### Tag Tiers
| Tier | tag_k | Role |
|------|-------|------|
| 0    | 0     | No tags; `aug_tags` is inactive. |
| 1    | 1-4   | Sparse tags coverage. |
| 2    | 5-8   | Solid tags coverage. |
| 3    | 9+    | Rich tags coverage. |

---

## 2D Weighting Matrix

Legend: `text` / `aug_text` / `aug_tags` / `img_desc`

| Text \ Tag | Tier 0 (None) | Tier 1 (Sparse) | Tier 2 (Solid) | Tier 3 (Rich) |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 0 (None)** | 1.00 / 0.00 / 0.00 / 0.20 | 0.40 / 0.00 / 0.60 / 0.20 | 0.30 / 0.00 / 0.70 / 0.20 | 0.25 / 0.00 / 0.75 / 0.20 |
| **Tier 1 (Peaks)** | 0.20 / 0.80 / 0.00 / 0.20 | 0.10 / 0.60 / 0.30 / 0.20 | 0.10 / 0.50 / 0.40 / 0.20 | 0.10 / 0.40 / 0.50 / 0.20 |
| **Tier 2 (Reclaims)** | 0.70 / 0.30 / 0.00 / 0.20 | 0.50 / 0.20 / 0.30 / 0.20 | 0.45 / 0.15 / 0.40 / 0.20 | 0.40 / 0.15 / 0.45 / 0.20 |
| **Tier 3 (Rich)** | 0.90 / 0.10 / 0.00 / 0.20 | 0.65 / 0.05 / 0.30 / 0.20 | 0.60 / 0.05 / 0.35 / 0.20 | 0.55 / 0.05 / 0.40 / 0.20 |
