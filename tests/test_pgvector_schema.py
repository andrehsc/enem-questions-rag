"""
Testes de integração para o schema pgvector — Story 1.1.

Requer banco PostgreSQL real com pgvector instalado.
Executar com:
    RUN_INTEGRATION_TESTS=true pytest tests/test_pgvector_schema.py -v

Ou usando a flag customizada:
    pytest tests/test_pgvector_schema.py -v --integration

Pré-requisitos:
- Docker rodando: docker-compose up -d postgres
- Variável DATABASE_URL configurada (ou padrão do config.py)
- Migration executada: database/pgvector-migration.sql
"""

import os
import uuid
import hashlib
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


# ─── Skip automático se não for ambiente de integração ───────────────────────

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: testes que requerem banco de dados real (pgvector)"
    )


def is_integration_env():
    return (
        os.environ.get("RUN_INTEGRATION_TESTS", "").lower() in ("1", "true", "yes")
        or "--integration" in os.sys.argv
    )


pytestmark = pytest.mark.skipif(
    not is_integration_env(),
    reason="Testes de integração — set RUN_INTEGRATION_TESTS=true para executar"
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"
)


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


@pytest.fixture(scope="module")
def sample_question_id(engine):
    """UUID de uma questão existente no banco — necessário como FK."""
    with Session(engine) as session:
        result = session.execute(
            text("SELECT id FROM enem_questions.questions LIMIT 1")
        ).fetchone()
        if result is None:
            pytest.skip(
                "Banco sem questões ingeridas. Execute o pipeline de ingestão primeiro."
            )
        return result[0]


def make_hash(text_content: str) -> str:
    """SHA-256 hex do conteúdo — mesma lógica que chunk_builder.py usará."""
    return hashlib.sha256(text_content.encode("utf-8")).hexdigest()


# ─── Testes ───────────────────────────────────────────────────────────────────


class TestExtensionAndSchema:
    """Valida que a extensão pgvector e as tabelas foram criadas."""

    def test_extension_vector_exists(self, db):
        """Extensão vector deve estar ativa no banco."""
        result = db.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        ).fetchone()
        assert result is not None, (
            "Extensão 'vector' não encontrada. "
            "Verifique se o container usa pgvector/pgvector:pg16."
        )

    def test_question_chunks_table_exists(self, db):
        """Tabela question_chunks deve existir no schema enem_questions."""
        result = db.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'enem_questions' AND table_name = 'question_chunks'"
            )
        ).fetchone()
        assert result is not None, (
            "Tabela 'enem_questions.question_chunks' não encontrada. "
            "Execute database/pgvector-migration.sql"
        )

    def test_question_images_table_exists(self, db):
        """Tabela question_images deve existir no schema enem_questions."""
        result = db.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'enem_questions' AND table_name = 'question_images'"
            )
        ).fetchone()
        assert result is not None, "Tabela 'enem_questions.question_images' não encontrada."

    def test_embedding_status_column_exists(self, db):
        """Coluna embedding_status deve existir na tabela questions."""
        result = db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'enem_questions' "
                "  AND table_name   = 'questions' "
                "  AND column_name  = 'embedding_status'"
            )
        ).fetchone()
        assert result is not None, "Coluna 'embedding_status' não encontrada em questions."

    def test_ingestion_hash_column_exists(self, db):
        """Coluna ingestion_hash deve existir na tabela questions."""
        result = db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'enem_questions' "
                "  AND table_name   = 'questions' "
                "  AND column_name  = 'ingestion_hash'"
            )
        ).fetchone()
        assert result is not None, "Coluna 'ingestion_hash' não encontrada em questions."

    def test_hnsw_index_exists(self, db):
        """Índice HNSW deve existir na coluna embedding de question_chunks."""
        result = db.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = 'enem_questions' "
                "  AND tablename  = 'question_chunks' "
                "  AND indexname  = 'idx_question_chunks_embedding'"
            )
        ).fetchone()
        assert result is not None, (
            "Índice HNSW 'idx_question_chunks_embedding' não encontrado. "
            "A migration pode ter falhado silenciosamente."
        )


