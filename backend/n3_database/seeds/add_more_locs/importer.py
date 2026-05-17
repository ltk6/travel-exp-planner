from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from pprint import pformat
from textwrap import indent

# Setup path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.n3_database.db_manager import save_location
from backend.modules.n1_embedding import embed_batch
from backend.n3_database.seeds.image_resizer import resize_and_crop

SEED_PATH = PROJECT_ROOT / "backend/n3_database/seeds/seed_data.py"
VECTORS_JSON_PATH = PROJECT_ROOT / "backend/n3_database/seeds/locations_with_vectors.json"
RAW_IMAGE_DIR = PROJECT_ROOT / "backend/n3_database/seeds/raw_imgs"
SEED_IMAGE_DIR = PROJECT_ROOT / "backend/n3_database/seeds/images"
SKIP_FILES = {"example.json", "new_location.json"}
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]


class FileTransaction:
    def __init__(self) -> None:
        self._backups: dict[Path, bytes | None] = {}

    def backup(self, path: Path) -> None:
        if path in self._backups:
            return
        self._backups[path] = path.read_bytes() if path.exists() else None

    def write_text(self, path: Path, content: str) -> None:
        self.backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)

    def write_bytes(self, path: Path, content: bytes) -> None:
        self.backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_bytes(content)
        tmp_path.replace(path)

    def delete(self, path: Path) -> None:
        self.backup(path)
        if path.exists():
            path.unlink()

    def restore(self) -> None:
        for path, content in reversed(list(self._backups.items())):
            if content is None:
                if path.exists():
                    path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


def _load_seed_content() -> str:
    if not SEED_PATH.exists():
        raise FileNotFoundError(f"seed_data.py not found at {SEED_PATH}")
    return SEED_PATH.read_text(encoding="utf-8")


def _load_seed_locations() -> list[dict]:
    namespace: dict[str, object] = {}
    content = _load_seed_content()
    exec(compile(content, str(SEED_PATH), "exec"), namespace)
    locations = namespace.get("LOCATIONS")
    if not isinstance(locations, list):
        raise ValueError("LOCATIONS was not found or is not a list in seed_data.py")
    return locations


