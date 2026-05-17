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
rank_locations(data: dict[str, Any]) -> dict[str, Any]
```

## Input Shape

```python
{
    "text_k": int,
    "tags_k": int,
    "user_vectors": {
        "text": list[float] | None,
        "aug_text": list[float] | None,
        "aug_tags": list[float] | None,
        "img_desc": list[float] | None,
    },
    "locations": [
        {
            "location_id": str,
            "location_vectors": {
                "text": list[float] | None,
                "aug_tags": list[float] | None,
            },
        }
    ],
    "top_k": int,
}
```

- `text_k`: count of text-side semantic signals
- `tags_k`: count of tag-side semantic signals
- `user_vectors`: query-side vectors used for scoring
- `locations`: candidate locations to rank
- `top_k`: maximum number of ranked locations to return

## Output Shape

```python
{
    "locations": [
        {
            "location_id": str,
            "score": float,
            "reason": str,
        }
    ],
    "metadata": {
        "text_k": int,
        "tags_k": int,
        "weights": {
            "text": float,
            "aug_text": float,
            "aug_tags": float,
            "img_desc": float,
        },
        "latency_ms": int,
    },
}
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
