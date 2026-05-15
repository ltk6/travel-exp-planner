# N8 Orchestrator Module

N8 is the backend API layer for the project. It exposes HTTP endpoints, validates protected access, coordinates recommendation and activity workflows, and manages caching for location records and image assets.

## Responsibilities

- Start and configure the Flask application
- Register API routes and apply CORS rules
- Protect selected routes with an internal request key
- Execute recommendation, activity, and feedback workflows
- Cache location payloads and decoded image assets locally
- Return API-ready JSON responses for the frontend

## Entry Point

```python
app.py
```

## Public Routes

```text
GET  /health
POST /recommend
POST /activities
POST /cache/reset
GET  /cache/fingerprint
POST /feedback/recommend
POST /feedback/activities
```

## Route Behavior

- `/health`: returns service availability and runtime status information
- `/recommend`: accepts a recommendation payload and returns ranked location results
- `/activities`: accepts one selected location plus user context and returns ranked activities
- `/cache/reset`: forces a refresh of cached location data
- `/cache/fingerprint`: returns the current data fingerprint used for cache validation
- `/feedback/recommend`: refines a recommendation request with feedback text
- `/feedback/activities`: refines an activity request with feedback text

## Request Validation

Protected routes require:

```text
X-Internal-Key
```

Requests missing the expected key are rejected with `401`.

The recommendation route also requires at least one of:

- `text`
- `tags`

The activities route requires:

- `location`

The feedback routes require:

- `feedback`

## Response Behavior

N8 returns JSON responses for all routes.

Typical response shapes include:

- ranked `locations`
- ranked `activities`
- workflow `metadata`
- optional `refined` payloads after feedback-driven reruns
- error objects for invalid or failed requests

## Caching Behavior

N8 maintains a hybrid cache for location data:

1. in-memory cache for the fastest reuse path
2. disk cache in `location_cache.json`
3. local image file cache in `image_cache/`

Cache validity is checked with a fingerprint value. Image payloads are persisted as local JPEG files so large Base64 blobs do not have to remain in memory or JSON cache files.

## Runtime Notes

- the Flask app enables CORS for configured origins
- routes are registered through a blueprint
- the module logs service loading, cache behavior, and request execution through the project logging helper
- the API host, port, debug mode, protected route set, and internal key are loaded from project configuration
