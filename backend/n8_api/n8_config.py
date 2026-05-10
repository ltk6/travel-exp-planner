import os
import sys
import logging
from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

# ── Load .env từ project root ─────────────────────────────────
load_dotenv(os.path.join(_root, ".env"))

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("N8")

# ── App Config ────────────────────────────────────────────────
INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "")
ALLOWED_ORIGINS = [
    "http://localhost:8501", 
    "http://localhost:8502", 
    "http://127.0.0.1:8501", 
    "http://127.0.0.1:8502"
]
PROTECTED_ROUTES = {"/recommend", "/activities"}

HOST = "0.0.0.0"
PORT = 5000
DEBUG = False
