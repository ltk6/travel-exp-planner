"""
reenrich_activities.py
======================
Re-enrich activities hiện có `enriched=False` (chưa được dịch VN tên/mô tả)
bằng cách gọi lại N5 LLM via groq. Dùng khi Groq daily limit đã reset
sau khi seed bị 429.

Idempotent: chỉ touch row enriched=False. Sau khi dịch xong, set enriched=True.

Usage:
  python -m backend.n3_database.seeds.reenrich_activities
  python -m backend.n3_database.seeds.reenrich_activities --provider osm
  python -m backend.n3_database.seeds.reenrich_activities --max-locs 5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.n3_database.db_manager import (
    ACTIVITY_PROVIDERS,
    _activity_table,
    _get_connection,
)
from backend.n3_database.seeds.seed_data import LOCATIONS
from backend.modules.activity_retrievals.processor import _enrich_descriptions
from backend.modules.n1_embedding import embed_batch


LOC_NAME_BY_ID = {L["location_id"]: L["metadata"]["name"] for L in LOCATIONS}


def _collect_unenriched(loc_id: str) -> List[Dict[str, Any]]:
    """Đọc activities enriched=False cho 1 loc, gộp từ N provider."""
    conn = _get_connection()
    cur = conn.cursor()
    acts: List[Dict[str, Any]] = []
    try:
        for p in ACTIVITY_PROVIDERS:
            table = _activity_table(p)
            cur.execute(
                f"SELECT activity_id, metadata, source FROM {table} "
                f"WHERE location_id=%s AND enriched=FALSE;",
                (loc_id,),
            )
            for r in cur.fetchall():
                md = r["metadata"] if isinstance(r["metadata"], dict) else json.loads(r["metadata"] or "{}")
                acts.append({
                    "_table":      table,
                    "activity_id": r["activity_id"],
                    "source":      r["source"] or p,
                    "metadata":    md,
                })
    finally:
        cur.close()
        conn.close()
    return acts


def _persist(acts: List[Dict[str, Any]]) -> int:
    """Cập nhật metadata + re-embed vec_text/vec_tag + enriched=True."""
    if not acts:
        return 0
    n1_inputs = []
    for a in acts:
        md = a["metadata"]
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
        n1_inputs.append({"text": text, "tags": tags, "img_desc": ""})

    n1_results = embed_batch(n1_inputs)
    conn = _get_connection()
    cur = conn.cursor()
    n_updated = 0
    try:
        for a, r in zip(acts, n1_results):
            v = r.get("vectors") or {}
            vec_text = v.get("text")
            vec_tag = v.get("aug_tags")
            cur.execute(
                f"UPDATE {a['_table']} SET metadata=%s, vec_text=%s, vec_tag=%s, "
                f"embedded_at=CURRENT_TIMESTAMP, enriched=TRUE WHERE activity_id=%s;",
                (
                    json.dumps(a["metadata"], ensure_ascii=False),
                    vec_text,
                    vec_tag,
                    a["activity_id"],
                ),
            )
            n_updated += 1
    finally:
        cur.close()
        conn.close()
    return n_updated


def _locs_with_unenriched() -> List[str]:
    conn = _get_connection()
    cur = conn.cursor()
    locs: set = set()
    try:
        for p in ACTIVITY_PROVIDERS:
            table = _activity_table(p)
            cur.execute(f"SELECT DISTINCT location_id FROM {table} WHERE enriched=FALSE;")
            for r in cur.fetchall():
                locs.add(r["location_id"])
    finally:
        cur.close()
        conn.close()
    return sorted(locs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-locs", type=int, default=None, help="Limit number of locs")
    parser.add_argument("--loc", type=str, default=None, help="Single location_id")
    args = parser.parse_args()

    if args.loc:
        target_locs = [args.loc]
    else:
        target_locs = _locs_with_unenriched()
        if args.max_locs:
            target_locs = target_locs[:args.max_locs]

    print("=" * 70)
    print(f"REENRICH — {len(target_locs)} loc(s) with unenriched activities")
    print("=" * 70)

    t_total = time.time()
    n_locs_done = 0
    n_acts_enriched = 0
    for i, loc_id in enumerate(target_locs, 1):
        loc_name = LOC_NAME_BY_ID.get(loc_id, loc_id)
        t0 = time.time()
        acts = _collect_unenriched(loc_id)
        if not acts:
            print(f"\n[{i:03d}/{len(target_locs)}] loc={loc_id} {loc_name} — no unenriched, skip")
            continue
        print(f"\n[{i:03d}/{len(target_locs)}] loc={loc_id} {loc_name} ({len(acts)} acts)")

        # Run LLM enrich — modifies metadata in-place
        try:
            n = _enrich_descriptions(acts, loc_name)
            print(f"  enrich: {n}/{len(acts)} via LLM ({time.time() - t0:.1f}s)")
        except Exception as e:
            print(f"  [ERR] enrich failed: {type(e).__name__}: {e}")
            continue

        if n == 0:
            print("  no enrichment produced (LLM returned empty) — skipping persist")
            continue

        try:
            n_upd = _persist(acts)
            n_acts_enriched += n_upd
            n_locs_done += 1
            print(f"  persisted: {n_upd} rows updated ({time.time() - t0:.1f}s total)")
        except Exception as e:
            print(f"  [ERR] persist failed: {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    print(f"DONE in {time.time() - t_total:.1f}s")
    print(f"  locs processed:    {n_locs_done}/{len(target_locs)}")
    print(f"  acts enriched:     {n_acts_enriched}")


if __name__ == "__main__":
    main()
