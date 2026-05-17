from __future__ import annotations

import json
from typing import Any
from pathlib import Path
import sys

# ─────────────────────────────────────────────
# SAFE IMPORT PATH
# ─────────────────────────────────────────────
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.modules.n2_image_processing import process_image


# ─────────────────────────────────────────────
# OUTPUT DIRECTORY
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR
OUTPUT_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────
# JSON SAVE
# ─────────────────────────────────────────────
def save_json(result: dict, filename: str):
    def sanitize(obj: Any):
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(v) for v in obj]
        return obj

    output_path = OUTPUT_DIR / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sanitize(result), f, ensure_ascii=False, indent=2)

    print(f"[saved] {output_path}")


# ─────────────────────────────────────────────
# TEST DATA
# ─────────────────────────────────────────────
TEST_SET = [
    {"path": Path(__file__).parent / "beach.png", "name": "beach"},
    {"path": Path(__file__).parent / "city.png", "name": "city"},
    {"path": Path(__file__).parent / "lake.png", "name": "lake"},
]

# ─────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────
def run_tests():
    for t in TEST_SET:
        if not t["path"].exists():
            print(f"[skip] {t['path']} not found")
            continue

        image_bytes = t["path"].read_bytes()
        result = process_image({"image": image_bytes})
        
        desc = result.get("img_desc", "")
        error = result.get("error", "")
        
        meta = result.get("metadata", {})
        usage = meta.get("usage", {})
        print(f"  [{t['name']}] — model: {meta.get('model')}  tokens: {usage.get('total_tokens', 'N/A')}")
        
        save_json(result, f"image_{t['name']}.json")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("Running N2 IMAGE tests...")
    run_tests()