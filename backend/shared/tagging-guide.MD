# N1 Tagging Guide
## Tags, Questionnaires, and the Single Tagging Vector Space

---

## 0. How the Pipeline Works (Read This First)

Understanding the math prevents bad tagging decisions.

```
User input (text + tags)
        │
        ▼
  preprocessor.py
  ┌─────────────────────────────────────────────────────┐
  │  "text"     → raw user description string           │
  │  "aug_text" → text + emotion expansions             │
  │  "aug_tags" → joined expanded tag strings           │
  └─────────────────────────────────────────────────────┘
        │
        ▼
  embedder.py  →  BGE-M3  →  4 separate vectors
        │
        ▼  (for now: tags fused into 1 combined aug_tags vector)
  cosine_similarity(user_aug_tags_vec, location_aug_tags_vec)
        │
        ▼
  score → N4 ranking
```

Your `aug_tags` string is built by:
1. Looking up each tag key in `ALL_TAGS`
2. Replacing it with its expansion string
3. Joining all expansions into one long string
4. Embedding that string as **a single vector**

**Critical implication**: every tag in that joined string competes for influence over the final vector. BGE-M3 averages the semantic content of the entire string. This has direct consequences for how many tags you assign and which categories matter most.

---

## 1. The Fundamental Laws of Single-Vector Tagging

### Law 1 — Dilution is real
The more tags you add, the more the vector is pulled toward the average of all tag clusters. Specific signal is lost. A location tagged with 25 tags has a vector that sits near the center of the embedding space — it will score "okay" against everything and "great" against nothing.

```
# Too many tags → vector sits in the middle → weak discrimination
["beach", "mountain", "city", "history", "adventure", "peaceful",
 "romantic", "vibrant", "budget", "luxury", "family", "solo", ...]

# Focused tags → vector pulls toward a specific cluster → strong matches
["beach", "snorkeling", "island", "peaceful", "couple", "seafood"]
```

### Law 2 — Category balance matters
If you assign 8 activity tags and 1 vibe tag, the vector will be heavily activity-oriented even if the location's strongest draw is atmosphere. The categories you load with more tags dominate the vector.

### Law 3 — Expansions do the real semantic work
The tag key `"trekking"` is just a lookup key. The vector is shaped by the expansion `"multi-day trekking mountain trail jungle endurance rewarding"`. When you choose a tag, you are choosing its expansion, not its label.

### Law 4 — User and location tags must use the same vocabulary
The cosine similarity only works because both sides expand through the same `ALL_TAGS` dictionary into the same semantic space. A user who answers "I want to go hiking" gets mapped to `"trekking"` → expansion. A location tagged `"trekking"` gets the same expansion. Their vectors will be nearby.

---

## 2. Location Tagging Rules

### 2.1 Total Tag Budget

| Tier | Total Tags | When to Use |
|------|-----------|-------------|
| Focused | **8–12** | Destination with a clear primary identity (e.g. Bai Sao beach, Langbiang peak) |
| Standard | **13–18** | Multi-experience destination (e.g. Nha Trang, Hoi An) |
| Complex | **19–24** | Major hub with genuinely diverse offer (e.g. Da Nang, Phu Quoc) |
| Never exceed | **25** | Hard cap. Above this, discrimination collapses. |

> **Default to Focused.** Err on the side of fewer, more precise tags. You can always add later; over-tagged locations produce mediocre matches everywhere.

### 2.2 Per-Category Allocation

These are **per-location** guidelines. A category slot left empty is fine — do not fill it with weak tags just to have coverage.

