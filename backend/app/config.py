from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    llm_model: str = Field(default="llama-3.3-70b-versatile", alias="LLM_MODEL")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    knowledge_base_dir: str = Field(default="../../knowledge_base", alias="KNOWLEDGE_BASE_DIR")
    email_data_file: str = Field(default="email-data-advanced.json", alias="EMAIL_DATA_FILE")
    scrape_cache_ttl_hours: int = Field(default=6, alias="SCRAPE_CACHE_TTL_HOURS")
    scrape_timeout_seconds: int = Field(default=10, alias="SCRAPE_TIMEOUT_SECONDS")
    port: int = Field(default=8000, alias="PORT")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")
    simulation_speed: float = Field(default=1.0, alias="SIMULATION_SPEED")

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
