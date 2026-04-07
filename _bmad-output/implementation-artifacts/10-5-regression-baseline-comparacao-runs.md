# Story 10.5: Regression Baseline + Comparação entre Runs

Status: ready-for-dev

## Story

Como desenvolvedor,
Quero um baseline de scores salvo e comparação automática entre rodadas de avaliação,
Para que eu detecte regressões de qualidade ao fazer mudanças no pipeline RAG.

## Acceptance Criteria (AC)

1. `--save-baseline` flag salva scores em `tests/fixtures/eval_baseline.json` com timestamp e provider
2. Nova avaliação com baseline existente inclui coluna "Delta vs Baseline" para cada métrica
3. Métricas que caíram > 5% destacadas como WARNING no relatório
4. Métricas que caíram > 15% destacadas como CRITICAL no relatório
5. Testes pytest em `tests/test_rag_evaluation.py` falham se métrica abaixo do threshold mínimo do baseline
6. Baseline JSON contém thresholds mínimos por métrica

## Tasks / Subtasks

- [ ] Task 1: Implementar baseline save/load (AC: 1, 6)
  - [ ] 1.1 Criar `src/rag_evaluation/baseline.py`:
    ```python
    """Baseline management for regression detection."""
    import json
    from datetime import datetime
    from pathlib import Path

    BASELINE_PATH = Path("tests/fixtures/eval_baseline.json")

    def save_baseline(retrieval_results: dict, generation_results: dict, provider: str) -> Path:
        baseline = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "version": "1.0",
            "retrieval": {
                mode: results["aggregate"]
                for mode, results in retrieval_results.items()
            },
            "generation": {
                "faithfulness": generation_results["faithfulness_aggregate"],
                "enem_geval": generation_results["enem_geval_aggregate"],
            },
            "thresholds": _compute_thresholds(retrieval_results, generation_results),
        }
        BASELINE_PATH.write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")
        return BASELINE_PATH

    def load_baseline() -> dict | None:
        if not BASELINE_PATH.exists():
            return None
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    def _compute_thresholds(retrieval_results, generation_results) -> dict:
        """Set minimum thresholds at 85% of current scores (15% CRITICAL margin)."""
        thresholds = {}
        hybrid = retrieval_results.get("hybrid", {}).get("aggregate", {})
        for metric in ["precision_at_k", "recall_at_k", "mrr", "hit_rate"]:
            if metric in hybrid:
                thresholds[f"retrieval_{metric}"] = round(hybrid[metric]["mean"] * 0.85, 4)
        gen = generation_results
        thresholds["faithfulness"] = round(gen.get("faithfulness_aggregate", {}).get("mean", 0) * 0.85, 4)
        thresholds["enem_geval"] = round(gen.get("enem_geval_aggregate", {}).get("mean", 0) * 0.85, 4)
        return thresholds
    ```

- [ ] Task 2: Implementar comparação delta (AC: 2, 3, 4)
  - [ ] 2.1 Criar `src/rag_evaluation/regression.py`:
    ```python
    """Regression detection: compare current scores vs baseline."""
    from dataclasses import dataclass

    @dataclass
    class MetricDelta:
        metric_name: str
        baseline_value: float
        current_value: float
        delta: float
        delta_pct: float
        status: str  # "OK", "WARNING", "CRITICAL"

    def compare_with_baseline(current: dict, baseline: dict) -> list[MetricDelta]:
        """Compare current evaluation results with saved baseline."""
        deltas = []
        for metric, current_val in _flatten_metrics(current).items():
            baseline_val = _get_baseline_value(baseline, metric)
            if baseline_val is None:
                continue
            delta = current_val - baseline_val
            delta_pct = (delta / baseline_val * 100) if baseline_val != 0 else 0
            status = "OK"
            if delta_pct < -15:
                status = "CRITICAL"
            elif delta_pct < -5:
                status = "WARNING"
            deltas.append(MetricDelta(
                metric_name=metric,
                baseline_value=baseline_val,
                current_value=current_val,
                delta=delta,
                delta_pct=delta_pct,
                status=status,
            ))
        return deltas
    ```
  - [ ] 2.2 Integrar deltas no `report_generator.py` — adicionar seção "Delta vs Baseline" com tabela

