from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    name: str = "ReelPilot API"
    env: str = "development"
    database_url: str = "sqlite:///./reelpilot.db"
    redis_url: str = "redis://localhost:6379/0"
    web_origin: str = "http://localhost:3000"
    auth_secret: str = "local-development-secret-change-me"
    access_token_minutes: int = 60 * 24 * 7
    max_comments_per_month: int = 1_000
    max_analyses_per_month: int = 100
    max_generations_per_month: int = 50
    embedding_provider: str = "auto"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 256
    generation_provider: str = "auto"
    generation_model: str = "gpt-5.6-terra"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    instagram_app_id: str = ""
    instagram_app_secret: str = ""
    instagram_redirect_uri: str = "http://localhost:8000/v1/instagram/callback"
    instagram_api_version: str = "v26.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
