"""
seed_activities.py
==================
Seed N9-N14 activities cho 25 loc trong seed_data.LOCATIONS vào Postgres.

Flow per loc:
  1. Check activity_fetch_status — bỏ qua provider đã 'success' hoặc 'empty'
  2. Fetch + normalize từng provider còn thiếu (uses orchestrator._run_source)
  3. Apply filter chain:
       has_coords + has_type
     → drop anchor duplicates
     → quality score + sort (desc, distance asc)
     → drop foreign script (Cyrillic/CJK/Arabic/...)
     → quality >= 0.3
     → name+coord dedupe
     → cap 30/provider
  4. LLM enrich (Vietnamese name + description) — eager
  5. N1 batch embed (text vector + tag vector)
  6. Bulk upsert vào activities_<provider> + mark fetch_status

Idempotent: rerun chỉ retry các (loc, provider) chưa success/empty.

Usage:
  python -m backend.n3_database.seeds.seed_activities              # incremental
  python -m backend.n3_database.seeds.seed_activities --reset      # drop+recreate DB
  python -m backend.n3_database.seeds.seed_activities --loc loc_001 # 1 loc
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.n3_database.db_manager import (
    ACTIVITY_PROVIDERS,
    count_activities_by_provider,
    delete_activities_for_location,
    get_all_locations,
    get_fetch_status_map,
    init_activities_db,
    mark_fetch_status,
    save_activities_batch,
)
from backend.n3_database.seeds.seed_data import LOCATIONS
from backend.modules.activity_retrievals.orchestrator import _run_source
from backend.modules.activity_retrievals.processor import (
    _dedupe_aggressive,
    _drop_anchor_duplicates,
    _enrich_descriptions,
    _fix_mojibake_names,
    _has_required,
    _quality_score,
    _rank_key,
    cap_per_source,
    drop_foreign_script,
    drop_non_vietnamese,
    drop_off_anchor,
    filter_by_distance,
    filter_by_quality,
)
from backend.modules.n1_embedding import embed_batch

RADIUS_M = 20000
MAX_PER_SOURCE = 30
MIN_QUALITY = 0.3
MAX_DISTANCE_M = 8000.0   # bán kính cho "phải nằm tại" anchor (city-level OK).

# Status được coi là đã "xong" — không retry trừ khi --force
DONE_STATUSES = {"success", "empty"}


def _build_n1_input(activity: Dict[str, Any]) -> Dict[str, Any]:
    md = activity.get("metadata") or {}
    name = (md.get("name") or "").strip()
    desc = (md.get("description") or "").strip()
    text = f"{name}. {desc}".strip(". ").strip()
    raw_tags = md.get("categories_raw") or md.get("tags") or []
    if not isinstance(raw_tags, list):
        raw_tags = []
    tags: List[str] = []
    for t in raw_tags:
        if not isinstance(t, str):
            continue
        cleaned = t.split("=", 1)[-1]
        cleaned = cleaned.replace(".", " ").replace("_", " ").replace("-", " ").strip()
        if cleaned:
            tags.append(cleaned)
    return {"text": text, "tags": tags, "img_desc": ""}


def _seed_one_location(loc: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
    """Seed 1 loc. Return stats dict."""
    loc_id = loc["location_id"]
    loc_name = loc["metadata"]["name"]
    lat = float(loc["geo"]["lat"])
    lng = float(loc["geo"]["lng"])

    t0 = time.time()
    print(f"\n[loc={loc_id}] {loc_name} ({lat:.4f},{lng:.4f})")

    status_map = {} if force else get_fetch_status_map(loc_id)
    todo_providers = [
        p for p in ACTIVITY_PROVIDERS
        if status_map.get(p, {}).get("status") not in DONE_STATUSES
    ]

    if not todo_providers:
        print(f"  [skip] All 6 providers already fetched")
        return {"loc_id": loc_id, "skipped": True}

    # Khi --force: xoá toàn bộ rows cũ cho loc này để tránh leftover từ pipeline cũ
    # (pipeline mới drop nhiều POI hơn → activity_id cũ thành stale).
    if force:
        n_deleted = delete_activities_for_location(loc_id)
        if n_deleted:
            print(f"  [reset] deleted {n_deleted} stale rows from previous run")

    ctx = {
        "location_id":    loc_id,
        "anchor_lat":     lat,
        "anchor_lng":     lng,
        "anchor_address": loc.get("address"),
    }

    # ─── 1. Fetch + normalize per provider ──────────────────────────────────
    raw_by_provider: Dict[str, List[Dict[str, Any]]] = {}
    per_provider_stats: Dict[str, Dict[str, Any]] = {}

    for provider in todo_providers:
        t_p = time.time()
        result = _run_source(provider, lat, lng, RADIUS_M, ctx, validate=True)
        elapsed = time.time() - t_p

        if result.get("error"):
            err = result["error"]
            status = "rate_limited" if "429" in err or "RateLimit" in err else "error"
            mark_fetch_status(loc_id, provider, status, error_msg=err[:500])
            per_provider_stats[provider] = {"status": status, "raw": 0, "err": err[:80]}
            print(f"  [{provider:10s}] {status:14s} ({elapsed:.1f}s) — {err[:80]}")
            continue

        acts = result.get("activities") or []
        raw_by_provider[provider] = acts
        per_provider_stats[provider] = {
            "status": "ok",
            "raw":    result["raw_count"],
            "valid":  result["valid_count"],
        }
        print(f"  [{provider:10s}] raw={result['raw_count']:4d} valid={result['valid_count']:4d} ({elapsed:.1f}s)")

    if not raw_by_provider:
        print(f"  [fail] No provider returned data for {loc_id}")
        return {"loc_id": loc_id, "total_saved": 0, "providers": per_provider_stats}

    # ─── 2. Aggregate + filter chain ────────────────────────────────────────
    all_acts: List[Dict[str, Any]] = []
    for acts in raw_by_provider.values():
        all_acts.extend(acts)

    n_raw = len(all_acts)
    all_acts = [a for a in all_acts if _has_required(a)]
    n_req = len(all_acts)

    all_acts = _drop_anchor_duplicates(all_acts, loc_name)
    n_anchor = len(all_acts)

    # Strict distance — phải nằm TẠI anchor location, không chỉ "gần đó".
    all_acts = filter_by_distance(all_acts, max_distance_m=MAX_DISTANCE_M)
    n_dist = len(all_acts)

    for a in all_acts:
        a["_quality"] = _quality_score(a)
    all_acts.sort(key=_rank_key)

    all_acts = drop_foreign_script(all_acts)
    n_foreign = len(all_acts)

    all_acts = filter_by_quality(all_acts, min_quality=MIN_QUALITY)
    n_quality = len(all_acts)

    # Aggressive dedupe (translation-aware + coord bucket + core-name).
    all_acts = _dedupe_aggressive(all_acts)
    n_dedupe = len(all_acts)

    all_acts = cap_per_source(all_acts, max_per=MAX_PER_SOURCE)
    n_cap = len(all_acts)

    print(f"  filter: raw={n_raw} req={n_req} anchor={n_anchor} dist={n_dist} foreign={n_foreign} quality={n_quality} dedupe={n_dedupe} cap={n_cap}")

    if not all_acts:
        for provider in todo_providers:
            if per_provider_stats.get(provider, {}).get("status") == "ok":
                mark_fetch_status(loc_id, provider, "empty", 0)
        return {"loc_id": loc_id, "total_saved": 0, "providers": per_provider_stats}

    # ─── 3. Eager LLM enrich — name VN, description VN, tags từ ontology,
    #        at_anchor flag (compound model có web-search để xác minh).
    t_e = time.time()
    n_before_enrich = len(all_acts)
    enriched_count = _enrich_descriptions(all_acts, loc_name)
    # Đánh dấu activities đã được LLM chạm vào → DB.enriched=True chỉ với những
    # POI thật sự có _confidence > 0 (đã có name+desc+tags từ LLM).
    for a in all_acts:
        if a.get("_confidence") is not None:
            a["enriched"] = True

    # Recover mojibake (vd "VƯỜN" → "VÉN") trước các filter ngôn ngữ — LLM enrich
    # đôi khi re-encode sai tên có dấu, phải restore từ name_original nếu sạch.
    all_acts = _fix_mojibake_names(all_acts)

    # Hậu lọc dựa trên đánh giá của LLM (at_anchor + ngôn ngữ).
    all_acts = drop_off_anchor(all_acts)
    n_after_anchor = len(all_acts)
    all_acts = drop_non_vietnamese(all_acts)
    n_after_vn = len(all_acts)

    # Strip transient flags trước khi embed/save.
    for a in all_acts:
        a.pop("_at_anchor", None)
        a.pop("_confidence", None)

    print(
        f"  enrich: {enriched_count}/{n_before_enrich} via LLM "
        f"→ at_anchor={n_after_anchor} → vn={n_after_vn} ({time.time()-t_e:.1f}s)"
    )

    if not all_acts:
        for provider in todo_providers:
            if per_provider_stats.get(provider, {}).get("status") == "ok":
                mark_fetch_status(loc_id, provider, "empty", 0)
        return {"loc_id": loc_id, "total_saved": 0, "providers": per_provider_stats}

    # ─── 4. N1 batch embed ──────────────────────────────────────────────────
    t_n1 = time.time()
    n1_inputs = [_build_n1_input(a) for a in all_acts]
    n1_results = embed_batch(n1_inputs)
    for a, r in zip(all_acts, n1_results):
        v = r.get("vectors") or {}
        a["vectors"] = {"text": v.get("text"), "tag": v.get("aug_tags")}
        a["quality_score"] = a.pop("_quality", None)
    print(f"  embed:  {len(all_acts)} acts via N1 ({time.time()-t_n1:.1f}s)")

    # ─── 5. Group by source, bulk save ──────────────────────────────────────
    by_source: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for a in all_acts:
        by_source[a["source"]].append(a)

    saved_per_provider: Dict[str, int] = {}
    for provider in todo_providers:
        acts_for_p = by_source.get(provider, [])
        if not acts_for_p:
            if per_provider_stats.get(provider, {}).get("status") == "ok":
                mark_fetch_status(loc_id, provider, "empty", 0)
            saved_per_provider[provider] = 0
            continue
        n_saved = save_activities_batch(provider, acts_for_p)
        mark_fetch_status(loc_id, provider, "success", n_saved)
        saved_per_provider[provider] = n_saved

    total_saved = sum(saved_per_provider.values())
    print(f"  saved:  {' '.join(f'{p}={n}' for p,n in saved_per_provider.items())} → total {total_saved} ({time.time()-t0:.1f}s)")

    return {
        "loc_id":      loc_id,
        "total_saved": total_saved,
        "saved":       saved_per_provider,
        "providers":   per_provider_stats,
        "elapsed_s":   round(time.time() - t0, 2),
    }


def _load_all_locations_union() -> List[Dict[str, Any]]:
    """
    Merge LOCATIONS (seed_data.py) với toàn bộ rows trong DB locations table.
    Lý do: locations mới được add qua add_more_locs/importer.py chỉ vào DB chứ
    không quay lại seed_data.py → cần lấy từ DB để cover loc_026+.

    Ưu tiên entry từ seed_data.py (canonical metadata) khi trùng location_id.
    """
    by_id: Dict[str, Dict[str, Any]] = {}
    for L in LOCATIONS:
        by_id[L["location_id"]] = L

    db_resp = get_all_locations(include_images=False)
    if db_resp.get("status") == "success":
        for d in db_resp.get("data", []):
            lid = d.get("location_id")
            if not lid or lid in by_id:
                continue
            geo = d.get("geo") or {}
            md  = d.get("metadata") or {}
            by_id[lid] = {
                "location_id": lid,
                "metadata":    md,
                "geo":         {"lat": geo.get("lat"), "lng": geo.get("lng")},
                "address":     d.get("address"),
            }
    return sorted(by_id.values(), key=lambda L: L["location_id"])


def main():
    parser = argparse.ArgumentParser(description="Seed activities for N9-N14 sources")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all activity tables")
    parser.add_argument("--force", action="store_true", help="Re-fetch even success/empty providers")
    parser.add_argument("--loc", type=str, default=None, help="Seed only this location_id")
    parser.add_argument("--from-loc", type=str, default=None,
                        help="Seed from this location_id onwards (inclusive)")
    parser.add_argument("--to-loc", type=str, default=None,
                        help="Seed up to this location_id (inclusive)")
    args = parser.parse_args()

    all_locs = _load_all_locations_union()

    print("=" * 70)
    print(f"N9-N14 ACTIVITY SEEDING — {len(all_locs)} loc total (seed_data + DB)")
    print(f"  reset={args.reset}  force={args.force}  loc={args.loc or 'all'}"
          f"  from={args.from_loc or '-'}  to={args.to_loc or '-'}")
    print("=" * 70)

    init_activities_db(drop_existing=args.reset)

    targets = all_locs
    if args.loc:
        targets = [l for l in targets if l["location_id"] == args.loc]
    if args.from_loc:
        targets = [l for l in targets if l["location_id"] >= args.from_loc]
    if args.to_loc:
        targets = [l for l in targets if l["location_id"] <= args.to_loc]
    if not targets:
        print(f"[ERROR] No locations matched filter "
              f"(loc={args.loc!r} from={args.from_loc!r} to={args.to_loc!r})")
        sys.exit(1)

    t_total = time.time()
    results = []
    for i, loc in enumerate(targets, 1):
        try:
            print(f"\n{'-' * 70}\n[{i:02d}/{len(targets)}]", end=" ")
            r = _seed_one_location(loc, force=args.force)
            results.append(r)
        except KeyboardInterrupt:
            print("\n[INTERRUPTED] partial state saved")
            break
        except Exception as e:
            print(f"  [FATAL] {loc['location_id']}: {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()
            results.append({"loc_id": loc["location_id"], "error": str(e)})

    elapsed = time.time() - t_total

    print("\n" + "=" * 70)
    print(f"SEED COMPLETE in {elapsed:.1f}s")
    print("=" * 70)
    counts = count_activities_by_provider()
    print("\nDB totals per provider:")
    for p, n in counts.items():
        print(f"  {p:12s} = {n}")
    print(f"  {'TOTAL':12s} = {sum(counts.values())}")

    skipped = sum(1 for r in results if r.get("skipped"))
    errors  = sum(1 for r in results if r.get("error"))
    seeded  = len(results) - skipped - errors
    print(f"\nLocations: seeded={seeded} skipped={skipped} errors={errors}")


if __name__ == "__main__":
    main()
