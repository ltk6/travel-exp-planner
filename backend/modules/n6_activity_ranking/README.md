# N6 Activity Ranking Module

N6 ranks candidate activities by combining semantic similarity with rule-based attribute fit. It compares query-side vector channels against activity vectors, infers user preference axes from input text and tags, and returns a sorted result list with normalized scores and explanation strings.

## Responsibilities

- Accept query signal counters, user input, user vectors, and candidate activities
- Score semantic similarity across `text` and `aug_tags` channels
- Infer preference axes for intensity, physical effort, and social style from user input
- Blend semantic and attribute scores into a single final ranking
- Return ranked activities with normalized scores and lightweight metadata

## Module Structure

```
backend/modules/n6_activity_ranking/
├── __init__.py          # Re-exports rank_activities
├── rank_activities.py   # Scoring, blending, normalization logic
├── preferences.py       # Rule-based user preference inference (3 axes)
└── requirements.txt
```

## Public API

```python
from modules.n6_activity_ranking import rank_activities
from backend.shared.contracts.n6_contracts import N6RankInput

rank_activities(data: Union[N6RankInput, dict]) -> dict
```

`rank_activities()` enforces Pydantic V2 validation at the module boundary.

---

## Input Contract

```python
class UserInput(BaseModel):
    text: Optional[str] = ""
    tags: List[str] = []
    img_desc: Optional[str] = ""

class UserVectors(BaseModel):
    text: Optional[List[float]] = None
    aug_text: Optional[List[float]] = None
    aug_tags: Optional[List[float]] = None
    img_desc: Optional[List[float]] = None

class N6RankInput(BaseModel):
    text_k: int = 0
    tags_k: int = 0
    user_input: UserInput
    user_vectors: UserVectors
    activities: List[Dict[str, Any]] = []
    top_k: int = 5
```

| Field | Description |
|---|---|
| `text_k` / `tags_k` | Signal counters from N1 for dynamic channel weighting |
| `user_input` | Raw query — used to infer attribute preference axes |
| `user_vectors` | Query embeddings from N1 |
| `activities` | Candidate list from N3 (v2 path) or N5 (v1 path), each with `vectors` |
| `top_k` | Maximum ranked results to return |

---

## Output Contract

```python
class RankedActivityItem(BaseModel):
    activity_id: Optional[str] = None
    location_id: Optional[str] = None
    score: float = 0.0
    reason: Optional[str] = ""

class N6RankOutput(BaseModel):
    activities: List[RankedActivityItem]
    metadata: Dict[str, Any]
```

- `score` is rescaled for display after ranking (not normalized to 1.0 like N4)
- `reason` is built from the activity type and score highlights
- Empty input `activities` → empty output (fully valid, not an error)

---

## Scoring Behavior

N6 combines two top-level components with equal weight:

```
final_score = 0.5 × semantic_score + 0.5 × attribute_score
```

### Semantic Scoring

Cosine similarity between query and activity vectors across three channel pairs:

| Query channel | Activity channel |
|---|---|
| `aug_tags` | `aug_tags` (or legacy `tag`) |
| `aug_text` | `text` |
| `text` | `text` |

Channel weights are resolved dynamically from `text_k` / `tags_k`.

### Attribute Scoring (`preferences.py`)

User preference is inferred across three axes using a tag lookup table + keyword scan on `text` + `img_desc`:

| Axis | Meaning |
|---|---|
| `intensity` | Preference for dramatic/adventurous activities |
| `physical` | Preference for physically active activities |
| `social` | Preference for group/crowd activities |

Each axis returns a value in `[0.0, 1.0]` (via sigmoid) or `None` if no signal is detected. Axes with `None` are skipped — the activity is not penalized for missing preference data.

Attribute fit for each axis is computed as `1.0 - |preference - activity_level|`.

---

## Ranking Flow

1. Read `user_input`, `user_vectors`, `activities`, and signal counters
2. Infer preference axes from tags, text, and `img_desc` via `preferences.infer_user_preferences()`
3. Compute semantic and attribute scores for each candidate activity
4. Blend the two scores into one final value
5. Sort activities by descending final score
6. Rescale scores and build explanation strings
7. Return the top `k` results plus metadata

---

## Runtime Notes

- Cosine similarity returns `0.0` for missing, empty, or dimension-mismatched vectors
- If no semantic channels are usable, semantic scoring falls back to a neutral baseline
- If no preference axes are inferable, attribute scoring falls back to a neutral baseline
- The `aug_tags` key remapping from legacy `tag` (N3 activity schema) is handled in N8 before calling N6
- Logging covers ranking activity and per-call timing via the project logging helper
