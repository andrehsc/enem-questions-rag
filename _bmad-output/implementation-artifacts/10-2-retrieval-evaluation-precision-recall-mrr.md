# Story 10.2: Retrieval Evaluation — Precision@K, Recall@K, MRR

Status: done

## Story

Como desenvolvedor,
Quero métricas objetivas de qualidade da busca semântica hybrid (pgvector + tsvector + RRF),
Para que eu saiba se o retriever está encontrando os chunks corretos e no ranking adequado.

## Acceptance Criteria (AC)

1. Módulo `src/rag_evaluation/retrieval_metrics.py` calcula Precision@K, Recall@K, MRR e Hit Rate para cada query do golden eval dataset
2. Resultados agregados com scores médios e desvio padrão por métrica
3. Avaliação executa nos 3 modos do PgVectorSearch (`semantic`, `text`, `hybrid`) com relatório comparativo
4. DeepEval RAGAS Context Precision e Context Recall calculados via Ollama para cada query
5. Scores salvos em JSON (`reports/retrieval_eval_{date}.json`) para comparação futura
6. Testes pytest em `tests/test_retrieval_evaluation.py` com marker `eval`

## Tasks / Subtasks

- [ ] Task 1: Implementar métricas IR tradicionais (AC: 1, 2)
  - [ ] 1.1 Criar `src/rag_evaluation/retrieval_metrics.py`:
    ```python
    """Traditional IR metrics for retrieval evaluation."""
    from dataclasses import dataclass
    from typing import List, Dict, Optional
    import statistics

    @dataclass
    class RetrievalResult:
        query_id: str
        query: str
        retrieved_ids: List[str]
        relevant_ids: List[str]
        precision_at_k: float
        recall_at_k: float
        mrr: float
        hit_rate: float

    def precision_at_k(retrieved: List[str], relevant: List[str], k: int = 5) -> float:
        """Fraction of top-K retrieved docs that are relevant."""
        top_k = retrieved[:k]
        if not top_k:
            return 0.0
        hits = sum(1 for doc in top_k if doc in relevant)
        return hits / len(top_k)

    def recall_at_k(retrieved: List[str], relevant: List[str], k: int = 5) -> float:
        """Fraction of relevant docs found in top-K."""
        if not relevant:
            return 0.0
        top_k = retrieved[:k]
        hits = sum(1 for doc in relevant if doc in top_k)
        return hits / len(relevant)

    def mean_reciprocal_rank(retrieved: List[str], relevant: List[str]) -> float:
        """Reciprocal of rank of first relevant document."""
        for i, doc in enumerate(retrieved, 1):
            if doc in relevant:
                return 1.0 / i
        return 0.0

    def hit_rate(retrieved: List[str], relevant: List[str], k: int = 5) -> float:
        """1 if at least one relevant doc in top-K, else 0."""
        top_k = retrieved[:k]
        return 1.0 if any(doc in relevant for doc in top_k) else 0.0

    def aggregate_metrics(results: List[RetrievalResult]) -> Dict:
        """Compute mean and stdev for all metrics."""
        metrics = {}
        for field in ["precision_at_k", "recall_at_k", "mrr", "hit_rate"]:
            values = [getattr(r, field) for r in results]
            metrics[field] = {
                "mean": statistics.mean(values),
                "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
                "min": min(values),
                "max": max(values),
            }
        return metrics
    ```
  - [ ] 1.2 Implementar `evaluate_retrieval()` que itera sobre retrieval pairs do golden eval dataset, chama `PgVectorSearch.search_questions()`, e computa métricas

- [ ] Task 2: Adapter PgVectorSearch → retrieval evaluation (AC: 3)
  - [ ] 2.1 Criar `src/rag_evaluation/retrieval_evaluator.py`:
    ```python
    """Evaluator that runs retrieval metrics over PgVectorSearch."""
    from src.rag_features.semantic_search import PgVectorSearch
    from src.rag_evaluation.retrieval_metrics import (
        precision_at_k, recall_at_k, mean_reciprocal_rank,
        hit_rate, RetrievalResult, aggregate_metrics,
    )

    class RetrievalEvaluator:
        def __init__(self, search: PgVectorSearch, k: int = 5):
            self.search = search
            self.k = k

        async def evaluate(
            self,
            retrieval_pairs: list,
            search_modes: list = ["semantic", "text", "hybrid"],
        ) -> dict:
            """Evaluate retrieval over all pairs and modes."""
            results_by_mode = {}
            for mode in search_modes:
                results = []
                for pair in retrieval_pairs:
                    retrieved = await self.search.search_questions(
                        query=pair["query"],
                        limit=self.k,
                        search_mode=mode,
                    )
                    retrieved_ids = [r["question_id"] for r in retrieved]
                    relevant_ids = pair["expected_question_ids"]
                    results.append(RetrievalResult(
                        query_id=pair["id"],
                        query=pair["query"],
                        retrieved_ids=retrieved_ids,
                        relevant_ids=relevant_ids,
                        precision_at_k=precision_at_k(retrieved_ids, relevant_ids, self.k),
                        recall_at_k=recall_at_k(retrieved_ids, relevant_ids, self.k),
                        mrr=mean_reciprocal_rank(retrieved_ids, relevant_ids),
                        hit_rate=hit_rate(retrieved_ids, relevant_ids, self.k),
                    ))
                results_by_mode[mode] = {
                    "results": results,
                    "aggregate": aggregate_metrics(results),
                }
            return results_by_mode
    ```
  - [ ] 2.2 Identificar qual modo tem melhor performance e incluir no output

