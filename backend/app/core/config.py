"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "CloudDesk Support"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/clouddesk",
        description="Async PostgreSQL connection URL",
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_max_connections: int = 50

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "clouddesk-api"
    kafka_topics: dict = Field(
        default_factory=lambda: {
            "support_request": "support.request.created",
            "ticket_updated": "support.ticket.updated",
            "action_executed": "support.action.executed",
        }
    )

    # JWT
    jwt_secret_key: str = Field(
        default="dev-secret-change-in-production",
        description="Secret key for JWT signing",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Rate limiting
    rate_limit_default: str = "60/minute"
    rate_limit_authenticated: str = "120/minute"
    rate_limit_admin: str = "300/minute"

    # Vector store
    vector_store_type: Literal["pinecone", "weaviate", "qdrant", "memory"] = "memory"
    vector_store_config: dict = Field(default_factory=dict)

    # Embeddings
    embedding_provider: Literal["openai", "cohere", "fake"] = "fake"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # LLM
    llm_provider: Literal["openai", "anthropic", "fake"] = "fake"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2000

    # Demo mode
    demo_mode: bool = True
    fake_llm_delay_ms: int = 100

    # Security
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1"]
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    log_file: Optional[str] = None

    # External APIs (optional)
    zendesk_subdomain: Optional[str] = None
    zendesk_email: Optional[str] = None
    zendesk_token: Optional[str] = None
    intercom_access_token: Optional[str] = None
    stripe_secret_key: Optional[str] = None
    sendgrid_api_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()