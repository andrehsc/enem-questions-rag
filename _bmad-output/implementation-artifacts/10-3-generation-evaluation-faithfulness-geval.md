# Story 10.3: Generation Evaluation — Faithfulness + G-Eval ENEM Rubric

Status: done

## Story

Como desenvolvedor,
Quero avaliar se as questões geradas pelo RAG são fiéis ao contexto recuperado e seguem o padrão ENEM,
Para que eu saiba se o question_generator produz conteúdo de qualidade pedagógica.

## Acceptance Criteria (AC)

1. Módulo `src/rag_evaluation/generation_evaluator.py` avalia output do RAGQuestionGenerator com Faithfulness e G-Eval ENEM
2. DeepEval FaithfulnessMetric calcula score (claims suportados / total claims) com `reason` field explicando claims não-fiéis
3. G-Eval ENEM custom com rubric escala 1-4:
   - 1 = questão irrelevante ou mal formatada
   - 2 = questão parcialmente adequada, falta elementos ENEM
   - 3 = questão adequada mas poderia ser melhorada
   - 4 = questão excelente no padrão ENEM completo
4. Chain-of-thought do LLM judge salvo para auditoria
5. Avaliação executa sobre 20 questões de referência do golden eval dataset
6. Relatório consolidado com score médio, piores casos e distribuição
7. Avaliação completa executa em < 10 minutos com Ollama

## Tasks / Subtasks

- [ ] Task 1: Criar G-Eval ENEM Rubric (AC: 3, 4)
  - [ ] 1.1 Criar `src/rag_evaluation/enem_rubric.py`:
    ```python
    """ENEM-specific G-Eval rubric for question generation evaluation."""
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCaseParams

    ENEM_RUBRIC = """Avalie a questão ENEM gerada com base nos critérios abaixo.

    Critérios de avaliação:
    1. Formato ENEM: A questão tem texto-base/contexto quando necessário,
       enunciado com comando claro, e exatamente 5 alternativas (A-E)?
    2. Qualidade pedagógica: O enunciado é claro e avalia competência
       cognitiva? As alternativas são plausíveis e bem redigidas?
    3. Fidelidade ao conteúdo: A questão reflete com precisão o tema
       e informações do contexto fornecido?
    4. Distratores: As alternativas incorretas são plausíveis mas
       claramente distinguíveis da resposta correta?

    Escala de avaliação:
    1: Questão irrelevante ou mal formatada — falta alternativas, enunciado confuso, ou sem relação com o tema
    2: Questão parcialmente adequada — tem estrutura básica mas falta elementos ENEM (distratores fracos, enunciado vago)
    3: Questão adequada — segue formato ENEM, conteúdo correto, mas poderia ter distratores melhores ou enunciado mais preciso
    4: Questão excelente — padrão ENEM completo, pedagogicamente sólida, distratores plausíveis, enunciado claro com comando de ação"""

    def create_enem_geval(eval_llm) -> GEval:
        """Create G-Eval metric with ENEM rubric."""
        return GEval(
            name="ENEM Question Quality",
            criteria=ENEM_RUBRIC,
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
            ],
            threshold=0.5,  # Minimum acceptable: 2/4 = 0.5
            model=eval_llm,
        )
    ```

