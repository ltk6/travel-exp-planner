"""
backfill_vec_tag.py
===================
Backfill vec_tag cho activities cũ có vec_tag IS NULL.

Sử dụng cùng logic chuẩn hoá tag như seed_activities._build_n1_input + N1
preprocessor fallback mới (raw tag khi ontology không match).

Idempotent: skip row đã có vec_tag. Chạy lại an toàn.

Usage:
  python -m backend.n3_database.seeds.backfill_vec_tag
  python -m backend.n3_database.seeds.backfill_vec_tag --provider osm
  python -m backend.n3_database.seeds.backfill_vec_tag --batch 64
"""
from __future__ import annotations

import argparse
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
from backend.modules.n1_embedding import embed_batch


def _normalize_tags(raw_tags: Any) -> List[str]:
    if not isinstance(raw_tags, list):
        return []
    out: List[str] = []
    for t in raw_tags:
        if not isinstance(t, str):
            continue
        cleaned = t.split("=", 1)[-1]
        cleaned = cleaned.replace(".", " ").replace("_", " ").replace("-", " ").strip()
        if cleaned:
            out.append(cleaned)
    return out


def _backfill_provider(provider: str, batch_size: int) -> Dict[str, int]:
    table = _activity_table(provider)
    conn = _get_connection()
    cur = conn.cursor()
    stats = {"scanned": 0, "embedded": 0, "skipped_no_tags": 0}
    try:
        cur.execute(
            f"SELECT activity_id, metadata FROM {table} WHERE vec_tag IS NULL ORDER BY activity_id;"
        )
        rows = list(cur.fetchall())
        if not rows:
            print(f"  [{provider}] no NULL vec_tag rows — skip")
            return stats

        print(f"  [{provider}] {len(rows)} rows to backfill")
        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i + batch_size]
            n1_inputs: List[Dict[str, Any]] = []
            row_ids: List[str] = []
            for r in chunk:
                md = r["metadata"] if isinstance(r["metadata"], dict) else {}
                tags = _normalize_tags(md.get("categories_raw") or md.get("tags"))
                if not tags:
                    stats["skipped_no_tags"] += 1
                    continue
                n1_inputs.append({"text": "", "tags": tags, "img_desc": ""})
                row_ids.append(r["activity_id"])

            stats["scanned"] += len(chunk)
            if not n1_inputs:
                continue

            results = embed_batch(n1_inputs)
            update_cur = conn.cursor()
            for aid, res in zip(row_ids, results):
                vec = (res.get("vectors") or {}).get("aug_tags")
                if vec is None:
                    continue
                update_cur.execute(
                    f"UPDATE {table} SET vec_tag = %s, embedded_at = CURRENT_TIMESTAMP WHERE activity_id = %s;",
                    (vec, aid),
                )
                stats["embedded"] += 1
            update_cur.close()
            print(f"    {min(i + batch_size, len(rows)):4d}/{len(rows)} processed (embedded so far: {stats['embedded']})")
    finally:
        cur.close()
        conn.close()
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=str, default=None, help="Single provider only")
    parser.add_argument("--batch", type=int, default=64, help="Batch size")
    args = parser.parse_args()

    providers = [args.provider] if args.provider else list(ACTIVITY_PROVIDERS)
    print("=" * 70)
    print(f"BACKFILL vec_tag — providers={providers} batch={args.batch}")
    print("=" * 70)

    t0 = time.time()
    total = {"scanned": 0, "embedded": 0, "skipped_no_tags": 0}
    for p in providers:
        if p not in ACTIVITY_PROVIDERS:
            print(f"[WARN] unknown provider {p!r} — skip")
            continue
        s = _backfill_provider(p, args.batch)
        for k, v in s.items():
            total[k] += v

    print("\n" + "=" * 70)
    print(f"DONE in {time.time() - t0:.1f}s")
    print(f"  scanned:         {total['scanned']}")
    print(f"  embedded:        {total['embedded']}")
    print(f"  skipped_no_tags: {total['skipped_no_tags']}")


if __name__ == "__main__":
    main()
