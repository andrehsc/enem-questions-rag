"""
Testes de integração: chunk_builder.py ↔ banco pgvector — Story 1.3.

Valida o fluxo completo: leitura de questões reais → build_chunks_from_db_row()
→ persistência em question_chunks → verificação de roundtrip.

NÃO duplica testes de test_pgvector_schema.py (constraints, HNSW, cascade).
Foco exclusivo na integração com chunk_builder.py.

Executar com:
    RUN_INTEGRATION_TESTS=true pytest tests/test_chunk_builder_integration.py -v

Ou usando a flag customizada:
    pytest tests/test_chunk_builder_integration.py -v --integration

Pré-requisitos:
- Docker rodando: docker-compose up -d postgres
- Variável DATABASE_URL configurada (ou padrão abaixo)
- Migration executada: database/pgvector-migration.sql
- Ao menos 1 questão ingerida em enem_questions.questions
"""

import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.enem_ingestion.chunk_builder import build_chunks_from_db_row, ChunkData


# ─── Guard de integração ──────────────────────────────────────────────────────
# Subtask 1.1: mesmo padrão de test_pgvector_schema.py

def is_integration_env():
    return (
        os.environ.get("RUN_INTEGRATION_TESTS", "").lower() in ("1", "true", "yes")
        or "--integration" in os.sys.argv
    )


pytestmark = pytest.mark.skipif(
    not is_integration_env(),
    reason="Testes de integração — set RUN_INTEGRATION_TESTS=true para executar"
)


# ─── Conexão ─────────────────────────────────────────────────────────────────

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────
# Subtask 1.2: mesma estrutura de test_pgvector_schema.py

@pytest.fixture(scope="module")
def engine():
    """Engine SQLAlchemy compartilhado no módulo."""
    eng = create_engine(DATABASE_URL, echo=False)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    """Sessão com rollback garantido após cada teste."""
    with Session(engine) as session:
        yield session
        session.rollback()


# Subtask 1.3: sample_question_row com JOIN para todos os campos necessários
@pytest.fixture(scope="module")
def sample_question_row(engine):
    """
    Retorna dict com todos os campos para build_chunks_from_db_row().

    Inclui alternatives como list[dict] via JOIN com question_alternatives.
    """
    with Session(engine) as session:
        row = session.execute(text("""
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
            WHERE q.question_text IS NOT NULL AND q.question_text <> ''
            LIMIT 1
        """)).fetchone()

        if row is None:
            pytest.skip("Banco sem questões. Execute o pipeline de ingestão primeiro.")

        q_id = str(row.id)

        alt_rows = session.execute(text("""
            SELECT alternative_letter, alternative_text
            FROM enem_questions.question_alternatives
            WHERE question_id = :qid
            ORDER BY alternative_order, alternative_letter
        """), {"qid": q_id}).fetchall()

        alternatives = [
            {"letter": r.alternative_letter, "text": r.alternative_text}
            for r in alt_rows
        ]

        return {
            "id": q_id,
            "question_text": row.question_text,
            "context_text": row.context_text,
            "subject": row.subject,
            "question_number": row.question_number,
            "has_images": row.has_images or False,
            "year": row.year,
            "alternatives": alternatives,
        }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _insert_chunk(db: Session, chunk: ChunkData) -> None:
    """Insere um ChunkData via SQL puro (sem ORM)."""
    db.execute(
        text("""
            INSERT INTO enem_questions.question_chunks
                (question_id, chunk_type, content, content_hash, token_count)
            VALUES (:qid, :ctype, :content, :hash, :tokens)
        """),
        {
            "qid": chunk.question_id,
            "ctype": chunk.chunk_type,
            "content": chunk.content,
            "hash": chunk.content_hash,
            "tokens": chunk.token_count,
        }
    )
    db.flush()


def _insert_chunk_idempotent(db: Session, chunk: ChunkData) -> None:
    """Insere chunk com ON CONFLICT — idempotente."""
    db.execute(
        text("""
            INSERT INTO enem_questions.question_chunks
                (question_id, chunk_type, content, content_hash, token_count)
            VALUES (:qid, :ctype, :content, :hash, :tokens)
            ON CONFLICT (content_hash) DO UPDATE
                SET updated_at = NOW()
        """),
        {
            "qid": chunk.question_id,
            "ctype": chunk.chunk_type,
            "content": chunk.content,
            "hash": chunk.content_hash,
            "tokens": chunk.token_count,
        }
    )
    db.flush()


# ─── Testes ───────────────────────────────────────────────────────────────────


