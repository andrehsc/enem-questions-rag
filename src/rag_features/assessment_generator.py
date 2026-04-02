#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assessment Generator — Story 4.1
Generates ENEM practice assessments by selecting real questions
via semantic search + filters, with difficulty distribution.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

DIFFICULTY_DISTRIBUTION = {
    "mixed": {"easy": 0.30, "medium": 0.40, "hard": 0.30},
    "easy": {"easy": 1.0},
    "medium": {"medium": 1.0},
    "hard": {"hard": 1.0},
}


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
        candidates = await self._select_questions(subject, difficulty, question_count * 3, years)

        # 2. Distribute by difficulty and limit
        selected = self._distribute_by_difficulty(candidates, difficulty, question_count)

        if len(selected) < question_count:
            raise InsufficientQuestionsError(
                f"Apenas {len(selected)} questoes encontradas para os filtros "
                f"(subject={subject}, difficulty={difficulty}, years={years}). "
                f"Solicitadas: {question_count}."
            )

        # 3. Build answer key
        answer_key = self._build_answer_key(selected)

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
        }

    async def _select_questions(
        self,
        subject: str,
        difficulty: str,
        max_candidates: int,
        years: Optional[List[int]],
    ) -> List[Dict[str, Any]]:
        query_text = f"questoes de {subject.replace('_', ' ')}"
        raw_results = await self.pgvector_search.search_questions(
            query=query_text,
            limit=max_candidates,
            subject=subject,
        )

        if years:
            raw_results = [r for r in raw_results if r.get("year") in years]

        seen_ids = set()
        unique_results = []
        for r in raw_results:
            qid = r["question_id"]
            if qid not in seen_ids:
                seen_ids.add(qid)
                unique_results.append(r)

        return unique_results

    def _distribute_by_difficulty(
        self,
        candidates: List[Dict[str, Any]],
        difficulty: str,
        count: int,
    ) -> List[Dict[str, Any]]:
        distribution = DIFFICULTY_DISTRIBUTION.get(difficulty, DIFFICULTY_DISTRIBUTION["mixed"])

        if difficulty != "mixed":
            return candidates[:count]

        # Mixed: group by difficulty level
        selected = []
        for diff_level, ratio in distribution.items():
            target = round(count * ratio)
            level_questions = [q for q in candidates if q.get("difficulty", "medium") == diff_level]
            selected.extend(level_questions[:target])

        # Fill remaining from other candidates
        selected_ids = {q["question_id"] for q in selected}
        for q in candidates:
            if len(selected) >= count:
                break
            if q["question_id"] not in selected_ids:
                selected.append(q)
                selected_ids.add(q["question_id"])

        return selected[:count]

    def _build_answer_key(self, questions: List[Dict[str, Any]]) -> Dict[int, str]:
        answer_key = {}
        for order, q in enumerate(questions, start=1):
            correct = self._get_correct_answer(q["question_id"])
            if correct:
                answer_key[order] = correct
        return answer_key

    def _get_correct_answer(self, question_id: int) -> Optional[str]:
        sql = text("""
            SELECT ak.correct_answer
            FROM enem_questions.answer_keys ak
            JOIN enem_questions.exam_metadata em ON em.id = ak.exam_id
            JOIN enem_questions.questions q ON q.exam_metadata_id = em.id
                AND q.question_number = ak.question_number
            WHERE q.id = :question_id
            LIMIT 1
        """)
        with self.engine.connect() as conn:
            row = conn.execute(sql, {"question_id": question_id}).fetchone()
            return row[0] if row else None

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
