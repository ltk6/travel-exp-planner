# Activity Retrievals — N9–N14

The `activity_retrievals` package is the multi-source POI ingestion layer. It fans out across six external map/data providers (N9–N14), normalizes all raw results to a unified activity schema, deduplicates cross-source matches, and produces a ranked, quality-scored set of activities ready for embedding by N1 and storage in N3.

This package is used offline as a seed pipeline (via `seed_activities.py`) to pre-populate the activities tables in PostgreSQL. At runtime, N8 serves the pre-seeded data via `activities_v2_service` without re-fetching.

## Responsibilities

- Fan out six provider retrievers in parallel (one thread per source, I/O-bound)
- Normalize all raw payloads into the unified activity schema
- Validate schema conformance per activity; drop invalid items without failing the pipeline
- Deduplicate activities cross-source by geo proximity and normalized name similarity
- Score activity quality by field completeness
- Filter by required fields (coordinates + activity_type), language, and quality threshold
- Balance sightseeing vs. active types and enforce source diversity in the final output
- Optionally enrich missing descriptions and names via N5 LLM (Vietnamese, experience-focused)
- Persist enriched results to `processed/{location_id}.json` for use by the seed script

## Package Structure

```
backend/modules/activity_retrievals/
├── __init__.py              # Public API: retrieve_all, process_activities, schema helpers
├── orchestrator.py          # Fan-out: 6 retrievers → normalize → aggregate
├── processor.py             # Clean + filter + score + balance + LLM enrich pipeline
├── dedup.py                 # Cross-source deduplication (geo cluster + name similarity)
├── schema.py                # Unified schema factory, validator, constants, helpers
├── SCHEMA.md                # Detailed schema specification (this document's companion)
├── normalizers/
│   ├── osm.py               # OSM Overpass → unified schema
│   ├── goong.py             # Goong Autocomplete → unified schema
│   ├── foursquare.py        # Foursquare → unified schema
│   ├── overture.py          # Overture Maps → unified schema
│   ├── wikidata.py          # Wikidata SPARQL → unified schema
│   ├── geoapify.py          # Geoapify Places → unified schema
│   ├── llm.py               # N5 LLM output → unified schema
│   └── shared.py            # Shared helpers (haversine, category mapping)
├── n9_osm/
│   └── retriever.py         # fetch_osm_nearby() via Overpass API
├── n10_goong/
│   └── retriever.py         # fetch_goong_nearby() via Goong Autocomplete
├── n11_foursquare/
│   └── retriever.py         # fetch_foursquare_nearby()
├── n12_overture/
│   └── retriever.py         # fetch_overture_nearby()
├── n13_wikidata/
│   └── retriever.py         # fetch_wikidata_nearby() via SPARQL
└── n14_geoapify/
    └── retriever.py         # fetch_geoapify_nearby()
```

## Public API

```python
from backend.modules.activity_retrievals import retrieve_all, process_activities
```

### `retrieve_all(location, radius, sources, validate, dedupe)`

Runs N9–N14 in parallel and returns all normalized activities for one anchor location.

```python
result = retrieve_all(
    location={"location_id": "loc_001", "lat": 22.30, "lng": 103.77},
    radius=20000,       # meters (default)
    sources=None,       # None = all 6; or list subset e.g. ["osm", "foursquare"]
    validate=True,      # schema validate each activity (default)
    dedupe=False,       # cross-source dedup (default off — see processor)
)
```

Returns:
```python
{
    "location_id":      str,
    "anchor":           {"lat": float, "lng": float},
    "radius_m":         int,
    "activities":       [unified activity dicts],
    "by_source":        {source: {raw_count, normalized_count, valid_count, elapsed_s, error}},
    "total_activities": int,
    "total_elapsed_s":  float,
    "dedup_stats":      { ... }  # only when dedupe=True
}
```

### `process_activities(location, radius, top_k, enrich_descriptions, persist)`

Full seed pipeline for one location: retrieve → filter → quality-score → balance → optionally enrich → persist.

```python
result = process_activities(
    location={"location_id": "loc_001", "lat": 22.30, "lng": 103.77, "name": "Fansipan"},
    radius=20000,
    top_k=10,
    enrich_descriptions=True,   # LLM rewrite names + generate Vietnamese descriptions
    persist=True,               # write processed/{location_id}.json
)
```

Returns:
```python
{
    "location_id": str,
    "activities":  [top_k cleaned activities],
    "stats": {
        "raw":                   int,
        "after_has_required":    int,
        "after_anchor_drop":     int,
        "after_name_dedupe":     int,
        "output":                int,
        "output_sightseeing":    int,
        "output_activity":       int,
        "descriptions_enriched": int,
    },
    "elapsed_s":   float,
    "output_path": str | None,
}
```

---

## Provider Sources (N9–N14)

