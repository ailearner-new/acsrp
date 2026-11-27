"""Tests for config and settings."""

import os
from unittest.mock import patch

import pytest

from backend.app.core.config import Settings, get_settings


def test_default_settings():
    """Test default settings values."""
    settings = Settings()
    assert settings.app_name == "CloudDesk Support"
    assert settings.app_version == "0.1.0"
    assert settings.environment == "development"
    assert settings.debug is True
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.demo_mode is True


def test_custom_env_settings():
    """Test loading settings from environment variables."""
    with patch.dict(
        os.environ,
        {
            "APP_NAME": "Custom App",
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "PORT": "9000",
            "DEMO_MODE": "false",
        },
    ):
        settings = Settings()
        assert settings.app_name == "Custom App"
        assert settings.environment == "production"
        assert settings.debug is False
        assert settings.port == 9000
        assert settings.demo_mode is False


def test_get_settings_cached():
    """Test that get_settings uses lru_cache."""
    settings_1 = get_settings()
    settings_2 = get_settings()
    assert settings_1 is settings_2


def test_database_settings():
    """Test database settings configuration."""
    settings = Settings()
    assert "postgresql+asyncpg" in settings.database_url
    assert settings.database_pool_size > 0
    assert settings.database_max_overflow >= 0


def test_redis_settings():
    """Test redis settings configuration."""
    settings = Settings()
    assert "redis://" in settings.redis_url


def test_llm_settings():
    """Test LLM configuration settings."""
    settings = Settings()
    assert settings.llm_provider in ["openai", "anthropic", "fake"]
    assert settings.embedding_provider in ["openai", "cohere", "fake"]
    assert settings.vector_store_type in ["pinecone", "weaviate", "qdrant", "memory"]