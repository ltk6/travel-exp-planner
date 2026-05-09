# Location Ranking Module

Ranks travel locations using weighted multi-channel cosine similarity between user and location vectors.

## API

```python
rank_locations(data: dict) -> dict
```

### Input

* `text_k`, `tags_k`: Signal strengths (determines weights)
* `user_vectors`: Embeddings from N1 (`text`, `aug_text`, `aug_tags`, `img_desc`)
* `locations`: List of locations from N3 with `location_vectors` (`text`, `aug_tags`)
* `top_k`: Number of locations to return

### Output

* `locations`: Sorted list of ranked results:
  * `location_id`: Unique identifier
  * `score`: Final similarity score (normalized)
  * `reason`: Vietnamese explanation of the recommendation