class TestChunkCRUD:
    """Valida inserção, leitura e constraints da tabela question_chunks."""

    def test_insert_chunk_with_mock_embedding(self, db, sample_question_id):
        """Insere chunk com embedding mock e verifica recuperação por question_id."""
        chunk_id = uuid.uuid4()
        content  = "Enunciado de teste para embedding mock"
        content_hash = make_hash(content + str(chunk_id))  # único por execução
        # Embedding mock: vetor de 1536 dimensões com valor 0.1
        mock_embedding = "[" + ",".join(["0.1"] * 1536) + "]"

        db.execute(
            text("""
                INSERT INTO enem_questions.question_chunks
                    (id, question_id, chunk_type, content, content_hash, embedding, token_count)
                VALUES
                    (:id, :question_id, 'full', :content, :hash, CAST(:emb AS vector), :tokens)
            """),
            {
                "id": str(chunk_id),
                "question_id": str(sample_question_id),
                "content": content,
                "hash": content_hash,
                "emb": mock_embedding,
                "tokens": 10,
            }
        )
        db.flush()

        row = db.execute(
            text(
                "SELECT chunk_type, token_count FROM enem_questions.question_chunks "
                "WHERE question_id = :qid AND chunk_type = 'full' "
                "AND content_hash = :hash"
            ),
            {"qid": str(sample_question_id), "hash": content_hash}
        ).fetchone()

        assert row is not None, "Chunk inserido não foi encontrado."
        assert row.chunk_type == "full"
        assert row.token_count == 10

    def test_content_hash_unique_constraint(self, db, sample_question_id):
        """Dois chunks com mesmo content_hash devem violar UNIQUE constraint."""
        shared_hash = make_hash("conteudo_duplicado_" + str(uuid.uuid4()))
        content = "Conteúdo duplicado para testar constraint"

        db.execute(
            text("""
                INSERT INTO enem_questions.question_chunks
                    (question_id, chunk_type, content, content_hash)
                VALUES (:qid, 'full', :content, :hash)
            """),
            {"qid": str(sample_question_id), "content": content, "hash": shared_hash}
        )
        db.flush()

        with pytest.raises(IntegrityError, match="uk_question_chunks_hash"):
            db.execute(
                text("""
                    INSERT INTO enem_questions.question_chunks
                        (question_id, chunk_type, content, content_hash)
                    VALUES (:qid, 'context', :content, :hash)
                """),
                {"qid": str(sample_question_id), "content": content, "hash": shared_hash}
            )
            db.flush()

    def test_invalid_chunk_type_rejected(self, db, sample_question_id):
        """chunk_type inválido deve violar CHECK constraint."""
        with pytest.raises(IntegrityError):
            db.execute(
                text("""
                    INSERT INTO enem_questions.question_chunks
                        (question_id, chunk_type, content, content_hash)
                    VALUES (:qid, 'invalid_type', 'texto', :hash)
                """),
                {
                    "qid": str(sample_question_id),
                    "hash": make_hash("invalid" + str(uuid.uuid4()))
                }
            )
            db.flush()

    def test_embedding_null_allowed(self, db, sample_question_id):
        """Chunk pode ser inserido sem embedding (NULL) — pipeline em 2 fases."""
        content_hash = make_hash("sem_embedding_" + str(uuid.uuid4()))
        db.execute(
            text("""
                INSERT INTO enem_questions.question_chunks
                    (question_id, chunk_type, content, content_hash)
                VALUES (:qid, 'full', 'texto sem embedding', :hash)
            """),
            {"qid": str(sample_question_id), "hash": content_hash}
        )
        db.flush()

        row = db.execute(
            text(
                "SELECT embedding FROM enem_questions.question_chunks "
                "WHERE content_hash = :hash"
            ),
            {"hash": content_hash}
        ).fetchone()

        assert row is not None
        assert row.embedding is None


class TestEmbeddingStatus:
    """Valida constraint de embedding_status na tabela questions."""

    def test_invalid_embedding_status_rejected(self, db, sample_question_id):
        """Status inválido deve violar CHECK constraint."""
        with pytest.raises(IntegrityError, match="chk_questions_embedding_status"):
            db.execute(
                text("""
                    UPDATE enem_questions.questions
                    SET embedding_status = 'invalid_status'
                    WHERE id = :qid
                """),
                {"qid": str(sample_question_id)}
            )
            db.flush()

    def test_valid_embedding_statuses_accepted(self, db, sample_question_id):
        """Todos os status válidos devem ser aceitos."""
        for status in ("pending", "processing", "done", "error"):
            db.execute(
                text("""
                    UPDATE enem_questions.questions
                    SET embedding_status = :status
                    WHERE id = :qid
                """),
                {"status": status, "qid": str(sample_question_id)}
            )
            db.flush()
            # Rollback parcial via savepoint não está disponível facilmente;
            # apenas verificamos que não houve exceção


