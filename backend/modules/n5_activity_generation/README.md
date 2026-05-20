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
from backend.shared.contracts.n5_contracts import N5GenerateInput

generate_activities(data: Union[N5GenerateInput, dict]) -> dict
```

`generate_activities()` strictly validates input schemas at the boundary using **Pydantic V2**.

## Input Shape

The module accepts raw dictionaries matching the schema below or a pre-instantiated `N5GenerateInput` Pydantic model:

```python
class N5UserInput(BaseModel):
    text: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    img_desc: Optional[str] = ""

class N5LocationMetadata(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    coordinates: Optional[Dict[str, Optional[float]]] = None
    address: Optional[str] = None

class N5LocationItem(BaseModel):
    location_id: str
    metadata: Optional[N5LocationMetadata] = None

class N5Constraints(BaseModel):
    time_of_day: Optional[str] = "anytime"

class N5GenerateInput(BaseModel):
    user: N5UserInput = Field(default_factory=N5UserInput)
    locations: List[N5LocationItem] = Field(default_factory=list)
    constraints: Optional[N5Constraints] = Field(default_factory=N5Constraints)
    provider_override: Optional[str] = None
```

- `user`: user preferences (Optional, defaults to empty preferences)
- `locations`: candidate locations to generate activities for (Optional, defaults to empty list `[]`)
- `constraints`: activity timing constraints (Optional, defaults to `time_of_day: "anytime"`)
- `provider_override`: override default LLM provider (Optional, defaults to None)

## Output Shape

N5 has no formal output contract. Malformed LLM results are dropped internally. The raw activity structure returned is:

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
- Malformed or incomplete activities are silently dropped by N5's internal parser
- In N8, N5-generated activities are validated against `N3ActivityItem` before entering the shared activity pipeline alongside DB-backed activities
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
