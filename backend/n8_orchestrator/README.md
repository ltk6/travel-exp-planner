# N8 Orchestrator Module

N8 is the backend API layer for the project. It exposes HTTP endpoints, validates protected access, coordinates all AI and data workflows, manages caching for location records and image assets, and handles user authentication and recommendation history.

## Responsibilities

- Start and configure the Flask application
- Register API routes and apply CORS rules
- Protect selected routes with an internal request key
- Deduplicate in-flight requests (idempotency guard)
- Warm up heavy modules in a background thread at startup
- Execute recommendation, activity, and feedback workflows
- Serve location images lazily from PostgreSQL (on-demand)
- Cache location payloads across RAM and disk
- Handle user registration, login, and recommendation history
- Return API-ready JSON responses for the frontend (N16)

## Entry Point

```python
app.py
```

## Module Structure

```
backend/n8_orchestrator/
├── app.py       # Flask app init, CORS, blueprint registration
├── routes.py    # All endpoint definitions and request guards
├── services.py  # Orchestration logic (recommend, activities, feedback, explore)
└── utils.py     # JSON parse helpers and error response builders
```

## Startup: Background Module Warmup

On startup, N8 spawns a background daemon thread (`_warmup_modules`) that eagerly imports all heavy dependencies (N1, N2, N3, N4, N5, N6, N17, shared weights). This eliminates the cold-start latency on the first real request. If the warmup thread fails, N8 falls back to lazy-loading via `__getattr__` on the services module.

---

## Public Routes

| Endpoint | Method | Auth Required | Description |
|---|---|---|---|
| `/health` | GET | No | Service status and runtime info |
| `/recommend` | POST | Yes | Full recommendation workflow |
| `/activities` | POST | No | Generate + rank activities via N5 LLM |
| `/activities/v2` | POST | No | DB-backed activities from N9–N14 providers |
| `/locations` | POST | No | Slim location list for Explore mode |
| `/api/images/<filename>` | GET | No | Lazy-serve location images from PostgreSQL |
| `/cache/reset` | POST | Yes | Force cache refresh from N3 |
| `/cache/fingerprint` | GET | Yes | Return current DB version fingerprint |
| `/feedback/recommend` | POST | Yes | Refine recommendation with user feedback |
| `/feedback/activities` | POST | Yes | Refine activity list with user feedback |
| `/api/auth/register` | POST | No | Register new user account |
| `/api/auth/login` | POST | No | Log in and return user_id |
| `/api/profile/history` | POST | Yes | Save a recommendation turn to history |
| `/api/profile/history/<user_id>` | GET | Yes | Retrieve recommendation history for user |

---

## Request Validation

### Authentication

Protected routes require the header:

```text
X-Internal-Key: <secret>
```

Requests missing or supplying an incorrect key are rejected with `401`.

### Idempotency Guard

For `POST` requests to `/recommend`, `/activities`, and `/activities/v2`, N8 computes a SHA-256 fingerprint of `{path}:{sorted JSON body}`. If an identical request is already in flight, the duplicate is rejected with `409 Conflict`. This prevents double-submissions from the frontend during slow AI calls.

Excluded from deduplication: `/cache/reset`, `/feedback/recommend`, `/feedback/activities`.

### Per-Endpoint Input Rules

| Endpoint | Required fields |
|---|---|
| `/recommend` | At least one of: `text`, `tags`, `image`, `images`, `img_desc` |
| `/activities` | `location` |
| `/activities/v2` | `location` (with `location_id`) |
| `/feedback/recommend` | `feedback` |
| `/feedback/activities` | `feedback` |

---

## Workflow: Recommendation (`/recommend`)

Orchestrates the full recommend pipeline:

1. Read `text`, `tags`, `image` (Base64), `img_desc`, `constraints`, `context`
2. If `image` is provided and `img_desc` is absent → call **N2** to generate `img_desc`
3. Call **N1** to embed `text + tags + img_desc` → `user_vectors`
4. Load locations from the hybrid cache (RAM → disk → N3)
5. Map N3 `vectors` key to `location_vectors` for N4 contract
6. Call **N4** to rank locations by cosine similarity
7. Attach lazy image URLs (`/api/images/{location_id}_{idx}.jpg`), metadata, and geo to ranked results
8. If `API_DEBUG` is set, attach a `trace` object with full pipeline visibility
9. If the body carries a `refined` field, pass it through to the response

