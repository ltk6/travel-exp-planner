import os
from dotenv import load_dotenv

load_dotenv(encoding="utf-8-sig")

# ── API keys ──────────────────────────────────────────────────────
XAI_API_KEY    = os.getenv("XAI_API_KEY")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ── LLM provider routing (N5) ─────────────────────────────────────
# Primary provider: "gemini" (nhanh) hoặc "groq".
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
# Fallback chain, ngăn cách dấu phẩy. Rỗng = tự suy ra trong registry.
LLM_FALLBACK = os.getenv("LLM_FALLBACK", "")

# ── Database ──────────────────────────────────────────────────────
PG_URI = os.getenv("PG_URI")
