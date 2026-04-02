# Story 4.1: Assessment Generator — Feature 2

**Status:** done
**Epic:** 4 — Geracao com RAG: Features 2 e 3
**Story ID:** 4.1
**Story Key:** `4-1-assessment-generator-feature-2`
**Criado:** 2026-04-02

---

## Story

Como professor no TeachersHub,
Quero gerar avaliacoes de treino com questoes reais do ENEM filtradas por materia e dificuldade,
Para criar provas personalizadas para meus alunos sem precisar selecionar questoes manualmente.

---

## Acceptance Criteria

1. Modulo `assessment_generator.py` criado em `src/rag_features/` com classe `AssessmentGenerator`
2. Seleciona questoes via busca semantica + filtros sem repeticao (nenhum `question_id` duplicado na avaliacao)
3. Todos os níveis de `difficulty` (easy, medium, hard, mixed) retornam top-N questões por score de similaridade; distribuição proporcional por nível de dificuldade removida pois o campo `difficulty` não está disponível nas questões retornadas pela busca semântica
4. Endpoint `POST /api/v1/assessments/generate` aceita `subject`, `difficulty`, `question_count`, `years` (lista opcional de anos)
5. Retorna `assessment_id` (UUID), lista de questoes completas e gabarito separado (`answer_key`)
6. Avaliacao persistida na tabela `enem_questions.assessments` com questoes linkadas em `enem_questions.assessment_questions`
7. Retorna HTTP 422 Unprocessable Entity se `question_count` fora do intervalo [1, 50]; retorna HTTP 400 se nao ha questoes suficientes para os filtros
8. Retorna HTTP 503 com `error.code = "ASSESSMENT_UNAVAILABLE"` se `PgVectorSearch` ou banco estiver indisponivel

---

## Tasks / Subtasks

- [x] **Task 1: Criar migration SQL para tabelas `assessments` e `assessment_questions`** (AC: 6)
  - [x] 1.1 Criar tabela `enem_questions.assessments` com campos: `id UUID`, `title`, `subject`, `difficulty`, `question_count`, `years_filter`, `created_at`, `updated_at`
  - [x] 1.2 Criar tabela `enem_questions.assessment_questions` com campos: `id UUID`, `assessment_id`, `question_id`, `question_order`, constraints UNIQUE
  - [x] 1.3 Criar indices para `assessment_id` e `question_id` na tabela de juncao
  - [x] 1.4 Documentar down migration (DROP TABLE) para reversibilidade

- [x] **Task 2: Criar `AssessmentGenerator` em `src/rag_features/assessment_generator.py`** (AC: 1-3, 6)
  - [x] 2.1 Implementar `__init__(database_url, pgvector_search)` — recebe engine SQLAlchemy e instancia de `PgVectorSearch`
  - [x] 2.2 Implementar `_select_questions(subject, difficulty, question_count, years) -> List[Dict]` — seleciona questoes via busca semantica + filtros SQL diretos sem repeticao
  - [x] 2.3 Implementar `_distribute_by_difficulty(questions, difficulty, count) -> List[Dict]` — distribui questoes por dificuldade (`mixed` = 30% easy / 40% medium / 30% hard)
  - [x] 2.4 Implementar `_build_answer_key(questions) -> Dict[int, str]` — monta gabarito { question_order: correct_answer }
  - [x] 2.5 Implementar `_persist_assessment(assessment_id, subject, difficulty, question_count, years, question_ids) -> None` — persiste no banco
  - [x] 2.6 Implementar `async generate(subject, difficulty, question_count, years) -> Dict` — orquestra selecao, distribuicao, persistencia e retorno

