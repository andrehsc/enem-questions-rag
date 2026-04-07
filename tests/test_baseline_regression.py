"""Tests for baseline management and regression detection."""

import json

import pytest

from src.rag_evaluation.baseline import (
    MetricDelta,
    _compute_thresholds,
    _make_delta,
    check_thresholds,
    compare_with_baseline,
    load_baseline,
    save_baseline,
)


@pytest.fixture
def sample_retrieval():
    return {
        "hybrid": {
            "aggregate": {
                "precision_at_k": {"mean": 0.72, "stdev": 0.12, "min": 0.4, "max": 1.0},
                "recall_at_k": {"mean": 0.68, "stdev": 0.16, "min": 0.3, "max": 1.0},
                "mrr": {"mean": 0.65, "stdev": 0.20, "min": 0.0, "max": 1.0},
                "hit_rate": {"mean": 0.87, "stdev": 0.10, "min": 0.0, "max": 1.0},
            }
        },
        "semantic": {"aggregate": {}},
        "text": {"aggregate": {}},
        "_best_mode": "hybrid",
    }


@pytest.fixture
def sample_generation():
    return {
        "faithfulness_aggregate": {"mean": 0.82, "stdev": 0.10, "min": 0.65, "max": 0.95},
        "enem_geval_aggregate": {"mean": 0.68, "stdev": 0.15, "min": 0.40, "max": 0.90},
    }


class TestMakeDelta:
    def test_ok_status(self):
        d = _make_delta("test", 0.80, 0.78)
        assert d.status == "OK"
        assert d.delta_pct == pytest.approx(-2.5, abs=0.1)

    def test_warning_status(self):
        d = _make_delta("test", 0.80, 0.72)
        assert d.status == "WARNING"
        assert d.delta_pct == pytest.approx(-10.0, abs=0.1)

    def test_critical_status(self):
        d = _make_delta("test", 0.80, 0.60)
        assert d.status == "CRITICAL"
        assert d.delta_pct == pytest.approx(-25.0, abs=0.1)

    def test_improvement_is_ok(self):
        d = _make_delta("test", 0.60, 0.80)
        assert d.status == "OK"
        assert d.delta_pct > 0

    def test_zero_baseline(self):
        d = _make_delta("test", 0.0, 0.5)
        assert d.status == "OK"
        assert d.delta_pct == 0


class TestComputeThresholds:
    def test_thresholds_at_85_percent(self, sample_retrieval, sample_generation):
        thresholds = _compute_thresholds(sample_retrieval, sample_generation)
        assert thresholds["retrieval_precision_at_k"] == pytest.approx(0.72 * 0.85, abs=0.001)
        assert thresholds["retrieval_mrr"] == pytest.approx(0.65 * 0.85, abs=0.001)
        assert thresholds["faithfulness"] == pytest.approx(0.82 * 0.85, abs=0.001)
        assert thresholds["enem_geval"] == pytest.approx(0.68 * 0.85, abs=0.001)

    def test_zero_metrics_excluded(self):
        thresholds = _compute_thresholds({"hybrid": {"aggregate": {}}}, {})
        assert len(thresholds) == 0


class TestSaveAndLoadBaseline:
    def test_save_and_load(self, sample_retrieval, sample_generation, tmp_path):
        filepath = tmp_path / "baseline.json"
        save_baseline(sample_retrieval, sample_generation, "ollama", path=filepath)

        loaded = load_baseline(path=filepath)
        assert loaded is not None
        assert loaded["provider"] == "ollama"
        assert "thresholds" in loaded
        assert "retrieval" in loaded
        assert "generation" in loaded

    def test_load_nonexistent(self, tmp_path):
        result = load_baseline(path=tmp_path / "nonexistent.json")
        assert result is None

    def test_baseline_has_hybrid_retrieval(self, sample_retrieval, sample_generation, tmp_path):
        filepath = tmp_path / "baseline.json"
        save_baseline(sample_retrieval, sample_generation, "ollama", path=filepath)
        loaded = load_baseline(path=filepath)
        assert "hybrid" in loaded["retrieval"]
        assert "precision_at_k" in loaded["retrieval"]["hybrid"]

    def test_baseline_has_generation(self, sample_retrieval, sample_generation, tmp_path):
        filepath = tmp_path / "baseline.json"
        save_baseline(sample_retrieval, sample_generation, "ollama", path=filepath)
        loaded = load_baseline(path=filepath)
        assert "faithfulness_aggregate" in loaded["generation"]
        assert "enem_geval_aggregate" in loaded["generation"]