| Module | Source | API | Coordinates | Key required |
|---|---|---|---|---|
| N9 | OpenStreetMap (Overpass) | Overpass API | Yes (`lat`/`lon`) | No |
| N10 | Goong Maps | Autocomplete endpoint | No (enriched via Place Detail) | `GOONG_API_KEY` |
| N11 | Foursquare | Places API | Yes (`latitude`/`longitude`) | `FOURSQUARE_API_KEY` |
| N12 | Overture Maps | DuckDB / Parquet | Yes (`geometry.coordinates`) | No |
| N13 | Wikidata | SPARQL endpoint | Yes (WKT `Point(lng lat)`) | No |
| N14 | Geoapify | Places API | Yes (`lat`/`lon`) | `GEOAPIFY_API_KEY` |

Each retriever exposes a single function `fetch_<source>_nearby(lat, lng, radius) -> list` and caches raw results to a local `cache/` directory to avoid repeat API calls during development.

---

## Unified Activity Schema

All sources are normalized to the same structure by their respective normalizers. See [SCHEMA.md](SCHEMA.md) for the full field reference.

Key top-level fields:

```jsonc
{
  "activity_id":  "{source}_{location_id}_{hash6}",
  "location_id":  "loc_001",
  "source":       "foursquare",       // osm|goong|foursquare|overture|wikidata|geoapify|llm
  "retrieved_at": "2026-05-11T07:23:14Z",
  "metadata":     { "name", "description", "activity_type", "indoor_outdoor", ... },
  "place":        { "coordinates", "distance_from_anchor_m", "address" },
  "signals":      { "rating", "image_url", "website", "opening_hours", ... },
  "provenance":   { "raw_source_id", "source_url", "merged_from" }
}
```

### Activity Type Enum

All sources map their categories to 7 activity types:

`adventure` · `relaxation` · `food` · `culture` · `nightlife` · `nature` · `shopping`

### Source Priority for Deduplication

When cross-source dedup finds duplicate POIs, the canonical record is chosen by priority:

`foursquare > overture > wikidata > geoapify > osm > goong > llm`

---

## Processing Pipeline (`processor.py`)

The `process_activities()` function runs a multi-stage pipeline:

1. **Retrieve** — `retrieve_all()` fans out N9–N14 in parallel
2. **Filter** — keep only activities with `coordinates` AND `activity_type`
3. **Anchor drop** — remove POIs whose name duplicates the anchor location name (e.g. "Hạ Long Bay" anchor → drop POI "Hạ Long")
4. **Quality score** — score each activity `[0.0, 1.0]` by field completeness (description, type, rating, etc.)
5. **Sort** — by quality descending, distance ascending as tiebreak
6. **Name dedup** — O(N) pass; keep highest-quality entry per normalized name or rounded coordinate
7. **Source diversity cap** — limit per-source dominance in the candidate pool
8. **Balance** — interleave sightseeing (`nature`, `culture`) and action types at a 40/60 ratio; or boost user-preferred types 70/30 if `preferred_types` is provided
9. **LLM enrich** — batch N5 call to rewrite names (Vietnamese, action-verb style) and generate Vietnamese descriptions for all top results
10. **Persist** — write `processed/{location_id}.json`

### Quality Score Weights

| Field | Weight |
|---|---|
| `metadata.description` | 2.0 |
| `metadata.activity_type` | 1.5 |
| `signals.rating` | 1.5 |
| `metadata.indoor_outdoor` | 1.0 |
| `signals.image_url` | 1.0 |
| `metadata.estimated_duration` | 0.5 |
| `signals.opening_hours` | 0.5 |
| `signals.website` | 0.3 |

---

## Deduplication (`dedup.py`)

`dedup.dedupe_activities()` performs cross-source deduplication in two stages:

1. **Geo cluster** — activities within ~50m of each other are candidates for the same POI
2. **Name similarity** — within a geo cluster, activities with normalized name similarity ≥ threshold are merged; the canonical record absorbs the others into `provenance.merged_from`

Standalone activities get `provenance.merged_from = []`.

> **Note:** The full `dedupe_activities()` call is currently disabled in `process_activities()` due to O(28 × N) comparison cost (~50s for ~3700 raw items). Source-diversity cap + filter steps give acceptable quality without it.

---

## Activity ID Format

```
{source}_{location_id}_{hash6}
```

`hash6 = md5(raw_source_id or name).hexdigest()[:6]`

- Global unique across sources (different prefix per source)
- Stable: same `raw_source_id` always produces the same `activity_id` (idempotent re-fetch)

---

## Runtime Notes

- Each source runs in its own thread (I/O-bound: network waits); up to 6 workers in parallel
- Source failures are isolated — a network error from Foursquare does not abort OSM or Wikidata
- Raw API responses are cached to `n{N}_{source}/cache/` to avoid repeat calls in development
- Language filter (`drop_foreign_script`) removes activities with Cyrillic, CJK, Arabic, Hangul, or Katakana characters to avoid noise from international tourist sources
- The `strip_raw()` helper removes `provenance.raw` before persisting to PostgreSQL to reduce row size