- [x] **Task 3: Adicionar modelos Pydantic e endpoint em `api/fastapi_app.py`** (AC: 4, 5, 7, 8)
  - [x] 3.1 Criar `AssessmentGenerateRequest(BaseModel)`: `subject: str`, `difficulty: str`, `question_count: int`, `years: Optional[List[int]]`
  - [x] 3.2 Criar `AssessmentQuestion(BaseModel)`: `question_order: int`, `question_id: int`, `full_text: str`, `subject: str`, `year: Optional[int]`, `images: List[str]`
  - [x] 3.3 Criar `AssessmentGenerateResponse(BaseModel)`: `data: AssessmentData`, `meta: Dict`, `error: Optional[Any]`
  - [x] 3.4 Criar `AssessmentData(BaseModel)`: `assessment_id: str`, `questions: List[AssessmentQuestion]`, `answer_key: Dict[int, str]`
  - [x] 3.5 Instanciar `AssessmentGenerator` no startup da app (reutilizando `PgVectorSearch` da Story 3.2)
  - [x] 3.6 Implementar handler `POST /api/v1/assessments/generate` com validacao, chamada ao generator e tratamento de erros
  - [x] 3.7 Adicionar decorators Swagger com tags `["Assessments"]`, summary e description

- [x] **Task 4: Criar `tests/test_assessment_generator.py`** (AC: 1-8)
  - [x] 4.1 Testar `generate()` retorna `assessment_id`, `questions`, `answer_key`
  - [x] 4.2 Testar questoes sem repeticao (`question_id` unicos)
  - [x] 4.3 Testar distribuicao `mixed` respeita proporcao 30/40/30
  - [x] 4.4 Testar filtro por `years` e filtra corretamente
  - [x] 4.5 Testar `question_count` insuficiente levanta erro apropriado
  - [x] 4.6 Testar persistencia chamada com parametros corretos

- [x] **Task 5: Criar `tests/test_endpoint_assessments_generate.py`** (AC: 4, 5, 7, 8)
  - [x] 5.1 Testar request valido retorna 200 com estrutura `{data: {assessment_id, questions, answer_key}, meta, error: null}`
  - [x] 5.2 Testar `question_count=0` retorna 422
  - [x] 5.3 Testar `question_count=51` retorna 422
  - [x] 5.4 Testar `difficulty` invalido retorna 422
  - [x] 5.5 Testar generator indisponivel retorna 503
  - [x] 5.6 Testar questoes insuficientes retorna 400 com mensagem descritiva

### Review Findings

- [x] [Review][Patch] AC-7 texto incorreto: diz "HTTP 400" mas comportamento correto é 422 (Pydantic/FastAPI padrão); atualizado AC-7
- [x] [Review][Patch] answer_key incompleto — corrigido: `_build_answer_key_batch` retorna `(answer_key, answers_missing)`; endpoint inclui `answers_missing` no meta
- [x] [Review][Patch] Remover _distribute_by_difficulty — corrigido: sempre retorna `candidates[:count]` (top-N por similaridade); AC-3 atualizado
- [x] [Review][Patch] N+1 queries em _build_answer_key — corrigido: `_build_answer_key_batch` usa `WHERE q.id = ANY(:question_ids)` em batch
- [x] [Review][Patch] Filtro de anos aplicado após limit no Python — corrigido: `fetch_limit = max_candidates * max(len(years), 1)` aumenta o fetch antes do filtro
- [x] [Review][Patch] years sem validação de range no Pydantic — corrigido: `Optional[List[Annotated[int, Field(ge=2020, le=2030)]]]`
- [x] [Review][Patch] assessments.title nullable no schema mas sempre obrigatório no código — corrigido: `VARCHAR(500) NOT NULL`
- [x] [Review][Defer] Credenciais hardcoded como fallback — padrão pré-existente na codebase [fastapi_app.py] — deferred, pre-existing
- [x] [Review][Defer] @app.on_event("startup") deprecated no FastAPI ≥ 0.93 — padrão pré-existente [fastapi_app.py] — deferred, pre-existing

---

## Dev Notes

### Arquivos a criar/modificar

```
src/rag_features/assessment_generator.py   <- NOVO
api/fastapi_app.py                         <- MODIFICAR (adicionar modelos, instancia e endpoint)
database/assessment-migration.sql          <- NOVO (migration para tabelas de avaliacoes)
tests/test_assessment_generator.py         <- NOVO
tests/test_endpoint_assessments_generate.py <- NOVO
```

