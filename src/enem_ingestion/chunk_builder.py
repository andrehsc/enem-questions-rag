"""
chunk_builder.py — Módulo de construção de chunks híbridos para questões ENEM.

Produz até 2 chunks por questão:
  - 'full'   : enunciado + alternativas (sempre gerado)
  - 'context': texto-base da questão (somente se context_text não for vazio)

Cada chunk inclui content_hash SHA-256 (calculado ANTES do truncamento)
e token_count via tiktoken cl100k_base.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import tiktoken

logger = logging.getLogger(__name__)

MAX_TOKENS = 8000

# Instanciar encoding uma única vez no nível do módulo
_ENC = tiktoken.get_encoding("cl100k_base")

_LETTERS = ["A", "B", "C", "D", "E"]


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class ChunkData:
    chunk_type: str          # 'full' | 'context'
    content: str             # texto do chunk (possivelmente truncado)
    content_hash: str        # SHA-256 hex, 64 chars — do conteúdo ORIGINAL
    token_count: int         # contagem tiktoken cl100k_base
    question_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _normalize_alternatives(alternatives: List[Any]) -> List[str]:
    """Normaliza alternativas para o formato 'A) texto', 'B) texto', etc."""
    normalized: List[str] = []
    for idx, alt in enumerate(alternatives):
        fallback_letter = _LETTERS[idx] if idx < len(_LETTERS) else str(idx)
        if isinstance(alt, dict):
            # Formato: {"letter": "A", "text": "..."}
            letter = alt.get("letter", fallback_letter).upper()
            text = alt.get("text", "")
            normalized.append(f"{letter}) {text}")
        else:
            text = str(alt)
            # Verifica se já começa com "A) ", "B) ", etc.
            if len(text) >= 3 and text[1] == ")" and text[0].upper() in _LETTERS:
                normalized.append(text)
            else:
                normalized.append(f"{fallback_letter}) {text}")
    return normalized


def _format_full_content(question_text: str, alternatives: List[Any]) -> str:
    """Formata o conteúdo do chunk 'full'."""
    normalized_alts = _normalize_alternatives(alternatives)
    parts = [f"[ENUNCIADO] {question_text}"]
    parts.extend(normalized_alts)
    return "\n".join(parts)


def _build_chunk(
    chunk_type: str,
    content: str,
    question_id: Optional[str],
    metadata: Dict[str, Any],
) -> ChunkData:
    """Cria um ChunkData com hash (do conteúdo original) e token_count."""
    # Hash ANTES do truncamento — representa o conteúdo original integral
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    tokens = _ENC.encode(content)
    token_count = len(tokens)

    if token_count > MAX_TOKENS:
        logger.warning(
            "Chunk truncado: question_id=%s chunk_type=%s content_hash=%s tokens_originais=%d tokens_limite=%d",
            question_id,
            chunk_type,
            content_hash,
            token_count,
            MAX_TOKENS,
        )
        content = _ENC.decode(tokens[:MAX_TOKENS])
        token_count = MAX_TOKENS

    return ChunkData(
        chunk_type=chunk_type,
        content=content,
        content_hash=content_hash,
        token_count=token_count,
        question_id=question_id,
        metadata=dict(metadata),
    )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def build_chunks(
    question_text: str,
    alternatives: List[Any],
    context_text: Optional[str] = None,
    question_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[ChunkData]:
    """
    Constrói chunks híbridos para uma questão ENEM.

    Retorna:
      - [full_chunk] quando context_text é None ou vazio
      - [full_chunk, context_chunk] quando context_text tem conteúdo
    """
    if metadata is None:
        metadata = {}

    chunks: List[ChunkData] = []

    # Chunk 'full'
    full_content = _format_full_content(question_text, alternatives)
    chunks.append(_build_chunk("full", full_content, question_id, metadata))

    # Chunk 'context' — somente se context_text não for vazio
    if context_text is not None and context_text.strip():
        chunks.append(_build_chunk("context", context_text, question_id, metadata))

    return chunks


def build_chunks_from_db_row(row: Dict[str, Any]) -> List[ChunkData]:
    """
    Converte um dict com dados de uma questão (resultado de query SQLAlchemy)
    em lista de ChunkData.

    row deve ter:
      - 'question_text' (str)
      - 'alternatives'  (list[str] | list[dict])
      - 'context_text'  (str | None)
      - 'id'            (str UUID)
      - 'subject'       (str | None)
      - 'year'          (int | None)
      - 'question_number' (int | None)
      - 'has_images'    (bool)
    """
    alternatives_raw: List[Any] = row.get("alternatives") or []
    metadata: Dict[str, Any] = {
        "year": row.get("year"),
        "subject": row.get("subject"),
        "question_number": row.get("question_number"),
        "has_images": row.get("has_images", False),
    }

    return build_chunks(
        question_text=row.get("question_text", ""),
        alternatives=alternatives_raw,
        context_text=row.get("context_text"),
        question_id=str(row["id"]) if row.get("id") is not None else None,
        metadata=metadata,
    )
