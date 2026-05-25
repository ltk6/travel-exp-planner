"""
N3/N5/N8 Configuration Module
Tập trung quản lý tất cả các biến môi trường và cấu hình hệ thống.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ====================== PROJECT SETUP ======================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Load .env file
load_dotenv(
    dotenv_path=os.path.join(PROJECT_ROOT, ".env"),
    encoding="utf-8-sig",
    override=True
)

# ====================== API KEYS ======================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

# ====================== LLM MODELS ======================
# Embedding Models
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")

# Groq Models
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.1-8b-instant")
GROQ_VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
)
GROQ_API_URL = os.getenv(
    "GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions"
)

# Gemini Models
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
GEMINI_API_BASE = os.getenv(
    "GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta/models"
)

# Groq Model Registry
GROQ_MODELS = {
    "gpt_120b": os.getenv("GROQ_GPT_120B", "openai/gpt-oss-120b"),
    "groq_70b": os.getenv("GROQ_70B_MODEL", "llama-3.3-70b-versatile"),
    "qwen_32b": os.getenv("GROQ_QWEN_32B", "qwen/qwen3-32b"),
    "groq_8b": os.getenv("GROQ_8B_MODEL", "llama-3.1-8b-instant"),
    "gpt_20b": os.getenv("GROQ_GPT_20B", "openai/gpt-oss-20b"),
    "gpt_safeguard": os.getenv("GROQ_GPT_SAFEGUARD", "openai/gpt-oss-safeguard-20b"),
    "groq_scout": os.getenv(
        "GROQ_SCOUT_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
    ),
}

# ====================== LLM CHAIN & BEHAVIOR ======================
LLM_CHAIN = os.getenv(
    "LLM_CHAIN", "groq_70b,qwen_32b,groq_8b,groq_scout"
)

# Activity Generation (N5)
LLM_ACTIVITIES_PER_CALL = int(os.getenv("LLM_ACTIVITIES_PER_CALL", "10"))
LLM_N5_TARGET_COUNT = int(os.getenv("LLM_N5_TARGET_COUNT", "10"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
LLM_RETRY_WAIT_BASE = float(os.getenv("LLM_RETRY_WAIT_BASE", "5.0"))

# ====================== RECOMMENDATION SETTINGS ======================
TOP_K_LOCATIONS = int(os.getenv("TOP_K_LOCATIONS", "5"))
TOP_K_ACTIVITIES = int(os.getenv("TOP_K_ACTIVITIES", "5"))

# ====================== DATABASE ======================
PG_URI = os.getenv("PG_URI")

# ====================== API SERVER (N8) ======================
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "5000"))
API_DEBUG = os.getenv("API_DEBUG", "False").lower() in ("true", "1", "yes")

PROTECTED_ROUTES = {"/recommend", "/activities", "/locations"}

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8501,http://localhost:8502,http://127.0.0.1:8501,http://127.0.0.1:8502"
).split(",")

USER_AGENT = os.getenv("USER_AGENT", "travel-exp-planner/1.0")

# ====================== LOGGING ======================
LOG_DATEFMT = "%H:%M:%S"
LOG_LEVEL = logging.INFO


class DynamicFormatter(logging.Formatter):
    DETAILED_FORMAT = "%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d]: %(message)s"
    SIMPLE_FORMAT = "[%(levelname)s] %(name)s: %(message)s"

    def __init__(self, datefmt=None):
        super().__init__(datefmt=datefmt)
        self.detailed_formatter = logging.Formatter(self.DETAILED_FORMAT, datefmt=datefmt)
        self.simple_formatter = logging.Formatter(self.SIMPLE_FORMAT, datefmt=datefmt)

    def format(self, record):
        if record.name.startswith("N8"):
            return self.detailed_formatter.format(record)
        return self.simple_formatter.format(record)


def setup_logging(name: str = __name__) -> logging.Logger:
    """Khởi tạo logging theo chuẩn dự án."""
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        formatter = DynamicFormatter(datefmt=LOG_DATEFMT)
        handler.setFormatter(formatter)
        root.addHandler(handler)
        root.setLevel(LOG_LEVEL)
    return logging.getLogger(name)