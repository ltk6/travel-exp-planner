# N17 Feedback Processing Module

N17 refines a travel query after the user provides natural-language feedback. It builds a structured prompt from the current query state, calls the configured LLM chain to produce a refined parameter set, validates the returned tags, and falls back to a deterministic response if the LLM path fails.

## Responsibilities

- Accept the current query state (text, tags, img_desc) plus a user feedback message
- Build a structured refinement prompt for the LLM
- Call the configured LLM chain and request JSON-only output
- Parse and validate the returned refinement payload
- Filter returned tags against the allowed tag list
- Fall back to a deterministic response when the LLM path fails or returns invalid JSON

## Module Structure

```
backend/modules/n17_feedback_processing/
├── __init__.py              # Re-exports process_feedback
├── feedback_processor.py    # Prompt construction, LLM call, parse + validate, fallback
└── requirements.txt
```

## Public API

```python
from modules.n17_feedback_processing import process_feedback
from backend.shared.contracts.n17_contracts import N17FeedbackInput

process_feedback(data: Union[N17FeedbackInput, dict]) -> dict
```

`process_feedback()` enforces Pydantic V2 validation at the module boundary.

---

## Input Contract

```python
class N17FeedbackInput(BaseModel):
    user_input: Optional[str] = ""         # Current free-form query text
    user_tags: List[str] = []              # Current normalized tag list
    img_desc: Optional[str] = ""           # Current image description
    feedback_text: Optional[str] = ""      # User's refinement request
    llm_chain: Optional[str] = None        # Optional model-chain override
```

| Field | Description |
|---|---|
| `user_input` | The original text prompt the user submitted |
| `user_tags` | Tags already selected in the UI |
| `img_desc` | Visual description from N2 (if an image was uploaded) |
| `feedback_text` | The user's new instruction (e.g. "add more outdoor options") |
| `llm_chain` | Optional override to force a specific LLM model chain |

---

## Output Contract

```python
class N17FeedbackOutput(BaseModel):
    refined_text: Optional[str] = ""
    refined_tags: List[str] = []
    refined_img_desc: Optional[str] = ""
    explanation: Optional[str] = ""
    metadata: Dict[str, Any] = {}
```

| Field | Description |
|---|---|
| `refined_text` | Rewritten query text incorporating the feedback |
| `refined_tags` | Updated, validated tag list |
| `refined_img_desc` | Updated image description (usually preserved unless feedback changes focus) |
| `explanation` | Human-readable summary of what changed — shown in N16 UI |
| `metadata` | Provider name, model, and token usage |

N8 passes `refined_text`, `refined_tags`, and `refined_img_desc` back into `recommend_service()` or `activities_service()` for a second run, then attaches the full refined payload to the response for display.

---

## Processing Flow

1. Build a prompt from the current `text`, `tags`, `img_desc`, and `feedback_text`
2. Call the LLM provider chain and request strictly JSON output
3. Parse the returned JSON object
4. Validate required fields (`refined_text`, `refined_tags`, `explanation`)
5. Filter `refined_tags` against the project's allowed tag list
6. Fill `refined_img_desc` if the LLM omitted it (defaults to current value)
7. Return the refined payload plus model metadata

---

## Fallback Behavior

If the LLM call fails, times out, or returns unparseable JSON, N17 returns:

| Field | Fallback value |
|---|---|
| `refined_text` | Concatenation of current `user_input` + `feedback_text` |
| `refined_tags` | Preserves current `user_tags` unchanged |
| `refined_img_desc` | Preserves current `img_desc` unchanged |
| `explanation` | `"Fallback: feedback appended to original query"` |

This ensures N8 always gets a usable payload to re-run the main workflow.

---

## Runtime Notes

- N17 uses the same Groq-compatible LLM endpoint as N5
- Model retries are performed across the configured provider chain
- Responses must contain JSON only — the LLM prompt explicitly instructs this
- Tag validation uses the project-wide tag registry (`backend.shared.maps.tags.ALL_TAGS`)
- Logging covers LLM call attempts, parse results, and fallback events via the project logging helper
