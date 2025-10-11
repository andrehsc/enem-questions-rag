"""Configuration management for ENEM ingestion pipeline."""

import os
from pathlib import Path
from typing import Optional, List


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Database configuration
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://username:password@localhost:5432/enem_questions"
        )
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "5432"))
        self.db_name = os.getenv("DB_NAME", "enem_questions")
        self.db_user = os.getenv("DB_USER", "username")
        self.db_password = os.getenv("DB_PASSWORD", "password")

        # INEP data sources
        self.inep_base_url = os.getenv("INEP_BASE_URL", "https://www.gov.br/inep/pt-br")
        self.download_cache_dir = Path(os.getenv("DOWNLOAD_CACHE_DIR", "./data/downloads"))

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        log_file_path = os.getenv("LOG_FILE", "./logs/enem_ingestion.log")
        self.log_file = Path(log_file_path) if log_file_path else None

        # Processing settings
        self.target_years = [2020, 2021, 2022, 2023, 2024]
        self.batch_size = int(os.getenv("BATCH_SIZE", "100"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))


# Global settings instance
settings = Settings()