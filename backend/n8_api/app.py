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
from config.settings import (
    ALLOWED_ORIGINS, API_HOST as HOST, API_PORT as PORT, API_DEBUG as DEBUG,
    setup_logging
)

logger = setup_logging("N8")

# ── 5. Routes (Imported after config to avoid issues) ─────────
from .routes import bp as n8_bp

app = Flask(__name__)
CORS(app, origins=ALLOWED_ORIGINS)

# Register routes
app.register_blueprint(n8_bp)

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)