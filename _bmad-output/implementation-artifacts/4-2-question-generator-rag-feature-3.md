# Story 4.2: Question Generator RAG — Feature 3

**Status:** review
**Epic:** 4 — Geração com RAG: Features 2 e 3
**Story ID:** 4.2
**Story Key:** `4-2-question-generator-rag-feature-3`
**Criado:** 2026-04-02

---

## Story

Como professor no TeachersHub,
Quero gerar novas questões inéditas no estilo ENEM baseadas em um assunto e nível de dificuldade,
Para criar material complementar além do corpus existente, personalizado para as necessidades dos meus alunos.

---

## Acceptance Criteria

1. Módulo `question_generator.py` atualizado em `src/rag_features/` — classe `RAGQuestionGenerator` substitui `EnemQuestionGenerator` legado, usando padrão OpenAI SDK v1+
2. Usa chunks `context` (tipo `chunk_type='context'`) como contexto RAG para o GPT-4o gerar questões inspiradas no estilo ENEM real
3. Prompt instrui GPT-4o a seguir formato ENEM: 5 alternativas (A–E), exatamente 1 correta, texto-base quando relevante ao tema
4. Questão gerada inclui: `stem` (enunciado), `alternatives` (A–E), `answer` (letra correta), `explanation` (explicação da resposta correta)
5. Inclui `source_context_ids` (UUIDs dos chunks usados como contexto RAG) em cada questão gerada
6. Endpoint `POST /api/v1/questions/generate` aceita `subject` (obrigatório), `topic` (obrigatório), `difficulty` (default="medium"), `count` (default=1, máx=5), `style` (default="enem")
7. Questões geradas NÃO são persistidas no corpus principal — ficam em tabela separada `enem_questions.generated_questions`
8. Retorna HTTP 400 para `count` fora do intervalo [1, 5] ou `subject`/`topic` vazios
9. Retorna HTTP 503 com `error.code = "GENERATION_UNAVAILABLE"` se `PgVectorSearch` ou OpenAI não estiverem disponíveis
10. Endpoint documentado no Swagger com exemplos de request/response

---

## Tasks / Subtasks

- [x] **Task 1: Criar migration para tabela `generated_questions`** (AC: 7)
  - [x] 1.1 Criar `database/generated-questions-migration.sql` com schema da tabela `enem_questions.generated_questions`
  - [x] 1.2 Incluir índices por `subject`, `created_at` e `requested_by`
  - [x] 1.3 Validar que migration é idempotente (`IF NOT EXISTS`)

- [x] **Task 2: Atualizar `src/rag_features/question_generator.py` — classe `RAGQuestionGenerator`** (AC: 1–5)
  - [x] 2.1 Manter classe legada `EnemQuestionGenerator` comentada/depreciada; criar `RAGQuestionGenerator` no mesmo arquivo
  - [x] 2.2 Implementar `__init__(database_url, openai_api_key, redis_url)` — instancia `PgVectorSearch` (Story 3.1) e `openai.AsyncOpenAI` client
  - [x] 2.3 Implementar `_fetch_context_chunks(subject, topic, limit=5) -> List[Dict]` — busca chunks `context` via `PgVectorSearch` para alimentar o prompt RAG
  - [x] 2.4 Implementar `_build_generation_prompt(topic, subject, difficulty, style, context_chunks) -> List[Dict]` — constrói mensagens system+user com template de geração
  - [x] 2.5 Implementar `generate_questions(subject, topic, difficulty, count, style) -> List[Dict]` — chama GPT-4o, parseia JSON, retorna lista de questões com `source_context_ids`
  - [x] 2.6 Implementar `_parse_llm_response(content: str) -> List[Dict]` — extrai JSON da resposta GPT-4o, com fallback robusto
  - [x] 2.7 Implementar `_persist_generated(questions, subject, topic, difficulty) -> List[UUID]` — salva na tabela `generated_questions`, retorna IDs

- [x] **Task 3: Adicionar modelos Pydantic em `api/fastapi_app.py`** (AC: 6, 8, 10)
  - [x] 3.1 Criar `QuestionGenerateRequest(BaseModel)`: `subject: str`, `topic: str`, `difficulty: str = Field("medium", pattern="^(easy|medium|hard)$")`, `count: int = Field(1, ge=1, le=5)`, `style: str = Field("enem")`
  - [x] 3.2 Criar `GeneratedQuestion(BaseModel)`: `id: Optional[UUID]`, `stem: str`, `context_text: Optional[str]`, `alternatives: Dict[str, str]`, `answer: str`, `explanation: str`, `source_context_ids: List[str]`
  - [x] 3.3 Criar `QuestionGenerateResponse(BaseModel)`: `data: List[GeneratedQuestion]`, `meta: Dict[str, Any]`, `error: Optional[Any] = None`

