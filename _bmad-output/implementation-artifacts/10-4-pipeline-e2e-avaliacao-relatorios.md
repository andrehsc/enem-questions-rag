# Story 10.4: Pipeline End-to-End de Avaliação + Relatórios

Status: ready-for-dev

## Story

Como desenvolvedor,
Quero um pipeline que execute a avaliação completa (retrieval + generation) e produza um relatório legível,
Para que eu tenha visibilidade end-to-end da qualidade do sistema RAG com um único comando.

## Acceptance Criteria (AC)

1. Script `scripts/run_rag_evaluation.py` executa avaliação completa com `python -m scripts.run_rag_evaluation`
2. Pipeline executa retrieval eval (Story 10.2) e generation eval (Story 10.3) sequencialmente
3. Relatório Markdown gerado em `reports/rag-evaluation-{date}.md` com:
   - Resumo executivo (3-5 linhas)
   - Scores por métrica com 2 casas decimais
   - Comparativo de modos de busca (tabela)
   - Top 5 piores cases
   - Recomendações
4. Flag `--provider` permite alternar: `ollama` (default), `github-models`, `openai`
5. Relatório indica qual LLM foi usado como judge e configuração
6. Pipeline completo executa em < 15 minutos com Ollama

## Tasks / Subtasks

- [ ] Task 1: Criar script de pipeline (AC: 1, 2)
  - [ ] 1.1 Criar `scripts/run_rag_evaluation.py`:
    ```python
    """End-to-end RAG evaluation pipeline.

    Usage:
        python -m scripts.run_rag_evaluation [--provider ollama|github-models|openai] [--save-baseline]
    """
    import argparse
    import asyncio
    import json
    from datetime import datetime
    from pathlib import Path

    from src.rag_evaluation.llm_provider import get_eval_llm
    from src.rag_evaluation.retrieval_evaluator import RetrievalEvaluator
    from src.rag_evaluation.generation_evaluator import GenerationEvaluator
    from src.rag_evaluation.report_generator import generate_markdown_report

    def parse_args():
        parser = argparse.ArgumentParser(description="RAG Evaluation Pipeline")
        parser.add_argument("--provider", default="ollama", choices=["ollama", "github-models", "openai"])
        parser.add_argument("--save-baseline", action="store_true")
        parser.add_argument("--k", type=int, default=5, help="Top-K for retrieval")
        return parser.parse_args()

    async def main():
        args = parse_args()
        os.environ["EVAL_LLM_PROVIDER"] = args.provider
        eval_llm = get_eval_llm()

        # Load golden eval dataset
        dataset = json.loads(Path("tests/fixtures/golden_eval_dataset.json").read_text("utf-8"))

        # Phase 1: Retrieval evaluation
        retrieval_evaluator = RetrievalEvaluator(search=..., k=args.k)
        retrieval_results = await retrieval_evaluator.evaluate(dataset["retrieval_pairs"])

        # Phase 2: Generation evaluation
        generation_evaluator = GenerationEvaluator(eval_llm=eval_llm)
        generation_results = await generation_evaluator.evaluate_batch(dataset["generation_references"])

        # Phase 3: Generate report
        report = generate_markdown_report(retrieval_results, generation_results, args)
        report_path = Path(f"reports/rag-evaluation-{datetime.now().strftime('%Y-%m-%d')}.md")
        report_path.write_text(report, encoding="utf-8")

        # Optional: Save baseline
        if args.save_baseline:
            save_baseline(retrieval_results, generation_results)

    if __name__ == "__main__":
        asyncio.run(main())
    ```
  - [ ] 1.2 Usar `create_semantic_search()` factory para obter PgVectorSearch instance
  - [ ] 1.3 Handler de erro gracioso se Ollama/DB não estiver disponível

