"""
prune_activities.py
===================
Post-process activities trong DB để giảm noise + size:

1. Cross-loc dedup: mỗi POI (source + name + coord_4dp) chỉ giữ ở loc gần
   nhất (haversine). Drop duplicates ở các loc xa hơn.
2. Re-score: score = quality * exp(-dist_km / DECAY_KM), với DECAY_KM=5
   (ưu tiên POI gần anchor).
3. Downsample: mỗi loc giữ top CAP_PER_LOC=65 acts theo score desc, cross
   provider. Drop rest.
4. Optional: drop entire provider (--drop-provider overture).

Idempotent: chạy lại không tạo dup mới. Sau khi xong nên `VACUUM FULL`
để reclaim disk.

Usage:
  python -m backend.n3_database.seeds.prune_activities --dry-run
  python -m backend.n3_database.seeds.prune_activities --drop-provider overture
  python -m backend.n3_database.seeds.prune_activities --cap 65 --decay-km 5
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.n3_database.db_manager import (
    ACTIVITY_PROVIDERS,
    _activity_table,
    _get_connection,
)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Khoảng cách giữa 2 điểm (km)."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _load_loc_anchors(cur) -> Dict[str, Tuple[float, float]]:
    cur.execute("SELECT location_id, geo FROM locations;")
    out: Dict[str, Tuple[float, float]] = {}
    for r in cur.fetchall():
        g = r["geo"] or {}
        lat = g.get("lat")
        lng = g.get("lng")
        if lat is not None and lng is not None:
            out[r["location_id"]] = (float(lat), float(lng))
    return out


def _load_acts(cur, table: str) -> List[Dict[str, Any]]:
    cur.execute(
        f"""SELECT activity_id, location_id,
                   metadata->>'name' AS name,
                   place->'coordinates'->>'lat' AS lat,
                   place->'coordinates'->>'lng' AS lng,
                   quality_score
            FROM {table};"""
    )
    acts: List[Dict[str, Any]] = []
    for r in cur.fetchall():
        lat = r["lat"]
        lng = r["lng"]
        try:
            lat = float(lat) if lat is not None else None
            lng = float(lng) if lng is not None else None
        except (TypeError, ValueError):
            lat = lng = None
        acts.append({
            "activity_id":  r["activity_id"],
            "location_id":  r["location_id"],
            "name":         (r["name"] or "").strip(),
            "lat":          lat,
            "lng":          lng,
            "quality":      float(r["quality_score"] or 0.0),
        })
    return acts


def _cross_loc_dedup(
    acts: List[Dict[str, Any]],
    anchors: Dict[str, Tuple[float, float]],
) -> Tuple[List[Dict[str, Any]], int]:
    """Group by (name, lat_4dp, lng_4dp). Trong mỗi group, giữ act ở loc
    gần POI nhất (theo haversine từ anchor loc tới POI).
    """
    groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    no_key: List[Dict[str, Any]] = []
    for a in acts:
        if not a["name"] or a["lat"] is None or a["lng"] is None:
            no_key.append(a)
            continue
        key = (a["name"].lower(), f"{round(a['lat'], 4):.4f}", f"{round(a['lng'], 4):.4f}")
        groups.setdefault(key, []).append(a)

    keep: List[Dict[str, Any]] = list(no_key)
    dropped = 0
    for group_acts in groups.values():
        if len(group_acts) == 1:
            keep.append(group_acts[0])
            continue
        # Pick the one with smallest distance from its loc anchor to POI
        best = None
        best_dist = float("inf")
        for a in group_acts:
            anchor = anchors.get(a["location_id"])
            if not anchor:
                continue
            d = _haversine_km(anchor[0], anchor[1], a["lat"], a["lng"])
            if d < best_dist:
                best_dist = d
                best = a
        if best is None:
            best = group_acts[0]
        keep.append(best)
        dropped += len(group_acts) - 1
    return keep, dropped


def _score(
    a: Dict[str, Any],
    anchors: Dict[str, Tuple[float, float]],
    decay_km: float,
) -> float:
    """score = quality * exp(-dist / decay_km). dist=0 nếu thiếu coord."""
    if a["lat"] is None or a["lng"] is None:
        return a["quality"]
    anchor = anchors.get(a["location_id"])
    if not anchor:
        return a["quality"]
    d = _haversine_km(anchor[0], anchor[1], a["lat"], a["lng"])
    return a["quality"] * math.exp(-d / decay_km)


def _downsample_per_loc(
    acts: List[Dict[str, Any]],
    anchors: Dict[str, Tuple[float, float]],
    cap: int,
    decay_km: float,
) -> Tuple[List[str], List[str]]:
    """Trả về (keep_ids, drop_ids). Group by loc, sort by score desc, keep top cap."""
    by_loc: Dict[str, List[Dict[str, Any]]] = {}
    for a in acts:
        by_loc.setdefault(a["location_id"], []).append(a)
    keep, drop = [], []
    for loc_id, group in by_loc.items():
        scored = sorted(
            group,
            key=lambda a: _score(a, anchors, decay_km),
            reverse=True,
        )
        keep.extend(a["activity_id"] for a in scored[:cap])
        drop.extend(a["activity_id"] for a in scored[cap:])
    return keep, drop


def _delete_ids(cur, table: str, ids: List[str], batch: int = 500) -> int:
    n = 0
    for i in range(0, len(ids), batch):
        chunk = ids[i:i + batch]
        cur.execute(f"DELETE FROM {table} WHERE activity_id = ANY(%s);", (chunk,))
        n += cur.rowcount
    return n


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap", type=int, default=65)
    parser.add_argument("--decay-km", type=float, default=2.0)
    parser.add_argument("--max-dist-km", type=float, default=None,
                        help="(legacy) Hard cut beyond this distance. Disabled if --tiers set.")
    parser.add_argument("--tiers", type=str, default="4,7,15",
                        help="Adaptive radius tiers in km, comma-sep. Default 4,7,15.")
    parser.add_argument("--min-acts", type=int, default=10,
                        help="Per-loc floor: expand to next tier if below this.")
    parser.add_argument("--drop-provider", action="append", default=[],
                        help="Provider to drop entirely (repeatable)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--vacuum", action="store_true",
                        help="VACUUM FULL after prune (locks tables briefly)")
    args = parser.parse_args()

    print("=" * 70)
    print(f"PRUNE — cap={args.cap}/loc  decay={args.decay_km}km  "
          f"drop={args.drop_provider}  dry_run={args.dry_run}")
    print("=" * 70)

    conn = _get_connection()
    cur = conn.cursor()
    anchors = _load_loc_anchors(cur)
    print(f"Loaded {len(anchors)} loc anchors")

    providers = [p for p in ACTIVITY_PROVIDERS if p not in args.drop_provider]
    print(f"Providers to process: {providers}")
    print(f"Providers to drop: {args.drop_provider}")

    summary: Dict[str, Dict[str, int]] = {}

    # ── 1. Drop entire providers ──────────────────────────────────────────
    for p in args.drop_provider:
        if p not in ACTIVITY_PROVIDERS:
            print(f"[WARN] unknown provider {p!r}")
            continue
        table = _activity_table(p)
        cur.execute(f"SELECT COUNT(*) AS n FROM {table};")
        n_before = cur.fetchall()[0]["n"]
        if args.dry_run:
            print(f"[DRY] would drop {n_before} rows from {table}")
        else:
            cur.execute(f"DELETE FROM {table};")
            cur.execute(
                "DELETE FROM activity_fetch_status WHERE provider=%s;", (p,)
            )
            print(f"  dropped {n_before} rows from {table}")
        summary[p] = {"dropped_full": n_before, "deduped": 0, "downsampled": 0}

    # ── 2a. Cross-loc dedup per provider ──────────────────────────────────
    surviving_by_provider: Dict[str, List[Dict[str, Any]]] = {}
    dedup_drop_by_provider: Dict[str, List[str]] = {}
    for p in providers:
        table = _activity_table(p)
        print(f"\n[{p}] loading...")
        acts = _load_acts(cur, table)
        n_before = len(acts)
        if n_before == 0:
            print(f"  {table} empty, skip")
            summary[p] = {"dropped_full": 0, "deduped": 0, "downsampled": 0, "out_of_radius": 0}
            surviving_by_provider[p] = []
            dedup_drop_by_provider[p] = []
            continue

        far_drop_ids: List[str] = []
        kept_acts, n_dedup_dropped = _cross_loc_dedup(acts, anchors)
        keep_set = {a["activity_id"] for a in kept_acts}
        dedup_drop_ids = [a["activity_id"] for a in acts if a["activity_id"] not in keep_set]
        surviving_by_provider[p] = kept_acts
        dedup_drop_by_provider[p] = dedup_drop_ids + far_drop_ids
        # Tag survivors with provider for cross-provider downsample
        for a in kept_acts:
            a["_provider"] = p
        print(f"  before={n_before}  out_of_radius=-{len(far_drop_ids)}  "
              f"cross-loc dup=-{n_dedup_dropped}  survive={len(kept_acts)}")
        summary[p] = {
            "dropped_full":   0,
            "deduped":        n_dedup_dropped,
            "downsampled":    0,
            "out_of_radius":  len(far_drop_ids),
        }

    # ── 2b. Adaptive-radius + cross-provider downsample per loc ───────────
    all_survivors: List[Dict[str, Any]] = []
    for acts in surviving_by_provider.values():
        all_survivors.extend(acts)
    print(f"\n[downsample] surviving across all providers: {len(all_survivors)}")

    tiers = sorted({float(t.strip()) for t in args.tiers.split(",") if t.strip()})
    if not tiers:
        tiers = [args.max_dist_km or 1e9]
    print(f"  tiers={tiers}km  min_acts={args.min_acts}  cap={args.cap}  decay={args.decay_km}km")

    by_loc: Dict[str, List[Dict[str, Any]]] = {}
    for a in all_survivors:
        by_loc.setdefault(a["location_id"], []).append(a)

    downsample_drop_ids: List[str] = []
    tier_used_count: Dict[float, int] = {t: 0 for t in tiers}
    for loc_id, group in by_loc.items():
        anchor = anchors.get(loc_id)
        if anchor is None:
            continue
        # Compute distance per act once
        for a in group:
            if a["lat"] is None or a["lng"] is None:
                a["_dist"] = 0.0
            else:
                a["_dist"] = _haversine_km(anchor[0], anchor[1], a["lat"], a["lng"])
        # Find smallest tier that yields >= min_acts (or use largest)
        chosen_tier = tiers[-1]
        for t in tiers:
            n_in = sum(1 for a in group if a["_dist"] <= t)
            if n_in >= args.min_acts:
                chosen_tier = t
                break
        tier_used_count[chosen_tier] += 1
        # Drop acts beyond chosen tier
        in_radius = []
        for a in group:
            if a["_dist"] <= chosen_tier:
                in_radius.append(a)
            else:
                downsample_drop_ids.append(a["activity_id"])
        # Score + downsample within radius
        in_radius.sort(
            key=lambda a: a["quality"] * math.exp(-a["_dist"] / args.decay_km),
            reverse=True,
        )
        for a in in_radius[args.cap:]:
            downsample_drop_ids.append(a["activity_id"])

    print(f"  drop {len(downsample_drop_ids)} rows total")
    print(f"  tier usage: {dict(sorted(tier_used_count.items()))}")

    # Map drop ids back to their provider table
    id_to_provider: Dict[str, str] = {a["activity_id"]: a["_provider"] for a in all_survivors}
    downsample_drops_by_provider: Dict[str, List[str]] = {}
    for aid in downsample_drop_ids:
        p = id_to_provider.get(aid)
        if p:
            downsample_drops_by_provider.setdefault(p, []).append(aid)

    # ── 2c. Apply deletes per provider ────────────────────────────────────
    for p in providers:
        table = _activity_table(p)
        dedup_ids = dedup_drop_by_provider.get(p, [])
        ds_ids = downsample_drops_by_provider.get(p, [])
        total_drop_ids = dedup_ids + ds_ids
        if not total_drop_ids:
            continue
        if args.dry_run:
            print(f"  [DRY] {table}: would delete {len(total_drop_ids)} rows "
                  f"(dedup={len(dedup_ids)}, downsample={len(ds_ids)})")
        else:
            n_deleted = _delete_ids(cur, table, total_drop_ids)
            print(f"  {table}: deleted {n_deleted} rows "
                  f"(dedup={len(dedup_ids)}, downsample={len(ds_ids)})")
        summary[p]["downsampled"] = len(ds_ids)

    # ── 3. VACUUM (reclaim disk) ──────────────────────────────────────────
    if args.vacuum and not args.dry_run:
        # Postgres VACUUM cannot run inside transaction → set autocommit and use new cursor
        conn.set_session(autocommit=True)
        for p in ACTIVITY_PROVIDERS:
            t = _activity_table(p)
            print(f"  VACUUM FULL {t}...")
            cur.execute(f"VACUUM FULL {t};")
        print("  VACUUM done")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total_dropped = 0
    for p in ACTIVITY_PROVIDERS:
        s = summary.get(p, {})
        if not s:
            continue
        n = (s.get("dropped_full", 0) + s.get("deduped", 0)
             + s.get("downsampled", 0) + s.get("out_of_radius", 0))
        total_dropped += n
        print(f"  {p:12s}  drop_provider={s.get('dropped_full',0):5d}  "
              f"out_of_radius={s.get('out_of_radius',0):5d}  "
              f"dedup={s.get('deduped',0):5d}  downsample={s.get('downsampled',0):5d}  "
              f"total_dropped={n}")
    print(f"\nTOTAL DROPPED: {total_dropped}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
