# N5 Activity Generation Module

N5 generates candidate activities for each location in a result set. It uses an LLM-first strategy when available, falls back to template expansion when needed, and returns a flat list of activity records plus per-location generation metadata.

## Responsibilities

- Accept user preferences, candidate locations, and simple constraints
- Normalize incoming user and location payloads
- Generate activities for each location with an LLM-first strategy
- Fall back to template-based generation when LLM output is missing or insufficient
- Return structured activity metadata and per-location generation diagnostics

## Public API

```python
generate_activities(data: dict[str, Any]) -> dict[str, Any]
```

## Input Shape

```python
{
    "user": {
        "text": str | None,
        "img_desc": str | None,
        "tags": list[str] | str | None,
    },
    "locations": [
        {
            "location_id": str,
            "metadata": {
                "name": str | None,
                "description": str | None,
                "tags": list[str] | None,
            },
        }
    ],
    "constraints": {
        "time_of_day": str | None,
    },
}
```

- `user.tags` may be provided as a list or comma-separated string
- missing fields are normalized to safe defaults
- location metadata is optional, but better metadata improves generation quality

## Output Shape

```python
{
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
        }
    ],
    "metadata": {
        "per_location": [
            {
                "location_id": str,
                "provider_used": str | None,
                "model_used": str | None,
                "usage": dict | None,
                "latency_ms": int,
            }
        ],
        "latency_ms": int,
    },
}
```

- `activities` is a flat list across all input locations
- `per_location` contains generation metadata for each processed location
- if generation is disabled by configuration, the module returns an empty `activities` list

## Generation Behavior

For each location, N5 follows this flow:

1. Normalize the user, location list, and constraints.
2. Build or enrich a lightweight location profile.
3. Try to generate activities with the configured LLM path.
4. Accept LLM output only if enough valid activities are returned.
5. Fill gaps or fully fall back with template expansion when needed.
6. Deduplicate by activity name.
7. Return the combined activity list and metadata.

## Activity Semantics

Each activity includes:

- a generated `activity_id`
- the source `location_id`
- human-readable `name` and `description`
- a list of normalized `tags`
- an `activity_type`
- continuous `intensity`, `physical_level`, and `social_level` scores

## Runtime Notes

- the module can short-circuit to an empty result when generation counts are configured to `0`
- template generation can add diversity modifiers when it needs extra coverage
- sightseeing-oriented activities may be boosted to maintain variety in the returned set
- the module logs generation progress and timing through the project logging helper
