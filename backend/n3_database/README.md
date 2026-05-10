# N3 Database Module

## Overview
This module manages database connections and schema for PostgreSQL + pgvector.

## API Functions

- `init_db()`: Initializes the PostgreSQL database schema and `pgvector` extension.
- `save_user_profile(user_data: dict)`: Stores or updates a user profile with vectors and metadata.
- `save_location(location_data: dict)`: Stores or updates a location with its metadata and vectors.
- `get_all_locations() -> dict`: Retrieves all stored locations with dynamic base64 image packing. Returns a JSON-compatible dict with status, total count, and data array. Falls back to JSON seed file if the DB is offline.

## Data Schema

### Location Data (Input / Output)
```python
{
    "location_id": str,
    "vectors": {
        "text":     list[float] | None,     # BGE-M3 (1024d)
        "aug_text": list[float] | None, 
        "aug_tags": list[float] | None,
        "img_desc": list[float] | None
    },
    "metadata": {
        "name":        str,
        "description": str,
        "tags":        list[str]
    },
    "geo": {
        "lat": float,
        "lng": float
    },
    # Note: When retrieved via get_all_locations(), output also includes:
    "images": list[str]       # List of data:image/jpeg;base64,... strings
}
```

### User Profile Data (Input)
```python
{
    "user_id": str,
    
    # User Vectors
    "text":     list[float] | None,
    "aug_text": list[float] | None,
    "aug_tags": list[float] | None,
    "img_desc": list[float] | None,
    
    # Structured Data
    "metadata": {
        "name": str,
        "age_range": str,
        "preferences": list[str]
    }
}
```