- [x] **Task 4: Implementar endpoint `POST /api/v1/questions/generate`** (AC: 6–10)
  - [x] 4.1 Instanciar `RAGQuestionGenerator` na startup da app (similar ao `PgVectorSearch` da Story 3.2)
  - [x] 4.2 Criar handler `async def generate_questions(request: QuestionGenerateRequest)`
  - [x] 4.3 Chamar `rag_question_generator.generate_questions(subject, topic, difficulty, count, style)`
  - [x] 4.4 Construir `meta`: `{total: len(results), subject, topic, difficulty, style, model: "gpt-4o", generated_at}`
  - [x] 4.5 Capturar exceções: retornar 503 com `error.code = "GENERATION_UNAVAILABLE"`
  - [x] 4.6 Adicionar decorator Swagger com tags, summary e description

- [x] **Task 5: Criar `tests/test_question_generator_rag.py`** (AC: 1–10)
  - [x] 5.1 Testar `_fetch_context_chunks` retorna chunks com `chunk_type='context'`
  - [x] 5.2 Testar `_build_generation_prompt` inclui contexto RAG e instruções de formato ENEM
  - [x] 5.3 Testar `generate_questions` retorna questões com campos obrigatórios (`stem`, `alternatives`, `answer`, `explanation`, `source_context_ids`)
  - [x] 5.4 Testar que `source_context_ids` contém UUIDs válidos dos chunks usados
  - [x] 5.5 Testar `_parse_llm_response` com JSON válido e com resposta mal-formatada (fallback)
  - [x] 5.6 Testar `_persist_generated` insere na tabela `generated_questions` (não na `question_chunks`)

- [x] **Task 6: Criar `tests/test_endpoint_question_generate.py`** (AC: 6–10)
  - [x] 6.1 Testar request válido retorna 200 com estrutura `{data, meta, error: null}`
  - [x] 6.2 Testar `count=6` retorna 422 (Pydantic validation)
  - [x] 6.3 Testar `subject` vazio retorna 422
  - [x] 6.4 Testar `difficulty` inválido retorna 422
  - [x] 6.5 Testar serviço indisponível retorna 503 com `error.code = "GENERATION_UNAVAILABLE"`
  - [x] 6.6 Testar resposta inclui `source_context_ids` em cada questão
  - [x] 6.7 Testar `meta` contém `subject`, `topic`, `difficulty`, `model`

---

## Dev Notes

### Arquivos a modificar / criar

```
src/rag_features/question_generator.py    ← MODIFICAR (adicionar RAGQuestionGenerator)
api/fastapi_app.py                        ← MODIFICAR (adicionar modelos e endpoint)
database/generated-questions-migration.sql ← NOVO
tests/test_question_generator_rag.py      ← NOVO
tests/test_endpoint_question_generate.py  ← NOVO
```

**NÃO modificar:** `src/rag_features/semantic_search.py` (Story 3.1), módulos de ingestão, tabela `question_chunks`.

### Schema SQL — tabela `generated_questions`

```sql
-- Migration: tabela para questões geradas por IA (Feature 3)
-- NÃO faz parte do corpus principal — isolada para evitar contaminação

CREATE TABLE IF NOT EXISTS enem_questions.generated_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject         VARCHAR(100) NOT NULL,
    topic           VARCHAR(255) NOT NULL,
    difficulty      VARCHAR(20) NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    style           VARCHAR(50) NOT NULL DEFAULT 'enem',
    stem            TEXT NOT NULL,                    -- enunciado da questão
    context_text    TEXT,                             -- texto-base gerado (quando aplicável)
    alternatives    JSONB NOT NULL,                   -- {"A": "...", "B": "...", ...}
    answer          CHAR(1) NOT NULL CHECK (answer IN ('A', 'B', 'C', 'D', 'E')),
    explanation     TEXT NOT NULL,                    -- explicação da resposta correta
    source_context_ids UUID[] NOT NULL DEFAULT '{}',  -- IDs dos chunks usados como contexto RAG
    model_used      VARCHAR(50) NOT NULL DEFAULT 'gpt-4o',
    requested_by    VARCHAR(255),                     -- futuro: user_id do professor
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para consultas frequentes
CREATE INDEX IF NOT EXISTS idx_gen_questions_subject
    ON enem_questions.generated_questions (subject);
CREATE INDEX IF NOT EXISTS idx_gen_questions_created_at
    ON enem_questions.generated_questions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gen_questions_requested_by
    ON enem_questions.generated_questions (requested_by);
CREATE INDEX IF NOT EXISTS idx_gen_questions_difficulty
    ON enem_questions.generated_questions (difficulty);
```

