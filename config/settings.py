import os
import sys
from dotenv import load_dotenv

# ── Project Paths ──────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Tự động thêm project root vào sys.path khi settings được import (hỗ trợ test files)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(encoding="utf-8-sig")

# ── API keys ──────────────────────────────────────────────────────
XAI_API_KEY    = os.getenv("XAI_API_KEY")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")
PROTECTED_ROUTES = {"/recommend", "/activities"}

# ── LLM provider routing (N5) ─────────────────────────────────────
# Primary provider: "gemini" (nhanh) hoặc "groq".
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
# Fallback chain, ngăn cách dấu phẩy. Rỗng = tự suy ra trong registry.
LLM_FALLBACK = os.getenv("LLM_FALLBACK", "groq")

# ── Model Settings ───────────────────────────────────────────────
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")

GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
GEMINI_API_BASE   = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta/models")

GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_API_URL    = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")

GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
XAI_VISION_MODEL = os.getenv("XAI_VISION_MODEL", "grok-vision-beta")
XAI_API_URL      = os.getenv("XAI_API_URL", "https://api.x.ai/v1/chat/completions")

USER_AGENT = os.getenv("USER_AGENT", "travel-exp-planner/1.0")

# ── Activity Generation (N5) ──────────────────────────────────────
LLM_ACTIVITIES_PER_CALL = int(os.getenv("LLM_ACTIVITIES_PER_CALL", "10"))
LLM_N5_TARGET_COUNT     = int(os.getenv("LLM_N5_TARGET_COUNT", "10"))
ENABLE_LLM_CACHE        = os.getenv("ENABLE_LLM_CACHE", "False").lower() == "true"

LLM_MAX_RETRIES         = int(os.getenv("LLM_MAX_RETRIES", "2"))
LLM_RETRY_WAIT_BASE     = float(os.getenv("LLM_RETRY_WAIT_BASE", "2.0"))

# ── Recommendation Limits (N4/N6) ─────────────────────────────────
TOP_K_LOCATIONS  = int(os.getenv("TOP_K_LOCATIONS", "5"))
TOP_K_ACTIVITIES = int(os.getenv("TOP_K_ACTIVITIES", "5"))

# ── Database ──────────────────────────────────────────────────────
PG_URI = os.getenv("PG_URI")

# ── API Server (N8) ───────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "5000"))
API_DEBUG = os.getenv("API_DEBUG", "False").lower() == "true"

import logging

# ── Logging Configuration ──────────────────────────────────────────
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATEFMT = "%H:%M:%S"
LOG_LEVEL = logging.INFO

def setup_logging(name: str):
    """Utility to initialize logging with the project standard."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        datefmt=LOG_DATEFMT,
    )
    return logging.getLogger(name)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501,http://localhost:8502,http://127.0.0.1:8501,http://127.0.0.1:8502").split(",")
