# Story 8.4: Deduplicação Inteligente de Cadernos

Status: pending

## Story

Como desenvolvedor,
Quero deduplicar questões entre cadernos mantendo a melhor extração,
Para que o banco tenha ~900 questões únicas em vez de ~4.700 duplicatas.

## Acceptance Criteria (AC)

1. Hash de conteúdo do enunciado normalizado (sem headers/números) como chave de dedup
2. Na ingestão, manter a versão com maior confidence score
3. Pick-best entre pdfplumber e pymupdf4llm para mesma questão
4. Coluna `canonical_question_id` linkando duplicatas ao registro canônico
5. Migration SQL idempotente para novas colunas (`content_hash`, `canonical_question_id`)
6. Testes: dedup correta, pick-best, questões similares-mas-diferentes mantidas separadas

## Tasks / Subtasks

- [ ] Task 1: Função de content hash (AC: 1)
  - [ ] 1.1 Método `compute_content_hash(enunciado: str) -> str` em `pipeline_v2.py` ou novo módulo:
    ```python
    def compute_content_hash(text: str) -> str:
        """Hash estável do enunciado normalizado."""
        normalized = text.lower().strip()
        # Remover headers, números de questão, pontuação variável
        normalized = re.sub(r'quest[ãa]o\s*\d+', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
    ```
  - [ ] 1.2 Hash incluir ano + dia para evitar false matches entre questões similares de anos diferentes
  - [ ] 1.3 Validação: mesma questão em CD1 e CD5 produz mesmo hash; questões diferentes de mesmo tema produzem hashes diferentes
- [ ] Task 2: Dedup na ingestão (AC: 2, 3)
  - [ ] 2.1 Em `pipeline_v2.py:_process_question()`:
    - Após scoring, computar content_hash do enunciado
    - Query: `SELECT id, confidence_score, extraction_method FROM questions WHERE content_hash = %s`
    - Se existe E score atual > existing score: UPDATE (substituir com melhor extração)
    - Se existe E score atual <= existing score: SKIP (manter melhor existente)
    - Se não existe: INSERT normal
  - [ ] 2.2 Log: `"[DEDUP] Q%d hash=%s action=%s (new=%.2f vs existing=%.2f)"`
- [ ] Task 3: Migration SQL (AC: 4, 5)
  - [ ] 3.1 Criar `database/dedup-migration.sql`:
    ```sql
    -- Dedup columns for Epic 8 (Story 8.4)
    ALTER TABLE enem_questions.questions
        ADD COLUMN IF NOT EXISTS content_hash VARCHAR(16),
        ADD COLUMN IF NOT EXISTS canonical_question_id UUID DEFAULT NULL;

    CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_content_hash
        ON enem_questions.questions (content_hash)
        WHERE content_hash IS NOT NULL;

    CREATE INDEX IF NOT EXISTS idx_questions_canonical
        ON enem_questions.questions (canonical_question_id)
        WHERE canonical_question_id IS NOT NULL;
    ```
  - [ ] 3.2 Migration idempotente (`IF NOT EXISTS`)
- [ ] Task 4: Script de dedup para dados existentes (AC: 2, 3)
  - [ ] 4.1 Criar `scripts/deduplicate_existing.py`:
    - Ler todas as questões do banco
    - Agrupar por content_hash
    - Para cada grupo: manter a de maior confidence_score, marcar as demais com canonical_question_id apontando para a melhor
    - Relatório: quantas questões únicas, quantas duplicatas consolidadas
  - [ ] 4.2 Modo dry-run: `--dry-run` mostra o que faria sem alterar o banco
  - [ ] 4.3 Log de cada decisão para auditoria
- [ ] Task 5: Testes (AC: 6)
  - [ ] 5.1 Teste: mesma questão de CD1 e CD5 → mesmo hash
  - [ ] 5.2 Teste: questões diferentes mas mesmo tema → hashes diferentes
  - [ ] 5.3 Teste: pick-best mantém a de maior confidence
  - [ ] 5.4 Teste: canonical_question_id aponta corretamente
  - [ ] 5.5 Teste: questão com texto similar mas ano diferente → NÃO deduplicada

## Dev Notes

### Estado atual: duplicatas massivas

- 4.709 entradas no relatório para ~900 questões únicas
- Cada questão aparece em 4-12 cadernos (CD1-CD4 Dia 1, CD5-CD8 Dia 2, CD9-CD12 variantes)
- Para 2020/2021: duplicação adicional entre pdfplumber e pymupdf4llm

### Pipeline v2 atual: dedup por file hash, não content hash

`pipeline_v2.py:_persist_question()` (linha ~292): UPSERT por `(exam_metadata_id, question_number)`. Questão 1 do CD1 e questão 45 do CD5 (mesma questão, números diferentes) são tratadas como distintas.

### Risco: fuzzy matching

Questões ENEM às vezes reutilizam textos-base entre anos. Incluir `year + day` no input do hash mitiga false matches.

### Dependências

- Rodável em paralelo com Stories 8.2/8.3
- Beneficia-se de 8.1 (texto mais limpo → hash mais estável)

### Anti-Patterns a Evitar

- NÃO deletar duplicatas — apenas marcar com `canonical_question_id`
- NÃO usar hash do texto completo (inclui alternativas que podem variar por extrator)
- NÃO deduplicar questões de anos diferentes só porque o tema é similar

### Project Structure Notes

- Novo: `database/dedup-migration.sql`
- Novo: `scripts/deduplicate_existing.py`
- Modificado: `src/enem_ingestion/pipeline_v2.py`

### References

- [Source: pipeline_v2.py:_persist_question] — current UPSERT logic, line ~292
- [Source: pipeline_v2.py:_process_pdf] — file hash checking
- [Source: PLAN-extraction-quality-improvements.md] — 4.709 entries, ~900 unique

## Dev Agent Record

### Agent Model Used
(pending)

### Debug Log References
(pending)

### Completion Notes List
(pending)

### File List
(pending)

### Review Findings
(pending)