### Prompt template GPT-4o para geração de questões

```python
SYSTEM_PROMPT = """Você é um especialista em elaboração de questões no padrão ENEM (Exame Nacional do Ensino Médio do Brasil).
Você recebe textos-base reais de questões ENEM como referência de estilo e contexto.
Sua tarefa é gerar questões INÉDITAS que sigam rigorosamente o formato ENEM.

Regras obrigatórias:
1. Cada questão deve ter um enunciado claro e contextualizado
2. Quando relevante ao tema, inclua um texto-base (trecho, gráfico descrito, situação-problema)
3. Exatamente 5 alternativas: A, B, C, D, E
4. Exatamente 1 alternativa correta
5. Alternativas incorretas devem ser plausíveis (distratores bem construídos)
6. Forneça explicação detalhada de por que a alternativa correta é a certa
7. Mantenha o nível de dificuldade solicitado

Responda EXCLUSIVAMENTE em JSON válido, sem markdown, sem backticks."""

USER_PROMPT_TEMPLATE = """Gere {count} questão(ões) no estilo ENEM sobre o assunto abaixo.

**Matéria:** {subject}
**Tópico:** {topic}
**Dificuldade:** {difficulty}

### Contexto de referência (textos-base reais do ENEM):
{context_chunks_text}

### Formato de resposta (JSON array):
[
  {{
    "stem": "Enunciado completo da questão com contextualização",
    "context_text": "Texto-base da questão (ou null se não aplicável)",
    "alternatives": {{
      "A": "Texto da alternativa A",
      "B": "Texto da alternativa B",
      "C": "Texto da alternativa C",
      "D": "Texto da alternativa D",
      "E": "Texto da alternativa E"
    }},
    "answer": "LETRA_CORRETA",
    "explanation": "Explicação detalhada de por que esta é a resposta correta"
  }}
]"""
```

### Classe `RAGQuestionGenerator` — estrutura