class TestHNSWSimilaritySearch:
    """Valida que busca por similaridade vetorial funciona via índice HNSW."""

    def test_hnsw_similarity_search_ordering(self, db, sample_question_id):
        """Busca por similaridade deve retornar chunks ordenados por distância."""
        # Inserir 3 chunks com embeddings distintos
        base = [0.0] * 1536
        embeddings = {
            "near":   [0.9 if i == 0 else 0.0 for i in range(1536)],  # próximo da query
            "medium": [0.5 if i == 0 else 0.0 for i in range(1536)],
            "far":    [0.1 if i == 0 else 0.0 for i in range(1536)],  # distante da query
        }
        hashes = {}
        for label, emb in embeddings.items():
            h = make_hash(f"hnsw_test_{label}_" + str(uuid.uuid4()))
            hashes[label] = h
            db.execute(
                text("""
                    INSERT INTO enem_questions.question_chunks
                        (question_id, chunk_type, content, content_hash, embedding)
                    VALUES (:qid, 'full', :content, :hash, CAST(:emb AS vector))
                """),
                {
                    "qid": str(sample_question_id),
                    "content": f"chunk_{label}",
                    "hash": h,
                    "emb": "[" + ",".join(map(str, emb)) + "]",
                }
            )
        db.flush()

        # Query vector próximo do "near"
        query_vec = "[" + ",".join(["0.95" if i == 0 else "0.0" for i in range(1536)]) + "]"

        rows = db.execute(
            text("""
                SELECT content_hash,
                       (embedding <=> CAST(:qvec AS vector)) AS distance
                FROM enem_questions.question_chunks
                WHERE content_hash = ANY(:hashes)
                ORDER BY embedding <=> CAST(:qvec AS vector)
                LIMIT 3
            """),
            {
                "qvec": query_vec,
                "hashes": list(hashes.values()),
            }
        ).fetchall()

        assert len(rows) == 3, "Deveria retornar 3 chunks."
        # O primeiro resultado deve ser o "near" (menor distância cosseno)
        assert rows[0].content_hash == hashes["near"], (
            f"Esperado 'near' como mais próximo, mas got {rows[0].content_hash}"
        )
        # Distâncias devem estar em ordem crescente
        distances = [r.distance for r in rows]
        assert distances == sorted(distances), "Resultados não estão ordenados por distância."


class TestCascadeDelete:
    """Valida que deletar questão remove seus chunks e imagens."""

    def test_cascade_delete_chunks(self, db, engine):
        """Deletar questão deve deletar seus chunks em cascata."""
        # Criar questão temporária
        temp_q_id = str(uuid.uuid4())
        # Buscar um exam_metadata_id válido para FK
        with Session(engine) as s2:
            meta = s2.execute(
                text("SELECT id FROM enem_questions.exam_metadata LIMIT 1")
            ).fetchone()
            if meta is None:
                pytest.skip("Sem exam_metadata disponível para teste de cascade.")
            meta_id = str(meta[0])

        db.execute(
            text("""
                INSERT INTO enem_questions.questions
                    (id, question_number, question_text, subject, exam_metadata_id)
                VALUES (:id, 9999, 'Questão temporária cascade test', 'matematica', :meta_id)
            """),
            {"id": temp_q_id, "meta_id": meta_id}
        )
        db.flush()

        # Inserir chunk para essa questão
        chunk_hash = make_hash("cascade_test_" + str(uuid.uuid4()))
        db.execute(
            text("""
                INSERT INTO enem_questions.question_chunks
                    (question_id, chunk_type, content, content_hash)
                VALUES (:qid, 'full', 'chunk cascade', :hash)
            """),
            {"qid": temp_q_id, "hash": chunk_hash}
        )
        db.flush()

        # Deletar questão
        db.execute(
            text("DELETE FROM enem_questions.questions WHERE id = :id"),
            {"id": temp_q_id}
        )
        db.flush()

        # Chunk deve ter sido deletado em cascata
        row = db.execute(
            text(
                "SELECT id FROM enem_questions.question_chunks WHERE content_hash = :hash"
            ),
            {"hash": chunk_hash}
        ).fetchone()

        assert row is None, "Chunk deveria ter sido deletado em cascata com a questão."


class TestMigrationIdempotency:
    """Valida que executar a migration duas vezes não gera erros."""

    def test_migration_idempotent(self, engine):
        """Re-executar a migration não deve lançar exceção."""
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..", "database", "pgvector-migration.sql"
        )
        migration_path = os.path.normpath(migration_path)

        assert os.path.exists(migration_path), (
            f"Arquivo de migration não encontrado: {migration_path}"
        )

        with open(migration_path, "r", encoding="utf-8") as f:
            sql = f.read()

        # Executar duas vezes — deve ser idempotente
        with engine.connect() as conn:
            # Primeira execução (já foi feita no setup)
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()

            # Segunda execução — não deve falhar
            conn.execute(text(sql))
            conn.commit()
