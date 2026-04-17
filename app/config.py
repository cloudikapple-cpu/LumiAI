"""Configuration management using Pydantic settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/lumiai",
        validation_alias="DATABASE_URL",
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10


class RedisSettings(BaseSettings):
    """Redis configuration."""

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )
    redis_pool_size: int = 20


class TelegramSettings(BaseSettings):
    """Telegram bot configuration."""

    bot_token: str = Field(validation_alias="TELEGRAM_BOT_TOKEN")
    bot_owner_id: int = Field(default=0)
    webhook_domain: str | None = None
    webhook_path: str = "/webhook"
    trusted_proxies: list[str] = Field(default_factory=list)


class LLMProviderSettings(BaseSettings):
    """LLM provider settings."""

    openrouter_api_key: str = Field(validation_alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "https://lumi.ai"
    openrouter_site_name: str = "LumiAI"

    nvidia_api_key: str = Field(validation_alias="NVIDIA_API_KEY")
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    groq_api_key: str = Field(validation_alias="GROQ_API_KEY")
    groq_base_url: str = "https://api.groq.com/openai/v1"


class ObjectStorageSettings(BaseSettings):
    """Object storage (S3-compatible) configuration."""

    storage_endpoint: str | None = Field(default=None, validation_alias="STORAGE_ENDPOINT")
    storage_access_key: str | None = Field(default=None, validation_alias="STORAGE_ACCESS_KEY")
    storage_secret_key: str | None = Field(default=None, validation_alias="STORAGE_SECRET_KEY")
    storage_bucket: str = "lumi-ai-media"
    storage_region: str = "us-east-1"
    storage_public_url: str | None = None


class WorkerSettings(BaseSettings):
    """Background worker configuration."""

    worker_concurrency: int = 4
    worker_queue_name: str = "lumi-ai-tasks"
    worker_max_retries: int = 3
    worker_retry_delay: int = 60


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration."""

    rate_limit_messages_per_minute: int = 60
    rate_limit_messages_per_hour: int = 1000
    rate_limit_burst: int = 10


class Settings(BaseSettings):
    """Main settings class combining all configurations."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    debug: bool = False
    log_level: str = "INFO"

    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    llm: LLMProviderSettings = Field(default_factory=LLMProviderSettings)
    storage: ObjectStorageSettings = Field(default_factory=ObjectStorageSettings)
    worker: WorkerSettings = Field(default_factory=WorkerSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()