| Category | Min | Soft Max | Hard Max | Notes |
|----------|-----|----------|----------|-------|
| **TERRAIN / WATER / ECOSYSTEM** | 1 | 3 | 4 | The physical setting. Always include at least 1. |
| **CLIMATE / SEASON** | 0 | 2 | 3 | Only tag if climate is a genuine draw (cool highland, snow, cloud sea). Skip for average coastal. |
| **CULTURE / HERITAGE** | 0 | 3 | 4 | Only if genuinely present. Don't tag `history` just because Vietnam has history. |
| **URBAN / SETTLEMENT** | 0 | 2 | 3 | Only for locations with a notable built environment (old town, market, fishing village). |
| **ACTIVITIES (all types combined)** | 1 | 4 | 6 | The most important category for matching. Be specific. Prefer actual available activities over aspirational ones. |
| **FOOD / DRINK** | 0 | 2 | 3 | Only tag if the food is a real draw specific to this place (not just "there is food here"). |
| **VIBE / MOOD** | 1 | 2 | 3 | Always include 1–2. This is what aligns with user emotional intent. |
| **TRIP PROFILE** | 0 | 2 | 3 | Only tag if the location is distinctively suited (e.g. "honeymoon" for a private resort island, "day trip" for a nearby attraction). |
| **BUDGET / STYLE** | 0 | 1 | 2 | Tag accommodation style only if it's a defining feature. Don't tag both `luxury` and `budget` — pick the dominant fit. |
| **SPECIAL INTEREST** | 0 | 2 | 3 | Only for genuine niche destinations (dive mecca → `scuba diving` + `eco travel`; war site → `war tourism`). |

### 2.3 The "Would a traveler come HERE specifically for this?" Test

Before adding any tag to a location, ask: *Would a reasonable traveler choose this specific location primarily because of this attribute?*

- **Yes** → Tag it.
- *"Sort of, maybe, it's also available"* → Skip it.

```
# Hoi An: should you tag "mountain"?
# → No. No traveler comes to Hoi An for mountains.

# Hoi An: should you tag "photography"?
# → Yes. The lanterns, old town, and light make it a photography draw.

# Nha Trang: should you tag "history"?
# → Debatable. Tag it only if you are pointing at Ponagar Tower specifically.
#   If the location is "Nha Trang Bay" generically, skip it.
```

### 2.4 Avoid Semantic Duplication Across Tags

The expansion strings of some tags overlap heavily in embedding space. Tagging both wastes your budget and over-reinforces one cluster.

| Avoid pairing | Reason |
|---|---|
| `peaceful` + `slow travel` | Near-identical vectors |
| `luxury` + `resort` + `boutique` | All pull toward same premium cluster |
| `romantic` + `honeymoon` + `couple` | Extreme redundancy |
| `trekking` + `hiking` | Very similar; pick one based on difficulty |
| `eco travel` + `eco lodge` + `biosphere reserve` | Triple-tagging same signal |
| `UNESCO heritage` + `history` + `colonial heritage` | Two is fine; three is redundant |

Choose the **most specific and most accurate** one. If two tags really both apply strongly and are distinct enough, keep both. But run the "dilution" test mentally.

### 2.5 Worked Location Examples

**Côn Đảo** (remote pristine island, war history, diving, turtles)
```python
tags = [
    # Terrain / Water
    "island", "beach", "coral reef",
    # Ecosystem
    "national park", "wildlife",
    # Activities
    "scuba diving", "snorkeling",
    # Culture
    "war history", "spiritual",
    # Vibe
    "off the beaten path", "peaceful",
    # Special interest
    "eco travel",
]
# Total: 13 tags — Standard tier, well-distributed
```

**Bà Nà Hills** (theme park, cable car, European architecture on a mountain)
```python
tags = [
    # Terrain
    "mountain", "cool climate",
    # Activities — Leisure
    "theme park", "cable car",
    # Activities — Land
    "photography",
    # Culture
    "colonial heritage",
    # Vibe
    "instagrammable", "modern",
    # Trip Profile
    "family",
]
# Total: 9 tags — Focused tier, clear identity
```

**Chợ Nổi Cái Răng** (floating market, Mekong Delta, food, culture)
```python
tags = [
    # Terrain / Water
    "delta", "river",
    # Urban
    "floating market",
    # Activities — Leisure
    "food tour",
    # Food
    "street food", "tropical fruit",
    # Culture
    "ethnic minority",         # ← Kinh Vietnamese river culture
    # Vibe
    "authentic", "immersive",
    # Trip Profile
    "day trip",
]
# Total: 9 tags
```

---

## 3. Questionnaire → Tag Derivation Rules

### 3.1 User Tag Budget

Users answer a questionnaire. Their answers produce tags. The rules are stricter than for locations because user intent needs to be **precise and sparse** — the retrieval model works by finding a close neighbor, not averaging everything the user mentioned.

| Questionnaire type | Recommended user tags |
|---|---|
| Short (3–5 questions) | **4–8 tags** |
| Standard (6–10 questions) | **8–14 tags** |
| Long / detailed (10+ questions) | **12–18 tags**, never above 20 |