```python
from openai import AsyncOpenAI
from src.rag_features.semantic_search import PgVectorSearch
from sqlalchemy import create_engine, text
from typing import List, Dict, Any, Optional
import json
import logging
import os

logger = logging.getLogger(__name__)

class RAGQuestionGenerator:
    """Gerador de questões ENEM usando RAG com contexto pgvector + GPT-4o."""

    def __init__(
        self,
        database_url: str,
        openai_api_key: str,
        redis_url: str = "redis://localhost:6380/1",
        model: str = "gpt-4o",
    ) -> None:
        self.engine = create_engine(database_url)
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.model = model
        self.pgvector_search = PgVectorSearch(
            database_url=database_url,
            openai_api_key=openai_api_key,
            redis_url=redis_url,
        )

    async def _fetch_context_chunks(
        self, subject: str, topic: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Busca chunks context do corpus ENEM para alimentar o prompt RAG."""
        results = await self.pgvector_search.search_questions(
            query=f"{subject} {topic}",
            limit=limit,
            subject=subject,
        )
        # Filtrar para chunks de contexto quando disponível
        # Retorna question_id + content para referência
        return results

    async def generate_questions(
        self,
        subject: str,
        topic: str,
        difficulty: str = "medium",
        count: int = 1,
        style: str = "enem",
    ) -> List[Dict[str, Any]]:
        """Gera questões inéditas usando RAG context + GPT-4o."""
        # 1. Buscar contexto RAG
        context_chunks = await self._fetch_context_chunks(subject, topic)
        source_context_ids = [str(c.get("chunk_id", c.get("question_id", ""))) for c in context_chunks]

        # 2. Construir prompt
        messages = self._build_generation_prompt(
            topic=topic,
            subject=subject,
            difficulty=difficulty,
            count=count,
            style=style,
            context_chunks=context_chunks,
        )

        # 3. Chamar GPT-4o
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=3000 * count,
        )

        content = response.choices[0].message.content

        # 4. Parsear resposta
        questions = self._parse_llm_response(content)

        # 5. Adicionar source_context_ids
        for q in questions:
            q["source_context_ids"] = source_context_ids

        # 6. Persistir na tabela generated_questions
        ids = self._persist_generated(questions, subject, topic, difficulty)
        for q, qid in zip(questions, ids):
            q["id"] = str(qid)

        return questions[:count]

    def _build_generation_prompt(self, topic, subject, difficulty, count, style, context_chunks):
        """Monta mensagens system + user com contexto RAG."""
        context_text = "\n\n---\n\n".join(
            [c.get("full_text", c.get("chunk_content", "")) for c in context_chunks]
        ) or "(Nenhum contexto encontrado no corpus)"

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                count=count,
                subject=subject,
                topic=topic,
                difficulty=difficulty,
                context_chunks_text=context_text,
            )},
        ]

    def _parse_llm_response(self, content: str) -> List[Dict[str, Any]]:
        """Extrai JSON da resposta GPT-4o com fallback robusto."""
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                parsed = [parsed]
            return parsed
        except json.JSONDecodeError:
            # Tentar extrair JSON de bloco markdown
            import re
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError("Resposta do LLM não contém JSON válido")

    def _persist_generated(
        self, questions: List[Dict], subject: str, topic: str, difficulty: str
    ) -> List[str]:
        """Persiste questões geradas na tabela generated_questions."""
        ids = []
        sql = text("""
            INSERT INTO enem_questions.generated_questions
                (subject, topic, difficulty, stem, context_text, alternatives, answer, explanation, source_context_ids, model_used)
            VALUES
                (:subject, :topic, :difficulty, :stem, :context_text, :alternatives::jsonb, :answer, :explanation, :source_context_ids, :model_used)
            RETURNING id
        """)
        with self.engine.begin() as conn:
            for q in questions:
                row = conn.execute(sql, {
                    "subject": subject,
                    "topic": topic,
                    "difficulty": difficulty,
                    "stem": q.get("stem", ""),
                    "context_text": q.get("context_text"),
                    "alternatives": json.dumps(q.get("alternatives", {})),
                    "answer": q.get("answer", "A"),
                    "explanation": q.get("explanation", ""),
                    "source_context_ids": q.get("source_context_ids", []),
                    "model_used": self.model,
                }).fetchone()
                ids.append(str(row[0]))
        return ids
```

### Modelos Pydantic — endpoint

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID

class QuestionGenerateRequest(BaseModel):
    subject: str = Field(..., min_length=1, description="Matéria (ex: historia, matematica)")
    topic: str = Field(..., min_length=1, description="Tópico específico (ex: Segunda Guerra Mundial)")
    difficulty: str = Field("medium", pattern="^(easy|medium|hard)$", description="Nível de dificuldade")
    count: int = Field(1, ge=1, le=5, description="Número de questões a gerar (máx 5)")
    style: str = Field("enem", description="Estilo da questão (default: enem)")

class GeneratedQuestion(BaseModel):
    id: Optional[str] = Field(None, description="UUID da questão gerada")
    stem: str = Field(..., description="Enunciado da questão")
    context_text: Optional[str] = Field(None, description="Texto-base (quando aplicável)")
    alternatives: Dict[str, str] = Field(..., description="Alternativas A-E")
    answer: str = Field(..., description="Letra da alternativa correta")
    explanation: str = Field(..., description="Explicação da resposta correta")
    source_context_ids: List[str] = Field(default_factory=list, description="IDs dos chunks usados como contexto RAG")

class QuestionGenerateResponse(BaseModel):
    data: List[GeneratedQuestion]
    meta: Dict[str, Any]
    error: Optional[Any] = None
```

### Implementação do endpoint

```python
from src.rag_features.question_generator import RAGQuestionGenerator

rag_question_generator: Optional[RAGQuestionGenerator] = None

@app.on_event("startup")
async def startup_question_generator():
    global rag_question_generator
    try:
        rag_question_generator = RAGQuestionGenerator(
            database_url=os.getenv("DATABASE_URL", "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6380/1"),
        )
        print("RAGQuestionGenerator inicializado com sucesso")
    except Exception as e:
        print(f"RAGQuestionGenerator indisponível: {e}")


