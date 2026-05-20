"""
refetch_overture.py
===================
Re-fetch ONLY overture provider cho các loc có `status=empty` (do CLI thiếu
trong lần seed đầu). Xóa fetch_status overture của những loc đó → seed sẽ
retry overture, các provider khác đã 'success'/'empty' nên KHÔNG bị động tới.

Usage:
  python -m backend.n3_database.seeds.refetch_overture --dry-run
  python -m backend.n3_database.seeds.refetch_overture
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.n3_database.db_manager import _get_connection
from backend.n3_database.seeds.seed_activities import main as seed_main


def _clear_overture_empty(dry_run: bool = False) -> int:
    conn = _get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT location_id FROM activity_fetch_status "
            "WHERE provider='overture' AND status='empty' ORDER BY location_id;"
        )
        locs = [r["location_id"] for r in cur.fetchall()]
        print(f"locs with overture status=empty: {len(locs)}")
        if dry_run:
            print("(dry run — not clearing)")
            return 0
        cur.execute(
            "DELETE FROM activity_fetch_status "
            "WHERE provider='overture' AND status='empty';"
        )
        return len(locs)
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    n_cleared = _clear_overture_empty(args.dry_run)
    if args.dry_run:
        return

    print(f"\nCleared {n_cleared} overture empty rows. Re-running seed_activities...\n")
    # Reuse seed entrypoint — vì DONE_STATUSES = {success, empty}, overture đã
    # bị xóa khỏi fetch_status nên sẽ được retry; các provider khác vẫn skip.
    sys.argv = ["seed_activities"]
    seed_main()


if __name__ == "__main__":
    main()
