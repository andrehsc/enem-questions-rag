"""
Testes unitários para pgvector_writer.py — Story 2.2.

Todos os testes usam mocks — sem banco real.
"""

import pytest
from unittest.mock import MagicMock, patch, call, ANY

from src.enem_ingestion.chunk_builder import ChunkData
from src.enem_ingestion.embedding_generator import EmbeddingResult
from src.enem_ingestion.pgvector_writer import PgvectorWriter, WriteResult


# ─── Helpers ─────────────────────────────────────────────────────────────────


def make_chunk(
    content_hash: str = "a" * 64,
    question_id: str = "uuid-1",
    chunk_type: str = "full",
    token_count: int = 50,
) -> ChunkData:
    return ChunkData(
        chunk_type=chunk_type,
        content="texto de questão",
        content_hash=content_hash,
        token_count=token_count,
        question_id=question_id,
    )


def make_embedding(content_hash: str = "a" * 64) -> EmbeddingResult:
    return EmbeddingResult(
        content_hash=content_hash,
        embedding=[0.1] * 1536,
        tokens_used=20,
        from_cache=False,
    )


@pytest.fixture
def mock_engine():
    with patch("src.enem_ingestion.pgvector_writer.create_engine") as mock:
        engine = MagicMock()
        mock.return_value = engine
        yield engine


@pytest.fixture
def mock_session(mock_engine):
    """Retorna o mock session usado dentro do context manager Session(engine)."""
    session = MagicMock()
    mock_engine.__class__ = MagicMock  # necessário para Session() funcionar com mock

    with patch("src.enem_ingestion.pgvector_writer.Session") as MockSession:
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=session)
        ctx.__exit__ = MagicMock(return_value=False)
        MockSession.return_value = ctx
        yield session, MockSession


@pytest.fixture
def writer(mock_engine):
    return PgvectorWriter(database_url="postgresql://fake/db")


# ─── TestWriteChunks ─────────────────────────────────────────────────────────


class TestWriteChunks:
    def test_insert_uses_on_conflict_clause(self, writer, mock_session):
        """SQL executado deve conter ON CONFLICT."""
        session, _ = mock_session
        chunk = make_chunk()
        embedding = make_embedding()

        writer.write_chunks([chunk], [embedding])

        assert session.execute.call_count == 1
        sql_arg = session.execute.call_args[0][0]
        sql_text = str(sql_arg)
        assert "ON CONFLICT" in sql_text.upper()

    def test_batch_3_chunks_generates_3_inserts(self, writer, mock_session):
        """3 chunks → 3 chamadas a session.execute (INSERT)."""
        session, _ = mock_session
        chunks = [make_chunk(content_hash=f"{i}" * 64) for i in range(1, 4)]
        embeddings = [make_embedding(content_hash=c.content_hash) for c in chunks]

        results = writer.write_chunks(chunks, embeddings)

        assert session.execute.call_count == 3
        assert len(results) == 3

    def test_chunk_error_does_not_stop_other_chunks(self, writer, mock_session):
        """Erro no 1º chunk não impede inserção do 2º e 3º."""
        session, _ = mock_session
        chunks = [make_chunk(content_hash=f"{i}" * 64) for i in range(1, 4)]
        embeddings = [make_embedding(content_hash=c.content_hash) for c in chunks]

        # Primeiro execute lança exceção; os demais têm sucesso
        session.execute.side_effect = [
            Exception("DB error"),
            MagicMock(),
            MagicMock(),
        ]

        results = writer.write_chunks(chunks, embeddings)

        assert results[0].success is False
        assert "DB error" in results[0].error
        assert results[1].success is True
        assert results[2].success is True

    def test_write_result_success_true_on_success(self, writer, mock_session):
        """WriteResult.success deve ser True quando INSERT tem sucesso."""
        session, _ = mock_session
        chunk = make_chunk()
        embedding = make_embedding()

        results = writer.write_chunks([chunk], [embedding])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].error is None
        assert results[0].chunk_hash == chunk.content_hash

    def test_write_result_success_false_on_db_error(self, writer, mock_session):
        """WriteResult.success deve ser False quando INSERT falha."""
        session, _ = mock_session
        session.execute.side_effect = Exception("connection refused")
        chunk = make_chunk()
        embedding = make_embedding()

        results = writer.write_chunks([chunk], [embedding])

        assert results[0].success is False
        assert results[0].error is not None

    def test_missing_embedding_returns_error_result(self, writer, mock_session):
        """Chunk sem embedding correspondente → WriteResult com success=False."""
        session, _ = mock_session
        chunk = make_chunk(content_hash="a" * 64)
        # Embedding com hash diferente — não corresponde ao chunk
        embedding = make_embedding(content_hash="b" * 64)

        results = writer.write_chunks([chunk], [embedding])

        assert results[0].success is False
        assert results[0].error is not None
        session.execute.assert_not_called()

    def test_question_id_preserved_in_result(self, writer, mock_session):
        """question_id do chunk deve ser preservado no WriteResult."""
        session, _ = mock_session
        chunk = make_chunk(question_id="my-uuid-123")
        embedding = make_embedding(content_hash=chunk.content_hash)

        results = writer.write_chunks([chunk], [embedding])

        assert results[0].question_id == "my-uuid-123"


