import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
TRUE_VALUES = {"1", "true", "yes", "on"}

if load_dotenv is not None:
    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(BASE_DIR / ".env")

PORT = os.getenv("PORT", "8001")
HOST = "0.0.0.0"
ALWAYS_PASS = os.getenv("SMARTFACE_ALWAYS_PASS", "1").strip().lower() in TRUE_VALUES
