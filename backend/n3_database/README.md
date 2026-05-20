# N3 Database Module

N3 is the unified persistence layer. It manages four data domains: location records, provider-sourced activities, user authentication, and recommendation history. All data is stored in PostgreSQL using `pgvector` for vector columns and JSONB for flexible payloads.

## Responsibilities

- Initialize all PostgreSQL schemas and required extensions
- Store and retrieve location vectors, metadata, geo, and images
- Store and retrieve activities from 6 external provider tables
- Track per-provider fetch status per location
- Manage user account registration and login
- Persist and retrieve full recommendation history per user
- Expose a lightweight database fingerprint for cache or sync checks
- Protect all connections with a Circuit Breaker and exponential-backoff retry

## Connection Resilience

N3 uses a built-in `CircuitBreaker` on all database connections:

- After 3 consecutive connection failures the breaker **opens**, rejecting all calls immediately to fail-fast
- After 30 seconds the breaker enters **half-open**, allowing one test connection
- On success the breaker **closes** and normal operation resumes

Each connection attempt retries up to 3 times with exponential backoff (0.5 s → 1 s → 2 s) before recording a failure.

---

## Domain 1: Locations

### Public API

```python
init_db(drop_existing: bool = False) -> None
save_location(location_data: dict[str, Any]) -> dict[str, Any]
get_all_locations(include_images: bool = True) -> dict[str, Any]
get_db_fingerprint() -> str
get_location_image_by_index(location_id: str, idx: int) -> bytes | None
attach_image_to_location(location_dict: dict[str, Any]) -> dict[str, Any]
```

### Storage Schema

Single `locations` table:

| Column | Type | Notes |
|---|---|---|
| `location_id` | `VARCHAR(255) PK` | Primary key |
| `text`, `aug_text`, `aug_tags`, `img_desc` | `vector(1024)` | Embedding channels |
| `metadata` | `JSONB` | Descriptive fields |
| `geo` | `JSONB` | Coordinates or map metadata |
| `images` | `BYTEA[]` | Raw image bytes |
| `updated_at` | `TIMESTAMP` | Used for fingerprinting |

### Input Shape (`save_location`)

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
    "images_binary": list[bytes],  # optional
}
```

- `images_binary` is optional; omitting it preserves existing images on upsert

### Output Contracts (`get_all_locations`)

All retrieval outputs are strictly validated at the N3 exit boundary using **Pydantic V2**:

```python
class N3LocationVectors(BaseModel):
    text: Optional[List[float]] = None
    aug_text: Optional[List[float]] = None
    aug_tags: Optional[List[float]] = None
    img_desc: Optional[List[float]] = None

class N3LocationMetadata(BaseModel):
    name: Optional[str] = "Unnamed Location"
    description: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    coordinates: Optional[Dict[str, Optional[float]]] = None
    address: Optional[str] = None
    model_config = {"extra": "allow"}

class N3Geo(BaseModel):
    lat: Optional[float] = 0.0
    lng: Optional[float] = 0.0
    model_config = {"extra": "allow"}

class N3LocationModel(BaseModel):
    location_id: str
    vectors: N3LocationVectors = Field(default_factory=N3LocationVectors)
    metadata: N3LocationMetadata = Field(default_factory=N3LocationMetadata)
    geo: Optional[N3Geo] = None
    images: List[str] = Field(default_factory=list)

class N3GetLocationsOutput(BaseModel):
    status: Optional[str] = "success"
    total: Optional[int] = 0
    data: List[N3LocationModel] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

`save_location` returns:

```python
{
    "status": "success" | "error",
    "location_id": str,
    "message": str,        # only on error
    "metadata": {"source": "postgresql", "latency_ms": int},
}
```

---

## Domain 2: Activities

N3 stores activities from 6 external providers: `osm`, `goong`, `foursquare`, `overture`, `wikidata`, `geoapify`. Each provider has its own table (`activities_<provider>`) and a shared `activity_fetch_status` tracker.

### Public API

```python
init_activities_db(drop_existing: bool = False) -> None
save_activities_batch(provider: str, activities: list[dict]) -> int
get_activities_for_location(location_id: str, providers: list[str] | None = None, include_vectors: bool = True) -> list[dict]
mark_fetch_status(location_id: str, provider: str, status: str, item_count: int = 0, error_msg: str | None = None) -> None
get_fetch_status_map(location_id: str) -> dict[str, dict]
count_activities_by_provider(location_id: str | None = None) -> dict[str, int]
```

