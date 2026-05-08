# Embedding Module

Provides public interfaces to convert raw inputs into multi-channel embeddings.

* Support multi-language inputs (BAAI/bge-m3).
* Efficiently handle single input and batch inputs.

## API

```python
embed(data: dict[str, Any]) -> dict[str, Any]
embed_batch(data_list: list[dict[str, Any]]) -> list[dict[str, Any]]
```

### Single Dict Input

* `text`: raw text input
* `tags`: list of tags
* `img_desc`: visual description

### Single Dict Output

* `text_k`: text keywords expansion count
* `tags_k`: tags expansion count
* `preprocessed`: normalized + expanded inputs with keys:
  * `text`: raw text input (pass through)
  * `aug_text`: expanded text input
  * `aug_tags`: expanded tag input
  * `img_desc`: visual description (pass through)
* `vectors`: embeddings for `text`, `aug_text`, `aug_tags`, `img_desc`

### Batch Inputs

* `data_list`: list of single dict inputs

### Batch Outputs

* `results`: list of single dict outputs
