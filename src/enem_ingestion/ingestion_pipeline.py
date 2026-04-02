"""
ingestion_pipeline.py — Orquestrador do pipeline de ingestão de embeddings.

Processa questões com embedding_status='pending' do banco,
gera embeddings via OpenAI e persiste no pgvector.
"""

from __future__ import annotations

import argparse
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.enem_ingestion.chunk_builder import build_chunks_from_db_row
from src.enem_ingestion.embedding_generator import EmbeddingGenerator, TokenLimitError
from src.enem_ingestion.pgvector_writer import PgvectorWriter

logger = logging.getLogger(__name__)

# Custo aproximado: text-embedding-3-small = $0.02 por 1M tokens
COST_PER_TOKEN = 0.02 / 1_000_000

_SELECT_PENDING_SQL_BASE = """
    SELECT
        q.id,
        q.question_text,
        q.context_text,
        q.subject,
        q.question_number,
        q.has_images,
        em.year
    FROM enem_questions.questions q
    LEFT JOIN enem_questions.exam_metadata em ON em.id = q.exam_metadata_id
    WHERE q.embedding_status = 'pending'
      AND q.question_text IS NOT NULL
      AND q.question_text <> ''
    ORDER BY q.id
"""

_SELECT_PENDING_SQL_NO_LIMIT = text(_SELECT_PENDING_SQL_BASE)
_SELECT_PENDING_SQL_WITH_LIMIT = text(_SELECT_PENDING_SQL_BASE + "    LIMIT :limit\n")

_SELECT_ALTS_SQL = text("""
    SELECT question_id, alternative_letter, alternative_text
    FROM enem_questions.question_alternatives
    WHERE question_id = ANY(CAST(:ids AS uuid[]))
    ORDER BY question_id, alternative_order, alternative_letter
""")


@dataclass
class IngestionReport:
    total_processed: int = 0
    new_embedded: int = 0
    skipped: int = 0       # embedding_status já era 'done' (garantido pela query)
    errors: int = 0
    tokens_used: int = 0
    estimated_cost_usd: float = 0.0


class IngestionPipeline:
    """
    Orquestra o pipeline completo de geração de embeddings.

    Processa questões com embedding_status='pending' do banco,
    gera embeddings via OpenAI e persiste no pgvector.

    Uso:
        pipeline = IngestionPipeline(
            database_url=os.environ["DATABASE_URL"],
            openai_api_key=os.environ["OPENAI_API_KEY"],
        )
        report = pipeline.run(limit=500)
        print(f"Novos embeddings: {report.new_embedded}")
    """

    def __init__(
        self,
        database_url: str,
        openai_api_key: str,
        redis_url: str = "redis://localhost:6380/1",
    ) -> None:
        self._engine = create_engine(database_url, echo=False)
        self._generator = EmbeddingGenerator(
            api_key=openai_api_key,
            redis_url=redis_url,
        )
        self._writer = PgvectorWriter(database_url=database_url)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def run(self, limit: Optional[int] = None) -> IngestionReport:
        """Executa o pipeline completo e retorna um relatório de ingestão."""
        report = IngestionReport()

        # 1. Carregar questões pendentes
        questions = self._load_pending_questions(limit)
        report.total_processed = len(questions)

        if not questions:
            return report

        # 2. Carregar alternativas em batch
        question_ids = [str(q["id"]) for q in questions]
        alts_by_qid = self._load_alternatives(question_ids)

        # 3. Construir chunks
        all_chunks = []
        for q in questions:
            q_dict = dict(q)
            q_dict["alternatives"] = alts_by_qid.get(str(q_dict["id"]), [])
            try:
                chunks = build_chunks_from_db_row(q_dict)
                all_chunks.extend(chunks)
            except Exception as exc:
                logger.error("Erro ao construir chunks para %s: %s", q_dict["id"], exc)
                report.errors += 1

        if not all_chunks:
            return report

        # 4. Gerar embeddings (com TokenLimitError por chunk)
        try:
            results = self._generator.generate_embeddings(all_chunks)
            report.tokens_used = self._generator.tokens_used
            report.estimated_cost_usd = report.tokens_used * COST_PER_TOKEN
        except TokenLimitError as exc:
            logger.error("TokenLimitError no batch: %s", exc)
            report.errors += len(questions)
            return report

        # 5. Escrever no pgvector
        write_results = self._writer.write_batch(all_chunks, results)
        report.new_embedded = sum(1 for r in write_results if r.success)
        report.errors += sum(1 for r in write_results if not r.success)

        return report

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _load_pending_questions(self, limit: Optional[int]) -> List[dict]:
        """Retorna lista de questões com embedding_status='pending'."""
        with Session(self._engine) as session:
            if limit is not None:
                rows = session.execute(
                    _SELECT_PENDING_SQL_WITH_LIMIT, {"limit": limit}
                ).mappings().all()
            else:
                rows = session.execute(
                    _SELECT_PENDING_SQL_NO_LIMIT
                ).mappings().all()
        return [dict(row) for row in rows]

    def _load_alternatives(self, question_ids: List[str]) -> dict:
        """Retorna dict {question_id: List[dict]} com alternativas em batch."""
        if not question_ids:
            return {}

        alts_by_qid: dict = {}
        with Session(self._engine) as session:
            rows = session.execute(
                _SELECT_ALTS_SQL, {"ids": question_ids}
            ).mappings().all()

        for row in rows:
            qid = str(row["question_id"])
            if qid not in alts_by_qid:
                alts_by_qid[qid] = []
            alts_by_qid[qid].append({
                "alternative_letter": row["alternative_letter"],
                "alternative_text": row["alternative_text"],
            })

        return alts_by_qid


if __name__ == "__main__":
    import logging
    logging.basicConfig(level="INFO")

    parser = argparse.ArgumentParser(description="ENEM Ingestion Pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de questões a processar")
    args = parser.parse_args()

    pipeline = IngestionPipeline(
        database_url=os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres123@localhost:5433/teachershub_enem",
        ),
        openai_api_key=os.environ["OPENAI_API_KEY"],
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6380/1"),
    )
    report = pipeline.run(limit=args.limit)

    print("=== Relatório de Ingestão ===")
    print(f"  Total processado:  {report.total_processed}")
    print(f"  Novos embeddings:  {report.new_embedded}")
    print(f"  Pulados (done):    {report.skipped}")
    print(f"  Erros:             {report.errors}")
    print(f"  Tokens usados:     {report.tokens_used:,}")
    print(f"  Custo estimado:    ${report.estimated_cost_usd:.4f}")
