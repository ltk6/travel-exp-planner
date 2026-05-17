# N6 Activity Ranking Module

N6 ranks candidate activities by combining semantic similarity with attribute fit. It compares query-side vector channels against activity vectors, infers simple user preference axes from input text and tags, and returns a sorted result list with normalized scores and explanation strings.

## Responsibilities

- Accept query signal counters, user input, user vectors, and candidate activities
- Score semantic similarity across text and tag channels
- Infer preference axes for intensity, physical effort, and social style
- Blend semantic and attribute scores into a final ranking
- Return ranked activities with lightweight metadata

## Public API

```python
rank_activities(data: dict[str, Any]) -> dict[str, Any]
infer_user_preferences(user_input: dict[str, Any]) -> dict[str, float | None]
```

## Input Shape

```python
{
    "user_input": {
        "text": str | None,
        "img_desc": str | None,
        "tags": list[str] | None,
    },
    "user_vectors": {
        "text": list[float] | None,
        "aug_text": list[float] | None,
        "aug_tags": list[float] | None,
        "img_desc": list[float] | None,
    },
    "activities": [
        {
            "activity_id": str,
            "location_id": str,
            "metadata": {
                "name": str,
                "description": str,
                "tags": list[str],
                "activity_type": str,
                "intensity": float,
                "physical_level": float | None,
                "social_level": float | None,
            },
            "vectors": {
                "text": list[float] | None,
                "tag": list[float] | None,
            },
        }
    ],
    "context": {
        "time_of_day": str | None,
    },
    "text_k": int,
    "tags_k": int,
    "top_k": int,
}
```

- `user_input` is used to infer attribute preferences
- `user_vectors` is used for semantic scoring
- `activities` must provide both metadata and vector payloads for best results
- `top_k` defaults to `5` in code when omitted

## Output Shape

```python
{
    "activities": [
        {
            "activity_id": str,
            "location_id": str,
            "score": float,
            "reason": str,
        }
    ],
    "metadata": {
        "user_prefs": {
            "intensity": float | None,
            "physical": float | None,
            "social": float | None,
        },
        "weights": {
            "text": float,
            "aug_text": float,
            "aug_tags": float,
            "img_desc": float,
        },
        "text_k": int,
        "tags_k": int,
        "latency_ms": int,
    },
}
```

- `score` is normalized into a readable range after sorting
- `reason` is derived from activity metadata plus the strongest matched signals
- if no activities are provided, the module returns an empty list with zero latency

## Scoring Behavior

N6 combines two top-level components:

- semantic score: similarity between query vectors and activity vectors
- attribute score: fit between inferred user preferences and activity metadata

The final score is:

```python
0.5 * semantic_score + 0.5 * attribute_score
```

Semantic scoring uses these channel pairs:

- `aug_tags` to `tag`
- `aug_text` to `text`
- `text` to `text`

Attribute scoring compares user preference axes against:

- `intensity`
- `physical_level`
- `social_level`

Missing data on a preference axis is skipped rather than penalized.

## Ranking Flow

1. Read `user_input`, `user_vectors`, `activities`, `context`, and signal counters.
2. Infer user preference axes from tags, text, and image description text.
3. Compute semantic and attribute scores for each activity.
4. Blend the scores into one final value.
5. Sort the activities by descending score.
6. Rescale the final scores for easier display.
7. Return the top `k` results plus metadata.

## Runtime Notes

- cosine similarity returns `0.0` for missing or mismatched vectors
- if no semantic channels are usable, semantic scoring falls back to a neutral value
- if no preference axes are inferable, attribute scoring falls back to a neutral value
- explanation strings are generated from activity type and score highlights
