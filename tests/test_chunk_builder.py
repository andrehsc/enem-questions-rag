"""
tests/test_chunk_builder.py — Testes unitários para chunk_builder.py

Todos os testes são puros (sem banco de dados).
"""
from __future__ import annotations

import hashlib
import logging
from unittest.mock import patch

import pytest

from src.enem_ingestion.chunk_builder import (
    MAX_TOKENS,
    ChunkData,
    _ENC,
    build_chunks,
    build_chunks_from_db_row,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_ALTERNATIVES = ["Texto A", "Texto B", "Texto C", "Texto D", "Texto E"]
PREFIXED_ALTERNATIVES = ["A) Texto A", "B) Texto B", "C) Texto C", "D) Texto D", "E) Texto E"]


# ---------------------------------------------------------------------------
# AC 2: Questão sem context_text gera exatamente 1 chunk do tipo 'full'
# ---------------------------------------------------------------------------


def test_simple_question_generates_one_full_chunk():
    """2.1 — sem context_text → 1 chunk tipo 'full'."""
    chunks = build_chunks(
        question_text="Qual é a capital do Brasil?",
        alternatives=SIMPLE_ALTERNATIVES,
        context_text=None,
        question_id="q-001",
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "full"


def test_none_context_generates_one_chunk():
    """context_text None → apenas chunk full."""
    chunks = build_chunks("Questão qualquer", SIMPLE_ALTERNATIVES, context_text=None)
    assert len(chunks) == 1


def test_empty_string_context_generates_one_chunk():
    """context_text '' → apenas chunk full."""
    chunks = build_chunks("Questão qualquer", SIMPLE_ALTERNATIVES, context_text="")
    assert len(chunks) == 1


def test_whitespace_only_context_generates_one_chunk():
    """context_text de somente espaços → apenas chunk full."""
    chunks = build_chunks("Questão qualquer", SIMPLE_ALTERNATIVES, context_text="   \n\t  ")
    assert len(chunks) == 1


# ---------------------------------------------------------------------------
# AC 1: Questão com context_text gera exatamente 2 chunks: 'full' e 'context'
# ---------------------------------------------------------------------------


def test_question_with_context_generates_two_chunks():
    """2.2 — com context_text → 2 chunks, tipos 'full' e 'context'."""
    chunks = build_chunks(
        question_text="A partir do texto, responda:",
        alternatives=SIMPLE_ALTERNATIVES,
        context_text="Era uma vez um texto-base muito importante.",
        question_id="q-002",
    )

    assert len(chunks) == 2
    types = [c.chunk_type for c in chunks]
    assert "full" in types
    assert "context" in types


def test_context_chunk_contains_context_text():
    """O chunk 'context' deve conter exatamente o context_text."""
    ctx = "Texto-base relevante com informações históricas."
    chunks = build_chunks("Pergunta", SIMPLE_ALTERNATIVES, context_text=ctx)
    context_chunk = next(c for c in chunks if c.chunk_type == "context")
    assert context_chunk.content == ctx


# ---------------------------------------------------------------------------
# AC 1/2: Formato exato do chunk full
# ---------------------------------------------------------------------------


def test_full_chunk_format_contains_alternatives():
    """2.3 — verificar formato [ENUNCIADO] ... A) ... B) ..."""
    chunks = build_chunks(
        question_text="Qual o resultado?",
        alternatives=SIMPLE_ALTERNATIVES,
    )
    full_chunk = next(c for c in chunks if c.chunk_type == "full")
    content = full_chunk.content

    assert content.startswith("[ENUNCIADO] Qual o resultado?")
    assert "A) Texto A" in content
    assert "B) Texto B" in content
    assert "C) Texto C" in content
    assert "D) Texto D" in content
    assert "E) Texto E" in content


def test_full_chunk_format_with_prefixed_alternatives():
    """Alternativas já prefixadas com 'A)' não devem ser duplicadas."""
    chunks = build_chunks("Pergunta", PREFIXED_ALTERNATIVES)
    full_chunk = next(c for c in chunks if c.chunk_type == "full")
    content = full_chunk.content

    # Deve aparecer "A) Texto A", não "A) A) Texto A"
    assert "A) A)" not in content
    assert "A) Texto A" in content


def test_full_chunk_empty_alternatives_contains_only_enunciado():
    """Se a lista de alternativas estiver vazia, o full chunk contém só o enunciado."""
    chunks = build_chunks("Questão sem alternativas", alternatives=[])
    full_chunk = chunks[0]
    assert full_chunk.content == "[ENUNCIADO] Questão sem alternativas"


# ---------------------------------------------------------------------------
# AC 3: content_hash é SHA-256 de 64 chars
# ---------------------------------------------------------------------------


def test_content_hash_is_64_char_hex():
    """2.4 — hash tem 64 chars e é o SHA-256 correto do conteúdo."""
    chunks = build_chunks("Questão teste", SIMPLE_ALTERNATIVES)
    full_chunk = chunks[0]

    assert len(full_chunk.content_hash) == 64
    # Verificar que é hexadecimal válido
    int(full_chunk.content_hash, 16)  # levanta ValueError se inválido


def test_content_hash_matches_sha256_of_content():
    """content_hash deve ser SHA-256 do conteúdo original (antes do truncamento)."""
    question_text = "Questão de verificação de hash"
    chunks = build_chunks(question_text, SIMPLE_ALTERNATIVES)
    full_chunk = chunks[0]

    expected_hash = hashlib.sha256(full_chunk.content.encode("utf-8")).hexdigest()
    assert full_chunk.content_hash == expected_hash


def test_hash_is_deterministic():
    """Mesmo input deve gerar mesmo hash."""
    chunks_1 = build_chunks("Questão constante", SIMPLE_ALTERNATIVES)
    chunks_2 = build_chunks("Questão constante", SIMPLE_ALTERNATIVES)
    assert chunks_1[0].content_hash == chunks_2[0].content_hash


# ---------------------------------------------------------------------------
# AC 4: token_count via tiktoken
# ---------------------------------------------------------------------------


def test_token_count_is_calculated():
    """2.5 — token_count > 0 para chunk com conteúdo."""
    chunks = build_chunks("Questão com texto", SIMPLE_ALTERNATIVES)
    for chunk in chunks:
        assert chunk.token_count > 0


def test_token_count_matches_tiktoken():
    """token_count deve ser igual ao resultado do encoding tiktoken."""
    chunks = build_chunks("Questão tiktoken", SIMPLE_ALTERNATIVES)
    full_chunk = chunks[0]

    expected = len(_ENC.encode(full_chunk.content))
    assert full_chunk.token_count == expected


# ---------------------------------------------------------------------------
# AC 5: Truncamento ao limite de 8000 tokens com log WARNING
# ---------------------------------------------------------------------------


def test_truncation_at_8000_tokens_logs_warning(caplog):
    """2.6 — chunk com >8000 tokens é truncado e logger.warning é chamado."""
    # Montar um question_text muito longo para superar 8000 tokens
    very_long_text = "palavra " * 10_000  # ~10000 tokens

    with caplog.at_level(logging.WARNING, logger="src.enem_ingestion.chunk_builder"):
        chunks = build_chunks(
            question_text=very_long_text,
            alternatives=SIMPLE_ALTERNATIVES,
            question_id="q-truncado",
        )

    full_chunk = next(c for c in chunks if c.chunk_type == "full")

    # Token count deve ter sido limitado
    assert full_chunk.token_count == MAX_TOKENS

    # Log warning emitido
    assert any("truncado" in record.message.lower() for record in caplog.records)

    # Log deve conter o content_hash (story spec: "logar o hash original")
    full_chunk = next(c for c in chunks if c.chunk_type == "full")
    assert any(full_chunk.content_hash in record.message for record in caplog.records)


def test_truncated_chunk_has_original_hash():
    """O hash de um chunk truncado refere-se ao conteúdo ORIGINAL, não ao truncado."""
    very_long_text = "palavra " * 10_000
    chunks = build_chunks(
        question_text=very_long_text,
        alternatives=SIMPLE_ALTERNATIVES,
        question_id="q-hash-original",
    )
    full_chunk = chunks[0]

    # O hash é de 64 chars (SHA-256 do original)
    assert len(full_chunk.content_hash) == 64
    # O conteúdo foi truncado (não é o original)
    assert full_chunk.token_count == MAX_TOKENS


# ---------------------------------------------------------------------------
# Testes com metadados
# ---------------------------------------------------------------------------


def test_question_with_images_metadata():
    """2.7 — questão com has_images=True preserva metadado no chunk."""
    meta = {"year": 2023, "subject": "matematica", "has_images": True}
    chunks = build_chunks(
        question_text="Observe a figura",
        alternatives=SIMPLE_ALTERNATIVES,
        metadata=meta,
    )
    for chunk in chunks:
        assert chunk.metadata["has_images"] is True


def test_metadata_is_preserved_in_all_chunks():
    """Metadados devem estar presentes em todos os chunks."""
    meta = {"year": 2022, "subject": "portugues", "question_number": 5}
    chunks = build_chunks(
        question_text="Questão de português",
        alternatives=SIMPLE_ALTERNATIVES,
        context_text="Leia o trecho:",
        metadata=meta,
    )
    assert len(chunks) == 2
    for chunk in chunks:
        assert chunk.metadata["year"] == 2022
        assert chunk.metadata["subject"] == "portugues"


# ---------------------------------------------------------------------------
# Questão matemática curta (sem contexto)
# ---------------------------------------------------------------------------


def test_short_math_question_no_context():
    """2.8 — questão matemática curta gera apenas 'full' sem crash."""
    chunks = build_chunks(
        question_text="Calcule: 2 + 2 = ?",
        alternatives=["2", "3", "4", "5", "6"],
        context_text=None,
    )
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "full"
    assert chunks[0].token_count > 0


# ---------------------------------------------------------------------------
# build_chunks_from_db_row
# ---------------------------------------------------------------------------


def test_build_chunks_from_db_row_list_str():
    """Helper com alternatives como list[str]."""
    row = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "question_text": "Questão via row",
        "alternatives": ["Resp A", "Resp B", "Resp C", "Resp D", "Resp E"],
        "context_text": None,
        "subject": "historia",
        "year": 2021,
        "question_number": 10,
        "has_images": False,
    }
    chunks = build_chunks_from_db_row(row)

    assert len(chunks) == 1
    assert chunks[0].question_id == "550e8400-e29b-41d4-a716-446655440000"
    assert chunks[0].metadata["year"] == 2021


def test_build_chunks_from_db_row_list_dict():
    """Helper com alternatives como list[dict] (formato {'letter', 'text'})."""
    row = {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "question_text": "Questão dict",
        "alternatives": [
            {"letter": "A", "text": "Opção A"},
            {"letter": "B", "text": "Opção B"},
            {"letter": "C", "text": "Opção C"},
            {"letter": "D", "text": "Opção D"},
            {"letter": "E", "text": "Opção E"},
        ],
        "context_text": "Texto de contexto",
        "subject": "biologia",
        "year": 2020,
        "question_number": 33,
        "has_images": True,
    }
    chunks = build_chunks_from_db_row(row)

    assert len(chunks) == 2
    full_chunk = next(c for c in chunks if c.chunk_type == "full")
    assert "Opção A" in full_chunk.content
    assert full_chunk.metadata["has_images"] is True


def test_dict_alternatives_respect_letter_field():
    """_normalize_alternatives deve usar o campo 'letter' do dict, não a posição."""
    # Alternativas fora de ordem: C, A, E, B, D
    chunks = build_chunks(
        question_text="Questão com alternativas fora de ordem",
        alternatives=[
            {"letter": "C", "text": "Texto C"},
            {"letter": "A", "text": "Texto A"},
            {"letter": "E", "text": "Texto E"},
            {"letter": "B", "text": "Texto B"},
            {"letter": "D", "text": "Texto D"},
        ],
        question_id="q-ordem",
    )
    full_chunk = next(c for c in chunks if c.chunk_type == "full")
    # Cada alternativa deve aparecer com sua própria letra, não com a posição
    assert "C) Texto C" in full_chunk.content
    assert "A) Texto A" in full_chunk.content
    assert "E) Texto E" in full_chunk.content
    assert "B) Texto B" in full_chunk.content
    assert "D) Texto D" in full_chunk.content
    # A posição 0 NÃO deve ser rotulada "A)" — é "C)"
    assert "A) Texto C" not in full_chunk.content


def test_build_chunks_from_db_row_with_context():
    """Helper deve gerar chunk 'context' quando context_text está presente."""
    row = {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "question_text": "Analise o texto",
        "alternatives": ["A", "B", "C", "D", "E"],
        "context_text": "Este é o texto-base da questão.",
        "subject": "literatura",
        "year": 2019,
        "question_number": 7,
        "has_images": False,
    }
    chunks = build_chunks_from_db_row(row)

    assert len(chunks) == 2
    context_chunk = next(c for c in chunks if c.chunk_type == "context")
    assert context_chunk.content == "Este é o texto-base da questão."


def test_build_chunks_from_db_row_no_id():
    """question_id pode ser None quando id não está no row."""
    row = {
        "question_text": "Questão sem id",
        "alternatives": SIMPLE_ALTERNATIVES,
        "context_text": None,
    }
    chunks = build_chunks_from_db_row(row)
    assert chunks[0].question_id is None
