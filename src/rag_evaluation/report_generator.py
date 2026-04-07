"""Generate Markdown evaluation reports from retrieval and generation results."""

from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_markdown_report(
    retrieval_results: Dict[str, Any],
    generation_results: Dict[str, Any],
    config: Dict[str, Any],
    baseline_deltas: Optional[List] = None,
) -> str:
    """Generate a complete Markdown evaluation report.

    Args:
        retrieval_results: Output from RetrievalEvaluator.evaluate()
        generation_results: Output from GenerationEvaluator.evaluate_batch()
        config: Pipeline config (provider, k, etc.)
        baseline_deltas: Optional regression deltas from compare_with_baseline()

    Returns:
        Complete Markdown report as string.
    """
    sections = [
        _header(config),
        _executive_summary(retrieval_results, generation_results),
        _retrieval_scores_table(retrieval_results),
        _search_mode_comparison(retrieval_results),
        _generation_scores_table(generation_results),
        _worst_cases(retrieval_results, generation_results),
    ]

    if baseline_deltas:
        sections.append(_regression_section(baseline_deltas))

    sections.append(_recommendations(retrieval_results, generation_results))

    return "\n\n".join(sections)


def _header(config: Dict[str, Any]) -> str:
    date = config.get("date", datetime.now().strftime("%Y-%m-%d"))
    provider = config.get("provider", "ollama")
    k = config.get("k", 5)
    dataset_version = config.get("dataset_version", "1.0")

    return f"""# RAG Evaluation Report — {date}

**LLM Judge:** {provider}
**Dataset:** golden_eval_dataset.json v{dataset_version}
**K:** {k}
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""


def _executive_summary(
    retrieval_results: Dict[str, Any],
    generation_results: Dict[str, Any],
) -> str:
    lines = ["## Resumo Executivo"]

    # Get hybrid metrics (preferred mode)
    hybrid = retrieval_results.get("hybrid", {}).get("aggregate", {})
    mrr = hybrid.get("mrr", {}).get("mean", 0)
    precision = hybrid.get("precision_at_k", {}).get("mean", 0)
    hit = hybrid.get("hit_rate", {}).get("mean", 0)

    faith = generation_results.get("faithfulness_aggregate", {}).get("mean", 0)
    geval = generation_results.get("enem_geval_aggregate", {}).get("mean", 0)

    best_mode = retrieval_results.get("_best_mode", "hybrid")

    lines.append(f"- **Retrieval:** MRR={mrr:.2f}, Precision@K={precision:.2f}, Hit Rate={hit:.2f} (best mode: {best_mode})")

    if faith > 0:
        lines.append(f"- **Faithfulness:** {faith:.2f}")
    if geval > 0:
        lines.append(f"- **ENEM G-Eval:** {geval:.2f}")

    # Health assessment
    if mrr >= 0.6 and (not faith or faith >= 0.7):
        lines.append("- **Status:** Sistema RAG com performance adequada.")
    elif mrr >= 0.4:
        lines.append("- **Status:** Sistema RAG com performance moderada — considere melhorias no retrieval.")
    else:
        lines.append("- **Status:** Sistema RAG com performance baixa — investigar qualidade do retrieval.")

    return "\n".join(lines)


def _retrieval_scores_table(results: Dict[str, Any]) -> str:
    lines = ["## Retrieval Metrics (Hybrid Mode)"]

    hybrid = results.get("hybrid", {}).get("aggregate", {})
    if not hybrid:
        return "\n".join(lines + ["_No hybrid results available._"])

    lines.append("")
    lines.append("| Metric | Mean | Stdev | Min | Max |")
    lines.append("|--------|------|-------|-----|-----|")

    metric_names = {
        "precision_at_k": "Precision@K",
        "recall_at_k": "Recall@K",
        "mrr": "MRR",
        "hit_rate": "Hit Rate",
    }

    for key, label in metric_names.items():
        m = hybrid.get(key, {})
        lines.append(
            f"| {label} | {m.get('mean', 0):.2f} | {m.get('stdev', 0):.2f} | {m.get('min', 0):.2f} | {m.get('max', 0):.2f} |"
        )

    return "\n".join(lines)


def _search_mode_comparison(results: Dict[str, Any]) -> str:
    lines = ["## Search Mode Comparison"]
    lines.append("")
    lines.append("| Metric | Semantic | Text | Hybrid |")
    lines.append("|--------|----------|------|--------|")

    metric_names = {
        "precision_at_k": "Precision@K",
        "recall_at_k": "Recall@K",
        "mrr": "MRR",
        "hit_rate": "Hit Rate",
    }

    best_mode = results.get("_best_mode", "hybrid")

    for key, label in metric_names.items():
        vals = []
        for mode in ["semantic", "text", "hybrid"]:
            agg = results.get(mode, {}).get("aggregate", {})
            val = agg.get(key, {}).get("mean", 0)
            cell = f"{val:.2f}"
            if mode == best_mode:
                cell = f"**{cell}**"
            vals.append(cell)
        lines.append(f"| {label} | {vals[0]} | {vals[1]} | {vals[2]} |")

    lines.append(f"\n*Best mode: **{best_mode}***")
    return "\n".join(lines)


def _generation_scores_table(results: Dict[str, Any]) -> str:
    lines = ["## Generation Metrics"]

    faith = results.get("faithfulness_aggregate", {})
    geval = results.get("enem_geval_aggregate", {})

    if not faith and not geval:
        return "\n".join(lines + ["_No generation results available._"])

    lines.append("")
    lines.append("| Metric | Mean | Stdev | Min | Max |")
    lines.append("|--------|------|-------|-----|-----|")

    if faith:
        lines.append(
            f"| Faithfulness | {faith.get('mean', 0):.2f} | {faith.get('stdev', 0):.2f} | {faith.get('min', 0):.2f} | {faith.get('max', 0):.2f} |"
        )
    if geval:
        lines.append(
            f"| ENEM G-Eval | {geval.get('mean', 0):.2f} | {geval.get('stdev', 0):.2f} | {geval.get('min', 0):.2f} | {geval.get('max', 0):.2f} |"
        )

    return "\n".join(lines)


def _worst_cases(
    retrieval_results: Dict[str, Any],
    generation_results: Dict[str, Any],
) -> str:
    lines = ["## Worst Cases"]

    # Retrieval worst cases
    worst_retrieval = []
    hybrid = retrieval_results.get("hybrid", {}).get("results", [])
    if hybrid:
        sorted_r = sorted(hybrid, key=lambda r: r.mrr)
        for r in sorted_r[:3]:
            worst_retrieval.append(f"- **{r.query_id}** ({r.query[:50]}): MRR={r.mrr:.2f}, P@K={r.precision_at_k:.2f}")

    if worst_retrieval:
        lines.append("\n### Retrieval (lowest MRR)")
        lines.extend(worst_retrieval)

    # Generation worst cases
    worst_gen = generation_results.get("worst_cases", [])
    if worst_gen:
        lines.append("\n### Generation (lowest G-Eval)")
        for w in worst_gen[:3]:
            score = w.get("enem_geval_score", 0) or 0
            lines.append(f"- **{w['ref_id']}** ({w['input_topic'][:50]}): G-Eval={score:.2f}")

    return "\n".join(lines)


def _regression_section(deltas: List) -> str:
    lines = ["## Regression Analysis (vs Baseline)"]
    lines.append("")
    lines.append("| Metric | Baseline | Current | Delta | Status |")
    lines.append("|--------|----------|---------|-------|--------|")

    for d in deltas:
        status_icon = ""
        if d.status == "CRITICAL":
            status_icon = "**CRITICAL**"
        elif d.status == "WARNING":
            status_icon = "**WARNING**"
        else:
            status_icon = "OK"

        lines.append(
            f"| {d.metric_name} | {d.baseline_value:.2f} | {d.current_value:.2f} | {d.delta_pct:+.1f}% | {status_icon} |"
        )

    return "\n".join(lines)


def _recommendations(
    retrieval_results: Dict[str, Any],
    generation_results: Dict[str, Any],
) -> str:
    lines = ["## Recommendations"]

    hybrid = retrieval_results.get("hybrid", {}).get("aggregate", {})
    mrr = hybrid.get("mrr", {}).get("mean", 0)
    precision = hybrid.get("precision_at_k", {}).get("mean", 0)
    recall = hybrid.get("recall_at_k", {}).get("mean", 0)
    geval = generation_results.get("enem_geval_aggregate", {}).get("mean", 0)
    faith = generation_results.get("faithfulness_aggregate", {}).get("mean", 0)

    recs = []

    if mrr < 0.5:
        recs.append("- Improve hybrid search — MRR below 0.50 suggests first relevant result often not in top positions")
    if precision < 0.5:
        recs.append("- Improve retrieval precision — many irrelevant chunks in top-K results")
    if recall < 0.5:
        recs.append("- Improve retrieval recall — many relevant chunks not being retrieved")
    if geval and geval < 0.5:
        recs.append("- Improve generation quality — G-Eval ENEM below 0.50 indicates formatting/pedagogical issues")
    if faith and faith < 0.7:
        recs.append("- Reduce hallucinations — Faithfulness below 0.70 indicates generated claims not supported by context")

    if not recs:
        recs.append("- No critical issues detected. Continue monitoring with baseline regression.")

    return "\n".join(lines + recs)
