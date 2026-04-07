# Story 10.1: Setup DeepEval + Ollama Docker + Golden Evaluation Dataset

Status: ready-for-dev

## Story

Como desenvolvedor,
Quero configurar o framework DeepEval com Ollama no Docker e criar um golden evaluation dataset para RAG,
Para que o time tenha infraestrutura de avaliação funcional com LLM local e dados de referência ENEM anotados.

## Acceptance Criteria (AC)

1. DeepEval adicionado como dependência opcional em `pyproject.toml` sob `[project.optional-dependencies.eval]`
2. Adapter `OllamaEvalLLM(DeepEvalBaseLLM)` implementado em `src/rag_evaluation/llm_provider.py` com `generate()` e `a_generate()` chamando Ollama API (`http://llama3-enem-service:11434` no Docker, `http://localhost:11434` local)
3. Flag `EVAL_LLM_PROVIDER` (env var) alterna entre `ollama` (default), `github-models`, `openai`
4. `deepeval test run` executa com sucesso usando Ollama como LLM judge em pelo menos 1 teste trivial
5. Golden evaluation dataset em `tests/fixtures/golden_eval_dataset.json` com:
   - Mínimo 30 pares query-documento com relevância anotada (retrieval eval)
   - Mínimo 20 questões de referência com expected output (generation eval)
6. Conftest fixtures para DeepEval em `tests/conftest_eval.py` carregam o dataset
7. G-Eval simples (escala 1-4) executa com Ollama e retorna score em < 30 segundos

## Tasks / Subtasks

- [ ] Task 1: Adicionar dependências de avaliação (AC: 1)
  - [ ] 1.1 Criar grupo `[project.optional-dependencies.eval]` em `pyproject.toml`:
    ```toml
    [project.optional-dependencies]
    eval = [
        "deepeval>=2.0",
    ]
    ```
  - [ ] 1.2 Instalar com `pip install -e ".[eval]"`
  - [ ] 1.3 Verificar compatibilidade: DeepEval requer Python 3.9+, projeto usa 3.11 ✓

- [ ] Task 2: Criar módulo `src/rag_evaluation/` com LLM provider adapter (AC: 2, 3)
  - [ ] 2.1 Criar `src/rag_evaluation/__init__.py`
  - [ ] 2.2 Criar `src/rag_evaluation/llm_provider.py`:
    ```python
    """LLM provider abstraction for RAG evaluation pipeline."""
    import os
    import httpx
    from deepeval.models import DeepEvalBaseLLM

    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    EVAL_LLM_PROVIDER = os.getenv("EVAL_LLM_PROVIDER", "ollama")

    class OllamaEvalLLM(DeepEvalBaseLLM):
        """Ollama adapter for DeepEval LLM-as-judge."""

        def __init__(self, model: str = "llama3"):
            self.model_name = model
            self.base_url = OLLAMA_URL

        def load_model(self):
            return self.model_name

        def generate(self, prompt: str) -> str:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model_name, "prompt": prompt, "stream": False},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["response"]

        async def a_generate(self, prompt: str) -> str:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model_name, "prompt": prompt, "stream": False},
                    timeout=60,
                )
                response.raise_for_status()
                return response.json()["response"]

        def get_model_name(self) -> str:
            return f"ollama/{self.model_name}"

    def get_eval_llm() -> DeepEvalBaseLLM:
        """Factory: returns LLM based on EVAL_LLM_PROVIDER env var."""
        provider = EVAL_LLM_PROVIDER
        if provider == "ollama":
            return OllamaEvalLLM()
        elif provider == "github-models":
            # GPT-4o via GitHub Models token
            from deepeval.models import GPTModel
            return GPTModel(model="gpt-4o")
        elif provider == "openai":
            from deepeval.models import GPTModel
            return GPTModel(model="gpt-4o")
        else:
            raise ValueError(f"Unknown EVAL_LLM_PROVIDER: {provider}")
    ```
  - [ ] 2.3 Tratar erro de conexão Ollama com mensagem clara (skip test gracefully se Ollama indisponível)

