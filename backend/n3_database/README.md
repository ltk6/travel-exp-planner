# N3 Database Module

N3 is the persistence layer for location records. It stores vectors in PostgreSQL with `pgvector`, keeps metadata and geo payloads in JSONB, and returns API-ready records with images encoded as Base64 data URLs.

## Responsibilities

- Initialize the PostgreSQL schema and required `vector` extension
- Store location vectors, metadata, geo fields, and optional binary images
- Return all stored locations in a normalized response structure
- Expose a lightweight database fingerprint for cache or sync checks
- Preserve a compatibility helper for image-attached location payloads

## Public API

```python
init_db() -> None
save_location(location_data: dict[str, Any]) -> dict[str, Any]
get_all_locations(include_images: bool = True) -> dict[str, Any]
get_db_fingerprint() -> str
attach_image_to_location(location_dict: dict[str, Any]) -> dict[str, Any]
```

## Storage Schema

N3 creates a single `locations` table with these fields:

- `location_id`: primary key
- `text`, `aug_text`, `aug_tags`, `img_desc`: `vector(1024)` columns
- `metadata`: JSONB payload for descriptive fields
- `geo`: JSONB payload for coordinates or map metadata
- `images`: `BYTEA[]` for raw image bytes
- `updated_at`: timestamp used for sync fingerprinting

## Input Shape

`save_location()` expects a location payload in this form:

```python
{
    "location_id": str,
    "vectors": {
        "text": list[float] | None,
        "aug_text": list[float] | None,
        "aug_tags": list[float] | None,
        "img_desc": list[float] | None,
    },
    "metadata": dict[str, Any],
    "geo": dict[str, Any],
    "images_binary": list[bytes],
}
```

- `images_binary` is optional; when omitted, existing stored images are preserved on upsert
- vector channels should already be normalized upstream if that property matters to ranking

## Output Shapes

`save_location()` returns:

```python
{
    "status": "success" | "error",
    "location_id": str,
    "message": str,  # only on error
    "metadata": {
        "source": "postgresql",
        "latency_ms": int,
    },
}
```

`get_all_locations()` returns:

```python
{
    "status": "success" | "error",
    "total": int,
    "data": [
        {
            "location_id": str,
            "vectors": {
                "text": list[float] | None,
                "aug_text": list[float] | None,
                "aug_tags": list[float] | None,
                "img_desc": list[float] | None,
            },
            "metadata": dict[str, Any] | None,
            "geo": dict[str, Any] | None,
            "images": list[str],
        }
    ],
    "metadata": {
        "source": "postgresql",
        "latency_ms": int,
    },
}
```

- `images` is always present and contains Base64 `data:image/jpeg` URLs when image bytes exist
- vector values are converted from pgvector objects into plain Python lists

## Persistence Behavior

`init_db()` is intentionally destructive for the `locations` table:

- it ensures the `vector` extension exists
- it drops `locations` if present
- it recreates the table from scratch

This is appropriate for controlled initialization and reseeding, but it should not be treated as a migration system.

`save_location()` uses an upsert keyed by `location_id`:

- vector, metadata, and geo fields are replaced on conflict
- images are replaced only when the incoming payload contains at least one image
- `updated_at` is refreshed on every insert or update

## Retrieval Behavior

`get_all_locations()` supports two modes:

- `include_images=True`: fetch vectors, metadata, geo, and binary images
- `include_images=False`: skip the `images` column at query time for lighter reads

The database fingerprint is derived from:

- total row count
- max `updated_at`

This gives callers a cheap way to detect whether a full reload is necessary.

## Runtime Notes

- Database connections use `psycopg2` with `RealDictCursor`
- `pgvector.psycopg2.register_vector()` is called on every new connection
- Logging is configured through the project logging helper
- The module reads its PostgreSQL connection string from project configuration
