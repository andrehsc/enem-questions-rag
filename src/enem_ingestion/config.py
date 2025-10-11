"""Configuration management for ENEM ingestion pipeline - TeachersHub Integration."""

import os
from pathlib import Path
from typing import Optional, List


class Settings:
    """Application settings loaded from environment variables - TeachersHub-ENEM Integration."""

    def __init__(self):
        # Database configuration - Using TeachersHub-ENEM hybrid credentials
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://enem_rag_service:enem123@localhost:5433/teachershub_enem"
        )
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "5433"))
        self.db_name = os.getenv("DB_NAME", "teachershub_enem")
        self.db_user = os.getenv("DB_USER", "enem_rag_service")
        self.db_password = os.getenv("DB_PASSWORD", "enem123")

        # Redis configuration
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6380"))
        self.redis_db = int(os.getenv("REDIS_DB", "1"))

        # INEP data sources
        self.inep_base_url = os.getenv("INEP_BASE_URL", "https://www.gov.br/inep/pt-br")
        self.download_cache_dir = Path(os.getenv("DOWNLOAD_CACHE_DIR", "./data/downloads"))

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        log_file_path = os.getenv("LOG_FILE", "./logs/enem_ingestion.log")
        self.log_file = Path(log_file_path) if log_file_path else None

        # TeachersHub Integration
        self.teachershub_api_url = os.getenv("TEACHERSHUB_API_URL", "http://localhost:5001")
        self.enem_rag_service_url = os.getenv("ENEM_RAG_SERVICE_URL", "http://localhost:8001")


# Global settings instance
settings = Settings()