- [ ] Task 3: Report delta section (AC: 2, 3, 4)
  - [ ] 3.1 Atualizar `report_generator.py` com seção de regressão:
    ```markdown
    ## Regression Analysis (vs Baseline 2026-04-06)

    | Metric | Baseline | Current | Delta | Status |
    |--------|----------|---------|-------|--------|
    | Precision@5 (hybrid) | 0.72 | 0.70 | -2.8% | OK |
    | Recall@5 (hybrid) | 0.68 | 0.55 | -19.1% | **CRITICAL** |
    | MRR (hybrid) | 0.65 | 0.62 | -4.6% | OK |
    | Faithfulness | 0.82 | 0.78 | -4.9% | OK |
    | ENEM G-Eval | 0.68 | 0.60 | -11.8% | **WARNING** |
    ```

- [ ] Task 4: Testes pytest com baseline thresholds (AC: 5)
  - [ ] 4.1 Criar `tests/test_rag_evaluation.py`:
    ```python
    """RAG evaluation regression tests."""
    import pytest
    from src.rag_evaluation.baseline import load_baseline

    pytestmark = [pytest.mark.eval]

    @pytest.fixture(scope="session")
    def baseline():
        b = load_baseline()
        if b is None:
            pytest.skip("No baseline found — run with --save-baseline first")
        return b

    class TestRetrievalRegression:
        def test_precision_above_threshold(self, baseline, retrieval_results):
            threshold = baseline["thresholds"]["retrieval_precision_at_k"]
            actual = retrieval_results["hybrid"]["aggregate"]["precision_at_k"]["mean"]
            assert actual >= threshold, f"Precision@K {actual:.4f} below threshold {threshold:.4f}"

        def test_recall_above_threshold(self, baseline, retrieval_results):
            ...

        def test_mrr_above_threshold(self, baseline, retrieval_results):
            ...

    class TestGenerationRegression:
        def test_faithfulness_above_threshold(self, baseline, generation_results):
            ...

        def test_enem_geval_above_threshold(self, baseline, generation_results):
            ...
    ```
  - [ ] 4.2 Executar: `pytest tests/test_rag_evaluation.py -m eval` — falha se abaixo dos thresholds

- [ ] Task 5: Integrar no pipeline script (AC: 1, 2)
  - [ ] 5.1 No `scripts/run_rag_evaluation.py`:
    - Se `--save-baseline`: salvar após avaliação completa
    - Se baseline existe: carregar e incluir deltas no relatório
  - [ ] 5.2 Print resumo no terminal: "Baseline saved to tests/fixtures/eval_baseline.json"
  - [ ] 5.3 Print warnings/criticals em vermelho no terminal

## Dev Notes

### Baseline JSON Structure
```json
{
  "timestamp": "2026-04-06T14:30:00",
  "provider": "ollama",
  "version": "1.0",
  "retrieval": {
    "hybrid": {
      "precision_at_k": {"mean": 0.72, "stdev": 0.12},
      "recall_at_k": {"mean": 0.68, "stdev": 0.16},
      "mrr": {"mean": 0.65, "stdev": 0.20},
      "hit_rate": {"mean": 0.87, "stdev": 0.10}
    }
  },
  "generation": {
    "faithfulness": {"mean": 0.82, "stdev": 0.10},
    "enem_geval": {"mean": 0.68, "stdev": 0.15}
  },
  "thresholds": {
    "retrieval_precision_at_k": 0.612,
    "retrieval_recall_at_k": 0.578,
    "retrieval_mrr": 0.5525,
    "faithfulness": 0.697,
    "enem_geval": 0.578
  }
}
```

### Regression Thresholds Strategy
- WARNING: > 5% drop — investigate but not blocking
- CRITICAL: > 15% drop — blocking, likely a regression in RAG pipeline
- Thresholds stored in baseline at 85% of current scores (auto-computed on save)
- Can be manually overridden in the JSON

### Dependencies on Previous Stories
- **Story 10.2:** RetrievalEvaluator results format
- **Story 10.3:** GenerationEvaluator results format
- **Story 10.4:** Pipeline script, report generator

### References

- [Research: technical-rag-llm-evaluation-pipeline-research-2026-04-06.md] — Regression testing pattern
- [Source: tests/test_golden_set.py] — Existing pytest patterns with thresholds
