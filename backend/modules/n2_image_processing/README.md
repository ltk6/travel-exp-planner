# N2 Image Processing Module

N2 is the vision-to-text bridge in the pipeline. It accepts raw image bytes, optimizes the image for the configured vision model, and returns a short Vietnamese scene description that downstream modules (N1) can embed and rank semantically.

## Responsibilities

- Accept uploaded image bytes from N8 (forwarded from N16)
- Normalize and compress images locally before sending to the vision API
- Generate a concise Vietnamese `img_desc` focused on travel-relevant semantics
- Return model and token metadata on success
- Return a structured error payload on failure without crashing the pipeline

## Module Structure

```
backend/modules/n2_image_processing/
├── __init__.py    # Re-exports process_image
├── processor.py   # Core logic: resize, encode, Groq vision API call
└── requirements.txt
```

## Public API

```python
from modules.n2_image_processing import process_image
from backend.shared.contracts.n2_contracts import N2ImageInput

process_image(data: Union[N2ImageInput, dict]) -> dict
```

`process_image()` enforces Pydantic V2 validation at the module boundary.

---

## Input Contract

```python
class N2ImageInput(BaseModel):
    image: Optional[bytes] = None  # Raw binary image bytes
```

If `image` is `None` or missing, N2 returns `{"img_desc": "", "error": "No image provided"}` immediately without calling the API.

---

## Output Contract

```python
class N2ImageOutput(BaseModel):
    img_desc: Optional[str] = ""           # Vietnamese scene description
    metadata: Optional[Dict[str, Any]] = None  # Model name, token usage
    error: Optional[str] = None            # Error string if processing failed
```

### Successful response

```json
{
  "img_desc": "Bãi biển cát trắng mịn màng hoang sơ dưới nắng chiều vàng rực rỡ...",
  "metadata": {
    "model": "llama-3.2-11b-vision-preview",
    "usage": { "prompt_tokens": 128, "completion_tokens": 45, "total_tokens": 173 }
  },
  "error": null
}
```

### Error response

```json
{
  "img_desc": "",
  "metadata": { "model": "llama-3.2-11b-vision-preview", "usage": {} },
  "error": "HTTPError: 401 - Unauthorized access to Groq vision model"
}
```

`metadata` is present on both success and most failure paths raised after request setup.

---

## Processing Flow

1. Read `image` bytes from the input
2. Decode with Pillow; convert non-RGB modes to RGB
3. Downscale large images to fit within `1560 × 1560` pixels
4. Re-encode as JPEG for the vision API request
5. Send the image + travel-focused prompt to the configured Groq vision model
6. Return the description text and token usage metadata

---

## Description Contract

The prompt in `processor.py` instructs the model to produce:

- One short Vietnamese paragraph, at most 50 words
- Location type, most distinctive visual feature, and atmospheric/emotional tone

The prompt explicitly avoids:

- Generic framing ("Trong ảnh có...", "Tôi thấy...")
- Irrelevant details (license plates, logos, timestamps)
- Verbose list-style descriptions

The output `img_desc` is designed for downstream semantic retrieval — matched against location `img_desc` channel vectors in N4 — not for pixel-perfect captioning.

---

## Runtime Notes

- Vision provider: Groq API (`config.GROQ_VISION_MODEL`, `config.GROQ_API_URL`)
- Request timeout: 60 seconds
- Image optimization (resize + JPEG compression) is performed locally before the API call to avoid payload size errors
- N2 is called only when the user uploads an image in N16 and `img_desc` is not already present in the N8 request body
