#!/usr/bin/env python3
"""Runner script para o pipeline v2 (épicos 5, 6 e 7)."""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from src.enem_ingestion.pipeline_v2 import ExtractionPipelineV2

DB_URL = "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"
INPUT_DIR = "data/tmp_ingest_epic567"
OUTPUT_DIR = "data/extracted_images"

pipeline = ExtractionPipelineV2(
    db_url=DB_URL,
    output_dir=OUTPUT_DIR,
    azure_config=None,  # Azure DI opcionalmente ativo via env var
)
report = pipeline.run(input_path=INPUT_DIR, force=True)
sys.exit(0 if report.errors == 0 or report.new > 0 else 1)