> Never exceed 20 user tags. Beyond this, the user's vector drifts to the center of the space and starts matching everything weakly.

### 3.2 Question → Tag Mapping Framework

Each question maps to a category. Design questions with a **maximum of 1–2 tags output per question**. Multi-select questions should be capped at 3 selections.

```
Question                           → Category       → Max tags from this Q
────────────────────────────────────────────────────────────────────────────
What landscape do you prefer?      → TERRAIN/WATER  → 1–2
What activities do you want?       → ACTIVITIES     → 2–3  ← most important
What vibe are you after?           → VIBE           → 1–2
Who are you traveling with?        → TRIP PROFILE   → 1
How long is your trip?             → TRIP PROFILE   → 1
What's your budget style?          → BUDGET         → 1
Any dietary / special requirements?→ FOOD / SPECIAL → 1
Any must-have experiences?         → SPECIAL INT.   → 0–2
What time of year?                 → SEASON         → 0–1
```

### 3.3 Activities Questions Are the Most Important

Activities are the strongest discriminator in the tag vector because:
1. They are specific and diverse (diving vs. trekking are very far apart in embedding space)
2. Users have genuine preferences they rarely compromise on
3. Locations differ most sharply on available activities

**Allocate the most question budget and the most tag slots here.** If a user says they want diving, that single `scuba diving` tag will strongly pull their vector toward Nha Trang, Con Dao, Ly Son — which is exactly right.

### 3.4 Vibe Questions Are the Tie-Breaker

When two locations score similarly on activities, vibe tags decide the ranking. A user who wants `peaceful` will get Con Dao over Nha Trang even if both have diving. Design at least 1 vibe question.

### 3.5 Negative Preferences — Handle with Absence, Not Tags

The current single-vector space has no subtraction mechanism. Do not create "anti-tags" like `no_crowds` or `avoid_beach`. Instead:

- If the user says **"I don't want beaches"**, simply don't include any beach/coastal tags in their vector.
- Their vector will naturally pull away from beach-heavy location vectors through absence of signal.
- Reserve explicit avoidance filtering for N4 (hard filters), not the embedding layer.

### 3.6 Do Not Infer — Only Map What Was Stated

If a user answers "I want to trek in the mountains", derive: `trekking`, `mountain`.
Do NOT also add: `camping`, `photography`, `cool climate`, `ethnic minority` — even if these are correlated. The user did not state them. Adding inferred tags contaminates the vector with assumptions.

The only safe inference is **Trip Profile**, which is structurally derivable:
```
"I'm going alone"        → solo
"Going with my partner"  → couple
"Family with kids"       → family
"Weekend trip"           → weekend trip
```

### 3.7 Questionnaire Worked Example

**User answers:**
- Destination type: *Beach / island* → `beach`, `island`
- Activities (pick up to 3): *Snorkeling, Kayaking, Doing nothing on the beach* → `snorkeling`, `kayaking` (skip "doing nothing" — no tag for that; it maps implicitly to `peaceful` or `chill`)
- Vibe: *Peaceful and romantic* → `peaceful`, `romantic`
- Travel companion: *Partner* → `couple`
- Trip length: *3–4 days* → `weekend trip`
- Budget: *Mid-range* → `mid range`
- Food: *Love seafood* → `seafood`
- Special: *Nothing specific* → (no tag)

**Resulting tag list (11 tags):**
```python
user_tags = [
    "beach", "island",           # Terrain/Water
    "snorkeling", "kayaking",    # Activities
    "peaceful", "romantic",      # Vibe
    "couple", "weekend trip",    # Trip Profile
    "mid range",                 # Budget
    "seafood",                   # Food
    "chill",                     # inferred from "doing nothing" → safe inference
]
```

This vector will closely match: **Bãi Sao Phú Quốc**, **Cù Lao Chàm**, **Côn Đảo** (in roughly that order based on the peaceful + romantic + mid-range weighting). It will score poorly against Ha Giang, Ba Na Hills, Hanoi — which is correct behavior.

---

## 4. Common Tagging Mistakes and How to Fix Them

### Mistake 1 — The "Completeness" Trap
*"This location has a beach, mountains nearby, a market, some history, good food, and it's peaceful and romantic and good for families..."*

