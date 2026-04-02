"""
pgvector_writer.py — Persistência de chunks e embeddings no PostgreSQL/pgvector.

Insere ChunkData + embeddings na tabela question_chunks via ON CONFLICT idempotente
e atualiza embedding_status na tabela questions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.enem_ingestion.chunk_builder import ChunkData
from src.enem_ingestion.embedding_generator import EmbeddingResult

logger = logging.getLogger(__name__)

_INSERT_CHUNK_SQL = text("""
    INSERT INTO enem_questions.question_chunks
        (question_id, chunk_type, content, content_hash, embedding, token_count)
    VALUES (:qid, :ctype, :content, :hash, CAST(:emb AS vector), :tokens)
    ON CONFLICT (content_hash) DO UPDATE
        SET updated_at = NOW()
""")

_UPDATE_STATUS_SQL = text("""
    UPDATE enem_questions.questions
    SET embedding_status = :status
    WHERE id = ANY(CAST(:ids AS uuid[]))
""")


@dataclass
class WriteResult:
    question_id: Optional[str]  # question_id do chunk; None se não definido
    chunk_hash: str              # content_hash do chunk
    success: bool
    error: Optional[str] = None


class PgvectorWriter:
    """
    Persiste chunks e embeddings no pgvector.

    Uso típico:
        writer = PgvectorWriter(database_url=os.environ["DATABASE_URL"])
        results = writer.write_batch(chunks, embeddings)
    """

    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, echo=False)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def write_chunks(
        self, chunks: List[ChunkData], embeddings: List[EmbeddingResult]
    ) -> List[WriteResult]:
        """
        Insere cada (chunk, embedding) individualmente com try/except.

        - Usa ON CONFLICT (content_hash) para idempotência
        - Falha em um chunk NÃO interrompe os demais
        - Retorna WriteResult para cada chunk na ordem de entrada
        """
        emb_map: dict[str, EmbeddingResult] = {e.content_hash: e for e in embeddings}
        results: List[WriteResult] = []

        for chunk in chunks:
            embedding = emb_map.get(chunk.content_hash)
            if embedding is None:
                logger.warning(
                    "Embedding ausente para chunk question_id=%s hash=%s — pulando",
                    chunk.question_id,
                    chunk.content_hash[:12],
                )
                results.append(WriteResult(
                    question_id=chunk.question_id,
                    chunk_hash=chunk.content_hash,
                    success=False,
                    error="Embedding não encontrado para este chunk",
                ))
                continue

            try:
                emb_str = "[" + ",".join(map(str, embedding.embedding)) + "]"
                params = {
                    "qid": chunk.question_id,
                    "ctype": chunk.chunk_type,
                    "content": chunk.content,
                    "hash": chunk.content_hash,
                    "emb": emb_str,
                    "tokens": chunk.token_count,
                }
                with Session(self._engine) as session:
                    session.execute(_INSERT_CHUNK_SQL, params)
                    session.commit()

                logger.debug(
                    "chunk inserido: question_id=%s hash=%s",
                    chunk.question_id,
                    chunk.content_hash[:12],
                )
                results.append(WriteResult(
                    question_id=chunk.question_id,
                    chunk_hash=chunk.content_hash,
                    success=True,
                ))

            except Exception as exc:
                logger.error(
                    "Erro ao inserir chunk question_id=%s hash=%s: %s",
                    chunk.question_id,
                    chunk.content_hash[:12],
                    exc,
                )
                results.append(WriteResult(
                    question_id=chunk.question_id,
                    chunk_hash=chunk.content_hash,
                    success=False,
                    error=str(exc),
                ))

        return results

    def update_embedding_status(
        self, question_ids: List[str], status: str = "done"
    ) -> None:
        """
        Atualiza embedding_status em enem_questions.questions para todos
        os question_ids fornecidos em uma única query batch.
        """
        if not question_ids:
            return

        with Session(self._engine) as session:
            session.execute(
                _UPDATE_STATUS_SQL,
                {"status": status, "ids": question_ids},
            )
            session.commit()

        logger.info(
            "embedding_status='%s' atualizado para %d questão(ões)",
            status,
            len(question_ids),
        )

    def write_batch(
        self, chunks: List[ChunkData], embeddings: List[EmbeddingResult]
    ) -> List[WriteResult]:
        """
        Orquestra write_chunks + update_embedding_status.

        Atualiza embedding_status='done' apenas para question_ids
        que tiveram ao menos um chunk inserido com sucesso.
        """
        results = self.write_chunks(chunks, embeddings)

        successful_question_ids = list({
            r.question_id
            for r in results
            if r.success and r.question_id is not None
        })

        if successful_question_ids:
            self.update_embedding_status(successful_question_ids, status="done")

        return results
