"""
Orchestrator — fan-out 6 retrievers (n9-n14) song song cho 1 anchor location,
normalize tất cả về unified schema, trả 1 list activities + báo cáo per-source.

Hàm chính: `retrieve_all(location, radius=20000)`.

Lưu ý:
- KHÔNG bao gồm N5 (LLM). N5 cần `user` + `constraints` riêng — gọi qua
  `backend.modules.n5_activity_generation.generate_activities()`.
- Mỗi source chạy trong 1 thread (I/O-bound: chờ network). 6 worker tối đa.
- Source nào lỗi → log + đưa `error` vào `by_source`, KHÔNG phá toàn bộ pipeline.
- Mặc định validate=True: drop activity nào không pass schema (vẫn đếm trong
  `normalized_count`, chỉ `valid_count` mới phản ánh số đã pass).
"""

from __future__ import annotations

import concurrent.futures
import importlib
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from .normalizers import REGISTRY as _NORMALIZER_REGISTRY
from .schema import validate as _validate_schema

logger = logging.getLogger(__name__)


# source → (module_path, function_name)
_FETCHER_REGISTRY: Dict[str, tuple] = {
    "osm":        ("backend.modules.activity_retrievals.n9_osm.retriever",         "fetch_osm_nearby"),
    "goong":      ("backend.modules.activity_retrievals.n10_goong.retriever",      "fetch_goong_nearby"),
    "foursquare": ("backend.modules.activity_retrievals.n11_foursquare.retriever", "fetch_foursquare_nearby"),
    "overture":   ("backend.modules.activity_retrievals.n12_overture.retriever",   "fetch_overture_nearby"),
    "wikidata":   ("backend.modules.activity_retrievals.n13_wikidata.retriever",   "fetch_wikidata_nearby"),
    "geoapify":   ("backend.modules.activity_retrievals.n14_geoapify.retriever",   "fetch_geoapify_nearby"),
}

ALL_SOURCES = tuple(_FETCHER_REGISTRY.keys())


def _get_fetcher(source: str) -> Optional[Callable]:
    """Lazy-import fetcher function. Trả None nếu module/function không tồn tại."""
    if source not in _FETCHER_REGISTRY:
        return None
    module_path, func_name = _FETCHER_REGISTRY[source]
    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        logger.warning("Cannot import %s fetcher module: %s", source, e)
        return None
    fetcher = getattr(mod, func_name, None)
    if fetcher is None:
        logger.warning("%s fetcher module loaded but %r not found", source, func_name)
    return fetcher


def _run_source(
    source: str,
    lat: float,
    lng: float,
    radius: int,
    ctx: Dict[str, Any],
    validate: bool,
) -> Dict[str, Any]:
    """
    Fetch + normalize 1 source. KHÔNG raise — luôn trả dict status.
    """
    start = time.monotonic()
    result: Dict[str, Any] = {
        "source":            source,
        "raw_count":         0,
        "normalized_count":  0,
        "valid_count":       0,
        "elapsed_s":         0.0,
        "error":             None,
        "activities":        [],
    }

    try:
        fetcher = _get_fetcher(source)
        if fetcher is None:
            result["error"] = "fetcher_unavailable"
            return result

        raw_items = fetcher(lat=lat, lng=lng, radius=radius) or []
        result["raw_count"] = len(raw_items)

        normalizer = _NORMALIZER_REGISTRY[source]
        normalized = normalizer.normalize_all(raw_items, ctx)
        result["normalized_count"] = len(normalized)

        if validate:
            valid: List[Dict[str, Any]] = []
            for a in normalized:
                try:
                    _validate_schema(a)
                    valid.append(a)
                except ValueError as e:
                    logger.debug("[%s] schema invalid: %s", source, e)
            result["valid_count"] = len(valid)
            result["activities"]  = valid
        else:
            result["valid_count"] = len(normalized)
            result["activities"]  = normalized

    except (KeyError, AssertionError):
        # Programmer bug (sai registry / sai invariant) — re-raise để fail loud trong dev.
        raise
    except Exception as e:
        # Lỗi runtime của fetcher/normalizer (network, parse, schema field thiếu, …)
        # — không phá pipeline, chỉ ghi nhận trong by_source[source].error.
        result["error"] = f"{type(e).__name__}: {e}"
        logger.warning("[%s] fetch+normalize failed: %s", source, result["error"])

    result["elapsed_s"] = round(time.monotonic() - start, 2)
    return result


