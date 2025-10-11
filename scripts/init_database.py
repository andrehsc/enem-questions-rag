#!/usr/bin/env python3
"""Initialize the PostgreSQL database with ENEM questions schema."""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enem_ingestion.config import settings
from enem_ingestion.database import DatabaseManager, Subject

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database with tables and default data."""
    try:
        logger.info("Initializing database...")
        
        # Create database manager
        db_manager = DatabaseManager()
        
        # Create all tables
        logger.info("Creating database tables...")
        db_manager.create_tables()
        
        # Create default subjects
        logger.info("Creating default subjects...")
        session = db_manager.get_session()
        
        default_subjects = [
            Subject(name="Linguagens, Códigos e suas Tecnologias", code="LC"),
            Subject(name="Matemática e suas Tecnologias", code="MT"),
            Subject(name="Ciências da Natureza e suas Tecnologias", code="CN"),
            Subject(name="Ciências Humanas e suas Tecnologias", code="CH"),
        ]
        
        for subject in default_subjects:
            existing = session.query(Subject).filter_by(code=subject.code).first()
            if not existing:
                session.add(subject)
                logger.info(f"Created subject: {subject.name}")
        
        session.commit()
        session.close()
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


if __name__ == "__main__":
    init_database()