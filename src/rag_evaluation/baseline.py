"""Baseline management and regression detection for RAG evaluation.

Saves evaluation scores as baseline, computes deltas on subsequent runs,
and flags regressions at WARNING (>5% drop) and CRITICAL (>15% drop) levels.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

BASELINE_PATH = Path("tests/fixtures/eval_baseline.json")


@dataclass
class MetricDelta:
    """Comparison between current and baseline metric values."""

    metric_name: str
    baseline_value: float
    current_value: float
    delta: float
    delta_pct: float
    status: str  # "OK", "WARNING", "CRITICAL"


def save_baseline(
    retrieval_results: Dict[str, Any],
    generation_results: Dict[str, Any],
    provider: str,
    path: Optional[Path] = None,
) -> Path:
    """Save current evaluation scores as regression baseline.

    Args:
        retrieval_results: Output from RetrievalEvaluator.evaluate()
        generation_results: Output from GenerationEvaluator.evaluate_batch()
        provider: LLM provider used for evaluation
        path: Override for baseline file path

    Returns:
        Path to saved baseline file.
    """
    filepath = path or BASELINE_PATH

    baseline = {
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "version": "1.0",
        "retrieval": {},
        "generation": {},
        "thresholds": {},
    }

    # Extract retrieval aggregates per mode
    for mode in ["semantic", "text", "hybrid"]:
        if mode in retrieval_results:
            baseline["retrieval"][mode] = retrieval_results[mode].get("aggregate", {})

    # Extract generation aggregates
    for key in ["faithfulness_aggregate", "enem_geval_aggregate"]:
        if key in generation_results:
            baseline["generation"][key] = generation_results[key]

    # Compute thresholds at 85% of current scores (15% = CRITICAL margin)
    baseline["thresholds"] = _compute_thresholds(retrieval_results, generation_results)

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return filepath


def load_baseline(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load saved baseline. Returns None if no baseline exists."""
    filepath = path or BASELINE_PATH
    if not filepath.exists():
        return None
    return json.loads(filepath.read_text(encoding="utf-8"))


def compare_with_baseline(
    retrieval_results: Dict[str, Any],
    generation_results: Dict[str, Any],
    baseline: Dict[str, Any],
) -> List[MetricDelta]:
    """Compare current evaluation results with saved baseline.

    Args:
        retrieval_results: Current retrieval evaluation results
        generation_results: Current generation evaluation results
        baseline: Previously saved baseline

    Returns:
        List of MetricDelta objects with status flags.
    """
    deltas = []

    # Compare retrieval metrics (hybrid mode)
    for metric in ["precision_at_k", "recall_at_k", "mrr", "hit_rate"]:
        current_val = (
            retrieval_results.get("hybrid", {})
            .get("aggregate", {})
            .get(metric, {})
            .get("mean", 0)
        )
        baseline_val = (
            baseline.get("retrieval", {})
            .get("hybrid", {})
            .get(metric, {})
            .get("mean", 0)
        )
        if baseline_val > 0:
            deltas.append(_make_delta(f"retrieval_{metric}", baseline_val, current_val))

    # Compare generation metrics
    gen_metrics = {
        "faithfulness": "faithfulness_aggregate",
        "enem_geval": "enem_geval_aggregate",
    }
    for name, key in gen_metrics.items():
        current_val = generation_results.get(key, {}).get("mean", 0)
        baseline_val = baseline.get("generation", {}).get(key, {}).get("mean", 0)
        if baseline_val > 0:
            deltas.append(_make_delta(name, baseline_val, current_val))

    return deltas


def check_thresholds(
    retrieval_results: Dict[str, Any],
    generation_results: Dict[str, Any],
    baseline: Dict[str, Any],
) -> List[MetricDelta]:
    """Check if current metrics meet baseline thresholds.

    Returns only metrics that are BELOW their threshold.
    """
    thresholds = baseline.get("thresholds", {})
    violations = []

    # Check retrieval thresholds
    for metric in ["precision_at_k", "recall_at_k", "mrr", "hit_rate"]:
        threshold_key = f"retrieval_{metric}"
        threshold = thresholds.get(threshold_key, 0)
        if threshold <= 0:
            continue

        current = (
            retrieval_results.get("hybrid", {})
            .get("aggregate", {})
            .get(metric, {})
            .get("mean", 0)
        )
        if current < threshold:
            violations.append(
                _make_delta(threshold_key, threshold, current)
            )

    # Check generation thresholds
    gen_checks = {
        "faithfulness": "faithfulness_aggregate",
        "enem_geval": "enem_geval_aggregate",
    }
    for name, key in gen_checks.items():
        threshold = thresholds.get(name, 0)
        if threshold <= 0:
            continue
        current = generation_results.get(key, {}).get("mean", 0)
        if current < threshold:
            violations.append(_make_delta(name, threshold, current))

    return violations


def _make_delta(name: str, baseline_val: float, current_val: float) -> MetricDelta:
    """Create a MetricDelta with appropriate status."""
    delta = current_val - baseline_val
    delta_pct = (delta / baseline_val * 100) if baseline_val != 0 else 0

    if delta_pct < -15:
        status = "CRITICAL"
    elif delta_pct < -5:
        status = "WARNING"
    else:
        status = "OK"

    return MetricDelta(
        metric_name=name,
        baseline_value=round(baseline_val, 4),
        current_value=round(current_val, 4),
        delta=round(delta, 4),
        delta_pct=round(delta_pct, 2),
        status=status,
    )


def _compute_thresholds(
    retrieval_results: Dict[str, Any],
    generation_results: Dict[str, Any],
) -> Dict[str, float]:
    """Set minimum thresholds at 85% of current scores."""
    thresholds = {}

    hybrid = retrieval_results.get("hybrid", {}).get("aggregate", {})
    for metric in ["precision_at_k", "recall_at_k", "mrr", "hit_rate"]:
        mean = hybrid.get(metric, {}).get("mean", 0)
        if mean > 0:
            thresholds[f"retrieval_{metric}"] = round(mean * 0.85, 4)

    gen_metrics = {
        "faithfulness": "faithfulness_aggregate",
        "enem_geval": "enem_geval_aggregate",
    }
    for name, key in gen_metrics.items():
        mean = generation_results.get(key, {}).get("mean", 0)
        if mean > 0:
            thresholds[name] = round(mean * 0.85, 4)

    return thresholds
