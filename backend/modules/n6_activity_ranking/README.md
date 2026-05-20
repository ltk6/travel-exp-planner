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
from backend.shared.contracts.n6_contracts import N6RankInput

rank_activities(data: Union[N6RankInput, dict]) -> dict
```

`rank_activities()` strictly validates input schemas at the boundary using **Pydantic V2**.

## Input Shape

The module accepts raw dictionaries matching the schema below or a pre-instantiated `N6RankInput` Pydantic model:

```python
class UserInput(BaseModel):
    text: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    img_desc: Optional[str] = ""

class N6RankInput(BaseModel):
    user_input: UserInput = Field(default_factory=UserInput)
    user_vectors: UserVectors = Field(default_factory=UserVectors)
    activities: List[Dict[str, Any]] = Field(default_factory=list)
    top_k: int = Field(default=5)
    text_k: int = Field(default=0)
    tags_k: int = Field(default=0)
```

- `user_input`: raw query parameters to infer attribute preferences (Optional, defaults to empty UserInput)
- `user_vectors`: query-side vectors used for semantic scoring (Optional, defaults to empty UserVectors)
- `activities`: candidate activities to rank (Optional, defaults to empty list `[]`)
- `top_k`: maximum number of ranked activities to return (Optional, defaults to 5)
- `text_k`: count of text-side semantic signals (Optional, defaults to 0)
- `tags_k`: count of tag-side semantic signals (Optional, defaults to 0)

## Output Shape

The output of the N6 module strictly adheres to the `N6RankOutput` contract:

```python
class RankedActivityItem(BaseModel):
    activity_id: Optional[str] = None
    location_id: Optional[str] = None
    score: float = Field(default=0.0)
    reason: Optional[str] = ""

class N6RankOutput(BaseModel):
    activities: List[RankedActivityItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

- `activity_id`: identifier of the ranked activity (Optional, defaults to None)
- `location_id`: source location for this activity (Optional, defaults to None)
- `score`: normalized relevance score (Optional, defaults to `0.0`)
- `reason`: short explanation of the score (Optional, defaults to `""`)
- If the input `activities` list is empty, the output `activities` list is also empty — fully valid.


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