@app.post(
    "/api/v1/questions/generate",
    response_model=QuestionGenerateResponse,
    tags=["RAG"],
    summary="Gerar questões inéditas no estilo ENEM",
    description="Usa RAG com contexto de questões reais do ENEM para gerar questões novas via GPT-4o.",
)
async def generate_questions(request: QuestionGenerateRequest):
    if rag_question_generator is None:
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "GENERATION_UNAVAILABLE", "message": "Serviço de geração de questões indisponível"},
            },
        )
    try:
        questions = await rag_question_generator.generate_questions(
            subject=request.subject,
            topic=request.topic,
            difficulty=request.difficulty,
            count=request.count,
            style=request.style,
        )
        return QuestionGenerateResponse(
            data=[GeneratedQuestion(**q) for q in questions],
            meta={
                "total": len(questions),
                "subject": request.subject,
                "topic": request.topic,
                "difficulty": request.difficulty,
                "style": request.style,
                "model": "gpt-4o",
                "generated_at": datetime.now().isoformat(),
            },
        )
    except Exception as e:
        logger.error(f"Erro na geração de questões: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "GENERATION_UNAVAILABLE", "message": str(e)},
            },
        )
```

### Exemplo de request/response para Swagger

**Request:**
```json
{
  "subject": "historia",
  "topic": "Segunda Guerra Mundial",
  "difficulty": "hard",
  "count": 2,
  "style": "enem"
}
```

**Response 200:**
```json
{
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "stem": "Durante a Segunda Guerra Mundial, a participação do Brasil no conflito foi marcada pelo envio da Força Expedicionária Brasileira (FEB) à Itália em 1944. Considerando o contexto político e social do Estado Novo, é correto afirmar que a entrada do Brasil na guerra:",
      "context_text": "A participação brasileira na Segunda Guerra Mundial representou um paradoxo político: um regime autoritário aliou-se às democracias para combater o fascismo europeu.",
      "alternatives": {
        "A": "foi motivada exclusivamente por pressão econômica dos Estados Unidos sobre o governo Vargas",
        "B": "evidenciou contradições do regime varguista ao lutar contra regimes totalitários sendo ele próprio autoritário",
        "C": "ocorreu apenas após a queda do Estado Novo e a redemocratização do país",
        "D": "representou decisão unilateral das Forças Armadas sem participação do governo civil",
        "E": "limitou-se ao envio de suprimentos sem participação militar direta em combate"
      },
      "answer": "B",
      "explanation": "A alternativa B é correta porque o Brasil, sob o Estado Novo de Getúlio Vargas (um regime autoritário com censura e repressão política), declarou guerra ao Eixo e enviou tropas para lutar contra o fascismo na Europa. Essa contradição — um governo autoritário lutando contra regimes totalitários — é amplamente reconhecida pela historiografia como um dos paradoxos da era Vargas.",
      "source_context_ids": ["uuid-chunk-1", "uuid-chunk-2", "uuid-chunk-3"]
    }
  ],
  "meta": {
    "total": 1,
    "subject": "historia",
    "topic": "Segunda Guerra Mundial",
    "difficulty": "hard",
    "style": "enem",
    "model": "gpt-4o",
    "generated_at": "2026-04-02T14:30:00"
  },
  "error": null
}
```

**Response 503:**
```json
{
  "data": null,
  "meta": {},
  "error": {"code": "GENERATION_UNAVAILABLE", "message": "OPENAI_API_KEY não configurada"}
}
```

### Dependências

- `openai>=1.0.0` — SDK v1 com `AsyncOpenAI` ✅ (Story 2.1)
- `PgVectorSearch` — Story 3.1 (busca de contexto RAG)
- `sqlalchemy>=2.0.0` — persistência na `generated_questions` ✅
- `fastapi`, `pydantic` — já instalados ✅
- Padrões de endpoint — Story 3.2 (formato de resposta, startup pattern, error handling)

### Aprendizados das stories anteriores

- Schema qualificado: `enem_questions.generated_questions` (manter padrão do Epic 1)
- `DATABASE_URL` padrão: `postgresql://postgres:postgres123@localhost:5433/teachershub_enem`
- Usar `openai.AsyncOpenAI` (SDK v1) — classe legada usa API depreciada (`openai.ChatCompletion.acreate`)
- 100% mocks nos unit tests — sem banco real, sem OpenAI real, sem Redis real
- Startup pattern com `@app.on_event("startup")` e instância global (Story 3.2)

---

## Estrutura de Testes

