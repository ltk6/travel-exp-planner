# Add Locations (System Ingestion)

This folder contains the ingestion helper for adding new locations into the N3 seed pipeline and the live database.

## What the importer does

`importer.py` performs these steps for each new `*.json` file in this folder:

1. Validates the JSON structure.
2. Rejects duplicate `location_id` values that already exist in:
   - `seed_data.py`
   - `locations_with_vectors.json`
3. Generates embeddings through N1.
4. Appends the raw location into `seed_data.py`.
5. Appends the embedded location into `locations_with_vectors.json`.
6. Copies the paired source image into `backend/n3_database/seeds/raw_imgs/`.
7. Resizes/crops that image into `backend/n3_database/seeds/images/`.
8. Saves the final payload into the N3 PostgreSQL database using the resized JPEG bytes from `seeds/images/`.
9. Asks for explicit confirmation before deleting the source JSON/image files.

## Important behavior

- `locations_with_vectors.json` stores vectors, metadata, and geo only.
- Binary image bytes are saved to PostgreSQL from the resized JPEG in `seeds/images/`.
- Raw source images are preserved in `seeds/raw_imgs/`.
- Resized seed images are preserved in `seeds/images/`.
- File updates are restored automatically if the database save fails.
- This tool is for adding new locations. It does not update existing `location_id` entries.

## How to use

1. Copy `new_location.json` and rename it, for example:
   - `phu_quy.json`
2. Fill in the location data.
3. Place a matching image next to it:
   - `phu_quy.png`
   - `phu_quy.jpg`
   - `phu_quy.jpeg`
   - `phu_quy.webp`
4. Run:

```bash
python backend/n3_database/seeds/add_more_locs/importer.py
```

## Templates

- `new_location.json`: editable working template
- `example.json`: reference example, ignored by the importer

## Notes

- The importer modifies core seed artifacts: `seed_data.py`, `locations_with_vectors.json`, and `seeds/images/`.
- The importer also maintains `seeds/raw_imgs/` so the raw and resized image stores stay in sync.
- If the import succeeds, the script will ask whether you want to delete the source JSON/image files from `add_more_locs/`.
