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

        # ENEM target years configuration
        target_years_env = os.getenv("TARGET_YEARS", "2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024")
        self.target_years = [int(year.strip()) for year in target_years_env.split(",")]


# Configuration class for AI-enhanced parsing
class Config:
    """Configuration for AI-enhanced ENEM parser."""
    
    def __init__(self):
        # AI Processing Configuration
        self.ai_confidence_threshold = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.4"))
        self.ai_batch_size = int(os.getenv("AI_BATCH_SIZE", "5"))
        self.ai_timeout_seconds = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))
        
        # Feature toggles
        self.enable_missing_detection = os.getenv("ENABLE_MISSING_DETECTION", "true").lower() == "true"
        self.enable_repair = os.getenv("ENABLE_REPAIR", "true").lower() == "true"
        self.enable_ai_validation = os.getenv("ENABLE_AI_VALIDATION", "true").lower() == "true"
        
        # LLama API Configuration
        self.llama_api_url = os.getenv("LLAMA_API_URL", "http://localhost:11434")
        self.llama_model = os.getenv("LLAMA_MODEL", "llama3")
        self.llama_max_retries = int(os.getenv("LLAMA_MAX_RETRIES", "3"))
        
        # Processing limits
        self.max_questions_per_batch = int(os.getenv("MAX_QUESTIONS_PER_BATCH", "10"))
        self.max_repair_attempts = int(os.getenv("MAX_REPAIR_ATTEMPTS", "2"))
        
        # Legacy settings access
        self.settings = settings


# Global settings instance
settings = Settings()
