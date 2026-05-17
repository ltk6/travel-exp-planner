"""
Unified activity retrieval package.

Sub-packages:
- normalizers/: 7 adapter functions (osm, goong, foursquare, overture, wikidata, geoapify, llm)
  → chuyển payload thô từ N5 + N9-N14 thành unified schema.
- schema.py: định nghĩa schema + validator + factory + helpers.
- orchestrator.py: fan-out 6 retrievers (n9-n14) song song, normalize, aggregate.

Public API:
    >>> from backend.modules.activity_retrievals import retrieve_all
    >>> retrieve_all({"location_id": "loc_001", "lat": 22.30, "lng": 103.77})

Tham khảo SCHEMA.md để biết chi tiết unified schema.
"""

from .orchestrator import ALL_SOURCES, retrieve_all
from .processor import process_activities
from .schema import (
    ALLOWED_ACTIVITY_TYPES,
    ALLOWED_INDOOR_OUTDOOR,
    ALLOWED_SOURCES,
    ALLOWED_TIME_OF_DAY,
    build_activity,
    haversine_m,
    make_activity_id,
    strip_raw,
    validate,
)

__all__ = [
    "ALL_SOURCES",
    "ALLOWED_SOURCES",
    "ALLOWED_ACTIVITY_TYPES",
    "ALLOWED_INDOOR_OUTDOOR",
    "ALLOWED_TIME_OF_DAY",
    "build_activity",
    "haversine_m",
    "make_activity_id",
    "process_activities",
    "retrieve_all",
    "strip_raw",
    "validate",
]
