# N1 Embedding Module

N1 is the semantic entry point for the retrieval pipeline. It takes raw user or location input, expands the available signals across four semantic channels, and returns normalized embedding vectors plus lightweight signal metadata used by downstream ranking modules.

## Responsibilities

- Preprocess `text`, `tags`, and `img_desc` into richer semantic strings via channel-specific augmentation
- Generate 1024-dim normalized embeddings for `text`, `aug_text`, `aug_tags`, and `img_desc`
- Return signal-strength counters `text_k` and `tags_k` for dynamic weight resolution in N4/N6
- Attach per-item metadata (model name, device, latency) to every output

## Module Structure

```
backend/modules/n1_embedding/
├── __init__.py      # Public API: embed() and embed_batch()
├── embedder.py      # SentenceTransformer wrapper, model singleton, embed_strings()
├── preprocessor.py  # Text expansion, tag ontology lookup, channel string construction
└── requirements.txt
```

## Public API

```python
from modules.n1_embedding import embed, embed_batch
from backend.shared.contracts.n1_contracts import N1EmbedInput

embed(data: Union[N1EmbedInput, dict]) -> dict
embed_batch(data_list: list[Union[N1EmbedInput, dict]]) -> list[dict]
```

`embed()` is a thin wrapper over `embed_batch([data])`. Both functions enforce Pydantic V2 validation at the module boundary.

---

## Input Contract

```python
class N1EmbedInput(BaseModel):
    text: str = ""          # Free-form user or location text
    tags: List[str] = []    # Controlled travel tags
    img_desc: str = ""      # Visual description from N2 (optional)
```

All fields are optional and default to empty. At least one non-empty field is expected for a useful embedding.

---

## Output Contract

```python
class PreprocessedText(BaseModel):
    text: Optional[str] = ""
    aug_text: Optional[str] = ""
    aug_tags: Optional[str] = ""
    img_desc: Optional[str] = ""

class EmbedVectors(BaseModel):
    text: Optional[List[float]] = None
    aug_text: Optional[List[float]] = None
    aug_tags: Optional[List[float]] = None
    img_desc: Optional[List[float]] = None

class N1EmbedOutput(BaseModel):
    text_k: int = 0
    tags_k: int = 0
    preprocessed: PreprocessedText
    vectors: EmbedVectors
    metadata: Dict[str, Any]
```

| Field | Description |
|---|---|
| `text_k` | Count of emotion/context expansions merged into `aug_text` |
| `tags_k` | Count of recognized tag expansions merged into `aug_tags` |
| `preprocessed` | Actual strings sent to the embedding model (for tracing) |
| `vectors` | 1024-dim float lists, or `None` for channels with no content |
| `metadata` | `{model, device, latency_ms}` |

---

## Preprocessing Behavior

Before encoding, `preprocessor.preprocess()` constructs four channel strings:

| Channel | Content |
|---|---|
| `text` | Original text, trimmed |
| `aug_text` | Original text + matched emotion/context keyword expansions |
| `aug_tags` | Ontology expansions for recognized tag values |
| `img_desc` | Original image description, trimmed |

`text_k` and `tags_k` count how many expansions were added. These are passed to N4/N6 to scale trust in each channel dynamically — a query with rich tags gives more weight to `aug_tags`, and so on.

---

## Batch Strategy

`embed_batch()` is the preferred high-throughput path and is used by N8 for both user-query embedding and activity batch-embedding:

1. Validate and preprocess every item
2. Flatten all four channels across the entire batch into one string list
3. Run a single `SentenceTransformer.encode()` call
4. Unflatten results back into per-item output dicts

This ensures exactly one GPU/CPU forward pass regardless of batch size.

---

## Runtime Notes

- Model: `BAAI/bge-m3` via `config.EMBEDDING_MODEL_NAME`
- Embeddings are generated with `normalize_embeddings=True` (unit vectors for cosine similarity)
- Empty strings produce `None` vectors, preserved structurally in the output
- The model is loaded once as a module-level singleton via `embedder.get_model()`
- Device (CPU/GPU) is detected automatically and reported in metadata
