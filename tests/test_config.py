"""Tests for configuration management."""

import pytest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from enem_ingestion.config import Settings


def test_settings_default_values():
    """Test default configuration values."""
    settings = Settings()
    
    assert settings.db_host == "localhost"
    assert settings.db_port == 5433
    assert settings.db_name == "teachershub_enem"
    assert settings.log_level == "INFO"
    assert isinstance(settings.download_cache_dir, Path)
    assert len(settings.target_years) == 16
    assert 2024 in settings.target_years
    assert 2009 in settings.target_years


def test_settings_env_override(monkeypatch):
    """Test environment variable override."""
    monkeypatch.setenv("DB_HOST", "test_host")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    settings = Settings()
    
    assert settings.db_host == "test_host"
    assert settings.db_port == 5433
    assert settings.log_level == "DEBUG"