- [ ] Task 2: Implementar Generation Evaluator (AC: 1, 2, 5)
  - [ ] 2.1 Criar `src/rag_evaluation/generation_evaluator.py`:
    ```python
    """Evaluator for RAG question generation quality."""
    from deepeval.metrics import FaithfulnessMetric
    from deepeval.test_case import LLMTestCase
    from src.rag_evaluation.enem_rubric import create_enem_geval

    class GenerationEvaluator:
        def __init__(self, eval_llm, faithfulness_threshold=0.7, geval_threshold=0.5):
            self.eval_llm = eval_llm
            self.faithfulness = FaithfulnessMetric(
                threshold=faithfulness_threshold,
                model=eval_llm,
                include_reason=True,
            )
            self.enem_geval = create_enem_geval(eval_llm)

        async def evaluate_question(
            self,
            input_topic: str,
            generated_question: str,
            retrieval_context: list[str],
        ) -> dict:
            """Evaluate a single generated question."""
            test_case = LLMTestCase(
                input=input_topic,
                actual_output=generated_question,
                retrieval_context=retrieval_context,
            )
            self.faithfulness.measure(test_case)
            self.enem_geval.measure(test_case)
            return {
                "faithfulness_score": self.faithfulness.score,
                "faithfulness_reason": self.faithfulness.reason,
                "enem_geval_score": self.enem_geval.score,
                "enem_geval_reason": self.enem_geval.reason,
            }

        async def evaluate_batch(self, generation_references: list) -> dict:
            """Evaluate all generation references from golden eval dataset."""
            results = []
            for ref in generation_references:
                result = await self.evaluate_question(
                    input_topic=ref["input_topic"],
                    generated_question=ref["reference_question"]["question_text"],
                    retrieval_context=ref.get("source_contexts", []),
                )
                result["ref_id"] = ref["id"]
                results.append(result)
            return self._aggregate(results)

        def _aggregate(self, results: list) -> dict:
            """Compute summary statistics."""
            ...
    ```
  - [ ] 2.2 Implementar `_aggregate()` com mean, stdev, min, max, distribuição (quartis), e piores 5 cases

- [ ] Task 3: Integrar com RAGQuestionGenerator (AC: 1)
  - [ ] 3.1 Adicionar método `evaluate_live_generation()` que:
    1. Chama `RAGQuestionGenerator.generate_questions(subject, topic)` para gerar questão
    2. Captura chunks usados como contexto
    3. Avalia a questão gerada com Faithfulness + G-Eval ENEM
  - [ ] 3.2 Usar `PgVectorSearch.search_questions()` para obter os mesmos chunks que o generator usa

- [ ] Task 4: Salvar chain-of-thought para auditoria (AC: 4)
  - [ ] 4.1 Persistir `reason` field tanto de Faithfulness quanto G-Eval em JSON de resultados
  - [ ] 4.2 Estrutura: `reports/generation_eval_{date}.json` com todas as razões por questão

- [ ] Task 5: Testes (AC: 6, 7)
  - [ ] 5.1 Criar `tests/test_generation_evaluation.py`:
    - Teste unitário: rubric ENEM é válida e cria GEval sem erros
    - Teste com mock LLM: GenerationEvaluator retorna scores
    - Teste de integração com Ollama (marker `eval`): avalia 3 questões do golden set
  - [ ] 5.2 Verificar tempo de execução < 10 min para 20 questões com Ollama

## Dev Notes

### RAGQuestionGenerator Interface
```python
# src/rag_features/question_generator.py:118
async def generate_questions(
    self, subject: str, topic: str,
    difficulty: str = "medium", count: int = 1, style: str = "enem",
) -> tuple:  # Returns (questions: List[Dict], meta: Dict)
# Generated question: {"stem", "context_text", "alternatives": {"A"-"E"}, "answer", "explanation", "source_context_ids"}
```

### Faithfulness Flow
1. DeepEval extrai claims atômicos da questão gerada
2. Cada claim é verificado contra os chunks do retrieval_context
3. Score = claims_suportados / total_claims
4. `reason` explica quais claims não foram suportados

### G-Eval ENEM Flow
1. LLM judge recebe: rubric + input (topic) + actual_output (questão gerada)
2. Chain-of-thought: LLM raciocina sobre cada critério da rubric
3. Score numa escala 1-4, normalizado para 0-1 pelo DeepEval
4. `reason` contém o chain-of-thought completo

### LLM-as-Judge Best Practices (from research)
- Escala 1-4 inteira (NÃO float) — melhor correlação com humanos
- Chain-of-thought obrigatório antes do score
- Cada ponto da escala com descrição clara
- Prompt em português para avaliar conteúdo ENEM em PT-BR

### Performance Budget
- Faithfulness: ~10s/question (claim extraction + verification)
- G-Eval ENEM: ~5s/question (single LLM call with rubric)
- 20 questions × 15s = ~5 min total (within 10 min budget)

### References

- [Source: src/rag_features/question_generator.py:118] — RAGQuestionGenerator.generate_questions()
- [Research: technical-rag-llm-evaluation-pipeline-research-2026-04-06.md] — LLM-as-Judge best practices, G-Eval
- [Source: tests/fixtures/golden_eval_dataset.json] — Generation references (Story 10.1)
