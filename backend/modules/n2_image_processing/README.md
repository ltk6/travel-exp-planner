# N2 Image Processing Module

N2 is the vision-to-text bridge in the pipeline. It accepts raw image bytes, optimizes the image for the configured vision model, and returns a short Vietnamese scene description that downstream modules can embed and rank semantically.

## Responsibilities

- Accept uploaded image bytes from the UI or orchestrator
- Normalize and compress images before sending them to the vision API
- Generate a concise Vietnamese `img_desc` focused on travel-relevant semantics
- Return model and token metadata when the call succeeds
- Return a structured error payload when processing fails

## Public API

```python
from backend.shared.contracts.n2_contracts import N2ImageInput

process_image(data: Union[N2ImageInput, dict]) -> dict
```

`process_image()` strictly enforces type-safety and structural checking at the runtime boundary using **Pydantic V2**.

## Input Shape

The module accepts raw dictionaries matching the schema below or a pre-instantiated `N2ImageInput` Pydantic model:

```python
class N2ImageInput(BaseModel):
    image: Optional[bytes] = Field(default=None, description="Raw bytes of the image to be processed.")
```

- `image`: raw binary image bytes (Optional, defaults to None)

## Output Shape

The output adheres to the `N2ImageOutput` contract:

```python
class N2ImageOutput(BaseModel):
    img_desc: Optional[str] = ""          # Concise Vietnamese visual description (Optional, defaults to "")
    metadata: Optional[Dict[str, Any]] = None # Model metadata (model used, tokens, usage)
    error: Optional[str] = None          # Error string if processing failed
```

### Successful Response Example:

```json
{
    "img_desc": "Bãi biển cát trắng mịn màng hoang sơ dưới nắng chiều vàng rực rỡ...",
    "metadata": {
        "model": "llama-3.2-11b-vision-preview",
        "usage": {
            "prompt_tokens": 128,
            "completion_tokens": 45,
            "total_tokens": 173
        }
    },
    "error": null
}
```

### Error Response Example:

```json
{
    "img_desc": "",
    "metadata": {
        "model": "llama-3.2-11b-vision-preview",
        "usage": {}
    },
    "error": "HTTPError: 401 - Unauthorized access to Groq vision model"
}
```

Notes:

- If `image` is missing, N2 returns `{"img_desc": "", "error": "No image provided"}`.
- `metadata` is present on successful responses and on most failure paths raised after request setup.
- The description is intended for downstream semantic retrieval, not for pixel-perfect captioning.

## Processing Flow

1. Read `image` bytes from the input payload.
2. Decode the image with Pillow.
3. Convert non-RGB images to RGB.
4. Downscale large images to fit within `1560 x 1560`.
5. Re-encode as JPEG with compression for the vision API request.
6. Send the image plus a travel-focused prompt to the configured Groq vision model.
7. Return the final text description and token usage metadata.

## Description Contract

The prompt in `processor.py` asks the model to produce:

- one short Vietnamese paragraph
- at most 50 words
- the location type
- the most distinctive visual feature
- the atmosphere or emotional tone

The prompt also explicitly avoids:

- generic framing like "Trong anh co..." or "Toi thay..."
- irrelevant details such as license plates, logos, or timestamps
- verbose list-style descriptions

## Model and Runtime Notes

- Vision provider: Groq API
- Model source: `config.GROQ_VISION_MODEL`
- Endpoint source: `config.GROQ_API_URL`
- Request timeout: 60 seconds
- Image optimization (compression and downscaling) is performed locally before the API call to ensure reliability and avoid payload size errors.
