"""N3: PostgreSQL-backed location persistence API."""

from __future__ import annotations

from .db_manager import (
    attach_image_to_location,
    get_all_locations,
    get_db_fingerprint,
    init_db,
    save_location,
    init_profile_db,
    register_user,
    login_user,
    save_rec_turn,
    get_user_history,
    get_location_image_by_index,
)

__all__ = [
    "attach_image_to_location",
    "get_all_locations",
    "get_db_fingerprint",
    "init_db",
    "save_location",
    "init_profile_db",
    "register_user",
    "login_user",
    "save_rec_turn",
    "get_user_history",
    "get_location_image_by_index",
]