- [ ] Task 3: Integrar métricas LLM-based via DeepEval (AC: 4)
  - [ ] 3.1 Em `retrieval_evaluator.py`, adicionar avaliação DeepEval:
    ```python
    from deepeval.metrics import ContextualPrecisionMetric, ContextualRecallMetric
    from deepeval.test_case import LLMTestCase

    async def evaluate_with_llm_metrics(self, retrieval_pairs, eval_llm):
        """Run RAGAS Context Precision and Context Recall via DeepEval."""
        for pair in retrieval_pairs:
            retrieved = await self.search.search_questions(
                query=pair["query"], limit=self.k, search_mode="hybrid",
            )
            test_case = LLMTestCase(
                input=pair["query"],
                actual_output=retrieved[0]["full_text"] if retrieved else "",
                retrieval_context=[r["full_text"] for r in retrieved],
                expected_output=pair.get("expected_answer", ""),
            )
            ctx_precision = ContextualPrecisionMetric(model=eval_llm, threshold=0.5)
            ctx_recall = ContextualRecallMetric(model=eval_llm, threshold=0.5)
            ctx_precision.measure(test_case)
            ctx_recall.measure(test_case)
    ```

- [ ] Task 4: Persistir resultados em JSON (AC: 5)
  - [ ] 4.1 Salvar resultados em `reports/retrieval_eval_{date}.json`:
    ```json
    {
      "timestamp": "2026-04-06T...",
      "provider": "ollama",
      "k": 5,
      "modes": {
        "semantic": {"precision_at_k": {"mean": 0.72, "stdev": 0.15}, ...},
        "text": {...},
        "hybrid": {...}
      },
      "llm_metrics": {
        "context_precision": {"mean": 0.68, "stdev": 0.12},
        "context_recall": {"mean": 0.75, "stdev": 0.10}
      },
      "best_mode": "hybrid"
    }
    ```

- [ ] Task 5: Testes (AC: 6)
  - [ ] 5.1 Criar `tests/test_retrieval_evaluation.py`:
    - Testes unitários para cada métrica IR (precision, recall, MRR, hit_rate) com valores conhecidos
    - Teste de integração com mock do PgVectorSearch
    - Teste end-to-end com banco real (marker `eval`)
  - [ ] 5.2 Testes de edge cases: query sem resultados, todos relevantes, nenhum relevante

## Dev Notes

### PgVectorSearch Interface
```python
# src/rag_features/semantic_search.py:520
async def search_questions(
    self, query: str, limit: int = 10,
    year: Optional[int] = None, subject: Optional[str] = None,
    chunk_type: str = "full", search_mode: str = "hybrid",
) -> List[Dict[str, Any]]:
    # Returns: [{"question_id", "chunk_id", "full_text", "subject", "year", "similarity_score"}]
```

### Matching Strategy
O golden eval dataset usa `expected_question_ids` que mapeiam para IDs do golden set (`gs-xxx`). Estes precisam ser mapeados para `question_id` da tabela `enem_questions.questions` via `db_id` no golden set.

### RAGAS via DeepEval
DeepEval inclui wrapper para métricas RAGAS. `ContextualPrecisionMetric` e `ContextualRecallMetric` usam LLM-as-judge para avaliar relevância dos chunks recuperados vs a query — são versões LLM-enhanced de Precision e Recall.

### Performance
- Métricas IR tradicionais: < 1s por query (computação pura)
- Métricas LLM-based (Context Precision/Recall): ~5-10s por query com Ollama local
- 30 queries × 3 modos = ~90 search calls para IR, ~30 LLM calls para RAGAS

### References

- [Source: src/rag_features/semantic_search.py:520] — PgVectorSearch.search_questions()
- [Source: tests/fixtures/golden_eval_dataset.json] — Retrieval pairs (Story 10.1)
- [Research: technical-rag-llm-evaluation-pipeline-research-2026-04-06.md] — IR metrics + RAGAS Context Precision/Recall
