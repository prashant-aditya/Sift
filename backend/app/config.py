from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    groq_api_key: str = ""

    llm_model: str = "llama-3.1-70b-versatile"
    embedding_model: str = "all-MiniLM-L6-v2"

    chroma_persist_dir: str = "./chroma_data"

    max_sources_per_query: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 64

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