- [ ] Task 2: Gerador de relatório Markdown (AC: 3, 5)
  - [ ] 2.1 Criar `src/rag_evaluation/report_generator.py`:
    ```python
    """Generate Markdown evaluation reports."""

    def generate_markdown_report(
        retrieval_results: dict,
        generation_results: dict,
        config: dict,
    ) -> str:
        sections = [
            _header(config),
            _executive_summary(retrieval_results, generation_results),
            _retrieval_scores_table(retrieval_results),
            _search_mode_comparison(retrieval_results),
            _generation_scores_table(generation_results),
            _worst_cases(retrieval_results, generation_results),
            _recommendations(retrieval_results, generation_results),
        ]
        return "\n\n".join(sections)
    ```
  - [ ] 2.2 Seção header com: data, provider, K value, dataset version
  - [ ] 2.3 Seção resumo executivo: 3-5 linhas sobre saúde geral do RAG
  - [ ] 2.4 Tabela retrieval scores: Precision@K, Recall@K, MRR, Hit Rate (mean ± stdev)
  - [ ] 2.5 Tabela comparativa: semantic vs text vs hybrid (highlight best mode)
  - [ ] 2.6 Tabela generation scores: Faithfulness, G-Eval ENEM (mean ± stdev)
  - [ ] 2.7 Top 5 piores cases: query/question with lowest scores + reason
  - [ ] 2.8 Recomendações baseadas nos scores (e.g., "Considere melhorar hybrid search se MRR < 0.5")

- [ ] Task 3: Suporte a provider via CLI (AC: 4)
  - [ ] 3.1 `--provider ollama`: usa OllamaEvalLLM (default)
  - [ ] 3.2 `--provider github-models`: usa GPT-4o via GitHub token
  - [ ] 3.3 `--provider openai`: usa GPT-4o via OpenAI API key
  - [ ] 3.4 Relatório inclui: "LLM Judge: ollama/llama3" ou "LLM Judge: openai/gpt-4o"

- [ ] Task 4: Testes (AC: 6)
  - [ ] 4.1 Criar `tests/test_report_generator.py`:
    - Teste: report contém todas as seções esperadas
    - Teste: scores formatados com 2 casas decimais
    - Teste: worst cases corretamente identificados
  - [ ] 4.2 Teste E2E com mock data (não requer Ollama/DB)

## Dev Notes

### Report Format Example
```markdown
# RAG Evaluation Report — 2026-04-06

**LLM Judge:** ollama/llama3
**Dataset:** golden_eval_dataset.json v1.0 (30 retrieval pairs, 20 generation refs)
**K:** 5

## Resumo Executivo
O sistema RAG apresenta performance adequada em retrieval (MRR 0.65) com hybrid search
superando os modos individuais. A geração de questões atinge faithfulness de 0.82,
indicando boa fidelidade ao contexto. G-Eval ENEM médio de 0.68 sugere espaço para
melhoria no formato pedagógico.

## Retrieval Metrics
| Métrica | Semantic | Text | Hybrid |
|---------|----------|------|--------|
| Precision@5 | 0.62 ± 0.15 | 0.55 ± 0.18 | **0.72 ± 0.12** |
| Recall@5 | 0.58 ± 0.20 | 0.50 ± 0.22 | **0.68 ± 0.16** |
| MRR | 0.60 ± 0.25 | 0.52 ± 0.28 | **0.65 ± 0.20** |
| Hit Rate | 0.80 | 0.73 | **0.87** |

...
```

### Dependencies on Previous Stories
- **Story 10.1:** Golden eval dataset, LLM provider factory
- **Story 10.2:** RetrievalEvaluator, retrieval metrics
- **Story 10.3:** GenerationEvaluator, ENEM rubric

### References

- [Source: scripts/] — Existing scripts pattern (audit_extraction_quality.py)
- [Source: src/rag_evaluation/] — Modules from Stories 10.1-10.3
- [Research: technical-rag-llm-evaluation-pipeline-research-2026-04-06.md] — Report patterns
