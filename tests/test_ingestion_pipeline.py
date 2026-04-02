"""
Testes unitários para ingestion_pipeline.py — Story 2.3.

Todos os testes usam mocks — sem banco real, sem OpenAI real, sem Redis real.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from src.enem_ingestion.ingestion_pipeline import IngestionPipeline, IngestionReport, COST_PER_TOKEN
from src.enem_ingestion.chunk_builder import ChunkData
from src.enem_ingestion.embedding_generator import EmbeddingResult
from src.enem_ingestion.pgvector_writer import WriteResult


# ─── Helpers ─────────────────────────────────────────────────────────────────


def make_question(qid: str = "uuid-1", question_text: str = "Qual a resposta?") -> dict:
    return {
        "id": qid,
        "question_text": question_text,
        "context_text": None,
        "subject": "Matemática",
        "question_number": 1,
        "has_images": False,
        "year": 2022,
        "alternatives": [],
    }


def make_chunk(
    content_hash: str = "a" * 64,
    question_id: str = "uuid-1",
) -> ChunkData:
    return ChunkData(
        chunk_type="full",
        content="texto da questão com alternativas",
        content_hash=content_hash,
        token_count=80,
        question_id=question_id,
    )


def make_embedding_result(content_hash: str = "a" * 64) -> EmbeddingResult:
    return EmbeddingResult(
        content_hash=content_hash,
        embedding=[0.1] * 1536,
        tokens_used=80,
        from_cache=False,
    )


def make_write_result(success: bool = True, question_id: str = "uuid-1") -> WriteResult:
    return WriteResult(
        question_id=question_id,
        chunk_hash="a" * 64,
        success=success,
        error=None if success else "DB error",
    )


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_engine():
    with patch("src.enem_ingestion.ingestion_pipeline.create_engine") as mock_ce:
        engine = MagicMock()
        mock_ce.return_value = engine
        yield engine


@pytest.fixture
def mock_generator():
    with patch("src.enem_ingestion.ingestion_pipeline.EmbeddingGenerator") as MockGen:
        generator = MagicMock()
        generator.tokens_used = 0
        MockGen.return_value = generator
        yield generator


@pytest.fixture
def mock_writer():
    with patch("src.enem_ingestion.ingestion_pipeline.PgvectorWriter") as MockWriter:
        writer = MagicMock()
        MockWriter.return_value = writer
        yield writer


@pytest.fixture
def pipeline(mock_engine, mock_generator, mock_writer):
    return IngestionPipeline(
        database_url="postgresql://fake/db",
        openai_api_key="sk-fake",
    )


# ─── TestIngestionReport ─────────────────────────────────────────────────────


class TestIngestionReport:
    def test_default_values_are_zero(self):
        report = IngestionReport()
        assert report.total_processed == 0
        assert report.new_embedded == 0
        assert report.skipped == 0
        assert report.errors == 0
        assert report.tokens_used == 0
        assert report.estimated_cost_usd == 0.0

    def test_skipped_count_from_empty_pending(self, pipeline, mocker):
        """Sem questões pendentes, relatório retorna zeros (skipped permanece 0)."""
        mocker.patch.object(pipeline, "_load_pending_questions", return_value=[])

        report = pipeline.run()

        assert report.total_processed == 0
        assert report.new_embedded == 0
        assert report.skipped == 0
        assert report.errors == 0


# ─── TestRun ─────────────────────────────────────────────────────────────────


class TestRun:
    def test_run_empty_pending_returns_zero_report(self, pipeline, mocker):
        """Quando não há questões pendentes, run() retorna relatório zerado."""
        mocker.patch.object(pipeline, "_load_pending_questions", return_value=[])

        report = pipeline.run()

        assert report.total_processed == 0
        assert report.new_embedded == 0
        assert report.errors == 0

    def test_run_processes_pending_questions(self, pipeline, mock_generator, mock_writer, mocker):
        """run() processa questões pendentes e popula new_embedded corretamente."""
        question = make_question()
        chunk = make_chunk()
        emb = make_embedding_result()
        write_res = make_write_result(success=True)

        mocker.patch.object(pipeline, "_load_pending_questions", return_value=[question])
        mocker.patch.object(pipeline, "_load_alternatives", return_value={})
        mocker.patch(
            "src.enem_ingestion.ingestion_pipeline.build_chunks_from_db_row",
            return_value=[chunk],
        )
        mock_generator.generate_embeddings.return_value = [emb]
        mock_generator.tokens_used = 80
        mock_writer.write_batch.return_value = [write_res]

        report = pipeline.run()

        assert report.total_processed == 1
        assert report.new_embedded == 1
        assert report.errors == 0

    def test_run_respects_limit_parameter(self, pipeline, mocker):
        """run(limit=5) deve passar limit=5 para _load_pending_questions."""
        load_mock = mocker.patch.object(pipeline, "_load_pending_questions", return_value=[])

        pipeline.run(limit=5)

        load_mock.assert_called_once_with(5)

    def test_run_counts_errors_from_write_failures(self, pipeline, mock_generator, mock_writer, mocker):
        """Falha no write_batch deve incrementar report.errors."""
        question = make_question()
        chunk = make_chunk()
        emb = make_embedding_result()
        write_fail = make_write_result(success=False)

        mocker.patch.object(pipeline, "_load_pending_questions", return_value=[question])
        mocker.patch.object(pipeline, "_load_alternatives", return_value={})
        mocker.patch(
            "src.enem_ingestion.ingestion_pipeline.build_chunks_from_db_row",
            return_value=[chunk],
        )
        mock_generator.generate_embeddings.return_value = [emb]
        mock_generator.tokens_used = 0
        mock_writer.write_batch.return_value = [write_fail]

        report = pipeline.run()

        assert report.new_embedded == 0
        assert report.errors == 1

    def test_run_calculates_tokens_and_cost(self, pipeline, mock_generator, mock_writer, mocker):
        """tokens_used e estimated_cost_usd são calculados corretamente."""
        question = make_question()
        chunk = make_chunk()
        emb = make_embedding_result()
        write_res = make_write_result(success=True)

        mocker.patch.object(pipeline, "_load_pending_questions", return_value=[question])
        mocker.patch.object(pipeline, "_load_alternatives", return_value={})
        mocker.patch(
            "src.enem_ingestion.ingestion_pipeline.build_chunks_from_db_row",
            return_value=[chunk],
        )
        mock_generator.generate_embeddings.return_value = [emb]
        mock_generator.tokens_used = 5000
        mock_writer.write_batch.return_value = [write_res]

        report = pipeline.run()

        assert report.tokens_used == 5000
        assert report.estimated_cost_usd == pytest.approx(5000 * COST_PER_TOKEN)

    def test_token_limit_error_increments_errors(self, pipeline, mock_generator, mock_writer, mocker):
        """TokenLimitError no generate_embeddings deve incrementar errors e fazer early return."""
        from src.enem_ingestion.embedding_generator import TokenLimitError

        question = make_question()
        chunk = make_chunk()

        mocker.patch.object(pipeline, "_load_pending_questions", return_value=[question])
        mocker.patch.object(pipeline, "_load_alternatives", return_value={})
        mocker.patch(
            "src.enem_ingestion.ingestion_pipeline.build_chunks_from_db_row",
            return_value=[chunk],
        )
        mock_generator.generate_embeddings.side_effect = TokenLimitError("too many tokens")

        report = pipeline.run()

        assert report.errors == 1  # len(questions)
        assert report.new_embedded == 0
        mock_writer.write_batch.assert_not_called()

    def test_run_chunk_build_error_increments_errors(self, pipeline, mock_generator, mock_writer, mocker):
        """Erro no build_chunks_from_db_row deve incrementar errors sem parar o pipeline."""
        mocker.patch.object(pipeline, "_load_pending_questions", return_value=[make_question()])
        mocker.patch.object(pipeline, "_load_alternatives", return_value={})
        mocker.patch(
            "src.enem_ingestion.ingestion_pipeline.build_chunks_from_db_row",
            side_effect=ValueError("parse error"),
        )

        report = pipeline.run()

        assert report.errors == 1
        # generate_embeddings não é chamado pois não há chunks
        mock_generator.generate_embeddings.assert_not_called()

    def test_run_multiple_questions_counted_correctly(self, pipeline, mock_generator, mock_writer, mocker):
        """Processar 3 questões com 2 sucessos e 1 falha."""
        questions = [make_question(qid=f"uuid-{i}") for i in range(3)]
        chunks = [make_chunk(content_hash=f"{i}" * 64, question_id=f"uuid-{i}") for i in range(3)]
        embeddings = [make_embedding_result(content_hash=c.content_hash) for c in chunks]
        write_results = [
            make_write_result(success=True, question_id="uuid-0"),
            make_write_result(success=True, question_id="uuid-1"),
            make_write_result(success=False, question_id="uuid-2"),
        ]

        mocker.patch.object(pipeline, "_load_pending_questions", return_value=questions)
        mocker.patch.object(pipeline, "_load_alternatives", return_value={})
        mocker.patch(
            "src.enem_ingestion.ingestion_pipeline.build_chunks_from_db_row",
            side_effect=[[c] for c in chunks],
        )
        mock_generator.generate_embeddings.return_value = embeddings
        mock_generator.tokens_used = 240
        mock_writer.write_batch.return_value = write_results

        report = pipeline.run()

        assert report.total_processed == 3
        assert report.new_embedded == 2
        assert report.errors == 1


# ─── TestLoadPendingQuestions ─────────────────────────────────────────────────


class TestLoadPendingQuestions:
    def test_no_limit_uses_no_limit_query(self, pipeline, mock_engine, mocker):
        """Sem limit, a query sem LIMIT é executada."""
        mock_session_ctx = MagicMock()
        mock_session_inst = MagicMock()
        mock_session_ctx.__enter__ = MagicMock(return_value=mock_session_inst)
        mock_session_ctx.__exit__ = MagicMock(return_value=False)
        mock_session_inst.execute.return_value.mappings.return_value.all.return_value = []

        with patch("src.enem_ingestion.ingestion_pipeline.Session", return_value=mock_session_ctx):
            result = pipeline._load_pending_questions(None)

        assert result == []
        # Verificar que a query executada não tem :limit nos parâmetros
        call_args = mock_session_inst.execute.call_args
        # Sem limit: apenas 1 argumento posicional (a query), sem params dict
        assert len(call_args[0]) == 1

    def test_with_limit_passes_limit_param(self, pipeline, mock_engine):
        """Com limit, a query LIMIT :limit é executada com o valor correto."""
        mock_session_ctx = MagicMock()
        mock_session_inst = MagicMock()
        mock_session_ctx.__enter__ = MagicMock(return_value=mock_session_inst)
        mock_session_ctx.__exit__ = MagicMock(return_value=False)
        mock_session_inst.execute.return_value.mappings.return_value.all.return_value = []

        with patch("src.enem_ingestion.ingestion_pipeline.Session", return_value=mock_session_ctx):
            pipeline._load_pending_questions(42)

        call_args = mock_session_inst.execute.call_args
        params = call_args[0][1]
        assert params["limit"] == 42


# ─── TestLoadAlternatives ─────────────────────────────────────────────────────


class TestLoadAlternatives:
    def test_empty_ids_returns_empty_dict(self, pipeline):
        """Lista vazia de ids retorna dict vazio sem query."""
        result = pipeline._load_alternatives([])
        assert result == {}

    def test_groups_alternatives_by_question_id(self, pipeline, mock_engine):
        """Alternativas são agrupadas por question_id."""
        mock_session_ctx = MagicMock()
        mock_session_inst = MagicMock()
        mock_session_ctx.__enter__ = MagicMock(return_value=mock_session_inst)
        mock_session_ctx.__exit__ = MagicMock(return_value=False)

        # Simula 2 alternativas para qid-1 e 1 para qid-2
        rows = [
            {"question_id": "qid-1", "alternative_letter": "A", "alternative_text": "Opção A"},
            {"question_id": "qid-1", "alternative_letter": "B", "alternative_text": "Opção B"},
            {"question_id": "qid-2", "alternative_letter": "A", "alternative_text": "Opção X"},
        ]
        mock_session_inst.execute.return_value.mappings.return_value.all.return_value = rows

        with patch("src.enem_ingestion.ingestion_pipeline.Session", return_value=mock_session_ctx):
            result = pipeline._load_alternatives(["qid-1", "qid-2"])

        assert len(result["qid-1"]) == 2
        assert len(result["qid-2"]) == 1
        assert result["qid-1"][0]["alternative_letter"] == "A"
