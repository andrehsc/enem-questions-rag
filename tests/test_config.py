"""Tests for configuration management."""

import pytest
from pathlib import Path
from enem_ingestion.config import Settings


def test_settings_default_values():
    """Test default configuration values."""
    settings = Settings()
    
    assert settings.db_host == "localhost"
    assert settings.db_port == 5432
    assert settings.db_name == "enem_questions"
    assert settings.log_level == "INFO"
    assert isinstance(settings.download_cache_dir, Path)
    assert len(settings.target_years) == 5
    assert 2024 in settings.target_years


def test_settings_env_override(monkeypatch):
    """Test environment variable override."""
    monkeypatch.setenv("DB_HOST", "test_host")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    settings = Settings()
    
    assert settings.db_host == "test_host"
    assert settings.db_port == 5433
    assert settings.log_level == "DEBUG"