"""End-to-end RAG evaluation pipeline.

Runs retrieval and generation evaluation, generates a Markdown report.

Usage:
    python -m scripts.run_rag_evaluation [--provider ollama|github-models|openai] [--save-baseline] [--k 5]
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.rag_evaluation.llm_provider import get_eval_llm, is_ollama_available
from src.rag_evaluation.report_generator import generate_markdown_report


def parse_args():
    parser = argparse.ArgumentParser(description="RAG Evaluation Pipeline")
    parser.add_argument(
        "--provider",
        default="ollama",
        choices=["ollama", "github-models", "openai"],
        help="LLM provider for evaluation judge (default: ollama)",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save current scores as regression baseline",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Top-K for retrieval metrics (default: 5)",
    )
    parser.add_argument(
        "--skip-retrieval",
        action="store_true",
        help="Skip retrieval evaluation (generation only)",
    )
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Skip generation evaluation (retrieval only)",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory for output reports (default: reports)",
    )
    return parser.parse_args()


def load_golden_datasets():
    """Load golden evaluation dataset and golden set questions."""
    eval_path = PROJECT_ROOT / "tests" / "fixtures" / "golden_eval_dataset.json"
    golden_path = PROJECT_ROOT / "tests" / "fixtures" / "golden_set.json"

    eval_dataset = json.loads(eval_path.read_text(encoding="utf-8"))

    # Build map of gs-ID → question for generation eval
    golden_questions = {}
    if golden_path.exists():
        golden_set = json.loads(golden_path.read_text(encoding="utf-8"))
        for q in golden_set.get("questions", []):
            golden_questions[q["id"]] = q

    return eval_dataset, golden_questions


async def run_retrieval_evaluation(eval_dataset, k, search_modes=None):
    """Run retrieval evaluation if DB is available."""
    try:
        from src.rag_features.semantic_search import create_semantic_search
        from src.rag_evaluation.retrieval_evaluator import RetrievalEvaluator

        search = create_semantic_search()
        evaluator = RetrievalEvaluator(search=search, k=k)
        results = await evaluator.evaluate(
            eval_dataset["retrieval_pairs"],
            search_modes=search_modes or ["semantic", "text", "hybrid"],
        )
        return results
    except Exception as e:
        print(f"  WARNING: Retrieval evaluation failed: {e}")
        return None


async def run_generation_evaluation(eval_dataset, golden_questions, eval_llm):
    """Run generation evaluation with LLM judge."""
    try:
        from src.rag_evaluation.generation_evaluator import GenerationEvaluator

        evaluator = GenerationEvaluator(eval_llm=eval_llm)
        results = evaluator.evaluate_batch(
            eval_dataset["generation_references"],
            golden_questions=golden_questions,
        )
        return results
    except Exception as e:
        print(f"  WARNING: Generation evaluation failed: {e}")
        return None


async def main():
    args = parse_args()
    os.environ["EVAL_LLM_PROVIDER"] = args.provider

    print(f"=== RAG Evaluation Pipeline ===")
    print(f"Provider: {args.provider}")
    print(f"K: {args.k}")
    print()

    # Check provider availability
    if args.provider == "ollama" and not is_ollama_available():
        print("ERROR: Ollama is not available. Start Docker or use --provider openai")
        sys.exit(1)

    eval_llm = get_eval_llm(args.provider)
    print(f"LLM Judge: {eval_llm.get_model_name()}")

    # Load datasets
    print("\nLoading datasets...")
    eval_dataset, golden_questions = load_golden_datasets()
    print(f"  Retrieval pairs: {len(eval_dataset['retrieval_pairs'])}")
    print(f"  Generation refs: {len(eval_dataset['generation_references'])}")
    print(f"  Golden questions: {len(golden_questions)}")

    retrieval_results = None
    generation_results = None

    # Phase 1: Retrieval evaluation
    if not args.skip_retrieval:
        print("\n--- Phase 1: Retrieval Evaluation ---")
        retrieval_results = await run_retrieval_evaluation(eval_dataset, args.k)
        if retrieval_results:
            best = retrieval_results.get("_best_mode", "hybrid")
            hybrid = retrieval_results.get("hybrid", {}).get("aggregate", {})
            mrr = hybrid.get("mrr", {}).get("mean", 0)
            print(f"  Best mode: {best}")
            print(f"  Hybrid MRR: {mrr:.4f}")
    else:
        print("\n--- Skipping retrieval evaluation ---")

    # Phase 2: Generation evaluation
    if not args.skip_generation:
        print("\n--- Phase 2: Generation Evaluation ---")
        generation_results = await run_generation_evaluation(
            eval_dataset, golden_questions, eval_llm
        )
        if generation_results:
            geval = generation_results.get("enem_geval_aggregate", {}).get("mean", 0)
            print(f"  ENEM G-Eval mean: {geval:.4f}")
    else:
        print("\n--- Skipping generation evaluation ---")

    # Phase 3: Generate report
    print("\n--- Phase 3: Generating Report ---")

    config = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "provider": eval_llm.get_model_name(),
        "k": args.k,
        "dataset_version": eval_dataset.get("metadata", {}).get("version", "1.0"),
    }

    # Check for baseline
    baseline_deltas = None
    try:
        from src.rag_evaluation.baseline import load_baseline, compare_with_baseline

        baseline = load_baseline()
        if baseline and retrieval_results and generation_results:
            baseline_deltas = compare_with_baseline(
                retrieval_results, generation_results, baseline
            )
    except ImportError:
        pass

    report = generate_markdown_report(
        retrieval_results=retrieval_results or {},
        generation_results=generation_results or {},
        config=config,
        baseline_deltas=baseline_deltas,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"rag-evaluation-{datetime.now().strftime('%Y-%m-%d')}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Report saved: {report_path}")

    # Optional: Save baseline
    if args.save_baseline and retrieval_results and generation_results:
        from src.rag_evaluation.baseline import save_baseline

        bl_path = save_baseline(retrieval_results, generation_results, args.provider)
        print(f"  Baseline saved: {bl_path}")

    print("\n=== Evaluation Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