### Storage Schema

Six `activities_<provider>` tables:

| Column | Type |
|---|---|
| `activity_id` | `VARCHAR(255) PK` |
| `location_id` | `VARCHAR(255)` |
| `metadata`, `place`, `signals` | `JSONB` |
| `vec_text`, `vec_tag` | `vector(1024)` |
| `quality_score` | `REAL` |
| `source` | `VARCHAR(32)` |
| `retrieved_at`, `embedded_at` | `TIMESTAMP` |
| `enriched` | `BOOLEAN` |

`activity_fetch_status` table: `(location_id, provider)` primary key tracking status per provider.

### Contracts

```python
class N3ActivityVectors(BaseModel):
    text: Optional[List[float]] = None
    tag: Optional[List[float]] = None

class N3ActivityItem(BaseModel):
    activity_id: Optional[str] = None
    location_id: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    place: Dict[str, Any] = Field(default_factory=dict)
    signals: Dict[str, Any] = Field(default_factory=dict)
    quality_score: Optional[float] = None
    enriched: Optional[bool] = None
    vectors: Optional[N3ActivityVectors] = None

class N3FetchStatus(BaseModel):
    status: Optional[str] = None
    item_count: Optional[int] = 0
    fetched_at: Optional[str] = None
    error_msg: Optional[str] = None
```

- `save_activities_batch` returns the number of successfully upserted rows
- `get_fetch_status_map` returns `{provider: N3FetchStatus}` — providers with no row are absent (= not yet fetched)
- `status` values for `mark_fetch_status`: `success`, `empty`, `error`, `rate_limited`, `no_key`

---

## Domain 3: User Authentication

### Public API

```python
init_profile_db(drop_existing: bool = False) -> None
register_user(username: str, password: str) -> dict[str, Any]
login_user(username: str, password: str) -> dict[str, Any]
```

### Storage Schema

`users` table:

| Column | Type |
|---|---|
| `user_id` | `SERIAL PK` |
| `username` | `VARCHAR(255) UNIQUE` |
| `password_hash` | `VARCHAR(255)` |
| `created_at` | `TIMESTAMP` |

Passwords are hashed with `werkzeug.security.generate_password_hash`.

### Contracts

```python
class N3RegisterInput(BaseModel):
    username: str
    password: str

class N3LoginInput(BaseModel):
    username: str
    password: str

class N3AuthOutput(BaseModel):
    status: Optional[str] = ""
    message: Optional[str] = ""
    user_id: Optional[int] = None
```

- `register_user` returns `status: "error"` with `message: "Ten dang nhap da ton tai"` on duplicate username
- `login_user` returns `status: "error"` with `message: "Sai tai khoan va mat khau"` on bad credentials

---

## Domain 4: Recommendation History

### Public API

```python
save_rec_turn(user_id: int, input_data: dict, output_data: dict) -> dict[str, Any]
get_user_history(user_id: int) -> dict[str, Any]
```

### Storage Schema

`rec_history` table:

| Column | Type |
|---|---|
| `history_id` | `SERIAL PK` |
| `user_id` | `INT` |
| `input_data` | `JSONB` |
| `output_data` | `JSONB` |
| `created_at` | `TIMESTAMP` |

### Contracts

```python
class N3SaveHistoryInput(BaseModel):
    user_id: int
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)

class N3HistoryItem(BaseModel):
    history_id: Optional[int] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None

class N3GetHistoryOutput(BaseModel):
    status: Optional[str] = "success"
    data: List[N3HistoryItem] = Field(default_factory=list)
```

- `get_user_history` returns results ordered by `created_at DESC`
- `created_at` is serialized as `"YYYY-MM-DD HH:MM:SS"` string

---

## Runtime Notes

- Database connections use `psycopg2` with `RealDictCursor`
- `pgvector.psycopg2.register_vector()` is called on every new connection
- The database fingerprint is derived from total row count + max `updated_at` — a cheap way to detect whether a full reload is necessary
- Logging is configured through the project logging helper

## Seed Tooling

N3 also includes a seed-ingestion helper in [`seeds/add_more_locs/`](seeds/add_more_locs/README.md).

- It embeds new locations through N1 before saving them
- It updates `seed_data.py`, `locations_with_vectors.json`, `seeds/raw_imgs/`, and `seeds/images/`
- It saves the final record into PostgreSQL using resized image bytes from `seeds/images/`
- It asks for confirmation before deleting source JSON/image files after a successful import
