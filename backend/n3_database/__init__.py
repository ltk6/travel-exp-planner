"""N3: PostgreSQL-backed location persistence API."""

from __future__ import annotations

from .db_manager import (
    attach_image_to_location,
    get_all_locations,
    get_db_fingerprint,
    init_db,
    save_location,
    init_profile_db,       # Thêm dòng này
    save_user_profile,     # Thêm dòng này
    get_user_profile,       # Thêm dòng này
)

__all__ = [
    "attach_image_to_location",
    "get_all_locations",
    "get_db_fingerprint",
    "init_db",
    "save_location",
    "init_profile_db",     # Thêm dòng này
    "save_user_profile",   # Thêm dòng này
    "get_user_profile",    # Thêm dòng này
]