# ─── TestUpdateEmbeddingStatus ────────────────────────────────────────────────


class TestUpdateEmbeddingStatus:
    def test_update_status_executes_sql_with_correct_params(self, writer, mock_session):
        """update_embedding_status deve executar UPDATE com status e ids corretos."""
        session, _ = mock_session
        ids = ["uuid-1", "uuid-2"]

        writer.update_embedding_status(ids, status="done")

        assert session.execute.call_count == 1
        params = session.execute.call_args[0][1]
        assert params["status"] == "done"
        assert params["ids"] == ids

    def test_update_status_uses_correct_sql_pattern(self, writer, mock_session):
        """SQL deve conter UPDATE e embedding_status."""
        session, _ = mock_session

        writer.update_embedding_status(["uuid-1"])

        sql_arg = session.execute.call_args[0][0]
        sql_text = str(sql_arg).upper()
        assert "UPDATE" in sql_text
        assert "EMBEDDING_STATUS" in sql_text

    def test_update_status_empty_list_skips_execute(self, writer, mock_session):
        """Lista vazia não deve executar nenhuma query."""
        session, _ = mock_session

        writer.update_embedding_status([])

        session.execute.assert_not_called()


# ─── TestWriteBatch ───────────────────────────────────────────────────────────


class TestWriteBatch:
    def test_write_batch_calls_update_status_for_successful_ids(
        self, writer, mock_session
    ):
        """write_batch deve atualizar status apenas dos question_ids com sucesso."""
        session, _ = mock_session

        chunks = [
            make_chunk(content_hash="a" * 64, question_id="qid-1"),
            make_chunk(content_hash="b" * 64, question_id="qid-2"),
        ]
        embeddings = [make_embedding(content_hash=c.content_hash) for c in chunks]

        # Primeiro chunk falha, segundo tem sucesso
        session.execute.side_effect = [
            Exception("insert error"),  # chunk 1 INSERT falha
            MagicMock(),                # chunk 2 INSERT ok
            MagicMock(),                # update_status ok
        ]

        results = writer.write_batch(chunks, embeddings)

        assert results[0].success is False
        assert results[1].success is True

        # update_status deve ter sido chamado (3ª execute), verificar params
        last_params = session.execute.call_args_list[-1][0][1]
        assert "qid-2" in last_params["ids"]
        assert "qid-1" not in last_params["ids"]

    def test_write_batch_no_update_when_all_fail(self, writer, mock_session):
        """Se todos os chunks falharem, update_embedding_status NÃO deve ser chamado."""
        session, _ = mock_session
        session.execute.side_effect = Exception("all fail")

        chunk = make_chunk()
        embedding = make_embedding()

        results = writer.write_batch([chunk], [embedding])

        assert results[0].success is False
        # execute chamado apenas 1x (o INSERT que falhou); update_status não chama
        assert session.execute.call_count == 1

    def test_write_batch_returns_all_results(self, writer, mock_session):
        """write_batch deve retornar WriteResult para cada chunk."""
        session, _ = mock_session
        chunks = [make_chunk(content_hash=f"{i}" * 64) for i in range(1, 4)]
        embeddings = [make_embedding(content_hash=c.content_hash) for c in chunks]

        results = writer.write_batch(chunks, embeddings)

        assert len(results) == 3
