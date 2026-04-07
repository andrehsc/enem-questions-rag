"""Generation evaluator: assesses RAG-generated ENEM questions.

Uses DeepEval FaithfulnessMetric and custom G-Eval ENEM rubric
to evaluate quality of generated questions.
"""

import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class GenerationResult:
    """Result for a single generation evaluation."""

    def __init__(
        self,
        ref_id: str,
        input_topic: str,
        faithfulness_score: Optional[float] = None,
        faithfulness_reason: Optional[str] = None,
        enem_geval_score: Optional[float] = None,
        enem_geval_reason: Optional[str] = None,
    ):
        self.ref_id = ref_id
        self.input_topic = input_topic
        self.faithfulness_score = faithfulness_score
        self.faithfulness_reason = faithfulness_reason
        self.enem_geval_score = enem_geval_score
        self.enem_geval_reason = enem_geval_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ref_id": self.ref_id,
            "input_topic": self.input_topic,
            "faithfulness_score": self.faithfulness_score,
            "faithfulness_reason": self.faithfulness_reason,
            "enem_geval_score": self.enem_geval_score,
            "enem_geval_reason": self.enem_geval_reason,
        }


class GenerationEvaluator:
    """Evaluates RAG question generation quality."""

    def __init__(
        self,
        eval_llm,
        faithfulness_threshold: float = 0.7,
        geval_threshold: float = 0.5,
    ):
        self.eval_llm = eval_llm
        self.faithfulness_threshold = faithfulness_threshold
        self.geval_threshold = geval_threshold
        self._faithfulness_metric = None
        self._enem_geval_metric = None

    def _get_faithfulness(self):
        """Lazy-init FaithfulnessMetric."""
        if self._faithfulness_metric is None:
            from deepeval.metrics import FaithfulnessMetric

            self._faithfulness_metric = FaithfulnessMetric(
                threshold=self.faithfulness_threshold,
                model=self.eval_llm,
                include_reason=True,
            )
        return self._faithfulness_metric

    def _get_enem_geval(self):
        """Lazy-init G-Eval ENEM metric."""
        if self._enem_geval_metric is None:
            from src.rag_evaluation.enem_rubric import create_enem_geval

            self._enem_geval_metric = create_enem_geval(self.eval_llm)
        return self._enem_geval_metric

    def evaluate_question(
        self,
        input_topic: str,
        generated_question: str,
        retrieval_context: Optional[List[str]] = None,
        ref_id: str = "",
    ) -> GenerationResult:
        """Evaluate a single generated question.

        Args:
            input_topic: The topic/prompt that generated the question.
            generated_question: The full text of the generated question.
            retrieval_context: Chunks used as context for generation.
            ref_id: Reference ID for tracking.

        Returns:
            GenerationResult with scores and reasons.
        """
        from deepeval.test_case import LLMTestCase

        result = GenerationResult(ref_id=ref_id, input_topic=input_topic)

        test_case = LLMTestCase(
            input=input_topic,
            actual_output=generated_question,
            retrieval_context=retrieval_context or [],
        )

        # Faithfulness (requires retrieval_context)
        if retrieval_context:
            try:
                faithfulness = self._get_faithfulness()
                faithfulness.measure(test_case)
                result.faithfulness_score = faithfulness.score
                result.faithfulness_reason = faithfulness.reason
            except Exception as e:
                result.faithfulness_reason = f"Error: {e}"

        # G-Eval ENEM (always applicable)
        try:
            geval = self._get_enem_geval()
            geval.measure(test_case)
            result.enem_geval_score = geval.score
            result.enem_geval_reason = geval.reason
        except Exception as e:
            result.enem_geval_reason = f"Error: {e}"

        return result

    def evaluate_batch(
        self,
        generation_references: List[Dict[str, Any]],
        golden_questions: Optional[Dict[str, Dict]] = None,
    ) -> Dict[str, Any]:
        """Evaluate all generation references from golden eval dataset.

        Args:
            generation_references: List from golden_eval_dataset.json.
            golden_questions: Optional map of gs-ID → question dict for retrieving text.

        Returns:
            Dict with results list and aggregate stats.
        """
        results = []
        for ref in generation_references:
            # Get the question text from golden set if available
            question_text = ""
            if golden_questions and ref.get("source_question_id"):
                q = golden_questions.get(ref["source_question_id"], {})
                question_text = q.get("question_text", "")

            if not question_text:
                question_text = f"[Generated question about {ref['input_topic']}]"

            result = self.evaluate_question(
                input_topic=ref["input_topic"],
                generated_question=question_text,
                retrieval_context=ref.get("source_contexts", []),
                ref_id=ref["id"],
            )
            results.append(result)

        return self._build_summary(results)

    def _build_summary(self, results: List[GenerationResult]) -> Dict[str, Any]:
        """Build summary statistics from evaluation results."""
        summary: Dict[str, Any] = {
            "results": [r.to_dict() for r in results],
            "count": len(results),
        }

        # Faithfulness aggregate
        faith_scores = [
            r.faithfulness_score
            for r in results
            if r.faithfulness_score is not None
        ]
        if faith_scores:
            summary["faithfulness_aggregate"] = {
                "mean": round(statistics.mean(faith_scores), 4),
                "stdev": round(statistics.stdev(faith_scores), 4)
                if len(faith_scores) > 1
                else 0.0,
                "min": round(min(faith_scores), 4),
                "max": round(max(faith_scores), 4),
                "count": len(faith_scores),
            }

        # G-Eval ENEM aggregate
        geval_scores = [
            r.enem_geval_score
            for r in results
            if r.enem_geval_score is not None
        ]
        if geval_scores:
            summary["enem_geval_aggregate"] = {
                "mean": round(statistics.mean(geval_scores), 4),
                "stdev": round(statistics.stdev(geval_scores), 4)
                if len(geval_scores) > 1
                else 0.0,
                "min": round(min(geval_scores), 4),
                "max": round(max(geval_scores), 4),
                "count": len(geval_scores),
            }

        # Worst cases (lowest combined score)
        scored = [
            r
            for r in results
            if r.enem_geval_score is not None
        ]
        scored.sort(key=lambda r: r.enem_geval_score or 0)
        summary["worst_cases"] = [r.to_dict() for r in scored[:5]]

        return summary

    def save_results(
        self,
        results: Dict[str, Any],
        output_dir: str = "reports",
        provider: str = "ollama",
    ) -> Path:
        """Save generation evaluation results to JSON."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = output_path / f"generation_eval_{date_str}.json"

        output = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            **results,
        }

        filepath.write_text(
            json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return filepath
