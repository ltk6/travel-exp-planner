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

from backend.n3_database.db_manager import init_db, save_location

def seed_database():
    json_path = CURRENT_DIR / "locations_with_vectors.json"
    image_dir = CURRENT_DIR / "images"
    
    if not json_path.exists():
        print(f"❌ Error: {json_path} not found.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        locations = json.load(f)

    init_db()
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
    seed_database()