class TestCompareWithBaseline:
    @pytest.fixture
    def baseline(self, sample_retrieval, sample_generation, tmp_path):
        filepath = tmp_path / "baseline.json"
        save_baseline(sample_retrieval, sample_generation, "ollama", path=filepath)
        return load_baseline(path=filepath)

    def test_no_regression(self, baseline, sample_retrieval, sample_generation):
        deltas = compare_with_baseline(sample_retrieval, sample_generation, baseline)
        assert all(d.status == "OK" for d in deltas)

    def test_detects_warning(self, baseline, sample_generation):
        # Drop MRR by 10%
        degraded = {
            "hybrid": {
                "aggregate": {
                    "precision_at_k": {"mean": 0.72},
                    "recall_at_k": {"mean": 0.68},
                    "mrr": {"mean": 0.55},  # was 0.65, -15.4% → still within WARNING
                    "hit_rate": {"mean": 0.87},
                }
            }
        }
        deltas = compare_with_baseline(degraded, sample_generation, baseline)
        mrr_delta = next(d for d in deltas if d.metric_name == "retrieval_mrr")
        assert mrr_delta.status in ["WARNING", "CRITICAL"]

    def test_detects_critical(self, baseline, sample_generation):
        # Drop precision by 30%
        degraded = {
            "hybrid": {
                "aggregate": {
                    "precision_at_k": {"mean": 0.50},  # was 0.72, -30.5% → CRITICAL
                    "recall_at_k": {"mean": 0.68},
                    "mrr": {"mean": 0.65},
                    "hit_rate": {"mean": 0.87},
                }
            }
        }
        deltas = compare_with_baseline(degraded, sample_generation, baseline)
        p_delta = next(d for d in deltas if d.metric_name == "retrieval_precision_at_k")
        assert p_delta.status == "CRITICAL"

    def test_gen_regression(self, baseline, sample_retrieval):
        degraded_gen = {
            "faithfulness_aggregate": {"mean": 0.50},  # was 0.82
            "enem_geval_aggregate": {"mean": 0.68},
        }
        deltas = compare_with_baseline(sample_retrieval, degraded_gen, baseline)
        faith_delta = next(d for d in deltas if d.metric_name == "faithfulness")
        assert faith_delta.status == "CRITICAL"


class TestCheckThresholds:
    @pytest.fixture
    def baseline(self, sample_retrieval, sample_generation, tmp_path):
        filepath = tmp_path / "baseline.json"
        save_baseline(sample_retrieval, sample_generation, "ollama", path=filepath)
        return load_baseline(path=filepath)

    def test_no_violations(self, baseline, sample_retrieval, sample_generation):
        violations = check_thresholds(sample_retrieval, sample_generation, baseline)
        assert len(violations) == 0

    def test_detects_violation(self, baseline, sample_generation):
        degraded = {
            "hybrid": {
                "aggregate": {
                    "precision_at_k": {"mean": 0.30},  # below 0.72*0.85=0.612
                    "recall_at_k": {"mean": 0.68},
                    "mrr": {"mean": 0.65},
                    "hit_rate": {"mean": 0.87},
                }
            }
        }
        violations = check_thresholds(degraded, sample_generation, baseline)
        assert len(violations) >= 1
        assert any(v.metric_name == "retrieval_precision_at_k" for v in violations)