class TestChunkBuilderWithRealData:
    """
    Build chunks a partir de dados reais do banco (sem inserção).

    Não modifica o banco (nenhum INSERT/UPDATE).
    Valida ACs 1, 2, 5, 6.
    """

    def test_build_chunks_from_real_db_question(self, sample_question_row):
        """AC 1: lê questão real, chama build_chunks_from_db_row(), verifica campos."""
        chunks = build_chunks_from_db_row(sample_question_row)

        assert len(chunks) >= 1, "Deve produzir ao menos 1 chunk."
        full_chunk = chunks[0]

        assert full_chunk.chunk_type == "full"
        assert full_chunk.question_id == sample_question_row["id"]
        assert len(full_chunk.content_hash) == 64, (
            f"content_hash deve ter 64 chars hex, got {len(full_chunk.content_hash)}"
        )
        # Verifica que content_hash é hexadecimal válido
        int(full_chunk.content_hash, 16)
        assert full_chunk.token_count > 0

    def test_chunk_content_hash_is_deterministic(self, sample_question_row):
        """AC 2: mesma questão → mesmos hashes em duas chamadas consecutivas."""
        chunks_1 = build_chunks_from_db_row(sample_question_row)
        chunks_2 = build_chunks_from_db_row(sample_question_row)

        assert len(chunks_1) == len(chunks_2), (
            "Número de chunks deve ser idêntico em ambas as chamadas."
        )
        for c1, c2 in zip(chunks_1, chunks_2):
            assert c1.content_hash == c2.content_hash, (
                f"content_hash divergiu para chunk_type={c1.chunk_type}: "
                f"{c1.content_hash!r} != {c2.content_hash!r}"
            )

    def test_build_chunks_with_dict_alternatives_from_db(self, sample_question_row):
        """AC 5: alternativas no formato list[dict] → letras preservadas no conteúdo."""
        # Garantir que as alternativas estão no formato dict
        alts = sample_question_row.get("alternatives", [])
        if not alts:
            pytest.skip("Questão sem alternativas no banco.")

        chunks = build_chunks_from_db_row(sample_question_row)
        full_chunk = chunks[0]

        for alt in alts:
            letter = alt["letter"]
            assert f"{letter})" in full_chunk.content, (
                f"Letra '{letter})' não encontrada no conteúdo do chunk 'full'."
            )

    def test_build_chunks_from_question_with_context_text(self, engine):
        """AC 6 (opcional): questão com context_text → 2 chunks (full + context)."""
        with Session(engine) as session:
            row = session.execute(text("""
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
                WHERE q.context_text IS NOT NULL AND q.context_text <> ''
                LIMIT 1
            """)).fetchone()

        if row is None:
            pytest.skip("Nenhuma questão com context_text no banco.")

        with Session(engine) as session:
            alt_rows = session.execute(text("""
                SELECT alternative_letter, alternative_text
                FROM enem_questions.question_alternatives
                WHERE question_id = :qid
                ORDER BY alternative_order, alternative_letter
            """), {"qid": str(row.id)}).fetchall()

        question_dict = {
            "id": str(row.id),
            "question_text": row.question_text,
            "context_text": row.context_text,
            "subject": row.subject,
            "question_number": row.question_number,
            "has_images": row.has_images or False,
            "year": row.year,
            "alternatives": [
                {"letter": r.alternative_letter, "text": r.alternative_text}
                for r in alt_rows
            ],
        }

        chunks = build_chunks_from_db_row(question_dict)

        assert len(chunks) == 2, (
            f"Questão com context_text deve gerar 2 chunks, gerou {len(chunks)}."
        )
        chunk_types = {c.chunk_type for c in chunks}
        assert "full" in chunk_types
        assert "context" in chunk_types


class TestChunkInsertRoundTrip:
    """
    Insere chunks construídos pelo chunk_builder no banco (rollback garantido).

    Valida ACs 3 e 4.
    """

    def test_insert_chunk_built_by_chunk_builder(self, db, sample_question_row):
        """AC 3: constrói chunk → insere via SQL → lê de volta e valida campos."""
        chunks = build_chunks_from_db_row(sample_question_row)
        assert chunks, "build_chunks_from_db_row deve retornar ao menos 1 chunk."

        full_chunk = next(c for c in chunks if c.chunk_type == "full")
        _insert_chunk(db, full_chunk)

        row = db.execute(
            text("""
                SELECT content, content_hash, token_count, chunk_type
                FROM enem_questions.question_chunks
                WHERE content_hash = :hash
            """),
            {"hash": full_chunk.content_hash}
        ).fetchone()

        assert row is not None, "Chunk inserido não foi encontrado no banco."
        assert row.content == full_chunk.content
        assert row.content_hash == full_chunk.content_hash
        assert row.token_count == full_chunk.token_count
        assert row.chunk_type == full_chunk.chunk_type

    def test_idempotency_via_on_conflict(self, db, sample_question_row):
        """AC 4: inserir o mesmo chunk duas vezes via ON CONFLICT → sem erro, 1 linha."""
        chunks = build_chunks_from_db_row(sample_question_row)
        assert chunks, "build_chunks_from_db_row deve retornar ao menos 1 chunk."

        full_chunk = next(c for c in chunks if c.chunk_type == "full")

        # Primeira inserção
        _insert_chunk_idempotent(db, full_chunk)
        # Segunda inserção — não deve lançar exceção
        _insert_chunk_idempotent(db, full_chunk)

        count = db.execute(
            text("""
                SELECT COUNT(*)
                FROM enem_questions.question_chunks
                WHERE content_hash = :hash
            """),
            {"hash": full_chunk.content_hash}
        ).scalar()

        assert count == 1, (
            f"ON CONFLICT deve manter apenas 1 linha, mas encontrou {count}."
        )
