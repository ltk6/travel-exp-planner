# N4 Location Ranking Module

N4 ranks candidate locations with weighted multi-channel cosine similarity. It accepts a query-side vector bundle, compares it against a list of candidate location vectors, and returns the top-ranked results with normalized scores and short explanation strings.

## Responsibilities

- Accept query signal counters and vector channels
- Score each candidate location across text, tag, and image-description channels
- Apply dynamic channel weights based on available signal strength
- Sort and normalize the final ranking output
- Return lightweight ranking metadata for inspection

## Public API

```python
from backend.shared.contracts.n4_contracts import N4RankInput

rank_locations(data: Union[N4RankInput, dict]) -> dict
```

`rank_locations()` strictly validates its input payload at the entrypoint boundary using **Pydantic V2**.

## Input Shape

The module accepts raw dictionaries matching the schema below or a pre-instantiated `N4RankInput` Pydantic model:

```python
class UserVectors(BaseModel):
    text: Optional[List[float]] = None
    aug_text: Optional[List[float]] = None
    aug_tags: Optional[List[float]] = None
    img_desc: Optional[List[float]] = None

class N4RankInput(BaseModel):
    text_k: int = Field(default=0)
    tags_k: int = Field(default=0)
    user_vectors: UserVectors = Field(default_factory=UserVectors)
    locations: List[Dict[str, Any]] = Field(default_factory=list)
    top_k: int = Field(default=5)
```

- `text_k`: count of text-side semantic signals (Optional, defaults to 0)
- `tags_k`: count of tag-side semantic signals (Optional, defaults to 0)
- `user_vectors`: query-side vectors used for scoring (Optional, defaults to an empty UserVectors)
- `locations`: candidate locations to rank (Optional, defaults to an empty list `[]`)
- `top_k`: maximum number of ranked locations to return (Optional, defaults to 5)

## Output Shape

The output of the N4 module strictly adheres to the `N4RankOutput` contract:

```python
class RankedLocationItem(BaseModel):
    location_id: Optional[str] = None
    score: float = Field(default=0.0)
    reason: Optional[str] = ""

class N4RankOutput(BaseModel):
    locations: List[RankedLocationItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

- `score` is normalized relative to the top result when at least one score is positive
- `reason` is a short explanation string derived from the strongest active channels
- if no candidate locations are provided, `locations` is empty and latency is `0`

## Scoring Behavior

N4 computes four cosine-similarity channels:

- `text` to `text`
- `aug_text` to `text`
- `aug_tags` to `aug_tags`
- `img_desc` to `text`

The final raw score is a weighted sum of those similarities. Negative totals are clamped to `0.0`.

## Ranking Flow

1. Read `text_k`, `tags_k`, `user_vectors`, `locations`, and `top_k`.
2. Resolve channel weights from the signal counters.
3. Score every candidate location independently.
4. Sort candidates by descending score.
5. Truncate to `top_k`.
6. Normalize the returned scores against the top result.
7. Return ranked locations plus metadata.

## Runtime Notes

- Cosine similarity returns `0.0` for missing, empty, zero-norm, or mismatched vectors
- Score explanations only include channels that are both active and sufficiently aligned
- The module logs ranking activity and timing through the project logging helper
