# N17 Feedback Processing Module

N17 refines a travel query after the user provides feedback. It builds a structured prompt from the current query state, calls an LLM to rewrite the request, validates the returned tags, and falls back to a safe refinement payload if the LLM response fails.

## Responsibilities

- Accept the current query state plus a feedback message
- Build a structured refinement prompt for the LLM
- Call the configured LLM chain and request JSON-only output
- Parse and validate the returned refinement payload
- Fall back to a deterministic response when the LLM path fails

## Public API

```python
from backend.shared.contracts.n17_contracts import N17FeedbackInput

process_feedback(data: Union[N17FeedbackInput, dict]) -> dict
```

`process_feedback()` strictly validates input schemas at the boundary using **Pydantic V2**.

## Input Shape

The module accepts raw dictionaries matching the schema below or a pre-instantiated `N17FeedbackInput` Pydantic model:

```python
class N17FeedbackInput(BaseModel):
    user_input: Optional[str] = Field(default="", description="Original text prompt.")
    user_tags: List[str] = Field(default_factory=list, description="Original list of tags.")
    img_desc: Optional[str] = Field(default="", description="Original image description.")
    feedback_text: Optional[str] = Field(default="", description="The user feedback/correction text.")
    llm_chain: Optional[str] = Field(default=None, description="Model or chain override.")
```

- `user_input`: current free-form query text (Optional, defaults to `""`)
- `user_tags`: current normalized tag list (Optional, defaults to empty list `[]`)
- `img_desc`: current image description, if any (Optional, defaults to `""`)
- `feedback_text`: the user's refinement request (Optional, defaults to `""`)
- `llm_chain`: optional model-chain override (Optional, defaults to None)

## Output Shape

The output strictly adheres to the `N17FeedbackOutput` contract:

```python
class N17FeedbackOutput(BaseModel):
    refined_text: Optional[str] = ""
    refined_tags: List[str] = Field(default_factory=list)
    refined_img_desc: Optional[str] = ""
    explanation: Optional[str] = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

- `refined_text`: rewritten query text (Optional, defaults to `""`)
- `refined_tags`: filtered and normalized updated tag list (Optional, defaults to `[]`)
- `refined_img_desc`: updated image description (Optional, defaults to `""`)
- `explanation`: human-readable explanation shown in the UI (Optional, defaults to `""`)
- `metadata`: model/provider/usage info (Optional, defaults to `{}`)

## Processing Flow

1. Build a prompt from the current text, tags, image description, and feedback.
2. Call the configured LLM path and request JSON output.
3. Parse the returned JSON object.
4. Validate required fields and filter invalid tags.
5. Fill missing image-description output if needed.
6. Return the refined payload plus model metadata.

## Fallback Behavior

If the LLM call fails or the JSON response cannot be parsed, N17 returns a fallback payload:

- `refined_text`: concatenates the current query text and feedback
- `refined_tags`: preserves the original tag list
- `refined_img_desc`: preserves the current image description
- `explanation`: indicates that fallback behavior was used

## Runtime Notes

- the module sends requests directly to the configured Groq-compatible endpoint
- model retries are performed across the configured model chain
- responses are expected to contain JSON only
- logging is configured through the project logging helper
