import os
from dotenv import load_dotenv

load_dotenv(encoding="utf-8-sig")

XAI_API_KEY = os.getenv("XAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

PG_URI = os.getenv("PG_URI")