```python
# tests/test_question_generator_rag.py
from src.rag_features.question_generator import RAGQuestionGenerator

class TestFetchContextChunks:
    def test_returns_context_chunks_for_subject(self, mocker): ...
    def test_passes_subject_filter_to_pgvector(self, mocker): ...
    def test_returns_empty_list_when_no_context(self, mocker): ...

class TestBuildGenerationPrompt:
    def test_includes_system_prompt(self): ...
    def test_includes_context_chunks_in_user_prompt(self): ...
    def test_includes_subject_topic_difficulty(self): ...
    def test_handles_empty_context_gracefully(self): ...

class TestGenerateQuestions:
    def test_returns_questions_with_required_fields(self, mocker): ...
    def test_source_context_ids_populated(self, mocker): ...
    def test_respects_count_parameter(self, mocker): ...
    def test_calls_gpt4o_with_correct_model(self, mocker): ...
    def test_persists_to_generated_questions_table(self, mocker): ...

class TestParseLlmResponse:
    def test_parses_valid_json_array(self): ...
    def test_parses_single_object_as_array(self): ...
    def test_extracts_json_from_markdown_block(self): ...
    def test_raises_on_invalid_content(self): ...

class TestPersistGenerated:
    def test_inserts_into_generated_questions_table(self, mocker): ...
    def test_returns_list_of_uuids(self, mocker): ...
    def test_does_not_touch_question_chunks_table(self, mocker): ...
```

```python
# tests/test_endpoint_question_generate.py
from fastapi.testclient import TestClient
from api.fastapi_app import app

client = TestClient(app)

class TestQuestionGenerateEndpoint:
    def test_valid_request_returns_200(self, mocker): ...
    def test_count_exceeds_max_returns_422(self): ...
    def test_empty_subject_returns_422(self): ...
    def test_empty_topic_returns_422(self): ...
    def test_invalid_difficulty_returns_422(self): ...
    def test_service_unavailable_returns_503(self, mocker): ...
    def test_response_includes_source_context_ids(self, mocker): ...
    def test_meta_contains_generation_metadata(self, mocker): ...
    def test_response_format_matches_standard(self, mocker): ...
```

---

## Não faz parte desta story

- Modificar `PgVectorSearch` ou `semantic_search.py` — Story 3.1
- Endpoint de busca semântica — Story 3.2
- Assessment Generator (Feature 2) — Story 4.1
- Autenticação/JWT — fora do escopo do Epic 4 (integração TeachersHub)
- Modificar migrations existentes ou tabela `question_chunks` — Epic 1
- Interface frontend / wizard de geração — Epic 4.2 do PRD (frontend)
- Correção automatizada — Story 4.3
- Exportação PDF/Word — Epic 5

---

## Dev Agent Record

### Implementation Plan
1. Migration SQL (`database/generated-questions-migration.sql`) — table `generated_questions` with JSONB alternatives, UUID[] source_context_ids
2. `RAGQuestionGenerator` class added to `question_generator.py` alongside legacy `EnemQuestionGenerator`
3. GPT-4o prompt templates (SYSTEM_PROMPT + USER_PROMPT_TEMPLATE) with RAG context injection
4. Pydantic models + `POST /api/v1/questions/generate` endpoint in `fastapi_app.py`
5. Unit tests (18 tests) + endpoint tests (8 tests)

### Debug Log
- No issues encountered during implementation.

### Completion Notes
- All 26 tests passing (18 unit + 8 endpoint)
- `question_generator.py`: 63% coverage (legacy `EnemQuestionGenerator` untested — deprecated)
- `RAGQuestionGenerator` accepts `pgvector_search` as constructor param (injected from app startup)
- `_parse_llm_response` has robust fallback: tries direct JSON parse → regex extract from markdown → ValueError
- Endpoint validates: difficulty pattern, count range [1,5], subject/topic min_length=1

### Files
- `src/rag_features/question_generator.py` — `RAGQuestionGenerator` + prompt templates
- `api/fastapi_app.py` — Pydantic models, startup init, `POST /api/v1/questions/generate`
- `database/generated-questions-migration.sql` — DDL for `generated_questions`
- `tests/test_question_generator_rag.py` — 18 unit tests
- `tests/test_endpoint_question_generate.py` — 8 endpoint tests

---

## Change Log

| Data | Alteração |
|------|-----------|
| 2026-04-02 | Story criada — Question Generator RAG Feature 3 (Epic 4, Story 2) |
| 2026-04-02 | Implementation complete — 26/26 tests passing, status → review |