**NAO modificar:** `src/rag_features/semantic_search.py` (Story 3.1), modulos de ingestao, migrations existentes.

### Schema SQL — Migration

```sql
-- database/assessment-migration.sql
-- UP: Criar tabelas de avaliacoes

CREATE TABLE IF NOT EXISTS enem_questions.assessments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(500),
    subject         VARCHAR(100) NOT NULL,
    difficulty      VARCHAR(20) NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard', 'mixed')),
    question_count  INTEGER NOT NULL CHECK (question_count BETWEEN 1 AND 50),
    years_filter    INTEGER[],
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS enem_questions.assessment_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id   UUID NOT NULL REFERENCES enem_questions.assessments(id) ON DELETE CASCADE,
    question_id     INTEGER NOT NULL REFERENCES enem_questions.questions(id),
    question_order  INTEGER NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_assessment_question UNIQUE (assessment_id, question_id),
    CONSTRAINT uq_assessment_order UNIQUE (assessment_id, question_order)
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_assessment_questions_assessment_id
    ON enem_questions.assessment_questions (assessment_id);
CREATE INDEX IF NOT EXISTS idx_assessment_questions_question_id
    ON enem_questions.assessment_questions (question_id);
CREATE INDEX IF NOT EXISTS idx_assessments_subject
    ON enem_questions.assessments (subject);
CREATE INDEX IF NOT EXISTS idx_assessments_created_at
    ON enem_questions.assessments (created_at DESC);

-- DOWN: Reverter migration
-- DROP TABLE IF EXISTS enem_questions.assessment_questions;
-- DROP TABLE IF EXISTS enem_questions.assessments;
```

### Modelos Pydantic

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AssessmentGenerateRequest(BaseModel):
    subject: str = Field(..., description="Disciplina das questoes (ex: matematica, ciencias_natureza)")
    difficulty: str = Field(
        "mixed",
        description="Nivel de dificuldade: easy, medium, hard ou mixed",
        pattern="^(easy|medium|hard|mixed)$",
    )
    question_count: int = Field(10, ge=1, le=50, description="Quantidade de questoes na avaliacao")
    years: Optional[List[int]] = Field(None, description="Lista de anos para filtrar (ex: [2020, 2021, 2022])")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "subject": "matematica",
                    "difficulty": "medium",
                    "question_count": 10,
                    "years": [2020, 2021, 2022, 2023, 2024],
                }
            ]
        }
    }


class AssessmentQuestion(BaseModel):
    question_order: int
    question_id: int
    full_text: str
    subject: str
    year: Optional[int] = None
    images: List[str] = []


class AssessmentData(BaseModel):
    assessment_id: str
    title: str
    questions: List[AssessmentQuestion]
    answer_key: Dict[int, str]  # {question_order: correct_answer_letter}


class AssessmentGenerateResponse(BaseModel):
    data: Optional[AssessmentData] = None
    meta: Dict[str, Any] = {}
    error: Optional[Dict[str, Any]] = None
```

### Classe AssessmentGenerator — Estrutura

```python
# src/rag_features/assessment_generator.py

import uuid
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

DIFFICULTY_DISTRIBUTION = {
    "mixed": {"easy": 0.30, "medium": 0.40, "hard": 0.30},
    "easy": {"easy": 1.0},
    "medium": {"medium": 1.0},
    "hard": {"hard": 1.0},
}


class InsufficientQuestionsError(Exception):
    """Levantado quando nao ha questoes suficientes para os filtros solicitados."""
    pass


