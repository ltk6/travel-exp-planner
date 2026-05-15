# N1 Embedding Module

N1 is the semantic entry point for the retrieval pipeline. It takes raw user or location input, expands the available signals, and returns four normalized embedding channels plus lightweight metadata that downstream modules use for ranking.

## Responsibilities

- Preprocess `text`, `tags`, and `img_desc` into richer semantic strings
- Generate embeddings for `text`, `aug_text`, `aug_tags`, and `img_desc`
- Return signal-strength counters `text_k` and `tags_k`
- Attach per-item metadata about the active model, device, and latency

## Public API

```python
embed(data: dict[str, Any]) -> dict[str, Any]
embed_batch(data_list: list[dict[str, Any]]) -> list[dict[str, Any]]
```

`embed()` is a thin wrapper over `embed_batch([data])`.

## Input Shape

```python
{
    "text": str,
    "tags": list[str],
    "img_desc": str,
}
```

- `text`: free-form user or location text
- `tags`: controlled or semi-controlled travel tags
- `img_desc`: optional image description for multi-modal signal enrichment

## Output Shape

```python
{
    "text_k": int,
    "tags_k": int,
    "preprocessed": {
        "text": str,
        "aug_text": str,
        "aug_tags": str,
        "img_desc": str,
    },
    "vectors": {
        "text": list[float] | None,
        "aug_text": list[float] | None,
        "aug_tags": list[float] | None,
        "img_desc": list[float] | None,
    },
    "metadata": {
        "model": str,
        "device": str,
        "latency_ms": float,
    },
}
```

- `text_k`: number of matched text-side expansions added into `aug_text`
- `tags_k`: number of valid tag expansions added into `aug_tags`
- `preprocessed`: the strings that were actually sent to the embedding model
- `vectors`: normalized 1024-dim embeddings, or `None` for empty channels
- `metadata`: model/runtime information copied onto each item

## Preprocessing Behavior

N1 does not embed raw inputs blindly. Before encoding, it runs `preprocess()` to create channel-specific strings:

- `text`: original text, trimmed
- `aug_text`: original text plus matched emotion/context expansions
- `aug_tags`: ontology expansions for valid tags
- `img_desc`: original image description, trimmed

The preprocessor also emits:

- `text_k`: count of matched emotion/context expansions
- `tags_k`: count of recognized tag expansions

These counts are later consumed by ranking modules to adjust trust in each semantic channel.

## Batch Strategy

`embed_batch()` is the preferred high-throughput path.

- It preprocesses every item first.
- It flattens all four channels across the batch into one list of strings.
- It performs one `SentenceTransformer.encode()` call.
- It reconstructs the result into per-item dictionaries.

This keeps single-item and batch behavior consistent while avoiding repeated model calls.

## Model Notes

- Default model: `BAAI/bge-m3` via `config.EMBEDDING_MODEL_NAME`
- Embeddings are generated with `normalize_embeddings=True`
- Empty strings are preserved structurally but return `None` vectors
- The embedding model is loaded once and reused globally


