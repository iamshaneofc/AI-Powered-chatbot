"""
main.py — Centralised application settings.

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

    # ── AI Provider Settings ──────────────────────────────────────────────
    # Provider selection: openai | openrouter | nvidia | groq | cerebras | gemini | mimo | opencode | custom
    AI_PROVIDER: str = "openai"
    
    # OpenAI Settings
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 1024
    OPENAI_TEMPERATURE: float = 0.2
    
    # Provider-specific API keys
    OPENROUTER_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    MIMO_API_KEY: str = ""
    OPENCODE_API_KEY: str = ""
    CUSTOM_API_KEY: str = ""
    
    # Provider-specific base URLs (can be overridden)
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    CEREBRAS_BASE_URL: str = "https://api.cerebras.ai/v1"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    MIMO_BASE_URL: str = "https://api.xiaomimimo.com/v1"
    OPENCODE_BASE_URL: str = ""
    CUSTOM_BASE_URL: str = ""
    
    # Provider-specific model settings
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    NVIDIA_MODEL: str = "meta/llama-3.3-70b-instruct"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    CEREBRAS_MODEL: str = "llama-3.3-70b"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    MIMO_MODEL: str = "mimo-v2.6-flash-free"
    OPENCODE_MODEL: str = ""
    CUSTOM_MODEL: str = ""

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

    def get_active_api_key(self) -> str:
        """Get the API key for the currently selected provider."""
        provider = self.AI_PROVIDER.lower()
        if provider == "openai":
            return self.OPENAI_API_KEY
        elif provider == "openrouter":
            return self.OPENROUTER_API_KEY or (self.OPENAI_API_KEY if self.OPENAI_API_KEY.startswith("sk-or-") else self.OPENAI_API_KEY)
        elif provider == "nvidia":
            return self.NVIDIA_API_KEY
        elif provider == "groq":
            return self.GROQ_API_KEY
        elif provider == "cerebras":
            return self.CEREBRAS_API_KEY
        elif provider == "gemini":
            return self.GEMINI_API_KEY
        elif provider == "mimo":
            return self.MIMO_API_KEY
        elif provider == "opencode":
            return self.OPENCODE_API_KEY
        elif provider == "custom":
            return self.CUSTOM_API_KEY
        return ""

    def get_active_base_url(self) -> str:
        """Get the base URL for the currently selected provider."""
        provider = self.AI_PROVIDER.lower()
        if provider == "openai":
            return "https://api.openai.com/v1"
        elif provider == "openrouter":
            return self.OPENROUTER_BASE_URL
        elif provider == "nvidia":
            return self.NVIDIA_BASE_URL
        elif provider == "groq":
            return self.GROQ_BASE_URL
        elif provider == "cerebras":
            return self.CEREBRAS_BASE_URL
        elif provider == "gemini":
            return self.GEMINI_BASE_URL
        elif provider == "mimo":
            return self.MIMO_BASE_URL
        elif provider == "opencode":
            return self.OPENCODE_BASE_URL
        elif provider == "custom":
            return self.CUSTOM_BASE_URL
        return "https://api.openai.com/v1"

    def get_active_model(self) -> str:
        """Get the model for the currently selected provider."""
        provider = self.AI_PROVIDER.lower()
        if provider == "openai":
            return self.OPENAI_MODEL
        elif provider == "openrouter":
            return self.OPENROUTER_MODEL
        elif provider == "nvidia":
            return self.NVIDIA_MODEL
        elif provider == "groq":
            return self.GROQ_MODEL
        elif provider == "cerebras":
            return self.CEREBRAS_MODEL
        elif provider == "gemini":
            return self.GEMINI_MODEL
        elif provider == "mimo":
            return self.MIMO_MODEL
        elif provider == "opencode":
            return self.OPENCODE_MODEL
        elif provider == "custom":
            return self.CUSTOM_MODEL
        return self.OPENAI_MODEL

    def get_active_embedding_model(self) -> str:
        """Get the embedding model for the currently selected provider."""
        from app.config.providers import get_provider
        try:
            provider = get_provider(self.AI_PROVIDER.lower())
            return provider.embedding_model
        except ValueError:
            return self.OPENAI_EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton — instantiated once per process."""
    return Settings()


settings: Settings = get_settings()