def retrieve_all(
    location: Dict[str, Any],
    radius: int = 20000,
    sources: Optional[List[str]] = None,
    validate: bool = True,
    max_workers: int = 6,
    dedupe: bool = False,
) -> Dict[str, Any]:
    """
    Chạy 6 source song song cho 1 anchor location.

    Args:
        location: dict với required keys:
            - location_id: str
            - lat: float (anchor)
            - lng: float (anchor)
            Optional:
            - address: dict — kế thừa vào activity nếu source không cung cấp riêng
        radius:  bán kính (mét). Default 20000.
        sources: subset của ALL_SOURCES. Default = chạy hết 6 nguồn.
        validate: chạy schema.validate trên mỗi activity (default True).
        max_workers: số thread tối đa (default 6 = 1 thread/source).
        dedupe: nếu True, chạy cross-source dedup sau khi aggregate. Default False.

    Returns:
        {
            "location_id":      str,
            "anchor":           {"lat": float, "lng": float},
            "radius_m":         int,
            "activities":       [unified activities — flat list từ tất cả sources],
            "by_source":        {source: {raw_count, normalized_count, valid_count,
                                          elapsed_s, error}},
            "total_activities": int,
            "total_elapsed_s":  float,
            "dedup_stats":      {input_count, geo_clusters_merged, ...} (chỉ khi dedupe=True),
        }
    """
    if "location_id" not in location:
        raise ValueError("location must have 'location_id'")
    if "lat" not in location or "lng" not in location:
        raise ValueError("location must have 'lat' and 'lng'")

    loc_id = str(location["location_id"])
    lat    = float(location["lat"])
    lng    = float(location["lng"])
    sources = list(sources) if sources else list(ALL_SOURCES)

    unknown = [s for s in sources if s not in _FETCHER_REGISTRY]
    if unknown:
        raise ValueError(f"Unknown sources: {unknown}. Allowed: {ALL_SOURCES}")

    ctx = {
        "location_id":    loc_id,
        "anchor_lat":     lat,
        "anchor_lng":     lng,
        "anchor_address": location.get("address"),
    }

    start = time.monotonic()
    by_source: Dict[str, Dict[str, Any]] = {}
    all_activities: List[Dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_source = {
            executor.submit(_run_source, src, lat, lng, radius, ctx, validate): src
            for src in sources
        }
        for future in concurrent.futures.as_completed(future_to_source):
            src = future_to_source[future]
            result = future.result()
            # Tách activities khỏi status để by_source gọn
            by_source[src] = {k: v for k, v in result.items() if k != "activities"}
            all_activities.extend(result["activities"])

    elapsed = round(time.monotonic() - start, 2)
    logger.info(
        "retrieve_all loc=%s: %d activities from %d sources in %.2fs",
        loc_id, len(all_activities), len(sources), elapsed,
    )

    result: Dict[str, Any] = {
        "location_id":      loc_id,
        "anchor":           {"lat": lat, "lng": lng},
        "radius_m":         radius,
        "activities":       all_activities,
        "by_source":        by_source,
        "total_activities": len(all_activities),
        "total_elapsed_s":  elapsed,
    }

    if dedupe:
        from .dedup import dedupe_activities
        deduped, dedup_stats = dedupe_activities(all_activities)
        result["activities"]        = deduped
        result["total_activities"]  = len(deduped)
        result["dedup_stats"]       = dedup_stats
        logger.info(
            "retrieve_all loc=%s deduped: %d → %d (%d clusters merged, %d goong matched)",
            loc_id, dedup_stats["input_count"], dedup_stats["output_count"],
            dedup_stats["geo_clusters_merged"], dedup_stats["no_geo_matched"],
        )

    return result


__all__ = ["retrieve_all", "ALL_SOURCES"]
