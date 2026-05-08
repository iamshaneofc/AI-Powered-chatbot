"""
config.py — Centralised application settings.

Reads from environment variables (or a .env file via python-dotenv).
All other modules import `settings` from here — never os.getenv() directly.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    APP_NAME: str = "AI Q&A Backend"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"          # development | staging | production
    DEBUG: bool = True

    # ── Server ────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── CORS ──────────────────────────────────────────────────────────────
    # Comma-separated list in .env: CORS_ORIGINS=http://localhost:3000,https://app.example.com
    CORS_ORIGINS: Any = ["http://localhost:3000", "http://localhost:5173"]

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── OpenAI ───────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 1024
    OPENAI_TEMPERATURE: float = 0.2

    # ── Whisper ───────────────────────────────────────────────────────────
    WHISPER_MODEL: str = "base"              # tiny | base | small | medium | large

    # ── FAISS / Vector store ──────────────────────────────────────────────
    FAISS_INDEX_PATH: str = "/tmp/vectorstore/index"
    VECTOR_CHUNK_SIZE: int = 512
    VECTOR_CHUNK_OVERLAP: int = 64
    VECTOR_TOP_K: int = 5

    # ── File upload ───────────────────────────────────────────────────────
    UPLOAD_DIR: Path = Path("/tmp/uploads")
    MAX_UPLOAD_SIZE_MB: int = 50             # enforced in file_utils
    ALLOWED_EXTENSIONS: Any = [
        "pdf", "txt", "docx",               # documents
        "mp3", "mp4", "wav", "m4a", "webm", # audio / video
        "png", "jpg", "jpeg",               # images (future OCR)
    ]

    # ── Validators — allow comma-separated strings from .env ─────────────
    @field_validator("CORS_ORIGINS", "ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def _parse_list(cls, v):
        """Accept both JSON arrays and comma-separated plain strings."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton — instantiated once per process."""
    return Settings()


settings: Settings = get_settings()