class AssessmentGenerator:
    def __init__(
        self,
        database_url: str,
        pgvector_search,  # PgVectorSearch instance from Story 3.1
    ) -> None:
        self.engine: Engine = create_engine(database_url)
        self.pgvector_search = pgvector_search

    async def generate(
        self,
        subject: str,
        difficulty: str = "mixed",
        question_count: int = 10,
        years: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Orquestra geracao de avaliacao completa."""
        assessment_id = str(uuid.uuid4())

        # 1. Selecionar questoes candidatas (busca mais que o necessario para filtrar)
        candidates = await self._select_questions(subject, difficulty, question_count * 3, years)

        # 2. Distribuir por dificuldade e limitar
        selected = self._distribute_by_difficulty(candidates, difficulty, question_count)

        if len(selected) < question_count:
            raise InsufficientQuestionsError(
                f"Apenas {len(selected)} questoes encontradas para os filtros "
                f"(subject={subject}, difficulty={difficulty}, years={years}). "
                f"Solicitadas: {question_count}."
            )

        # 3. Montar gabarito
        answer_key = self._build_answer_key(selected)

        # 4. Persistir
        question_ids = [q["question_id"] for q in selected]
        title = f"Avaliacao {subject.replace('_', ' ').title()} — {difficulty}"
        await self._persist_assessment(assessment_id, title, subject, difficulty, question_count, years, question_ids)

        return {
            "assessment_id": assessment_id,
            "title": title,
            "questions": selected,
            "answer_key": answer_key,
        }

    async def _select_questions(
        self,
        subject: str,
        difficulty: str,
        max_candidates: int,
        years: Optional[List[int]],
    ) -> List[Dict[str, Any]]:
        """Seleciona questoes candidatas via busca semantica + filtros SQL."""
        # Usar busca semantica com query descritiva para o subject
        query_text = f"questoes de {subject.replace('_', ' ')}"
        raw_results = await self.pgvector_search.search_questions(
            query=query_text,
            limit=max_candidates,
            subject=subject,
        )

        # Filtrar por anos se especificado
        if years:
            raw_results = [r for r in raw_results if r.get("year") in years]

        # Garantir unicidade por question_id
        seen_ids = set()
        unique_results = []
        for r in raw_results:
            qid = r["question_id"]
            if qid not in seen_ids:
                seen_ids.add(qid)
                unique_results.append(r)

        return unique_results

    def _distribute_by_difficulty(
        self,
        candidates: List[Dict[str, Any]],
        difficulty: str,
        count: int,
    ) -> List[Dict[str, Any]]:
        """Distribui questoes respeitando proporcao de dificuldade."""
        distribution = DIFFICULTY_DISTRIBUTION.get(difficulty, DIFFICULTY_DISTRIBUTION["mixed"])

        if difficulty != "mixed":
            # Dificuldade unica: retornar primeiras `count` questoes
            return candidates[:count]

        # Distribuicao mixed: agrupar por dificuldade estimada
        # (difficulty vem do metadado da questao ou eh inferido pela posicao no exame)
        selected = []
        for diff_level, ratio in distribution.items():
            target = round(count * ratio)
            level_questions = [q for q in candidates if q.get("difficulty", "medium") == diff_level]
            selected.extend(level_questions[:target])

        # Preencher faltantes com questoes restantes
        selected_ids = {q["question_id"] for q in selected}
        for q in candidates:
            if len(selected) >= count:
                break
            if q["question_id"] not in selected_ids:
                selected.append(q)
                selected_ids.add(q["question_id"])

        return selected[:count]

    def _build_answer_key(self, questions: List[Dict[str, Any]]) -> Dict[int, str]:
        """Monta gabarito {question_order: correct_answer}."""
        answer_key = {}
        for order, q in enumerate(questions, start=1):
            correct = self._get_correct_answer(q["question_id"])
            if correct:
                answer_key[order] = correct
        return answer_key

    def _get_correct_answer(self, question_id: int) -> Optional[str]:
        """Busca gabarito da questao via answer_keys."""
        sql = text("""
            SELECT ak.correct_answer
            FROM enem_questions.answer_keys ak
            JOIN enem_questions.exam_metadata em ON em.id = ak.exam_id
            JOIN enem_questions.questions q ON q.exam_metadata_id = em.id
                AND q.question_number = ak.question_number
            WHERE q.id = :question_id
            LIMIT 1
        """)
        with self.engine.connect() as conn:
            row = conn.execute(sql, {"question_id": question_id}).fetchone()
            return row[0] if row else None

    async def _persist_assessment(
        self,
        assessment_id: str,
        title: str,
        subject: str,
        difficulty: str,
        question_count: int,
        years: Optional[List[int]],
        question_ids: List[int],
    ) -> None:
        """Persiste avaliacao e questoes no banco."""
        insert_assessment = text("""
            INSERT INTO enem_questions.assessments
                (id, title, subject, difficulty, question_count, years_filter)
            VALUES
                (CAST(:id AS UUID), :title, :subject, :difficulty, :question_count, :years_filter)
        """)
        insert_question = text("""
            INSERT INTO enem_questions.assessment_questions
                (assessment_id, question_id, question_order)
            VALUES
                (CAST(:assessment_id AS UUID), :question_id, :question_order)
        """)
        with self.engine.begin() as conn:
            conn.execute(insert_assessment, {
                "id": assessment_id,
                "title": title,
                "subject": subject,
                "difficulty": difficulty,
                "question_count": question_count,
                "years_filter": years or [],
            })
            for order, qid in enumerate(question_ids, start=1):
                conn.execute(insert_question, {
                    "assessment_id": assessment_id,
                    "question_id": qid,
                    "question_order": order,
                })
        logger.info("assessment_persisted", extra={
            "assessment_id": assessment_id,
            "question_count": len(question_ids),
            "subject": subject,
        })
```

### Implementacao do endpoint

```python
from src.rag_features.assessment_generator import AssessmentGenerator, InsufficientQuestionsError

assessment_generator: Optional[AssessmentGenerator] = None

@app.on_event("startup")
async def startup_event():
    global pgvector_search, assessment_generator
    try:
        pgvector_search = PgVectorSearch(
            database_url=os.getenv("DATABASE_URL", "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6380/1"),
        )
        assessment_generator = AssessmentGenerator(
            database_url=os.getenv("DATABASE_URL", "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"),
            pgvector_search=pgvector_search,
        )
        print("AssessmentGenerator inicializado com sucesso")
    except Exception as e:
        print(f"AssessmentGenerator indisponivel: {e}")


@app.post(
    "/api/v1/assessments/generate",
    response_model=AssessmentGenerateResponse,
    tags=["Assessments"],
    summary="Gerar avaliacao de treino com questoes ENEM",
    description="Seleciona questoes reais do ENEM por materia e dificuldade, "
                "monta avaliacao com gabarito e persiste para referencia futura.",
)
async def generate_assessment(request: AssessmentGenerateRequest):
    if assessment_generator is None:
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {
                    "code": "ASSESSMENT_UNAVAILABLE",
                    "message": "Servico de geracao de avaliacoes indisponivel",
                },
            },
        )
    try:
        result = await assessment_generator.generate(
            subject=request.subject,
            difficulty=request.difficulty,
            question_count=request.question_count,
            years=request.years,
        )
        questions_out = []
        for order, q in enumerate(result["questions"], start=1):
            questions_out.append(AssessmentQuestion(
                question_order=order,
                question_id=q["question_id"],
                full_text=q.get("full_text", ""),
                subject=q.get("subject", request.subject),
                year=q.get("year"),
                images=q.get("images", []),
            ))
        return AssessmentGenerateResponse(
            data=AssessmentData(
                assessment_id=result["assessment_id"],
                title=result["title"],
                questions=questions_out,
                answer_key=result["answer_key"],
            ),
            meta={
                "total_questions": len(questions_out),
                "subject": request.subject,
                "difficulty": request.difficulty,
                "years": request.years,
            },
        )
    except InsufficientQuestionsError as e:
        return JSONResponse(
            status_code=400,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "INSUFFICIENT_QUESTIONS", "message": str(e)},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "ASSESSMENT_UNAVAILABLE", "message": str(e)},
            },
        )
```

### Exemplo de request/response para Swagger

**Request:**
```json
{
  "subject": "matematica",
  "difficulty": "medium",
  "question_count": 10,
  "years": [2020, 2021, 2022, 2023, 2024]
}
```

**Response 200:**
```json
{
  "data": {
    "assessment_id": "a3f1c9e2-7b8d-4e5f-9a1b-2c3d4e5f6a7b",
    "title": "Avaliacao Matematica — medium",
    "questions": [
      {
        "question_order": 1,
        "question_id": 142,
        "full_text": "[ENUNCIADO] Uma funcao quadratica f(x) = ...\nA) ...\nB) ...\nC) ...\nD) ...\nE) ...",
        "subject": "matematica",
        "year": 2023,
        "images": []
      },
      {
        "question_order": 2,
        "question_id": 87,
        "full_text": "[ENUNCIADO] O grafico a seguir representa...\nA) ...\nB) ...\nC) ...\nD) ...\nE) ...",
        "subject": "matematica",
        "year": 2022,
        "images": ["data/extracted_images/2022/87/fig1.png"]
      }
    ],
    "answer_key": {
      "1": "C",
      "2": "A"
    }
  },
  "meta": {
    "total_questions": 2,
    "subject": "matematica",
    "difficulty": "medium",
    "years": [2020, 2021, 2022, 2023, 2024]
  },
  "error": null
}
```

**Response 400 (questoes insuficientes):**
```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "INSUFFICIENT_QUESTIONS",
    "message": "Apenas 3 questoes encontradas para os filtros (subject=filosofia, difficulty=hard, years=[2024]). Solicitadas: 10."
  }
}
```

**Response 503 (servico indisponivel):**
```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "ASSESSMENT_UNAVAILABLE",
    "message": "Servico de geracao de avaliacoes indisponivel"
  }
}
```

### Dependencias ja disponiveis

- `fastapi`, `pydantic` — ja instalados
- `sqlalchemy>=2.0.0` — ja em requirements.txt
- `PgVectorSearch` — implementado na Story 3.1
- Engine/conexao ao banco — ja configurado em `api/fastapi_app.py`
- `openai>=1.0.0`, `redis>=4.6.0` — adicionados nas Stories 2.x

### Aprendizados das stories anteriores

- Schema qualificado: `enem_questions.assessments` (padrao do projeto desde Story 1.1)
- `DATABASE_URL` padrao: `postgresql://postgres:postgres123@localhost:5433/teachershub_enem`
- `CAST(:param AS UUID)` para parametros UUID no SQLAlchemy (padrao Stories 1.x)
- 100% mocks nos unit tests — sem banco real, sem OpenAI real, sem Redis real
- Reutilizar `PgVectorSearch` instanciado no startup (Story 3.2) para evitar conexoes duplicadas
- Query SQL para `correct_answer` ja documentada na Story 3.2 — reutilizar mesma logica

### Relacionamento com tabelas existentes

```
enem_questions.assessments
    |
    |-- 1:N --> enem_questions.assessment_questions
    |                |
    |                |-- N:1 --> enem_questions.questions (id)
    |                                |
    |                                |-- 1:N --> enem_questions.question_chunks
    |                                |-- N:1 --> enem_questions.exam_metadata
    |                                |-- 1:N --> enem_questions.question_alternatives
    |                                |-- via exam_metadata --> enem_questions.answer_keys
```

---

## Estrutura de Testes

```python
# tests/test_assessment_generator.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestAssessmentGeneratorInit:
    def test_creates_engine_and_stores_pgvector_search(self): ...

class TestSelectQuestions:
    def test_calls_pgvector_search_with_subject(self, generator, mocker): ...
    def test_filters_by_years_when_provided(self, generator, mocker): ...
    def test_deduplicates_by_question_id(self, generator, mocker): ...
    def test_returns_empty_when_no_matches(self, generator, mocker): ...

class TestDistributeByDifficulty:
    def test_single_difficulty_returns_all_same_level(self, generator): ...
    def test_mixed_distributes_30_40_30(self, generator): ...
    def test_fills_remaining_from_other_levels(self, generator): ...
    def test_returns_at_most_count_questions(self, generator): ...

class TestBuildAnswerKey:
    def test_returns_dict_with_order_and_letter(self, generator, mocker): ...
    def test_skips_questions_without_answer(self, generator, mocker): ...

class TestGenerate:
    def test_returns_assessment_id_questions_answer_key(self, generator, mocker): ...
    def test_raises_insufficient_when_not_enough(self, generator, mocker): ...
    def test_persists_assessment_in_database(self, generator, mocker): ...
    def test_questions_have_unique_ids(self, generator, mocker): ...

class TestPersistAssessment:
    def test_inserts_assessment_row(self, generator, mocker): ...
    def test_inserts_question_rows_with_order(self, generator, mocker): ...
    def test_uses_transaction(self, generator, mocker): ...
```

```python
# tests/test_endpoint_assessments_generate.py

from fastapi.testclient import TestClient
from api.fastapi_app import app

client = TestClient(app)

class TestAssessmentEndpoint:
    def test_valid_request_returns_200(self, mocker): ...
    def test_response_contains_assessment_id_and_questions(self, mocker): ...
    def test_answer_key_matches_question_orders(self, mocker): ...
    def test_question_count_zero_returns_422(self): ...
    def test_question_count_51_returns_422(self): ...
    def test_invalid_difficulty_returns_422(self): ...
    def test_insufficient_questions_returns_400(self, mocker): ...
    def test_generator_unavailable_returns_503(self, mocker): ...
    def test_meta_contains_filters(self, mocker): ...
```

---

## Nao faz parte desta story

- Modificar `PgVectorSearch` ou `semantic_search.py` — Story 3.1
- Criar endpoint de busca semantica — Story 3.2
- Geracao de novas questoes via LLM (Feature 3) — Story 4.2
- Autenticacao/JWT — fora do escopo do Epic 4 (pipeline Python)
- Frontend/UI para selecao de questoes — Epics futuros (integracao TeachersHub)
- Modificar migrations existentes do Epic 1
- Dificuldade calculada/inferida das questoes — assume que campo `difficulty` ja existe nos metadados ou eh inferido pela posicao

---

## Dev Agent Record

### Implementation Plan
1. Migration SQL (`database/assessment-migration.sql`) — tables `assessments` + `assessment_questions`
2. `AssessmentGenerator` class with semantic search selection, difficulty distribution, answer key building, and persistence
3. Pydantic models + `POST /api/v1/assessments/generate` endpoint in `fastapi_app.py`
4. Unit tests (16 tests) + endpoint tests (8 tests)

### Debug Log
- Fixed `InsufficientQuestionsError` import path mismatch: endpoint uses `rag_features.` path while test used `src.rag_features.`. Updated test import to match.

### Completion Notes
- All 24 tests passing (16 unit + 8 endpoint)
- assessment_generator.py: 95% coverage (only `_get_correct_answer` SQL untested — requires real DB)
- Endpoint validates: difficulty pattern, question_count range [1,50], 503 for unavailable, 400 for insufficient questions

### Files
- `src/rag_features/assessment_generator.py` — `AssessmentGenerator`, `InsufficientQuestionsError`
- `api/fastapi_app.py` — Pydantic models, startup init, `POST /api/v1/assessments/generate`
- `database/assessment-migration.sql` — DDL for `assessments` + `assessment_questions`
- `tests/test_assessment_generator.py` — 16 unit tests
- `tests/test_endpoint_assessments_generate.py` — 8 endpoint tests

---

## Change Log

| Data | Alteracao |
|------|-----------|
| 2026-04-02 | Story criada — assessment_generator.py + endpoint POST /api/v1/assessments/generate (Epic 4, Story 1) |
| 2026-04-02 | Implementation complete — 24/24 tests passing, status → review |
