from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    groq_api_key: str = ""
    google_api_key: str = ""
    nvidia_api_key: str = ""
    hf_api_token: str = ""

    # LLM provider selection: "google" (Gemini) or "nvidia" (OpenAI-compatible endpoint).
    llm_provider: str = "google"

    # Default to a Gemini model when using GOOGLE_API_KEY.
    llm_model: str = "gemini-2.5-flash"

    # NVIDIA hosted endpoint base URL (OpenAI-compatible).
    nvidia_base_url: str = "https://integrate.api.nvidia.com"
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
