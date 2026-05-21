# N4 Location Ranking Module

N4 ranks candidate locations using weighted multi-channel cosine similarity. It accepts a query-side vector bundle and signal counters from N1, scores every candidate location across four embedding channels, and returns the top-ranked results with normalized scores and short explanation strings.

## Responsibilities

- Accept query signal counters (`text_k`, `tags_k`) and vector channels from N1
- Score each candidate location across `text`, `aug_text`, `aug_tags`, and `img_desc` channels
- Resolve dynamic channel weights from the available signal strength
- Sort, truncate to `top_k`, and normalize the final ranking output
- Return lightweight ranking metadata for tracing

## Module Structure

```
backend/modules/n4_location_ranking/
├── __init__.py         # Re-exports rank_locations
├── rank_locations.py   # Scoring, weighting, normalization logic
└── requirements.txt
```

## Public API

```python
from modules.n4_location_ranking import rank_locations
from backend.shared.contracts.n4_contracts import N4RankInput

rank_locations(data: Union[N4RankInput, dict]) -> dict
```

`rank_locations()` enforces Pydantic V2 validation at the module boundary.

---

## Input Contract

```python
class UserVectors(BaseModel):
    text: Optional[List[float]] = None
    aug_text: Optional[List[float]] = None
    aug_tags: Optional[List[float]] = None
    img_desc: Optional[List[float]] = None

class N4RankInput(BaseModel):
    text_k: int = 0
    tags_k: int = 0
    user_vectors: UserVectors
    locations: List[Dict[str, Any]] = []
    top_k: int = 5
```

| Field | Description |
|---|---|
| `text_k` | Text expansion count from N1 — used to scale `text`/`aug_text` weight |
| `tags_k` | Tag expansion count from N1 — used to scale `aug_tags` weight |
| `user_vectors` | Query-side embeddings from N1 |
| `locations` | Candidate location list from N3 cache, each with `location_vectors` |
| `top_k` | Maximum number of ranked results to return |

> **Note:** N8 maps N3's `vectors` key to `location_vectors` before passing to N4 to match this contract.

---

## Output Contract

```python
class RankedLocationItem(BaseModel):
    location_id: Optional[str] = None
    score: float = 0.0
    reason: Optional[str] = ""

class N4RankOutput(BaseModel):
    locations: List[RankedLocationItem]
    metadata: Dict[str, Any]
```

| Field | Description |
|---|---|
| `score` | Normalized relative to the top result (top result = 1.0) |
| `reason` | Short explanation derived from the strongest active channels |
| `metadata` | Timing and ranking diagnostics |

If no candidate locations are provided, `locations` is empty and `metadata.latency_ms` is `0`.

---

## Scoring Behavior

N4 computes four cosine-similarity channel pairs between query and location vectors:

| Query channel | Location channel |
|---|---|
| `text` | `text` |
| `aug_text` | `text` |
| `aug_tags` | `aug_tags` |
| `img_desc` | `text` |

The raw score is a weighted sum of those similarities. Channel weights are resolved dynamically from `text_k` and `tags_k` via the shared `get_weights()` helper — queries with richer tag signals give more weight to the `aug_tags` channel, and so on. Negative totals are clamped to `0.0`.

---

## Ranking Flow

1. Read `text_k`, `tags_k`, `user_vectors`, `locations`, and `top_k`
2. Resolve channel weights from the signal counters
3. Score every candidate location independently
4. Sort candidates by descending raw score
5. Truncate to `top_k`
6. Normalize scores against the top result
7. Build explanation strings from the strongest active channels
8. Return ranked list and metadata

---

## Runtime Notes

- Cosine similarity returns `0.0` for missing, empty, zero-norm, or dimension-mismatched vectors
- Explanation strings only include channels that are both active and sufficiently aligned
- Logging covers ranking activity and per-call timing via the project logging helper
