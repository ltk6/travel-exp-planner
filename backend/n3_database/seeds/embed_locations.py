"""
embed_locations.py
==================
Embeds all locations using N1 (real BGE-M3 if available).

Outputs:
  - locations_with_vectors.json
"""

from __future__ import annotations
import sys, json, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.n3_database.seeds.seed_data import LOCATIONS
from backend.modules.n1_embedding import embed, embed_batch

print("[N1] Using REAL BGE-M3 embeddings")


# ─────────────────────────────────────────────────────────────
# WRITE OUTPUTS
# ─────────────────────────────────────────────────────────────

def _write_json(locations: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(locations, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def run() -> list[dict]:
    print("\n" + "="*60)
    print(f"Embedding {len(LOCATIONS)} locations")
    print("Mode: N1 REAL (returns 4-vector dict) BATCHED")
    print("="*60 + "\n")

    t0 = time.time()
    
    # 1. Prepare batch
    inputs = []
    for loc in LOCATIONS:
        meta = loc["metadata"]
        inputs.append({
            "text": meta["description"],
            "tags": meta["tags"],
        })
        
    # 2. Execute batch
    print(f"Running batch embed for {len(inputs)} items...")
    results = embed_batch(inputs)
    
    ms = (time.time() - t0) * 1000
    print(f"Batch embed completed in {ms:.0f}ms")

    # 3. Reconstruct
    embedded = []
    for i, (loc, res) in enumerate(zip(LOCATIONS, results), 1):
        name = loc["metadata"]["name"]
        vec = res["vectors"]
        
        print(f"[{i:02d}] {name:<35} dim={len(vec['text'])}")

        embedded.append({
            "location_id": loc["location_id"],
            "vectors": vec,
            "metadata": loc["metadata"],
            "geo": loc["geo"],
        })

    json_path = PROJECT_ROOT / "backend/n3_database/seeds/locations_with_vectors.json"
    _write_json(embedded, json_path)

    print("\nSaved:")
    print(f" - {json_path}")
    print(f"\nVector sample dims (text): {len(embedded[0]['vectors']['text'])}")
    print("=" * 60 + "\n")

    return embedded


if __name__ == "__main__":
    run()