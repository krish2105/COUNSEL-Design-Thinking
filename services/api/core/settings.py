"""Runtime configuration. Every default is free."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    counsel_db: str = "./data/counsel.db"

    ollama_host: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3:8b"
    ollama_embed_model: str = "bge-m3:567m"

    gemini_api_key: str = ""
    groq_api_key: str = ""
    # Read, and never used. See services/api/core/llm.py::AnthropicProvider.
    anthropic_api_key: str = ""

    # Counted as requests, not tokens. See core/quota.py for why.
    quota_gemini_requests: int = 200
    quota_groq_requests: int = 200
    quota_session_requests: int = 120
    quota_ollama_requests: int = 10_000

    searxng_url: str = "http://localhost:8888"

    cors_origins: str = "http://localhost:3000"


@lru_cache
def settings() -> Settings:
    return Settings()
