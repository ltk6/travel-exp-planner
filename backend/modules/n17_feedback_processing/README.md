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
process_feedback(
    user_input: str,
    user_tags: list[str],
    img_desc: str,
    feedback_text: str,
    llm_chain: str | None = None,
) -> dict[str, Any]
```

## Input Shape

```python
{
    "user_input": str,
    "user_tags": list[str],
    "img_desc": str,
    "feedback_text": str,
    "llm_chain": str | None,
}
```

- `user_input`: current free-form query text
- `user_tags`: current normalized tag list
- `img_desc`: current image description, if any
- `feedback_text`: the user's refinement request
- `llm_chain`: optional model-chain override

## Output Shape

```python
{
    "refined_text": str,
    "refined_tags": list[str],
    "refined_img_desc": str,
    "explanation": str,
    "metadata": {
        "model": str | None,
        "provider": str | None,
        "usage": dict | None,
    },
}
```

- `refined_tags` is filtered to valid normalized tag keys
- `refined_img_desc` may be an empty string when the user wants to ignore the image
- `explanation` is intended to be shown directly in the UI

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
