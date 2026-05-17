from __future__ import annotations
import os
import sys
import logging
from flask import Flask
from flask_cors import CORS

# ── Path Setup (CRITICAL for locating modules) ────────────────
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
from config import (
    ALLOWED_ORIGINS, API_HOST as HOST, API_PORT as PORT, API_DEBUG as DEBUG,
    setup_logging
)

logger = setup_logging("N8")

# ── 5. Routes (Imported after config to avoid issues) ─────────
from .routes import bp as n8_bp
from .profile_routes import profile_bp # IMPORT

app = Flask(__name__)
CORS(app, origins=ALLOWED_ORIGINS)

# Register routes
app.register_blueprint(n8_bp)
app.register_blueprint(profile_bp)

if __name__ == "__main__":
    from backend.n3_database import init_profile_db
    try:
        init_profile_db()
    except Exception as e:
        logger.error(f"Khong the khoi tao bang: {e}")

    app.run(host=HOST, port=PORT, debug=DEBUG)