**Response shape:**

```json
{
  "locations": [ { "location_id", "score", "metadata", "geo", "images": ["url", ...] } ],
  "trace": { ... },   // only when API_DEBUG=true
  "refined": { ... }  // only after a feedback cycle
}
```

---

## Workflow: Activities v1 (`/activities`)

Legacy pipeline — calls **N5** (LLM) to generate activities on every request:

1. Embed user context via **N1**
2. Build N5 input from `location` metadata
3. Call **N5** to generate candidate activities
4. Normalize activities through the LLM normalizer
5. Embed generated activities via **N1** (batch)
6. Rank via **N6** (cosine + attribute scoring)
7. Enrich ranked activities with full metadata before returning

---

## Workflow: Activities v2 (`/activities/v2`)

DB-backed pipeline — uses pre-seeded activities from providers (N9–N14):

1. Read activities already stored in PostgreSQL for the requested `location_id`
2. **If DB count < 3** (sparse / not yet seeded) → fall back to **N5 LLM** generation + embed + merge
3. Embed any activities missing vectors via **N1** batch
4. If `user_vectors` not provided or dimension mismatch → re-embed user input via **N1**
5. Rank via **N6**
6. Return enriched activities with source/provider metadata

The `meta` field in the response indicates `provider_used` (e.g. `n9-n14_db+n5_fallback`), `fallback_used`, and `latency_ms`.

---

## Workflow: Feedback (`/feedback/recommend` and `/feedback/activities`)

Pattern is identical for both feedback endpoints:

1. Receive original `text`, `tags`, `img_desc` + new `feedback` string
2. Call **N17** to refine the input parameters (`refined_text`, `refined_tags`, `refined_img_desc`)
3. Re-run the corresponding main workflow with refined inputs
4. Attach a `refined` object to the response so the frontend can show what changed

---

## Workflow: Explore (`/locations`)

Returns a slim location list for the `/explore` page in N16:

- Strips vectors
- Returns `location_id`, `metadata`, `geo`, and the first image URL per location
- Uses the same hybrid cache as `/recommend`

---

## Image Serving (`/api/images/<filename>`)

Images are served lazily: the frontend receives only URL strings in `/recommend` and `/locations` responses, then the browser fetches each image independently as it scrolls into view.

- Filename format: `{location_id}_{index}.jpg`
- Images are fetched directly from PostgreSQL via `N3.get_location_image_by_index()`
- If no image exists for the requested index, a 1×1 transparent PNG is returned (no broken image icons)
- Successful responses carry `Cache-Control: public, max-age=86400` for browser caching

---

## Caching Behavior

N8 maintains a hybrid three-tier cache for location data:

1. **RAM cache** — `_CACHED_LOCATIONS_DATA` / `_CACHED_FINGERPRINT` (fastest)
2. **Disk cache** — `location_cache.json` alongside `services.py` (survives restarts)
3. **Fingerprint TTL** — fingerprint is refreshed at most every 10 seconds to reduce DB round-trips

Cache validity is checked by comparing the stored fingerprint against `N3.get_db_fingerprint()`. A mismatch triggers a fresh `get_all_locations(include_images=False)` call and updates both RAM and disk. Images are never stored in the JSON cache — they are served lazily from PostgreSQL.

---

## Response Fields Summary

| Field | Present in |
|---|---|
| `locations` | `/recommend`, `/feedback/recommend` |
| `activities` | `/activities`, `/activities/v2`, `/feedback/activities` |
| `meta` | `/activities/v2` — provider info and latency |
| `ranking_meta` | `/activities`, `/activities/v2` — N6 metadata |
| `refined` | Any feedback endpoint — what N17 changed |
| `trace` | `/recommend` when `API_DEBUG=true` |

---

## Runtime Notes

- The Flask app enables CORS for origins defined in project configuration
- Routes are registered via a `Blueprint` (`n8_routes`)
- Request timing is logged for every route via `@bp.after_request`
- The internal key, allowed origins, host, port, and debug flag are all loaded from `config`
- Module logging uses the project-wide `setup_logging("N8.*")` helper