def _load_vectors_data() -> list[dict]:
    if not VECTORS_JSON_PATH.exists():
        return []
    with open(VECTORS_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("locations_with_vectors.json must contain a list")
    return data


def _validate_raw_location(raw_data: dict, source_path: Path) -> None:
    location_id = raw_data.get("location_id")
    metadata = raw_data.get("metadata")
    geo = raw_data.get("geo")

    if not isinstance(location_id, str) or not location_id.strip():
        raise ValueError(f"{source_path.name}: missing valid 'location_id'")
    if not isinstance(metadata, dict):
        raise ValueError(f"{source_path.name}: missing 'metadata' object")
    if not isinstance(metadata.get("name"), str) or not metadata["name"].strip():
        raise ValueError(f"{source_path.name}: missing valid metadata.name")
    if not isinstance(metadata.get("description"), str) or not metadata["description"].strip():
        raise ValueError(f"{source_path.name}: missing valid metadata.description")
    if not isinstance(metadata.get("tags"), list) or not all(isinstance(tag, str) for tag in metadata["tags"]):
        raise ValueError(f"{source_path.name}: metadata.tags must be a list[str]")
    if geo is not None and not isinstance(geo, dict):
        raise ValueError(f"{source_path.name}: geo must be an object when present")


def _ensure_location_is_new(location_id: str) -> None:
    seed_locations = _load_seed_locations()
    if any(loc.get("location_id") == location_id for loc in seed_locations):
        raise ValueError(
            f"location_id '{location_id}' already exists in seed_data.py. "
            "This importer only supports adding new locations."
        )

    vector_locations = _load_vectors_data()
    if any(loc.get("location_id") == location_id for loc in vector_locations):
        raise ValueError(
            f"location_id '{location_id}' already exists in locations_with_vectors.json. "
            "This importer only supports adding new locations."
        )


def _append_to_seed_data_py(new_loc: dict, txn: FileTransaction) -> None:
    content = _load_seed_content()
    existing_locations = _load_seed_locations()
    last_bracket_idx = content.rfind("]")
    if last_bracket_idx == -1:
        raise ValueError("Could not find closing LOCATIONS bracket in seed_data.py")

    formatted_loc = indent(pformat(new_loc, width=100, sort_dicts=False), "    ")
    prefix = ",\n\n" if existing_locations else "\n"
    new_entry = prefix + formatted_loc
    new_content = content[:last_bracket_idx].rstrip() + new_entry + "\n]"
    txn.write_text(SEED_PATH, new_content)


def _build_vectors_json_payload(embedded_loc: dict) -> dict:
    return {
        "location_id": embedded_loc["location_id"],
        "vectors": embedded_loc["vectors"],
        "metadata": embedded_loc["metadata"],
        "geo": embedded_loc.get("geo", {}),
    }


def _update_locations_with_vectors_json(embedded_loc: dict, txn: FileTransaction) -> None:
    data = _load_vectors_data()
    payload = _build_vectors_json_payload(embedded_loc)
    data.append(payload)
    txn.write_text(VECTORS_JSON_PATH, json.dumps(data, indent=2, ensure_ascii=False))


def _find_source_image(json_path: Path) -> Path | None:
    for ext in IMAGE_EXTENSIONS:
        candidate = json_path.with_suffix(ext)
        if candidate.exists():
            return candidate
    return None


def _sync_image_assets(location_id: str, img_path: Path | None, txn: FileTransaction) -> list[bytes]:
    existing_raw = sorted(RAW_IMAGE_DIR.glob(f"{location_id}_*"))
    for old_file in existing_raw:
        txn.delete(old_file)

    existing_resized = sorted(SEED_IMAGE_DIR.glob(f"{location_id}_*.jpg"))
    for old_file in existing_resized:
        txn.delete(old_file)

    if img_path is None:
        return []

    raw_target = RAW_IMAGE_DIR / f"{location_id}_1{img_path.suffix.lower()}"
    txn.write_bytes(raw_target, img_path.read_bytes())

    resized_target = SEED_IMAGE_DIR / f"{location_id}_1.jpg"
    txn.backup(resized_target)
    resized_target.parent.mkdir(parents=True, exist_ok=True)
    ok = resize_and_crop(str(raw_target), str(resized_target))
    if not ok or not resized_target.exists():
        raise RuntimeError(f"Failed to create resized image for {location_id}")

    return [resized_target.read_bytes()]


def _confirm_source_cleanup(source_json: Path, source_img: Path | None) -> bool:
    cleanup_targets = [source_json.name]
    if source_img is not None:
        cleanup_targets.append(source_img.name)

    joined = ", ".join(cleanup_targets)
    try:
        answer = input(f"Delete source files after successful import ({joined})? [y/N]: ").strip().lower()
    except EOFError:
        print("  No interactive input available. Keeping source files.")
        return False
    return answer in {"y", "yes"}


def _cleanup_source_files(source_json: Path, source_img: Path | None) -> None:
    source_json.unlink(missing_ok=True)
    if source_img is not None:
        source_img.unlink(missing_ok=True)


def _embed_location(raw_data: dict) -> dict:
    metadata = raw_data.get("metadata", {})
    input_data = {
        "text": metadata.get("description", ""),
        "tags": metadata.get("tags", []),
    }

    print("  Generating embeddings via N1...")
    results = embed_batch([input_data])
    vectors = results[0]["vectors"]

    return {
        "location_id": raw_data["location_id"],
        "vectors": vectors,
        "metadata": metadata,
        "geo": raw_data.get("geo", {}),
    }


def run_import() -> None:
    current_dir = Path(__file__).resolve().parent
    json_files = sorted(current_dir.glob("*.json"))

    for json_file in json_files:
        if json_file.name in SKIP_FILES:
            continue

        print(f"\nProcessing: {json_file.name}")
        txn = FileTransaction()

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            _validate_raw_location(raw_data, json_file)
            _ensure_location_is_new(raw_data["location_id"])

            embedded_loc = _embed_location(raw_data)

            img_path = _find_source_image(json_file)
            if img_path is not None:
                print(f"  Found source image: {img_path.name}")

            _append_to_seed_data_py(raw_data, txn)
            _update_locations_with_vectors_json(embedded_loc, txn)
            resized_images_binary = _sync_image_assets(raw_data["location_id"], img_path, txn)
            if resized_images_binary:
                embedded_loc["images_binary"] = resized_images_binary

            result = save_location(embedded_loc)
            if result.get("status") != "success":
                raise RuntimeError(result.get("message") or "Unknown database error")

            print("  Saved to N3 database")
            print("  Updated seed_data.py")
            print("  Updated locations_with_vectors.json")
            if img_path is not None:
                print(f"  Synced original image into seeds/raw_imgs/{raw_data['location_id']}_1{img_path.suffix.lower()}")
                print(f"  Synced resized image into seeds/images/{raw_data['location_id']}_1.jpg")
                print("  Database save used resized image bytes from seeds/images")

            if _confirm_source_cleanup(json_file, img_path):
                _cleanup_source_files(json_file, img_path)
                print("  Source files deleted")
            else:
                print("  Source files kept")

        except Exception as e:
            txn.restore()
            print(f"  Import failed: {e}")


if __name__ == "__main__":
    run_import()
