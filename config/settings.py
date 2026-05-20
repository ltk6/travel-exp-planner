import os
import sys
import logging
from dotenv import load_dotenv

# ── Project Paths & Environment ────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

load_dotenv(os.path.join(PROJECT_ROOT, ".env"), encoding="utf-8-sig", override=True)

# ── API Keys ──────────────────────────────────────────────────────
GROQ_API_KEY     = os.getenv("GROQ_API_KEY")
XAI_API_KEY      = os.getenv("XAI_API_KEY")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

# ── Model Settings ───────────────────────────────────────────────
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
ALT_EMBEDDING_MODEL_NAME = os.getenv("ALT_EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-small")


GROQ_MODEL_NAME   = os.getenv("GROQ_MODEL_NAME", "llama-3.1-8b-instant")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_API_URL      = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")

# ── Gemini Specific ───────────────────────────────────────────────
GEMINI_MODEL_NAME=os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
GEMINI_API_BASE=os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta/models")

GROQ_MODELS = {
    "gpt_120b":      os.getenv("GROQ_GPT_120B", "openai/gpt-oss-120b"),
    "groq_70b":      os.getenv("GROQ_70B_MODEL", "llama-3.3-70b-versatile"),
    "qwen_32b":      os.getenv("GROQ_QWEN_32B", "qwen/qwen3-32b"),
    "groq_8b":       os.getenv("GROQ_8B_MODEL", "llama-3.1-8b-instant"),
    "gpt_20b":       os.getenv("GROQ_GPT_20B", "openai/gpt-oss-20b"),
    "gpt_safeguard": os.getenv("GROQ_GPT_SAFEGUARD", "openai/gpt-oss-safeguard-20b"),
    "groq_scout":    os.getenv("GROQ_SCOUT_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"),
}

# ── LLM Provider Routing (N5) ─────────────────────────────────────
# LLM Chain: Quality Ranking (70b > 32b > 8b > Scout)
LLM_CHAIN = os.getenv("LLM_CHAIN", "groq_70b,qwen_32b,groq_8b,groq_scout")

# ── Activity Generation Limits (N5) ───────────────────────────────
LLM_ACTIVITIES_PER_CALL = int(os.getenv("LLM_ACTIVITIES_PER_CALL", "10"))
LLM_N5_TARGET_COUNT     = int(os.getenv("LLM_N5_TARGET_COUNT", "10"))
LLM_MAX_RETRIES         = int(os.getenv("LLM_MAX_RETRIES", "2"))
LLM_RETRY_WAIT_BASE     = float(os.getenv("LLM_RETRY_WAIT_BASE", "5.0"))

# ── Recommendation Limits (N4/N6) ─────────────────────────────────
TOP_K_LOCATIONS  = int(os.getenv("TOP_K_LOCATIONS", "5"))
TOP_K_ACTIVITIES = int(os.getenv("TOP_K_ACTIVITIES", "5"))

# ── Database ──────────────────────────────────────────────────────
PG_URI = os.getenv("PG_URI")

# ── API Server (N8) ───────────────────────────────────────────────
API_HOST         = os.getenv("API_HOST", "0.0.0.0")
API_PORT         = int(os.getenv("API_PORT", "5000"))
API_DEBUG        = os.getenv("API_DEBUG", "False").lower() == "true"
PROTECTED_ROUTES = {"/recommend", "/activities", "/locations"}
ALLOWED_ORIGINS  = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501,http://localhost:8502,http://127.0.0.1:8501,http://127.0.0.1:8502").split(",")
USER_AGENT       = os.getenv("USER_AGENT", "travel-exp-planner/1.0")

# ── Logging Configuration ──────────────────────────────────────────
LOG_FORMAT  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATEFMT = "%H:%M:%S"
LOG_LEVEL   = logging.INFO

def setup_logging(name: str):
    """Utility to initialize logging with the project standard."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        datefmt=LOG_DATEFMT,
    )
    return logging.getLogger(name)
