#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assessment Generator — Story 4.1
Generates ENEM practice assessments by selecting real questions
via semantic search + filters, persisting results to DB.
"""

import asyncio
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class InsufficientQuestionsError(Exception):
    """Raised when not enough questions match the requested filters."""
    pass


class AssessmentGenerator:
    def __init__(
        self,
        database_url: str,
        pgvector_search,
    ) -> None:
        self.engine: Engine = create_engine(database_url)
        self.pgvector_search = pgvector_search

    async def generate(
        self,
        subject: str,
        difficulty: str = "mixed",
        question_count: int = 10,
        years: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        assessment_id = str(uuid.uuid4())

        # 1. Select candidate questions (fetch more than needed for filtering)
        candidates = await self._select_questions(subject, question_count * 3, years)

        # 2. Take top-N by similarity score
        selected = candidates[:question_count]

        if len(selected) < question_count:
            raise InsufficientQuestionsError(
                f"Apenas {len(selected)} questoes encontradas para os filtros "
                f"(subject={subject}, difficulty={difficulty}, years={years}). "
                f"Solicitadas: {question_count}."
            )

        # 3. Build answer key — single batch query
        answer_key, answers_missing = await asyncio.to_thread(
            self._build_answer_key_batch, selected
        )

        # 4. Persist
        question_ids = [q["question_id"] for q in selected]
        title = f"Avaliacao {subject.replace('_', ' ').title()} — {difficulty}"
        await self._persist_assessment(
            assessment_id, title, subject, difficulty, question_count, years, question_ids
        )

        return {
            "assessment_id": assessment_id,
            "title": title,
            "questions": selected,
            "answer_key": answer_key,
            "answers_missing": answers_missing,
        }

    async def _select_questions(
        self,
        subject: str,
        max_candidates: int,
        years: Optional[List[int]],
    ) -> List[Dict[str, Any]]:
        fetch_limit = max_candidates * max(len(years), 1) if years else max_candidates
        query_text = f"questoes de {subject.replace('_', ' ')}"
        raw_results = await self.pgvector_search.search_questions(
            query=query_text,
            limit=fetch_limit,
            subject=subject,
        )

        if years:
            raw_results = [r for r in raw_results if r.get("year") in years]

        seen_ids: set = set()
        unique_results = []
        for r in raw_results:
            qid = r["question_id"]
            if qid not in seen_ids:
                seen_ids.add(qid)
                unique_results.append(r)

        return unique_results

    def _build_answer_key_batch(
        self, questions: List[Dict[str, Any]]
    ) -> Tuple[Dict[int, str], List[int]]:
        """Fetches all correct answers in a single SQL query (no N+1)."""
        if not questions:
            return {}, []

        question_ids = [q["question_id"] for q in questions]
        sql = text("""
            SELECT q.id AS question_id, ak.correct_answer
            FROM enem_questions.answer_keys ak
            JOIN enem_questions.exam_metadata em ON em.id = ak.exam_id
            JOIN enem_questions.questions q ON q.exam_metadata_id = em.id
                AND q.question_number = ak.question_number
            WHERE q.id = ANY(:question_ids)
        """)
        with self.engine.connect() as conn:
            rows = conn.execute(sql, {"question_ids": question_ids}).fetchall()

        answer_map = {row[0]: row[1] for row in rows}

        answer_key: Dict[int, str] = {}
        answers_missing: List[int] = []
        for order, q in enumerate(questions, start=1):
            answer = answer_map.get(q["question_id"])
            if answer:
                answer_key[order] = answer
            else:
                answers_missing.append(order)

        return answer_key, answers_missing

    def _sync_persist_assessment(
        self,
        assessment_id: str,
        title: str,
        subject: str,
        difficulty: str,
        question_count: int,
        years: Optional[List[int]],
        question_ids: List[int],
    ) -> None:
        insert_assessment = text("""
            INSERT INTO enem_questions.assessments
                (id, title, subject, difficulty, question_count, years_filter)
            VALUES
                (CAST(:id AS UUID), :title, :subject, :difficulty, :question_count, :years_filter)
        """)
        insert_question = text("""
            INSERT INTO enem_questions.assessment_questions
                (assessment_id, question_id, question_order)
            VALUES
                (CAST(:assessment_id AS UUID), :question_id, :question_order)
        """)
        with self.engine.begin() as conn:
            conn.execute(insert_assessment, {
                "id": assessment_id,
                "title": title,
                "subject": subject,
                "difficulty": difficulty,
                "question_count": question_count,
                "years_filter": years or [],
            })
            for order, qid in enumerate(question_ids, start=1):
                conn.execute(insert_question, {
                    "assessment_id": assessment_id,
                    "question_id": qid,
                    "question_order": order,
                })
        logger.info("assessment_persisted", extra={
            "assessment_id": assessment_id,
            "question_count": len(question_ids),
            "subject": subject,
        })

    async def _persist_assessment(
        self,
        assessment_id: str,
        title: str,
        subject: str,
        difficulty: str,
        question_count: int,
        years: Optional[List[int]],
        question_ids: List[int],
    ) -> None:
        await asyncio.to_thread(
            self._sync_persist_assessment,
            assessment_id, title, subject, difficulty, question_count, years, question_ids,
        )
