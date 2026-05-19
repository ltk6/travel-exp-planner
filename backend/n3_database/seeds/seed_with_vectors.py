"""
seed_with_vectors.py
────────────────────
Seeds the database using pre-computed vectors and BINARY images.
"""

import sys
import json
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.n3_database.db_manager import init_db, save_location, init_profile_db, init_activities_db

def seed_database(reset_locations: bool = True, reset_activities: bool = False, reset_profiles: bool = False):
    json_path = CURRENT_DIR / "locations_with_vectors.json"
    image_dir = CURRENT_DIR / "images"
    
    if not json_path.exists():
        print(f"❌ Error: {json_path} not found.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        locations = json.load(f)

    # 1. Khởi tạo / reset các sub-schema
    init_db(drop_existing=reset_locations)
    init_profile_db(drop_existing=reset_profiles)
    init_activities_db(drop_existing=reset_activities)
    
    print(f"🚀 Seeding {len(locations)} locations with images into Postgres...")
    
    for i, loc in enumerate(locations, 1):
        loc_id = loc["location_id"]
        
        # Load binary images from seeds/images/
        images_binary = []
        for img_idx in range(1, 4):
            img_path = image_dir / f"{loc_id}_{img_idx}.jpg"
            if img_path.exists():
                with open(img_path, "rb") as f_img:
                    images_binary.append(f_img.read())
        
        # Pass binary to N3
        loc["images_binary"] = images_binary
        
        res = save_location(loc)
        if res.get("status") == "success":
            print(f"  [{i:02d}] Seeded: {loc['metadata']['name']} ({len(images_binary)} images)")
        else:
            print(f"  [{i:02d}] ❌ Failed: {loc_id} - {res.get('message')}")
            
    print("\n✨ Database seeding complete with Binary Image Persistence.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed the database with locations, vectors, and initialize schemas.")
    parser.add_argument("--reset-activities", action="store_true", help="Drop and recreate all activity tables")
    parser.add_argument("--reset-profiles", action="store_true", help="Drop and recreate user and rec_history tables (DANGEROUS)")
    parser.add_argument("--reset-all", action="store_true", help="Drop and recreate EVERYTHING (locations, activities, profiles)")
    args = parser.parse_args()
    
    r_act = args.reset_activities or args.reset_all
    r_prof = args.reset_profiles or args.reset_all
    
    seed_database(reset_locations=True, reset_activities=r_act, reset_profiles=r_prof)