**Problem**: Every tag is technically true. But 20 tags produce a vector that matches everyone and impresses no one.

**Fix**: Ask "What is the *primary reason* someone would choose THIS over every other destination?" Tag that reason heavily. Tag secondary draws lightly or not at all.

---

### Mistake 2 — Tagging the Region, Not the Destination
*Assigning `war history` to every location in central Vietnam because the region has war history.*

**Problem**: Only specific locations (Cu Chi Tunnels, DMZ, War Remnants Museum) are actual war history destinations. Tagging generic beach resorts nearby with `war history` contaminates their vector.

**Fix**: Tag attributes intrinsic to *this specific location*, not the surrounding region.

---

### Mistake 3 — Symmetric Over-Tagging (Both Luxury AND Budget)
*"This place has backpacker hostels AND 5-star resorts"*

**Problem**: Tagging both `luxury` and `budget` pulls the vector to the midpoint between clusters — it won't strongly match either segment.

**Fix**: Tag the *dominant* profile. If 80% of visitors are budget travelers, tag `budget`. Use `mid range` if genuinely mixed. Reserve `luxury` for destinations where upscale is the primary product.

---

### Mistake 4 — Forgetting Vibe Tags
Locations tagged only with terrain and activities will have flat, mechanical vectors. Two diving beaches with identical activity tags will be indistinguishable.

**Fix**: Every location must have at least 1–2 vibe tags. These carry the emotional differentiation that the embedding model excels at representing.

---

### Mistake 5 — User Tags Copied From Location Tags
Copying a location's tag list onto a user profile because "they said they like this place" creates circular retrieval — the user finds the same place they started from.

**Fix**: Always derive user tags from **stated preferences and intent**, never from places they've visited.

---

## 5. Quick Reference Card

### Location Tag Budget
```
Total tags:   8–12 (focused)  |  13–18 (standard)  |  19–24 (complex)
Hard cap:     25 tags maximum

Per category hard limits:
  Terrain/Water/Ecosystem   ≤ 4    Activities (all types)  ≤ 6
  Culture/Heritage          ≤ 4    Food/Drink              ≤ 3
  Vibe                      ≤ 3    Trip Profile            ≤ 3
  Budget/Style              ≤ 2    Special Interest        ≤ 3
  Season/Climate            ≤ 3    Urban/Settlement        ≤ 3
```

### User Tag Budget
```
Total tags from questionnaire:
  Short Q (3–5 questions)   → 4–8 tags
  Standard Q (6–10)         → 8–14 tags
  Long Q (10+)              → 12–18 tags, never exceed 20

Per question output:
  Terrain / Water           → 1–2 tags
  Activities (most important) → 2–3 tags  ← highest budget
  Vibe                      → 1–2 tags
  Trip Profile              → 1 tag
  Budget                    → 1 tag
  Food                      → 0–1 tags
  Special Interest          → 0–2 tags
  Season                    → 0–1 tags
```

### Decision Checklist Before Adding Any Tag

```
□ Would a traveler choose THIS SPECIFIC LOCATION because of this attribute?
□ Is this tag already covered by another tag I've assigned? (duplication check)
□ Is this the most specific tag available for this concept?
□ Am I under the category hard limit?
□ Am I under the total budget?
→ If all YES: add it.  If any NO: skip it.
```

### Tag Join Order (for aug_tags string)
```
1. Primary terrain / water
2. Key activities (2–3, most discriminative first)
3. Vibe / mood
4. Culture / heritage (if applicable)
5. Food / drink (if applicable)
6. Trip profile / budget (if applicable)
7. Special interest (if applicable)
```

---

## 6. Future Considerations

### 6.1 Tags That Should Eventually Move to Hard Filters (N4)
Some tags are better as boolean filters than embedding signals:
- `halal` — users either require it or don't; similarity is wrong here
- `wheelchair accessible` — same
- `pet friendly` — same
- `day trip` / `weekend trip` — better as a distance or duration filter

Keep them in `ALL_TAGS` for now (they still help when hard filtering isn't wired up), but plan to migrate them to N4 structured filters when the pipeline matures.

### 6.2 Confidence Scoring for Tag Assignment
When automating tag derivation from location descriptions (LLM-assisted tagging), emit a confidence score with each tag and discard tags below 0.7. A confidently-assigned set of 10 tags outperforms 20 tags where half are uncertain.