- [ ] Task 3: Criar Golden Evaluation Dataset (AC: 5)
  - [ ] 3.1 Criar `tests/fixtures/golden_eval_dataset.json` com estrutura:
    ```json
    {
      "metadata": {
        "version": "1.0",
        "created": "2026-04-06",
        "description": "Golden evaluation dataset for ENEM RAG pipeline"
      },
      "retrieval_pairs": [
        {
          "id": "ret-001",
          "query": "questões sobre termoquímica ENEM",
          "expected_question_ids": ["gs-xxx"],
          "expected_subjects": ["ciencias_natureza"],
          "relevance_annotations": [
            {"question_id": "gs-xxx", "relevance": 1}
          ]
        }
      ],
      "generation_references": [
        {
          "id": "gen-001",
          "input_topic": "termoquímica",
          "input_subject": "ciencias_natureza",
          "reference_question": { ... },
          "evaluation_criteria": ["formato_enem", "5_alternativas", "enunciado_claro"]
        }
      ]
    }
    ```
  - [ ] 3.2 Povoar 30+ retrieval pairs a partir do `golden_set.json` existente (50 questões, 4 assuntos):
    - 8 queries por subject (ciencias_humanas, ciencias_natureza, linguagens, matematica)
    - Queries variadas: por tema, por ano, por tipo de questão
  - [ ] 3.3 Povoar 20+ generation references com questões ENEM reais do golden set como expected output
  - [ ] 3.4 Incluir queries difíceis: acentuação ("equação"), sinônimos ("ecologia" vs "meio ambiente"), multi-word

- [ ] Task 4: Fixtures pytest para avaliação (AC: 6)
  - [ ] 4.1 Criar `tests/conftest_eval.py`:
    ```python
    import json
    import pytest
    from pathlib import Path

    @pytest.fixture(scope="session")
    def golden_eval_dataset():
        path = Path(__file__).parent / "fixtures" / "golden_eval_dataset.json"
        return json.loads(path.read_text(encoding="utf-8"))

    @pytest.fixture(scope="session")
    def retrieval_pairs(golden_eval_dataset):
        return golden_eval_dataset["retrieval_pairs"]

    @pytest.fixture(scope="session")
    def generation_references(golden_eval_dataset):
        return golden_eval_dataset["generation_references"]

    @pytest.fixture(scope="session")
    def eval_llm():
        from src.rag_evaluation.llm_provider import get_eval_llm
        return get_eval_llm()
    ```

- [ ] Task 5: Smoke test DeepEval + Ollama (AC: 4, 7)
  - [ ] 5.1 Criar `tests/test_eval_smoke.py`:
    ```python
    import pytest
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    pytestmark = [pytest.mark.eval, pytest.mark.skipif(...)]

    def test_geval_smoke(eval_llm):
        """Smoke test: G-Eval with Ollama returns score in < 30s."""
        metric = GEval(
            name="Simple Quality",
            criteria="Rate if the text is well-written (1=poor, 4=excellent)",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=eval_llm,
        )
        test_case = LLMTestCase(
            input="Avalie este texto",
            actual_output="O Brasil é um país localizado na América do Sul."
        )
        metric.measure(test_case)
        assert metric.score is not None
        assert 0.0 <= metric.score <= 1.0
    ```
  - [ ] 5.2 Adicionar marker `eval` no `pyproject.toml`:
    ```toml
    markers = [
        "golden: golden set benchmark tests",
        "benchmark: performance benchmark tests",
        "eval: RAG evaluation tests (require Ollama)",
    ]
    ```
  - [ ] 5.3 Executar: `deepeval test run tests/test_eval_smoke.py` — deve passar com Ollama rodando

## Dev Notes

### Existing Infrastructure
- **Ollama** já está no Docker Compose como `llama3-service` na porta 11434 (container `llama3-enem-service`)
- **Golden set v3.0** em `tests/fixtures/golden_set.json` com 50 questões, 10/year 2020-2024, 4 subjects
- **Pytest markers** já existem: `golden`, `benchmark` — adicionar `eval`

### DeepEval LLM Provider Architecture
DeepEval aceita custom LLM via `DeepEvalBaseLLM` subclass. O adapter Ollama deve implementar:
- `generate(prompt) -> str` (sync)
- `a_generate(prompt) -> str` (async)
- `get_model_name() -> str`
- `load_model()` (pode retornar nome do modelo)

### Golden Eval Dataset Design
O dataset de avaliação é diferente do golden set de extração:
- **Golden set (existente):** Valida qualidade de extração de PDFs
- **Golden eval dataset (novo):** Valida qualidade do RAG (retrieval + generation)

Retrieval pairs mapeiam queries → question IDs esperados (do golden set).
Generation references fornecem questões ENEM reais como expected output para comparar com geração.

### Provider Strategy
- `ollama` (default): Custo zero, Llama 3 local, ideal para dev/CI
- `github-models`: GPT-4o via token GitHub, rate-limited, melhor qualidade de judge
- `openai`: GPT-4o via API key, pay-per-use, máxima qualidade

### References

- [Research: technical-rag-llm-evaluation-pipeline-research-2026-04-06.md] — DeepEval + Ollama integration patterns
- [Source: docker-compose.yml:44-61] — Ollama service config
- [Source: tests/fixtures/golden_set.json] — Base data for golden eval dataset
- [Source: pyproject.toml:38-45] — Existing optional dependencies pattern
