# Unified Activity Schema — N5, N9–N14

> Package path: `backend/modules/activity_retrievals/`

Single source of truth cho output sau bước normalize của tất cả nguồn:
N5 (LLM) + N9 OSM + N10 Goong + N11 Foursquare + N12 Overture + N13 Wikidata + N14 Geoapify.

## Cấu trúc

```jsonc
{
  "activity_id": "foursquare_loc_001_56e626",   // {source}_{location_id}_{hash6}
  "location_id": "loc_001",                      // anchor location đang explore
  "source":      "foursquare",                   // enum: osm|goong|foursquare|overture|wikidata|geoapify|llm
  "retrieved_at":"2026-05-11T07:23:14Z",         // ISO-8601 UTC

  "metadata": {
    "name":             "Sapa Rice Fields",
    "description":      "Ruộng bậc thang Sa Pa...",
    "activity_type":    "nature",                // enum, xem dưới
    "activity_subtype": "scenic_walk",           // free-form, optional
    "categories_raw":   ["Nature Preserve"],     // category gốc từ nguồn, đã flatten string

    "estimated_duration":  180.0,                // minutes; null nếu không biết
    "price_level":         0.0,                  // 0.0 (free) → 1.0 (very expensive)
    "indoor_outdoor":      "outdoor",            // indoor | outdoor | mixed | null
    "weather_dependent":   true,                 // null nếu chưa xác định
    "time_of_day_suitable":"morning"             // morning | afternoon | night | anytime | null
  },

  "place": {
    "coordinates": { "lat": 22.300283, "lng": 103.892628 },  // hoặc null
    "distance_from_anchor_m": 12607,             // Haversine; null nếu coordinates null
    "address": {
      "country":   "VN",
      "region":    "Tỉnh Lào Cai",
      "city":      "Sa Pa",
      "street":    null,
      "formatted": "Sa Pa, Tỉnh Lào Cai"
    }
  },

  "signals": {
    "rating":        null,                       // 0.0 → 1.0
    "popularity":    null,                       // 0.0 → 1.0
    "image_url":     null,
    "website":       "https://...",
    "opening_hours": null,
    "phone":         null
  },

  "provenance": {
    "raw_source_id": "56e62678498e553b7a719cf4", // ID gốc trong nguồn; null cho LLM
    "source_url":    "https://foursquare.com/v/56e62678498e553b7a719cf4",
    "raw":           { /* payload gốc, optional — strip trước khi persist DB */ },
    "merged_from":   [                            // CHỈ XUẤT HIỆN sau khi chạy dedup
      {
        "source":          "osm",
        "activity_id":     "osm_loc_001_a7c4f1",
        "raw_source_id":   "node/854823033",
        "source_url":      "https://www.openstreetmap.org/node/854823033",
        "name_similarity": 0.92                    // chỉ có khi match Goong (stage 2)
      }
    ]
  }
}
```

## Enums

| Field | Allowed values |
|---|---|
| `source` | `osm`, `goong`, `foursquare`, `overture`, `wikidata`, `geoapify`, `llm` |
| `metadata.activity_type` | `adventure`, `relaxation`, `food`, `culture`, `nightlife`, `nature`, `shopping` |
| `metadata.indoor_outdoor` | `indoor`, `outdoor`, `mixed`, `null` |
| `metadata.time_of_day_suitable` | `morning`, `afternoon`, `night`, `anytime`, `null` |

## Quy tắc null vs default

- **`null`** = "không có thông tin từ nguồn này" (OSM thiếu `rating` → `null`).
- **Không bịa default** để tránh skew điểm N6. N6 hiện đã có nhánh xử lý null (`metadata.get(...)`), điểm trung tính 0.5.

## Per-source mapping ghi chú

| Nguồn | Coord có sẵn? | Category gốc | activity_type mapping |
|---|---|---|---|
| OSM | có (`lat`, `lon`) | `tags.tourism`, `tags.amenity`, `tags.historic`, `tags.leisure`, `tags.shop` | tags → 7 type |
| Goong | **không** (Autocomplete) | không có | `null` activity_type (sẽ enrich sau qua Place Detail) |
| Foursquare | có (`latitude`, `longitude`) | `categories[].name` | tên FSQ → 7 type |
| Overture | có (`geometry.coordinates`) | `properties.categories.primary` | Overture taxonomy → 7 type |
| Wikidata | có (`Point(lng lat)` WKT) | không có | default `culture` (nơi notable) |
| Geoapify | có (`lat`, `lon`) | `properties.categories[]` (dot-separated) | prefix → 7 type |
| LLM (N5) | **không** (kế thừa anchor) | không có | LLM tự gán |

## Activity ID

```
{source}_{location_id}_{hash6}
```

`hash6` = `md5(raw_source_id or name).hexdigest()[:6]`. Đảm bảo:
- Global unique giữa các nguồn (prefix khác).
- Stable: cùng raw_source_id luôn ra cùng activity_id (idempotent re-fetch).

## Storage strategy

- **Stage 1 (retrieve + normalize)**: giữ `provenance.raw` để debug.
- **Stage 2 (dedup)**: cross-source merge → thêm `provenance.merged_from` (list các source IDs đã absorbed). Xem `dedup.py`.
- **Stage 3 (persist + downstream)**: drop `provenance.raw` để giảm size (chỉ giữ `raw_source_id` + `source_url` + `merged_from`).
- Helper: `schema.strip_raw(activity)` để tiện chuyển stage.

## Dedup behavior

Sau khi chạy `dedup.dedupe_activities()` hoặc `retrieve_all(..., dedupe=True)`:
- Activity nào là canonical của 1 cluster → `provenance.merged_from` chứa entries của các source bị absorbed.
- Activity standalone (không duplicate) → `provenance.merged_from = []`.
- Canonical priority: `foursquare > overture > wikidata > geoapify > osm > goong > llm`.
