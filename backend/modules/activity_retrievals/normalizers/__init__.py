"""
Normalizer adapters.

Mỗi module exposes `normalize(raw_item, ctx)` và `normalize_all(raw_items, ctx)`.

`ctx` (LocationContext) shape:
    {
        "location_id":  str,            # required
        "anchor_lat":   float | None,
        "anchor_lng":   float | None,
        "anchor_address": dict | None,  # optional, dùng cho llm inheritance
    }
"""

from . import foursquare, geoapify, goong, llm, osm, overture, wikidata

# Registry: ánh xạ source name → module, tiện cho orchestrator gọi động.
REGISTRY = {
    "osm":        osm,
    "goong":      goong,
    "foursquare": foursquare,
    "overture":   overture,
    "wikidata":   wikidata,
    "geoapify":   geoapify,
    "llm":        llm,
}

__all__ = ["REGISTRY", "osm", "goong", "foursquare", "overture", "wikidata", "geoapify", "llm"]
