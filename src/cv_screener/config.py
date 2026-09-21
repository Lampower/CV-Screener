"""Central config: env loading + paths, so every module reads it the same way."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PROFILES_DIR = DATA_DIR / "profiles"
RESUMES_DIR = DATA_DIR / "resumes"
PHOTOS_DIR = DATA_DIR / "photos"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://cvscreener:cvscreener@localhost:5432/cvscreener",
)

CHAT_MODEL = "gpt-4o-mini"
IMAGE_MODEL = "gpt-image-1"
EMBEDDING_MODEL = "text-embedding-3-small"

COLLECTION_NAME = "cv_screener_candidates"


def require_api_key() -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    return OPENAI_API_KEY


def ensure_data_dirs() -> None:
    for d in (PROFILES_DIR, RESUMES_DIR, PHOTOS_DIR):
        d.mkdir(parents=True, exist_ok=True)
