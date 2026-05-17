"""
restore_missing_locations.py
============================
Restore các loc còn thiếu trong table `locations` từ locations_with_vectors.json.
KHÔNG drop table — chỉ UPSERT row thiếu (giữ nguyên rows đang có + activity tables).

Usage:
    python -m backend.n3_database.seeds.restore_missing_locations
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.n3_database.db_manager import save_location, _get_connection

CURRENT_DIR = Path(__file__).resolve().parent
JSON_PATH = CURRENT_DIR / "locations_with_vectors.json"
IMAGE_DIR = CURRENT_DIR / "images"


def main():
    if not JSON_PATH.exists():
        print(f"[ERROR] {JSON_PATH} not found")
        sys.exit(1)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        all_locs = json.load(f)
    print(f"Loaded {len(all_locs)} locs from JSON")

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT location_id FROM locations;")
    existing = {r["location_id"] for r in cur.fetchall()}
    conn.close()
    print(f"Existing in DB: {sorted(existing)}")

    missing = [l for l in all_locs if l["location_id"] not in existing]
    print(f"Missing: {len(missing)} locs to restore")

    if not missing:
        print("Nothing to restore — all 25 already present.")
        return

    for i, loc in enumerate(missing, 1):
        loc_id = loc["location_id"]
        # Load images from disk
        images_binary = []
        for img_idx in range(1, 4):
            img_path = IMAGE_DIR / f"{loc_id}_{img_idx}.jpg"
            if img_path.exists():
                with open(img_path, "rb") as f_img:
                    images_binary.append(f_img.read())
        loc["images_binary"] = images_binary

        res = save_location(loc)
        status = res.get("status")
        name = loc["metadata"]["name"]
        if status == "success":
            print(f"  [{i:02d}/{len(missing)}] OK   {loc_id:10s} \"{name}\" ({len(images_binary)} imgs)")
        else:
            print(f"  [{i:02d}/{len(missing)}] FAIL {loc_id:10s} {res.get('message','?')}")

    # Verify
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM locations;")
    final = cur.fetchone()["n"]
    conn.close()
    print(f"\nFinal locations count: {final}")


if __name__ == "__main__":
    main()
