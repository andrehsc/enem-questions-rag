#!/bin/bash
# Reingestão de Dados ENEM para Arquitetura Híbrida TeachersHub-ENEM
# Reexecuta todo o processo de ingestão no novo schema enem_questions

set -e

echo "��� Iniciando reingestão de dados ENEM para arquitetura híbrida..."

# Verificar se Docker containers estão rodando
echo "��� Verificando containers..."
if ! docker compose ps | grep -q "teachershub-enem-postgres.*Up"; then
    echo "❌ PostgreSQL container não está rodando"
    echo "��� Execute: docker compose up -d postgres redis"
    exit 1
fi

if ! docker compose ps | grep -q "teachershub-enem-redis.*Up"; then
    echo "❌ Redis container não está rodando"
    echo "��� Execute: docker compose up -d postgres redis"
    exit 1
fi

# Aguardar containers ficarem saudáveis
echo "⏱️ Aguardando containers ficarem saudáveis..."
sleep 10

# Verificar conectividade PostgreSQL diretamente
echo "��� Testando conectividade PostgreSQL..."
if ! docker compose exec postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "❌ PostgreSQL não responde"
    echo "��� Execute: ./logs.sh errors"
    exit 1
fi
echo "✅ PostgreSQL conectado com sucesso"

echo "✅ Containers saudáveis"

# Configurar schema ENEM no banco híbrido
echo "���️ Configurando schema ENEM..."
docker compose exec -T postgres psql -U postgres -d teachershub_enem << 'SQLEOF'
-- Configurar schema enem_questions se necessário
SET search_path TO enem_questions, shared_resources, public;

-- Verificar se tabelas ENEM existem
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname = 'enem_questions' 
ORDER BY tablename;

-- Se não existirem tabelas, vamos criá-las
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'enem_questions' 
        AND table_name = 'exam_metadata'
    ) THEN
        RAISE NOTICE 'Criando tabelas ENEM no schema enem_questions...';
        
        -- Tabela de metadata dos exames
        CREATE TABLE enem_questions.exam_metadata (
            id SERIAL PRIMARY KEY,
            year INTEGER NOT NULL,
            exam_type VARCHAR(50) NOT NULL,
            application_type VARCHAR(100),
            language VARCHAR(10) DEFAULT 'PT',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(year, exam_type, application_type, language)
        );

        -- Tabela de questões
        CREATE TABLE enem_questions.questions (
            id SERIAL PRIMARY KEY,
            exam_id INTEGER REFERENCES enem_questions.exam_metadata(id) ON DELETE CASCADE,
            question_number INTEGER NOT NULL,
            subject VARCHAR(50) NOT NULL,
            competency VARCHAR(100),
            skill VARCHAR(200),
            question_text TEXT NOT NULL,
            image_path TEXT,
            correct_answer CHAR(1),
            explanation TEXT,
            difficulty_level VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(exam_id, question_number)
        );

        -- Tabela de alternativas
        CREATE TABLE enem_questions.question_alternatives (
            id SERIAL PRIMARY KEY,
            question_id INTEGER REFERENCES enem_questions.questions(id) ON DELETE CASCADE,
            alternative_letter CHAR(1) NOT NULL,
            alternative_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(question_id, alternative_letter)
        );

        -- Tabela de gabaritos
        CREATE TABLE enem_questions.answer_keys (
            id SERIAL PRIMARY KEY,
            exam_id INTEGER REFERENCES enem_questions.exam_metadata(id) ON DELETE CASCADE,
            question_number INTEGER NOT NULL,
            correct_answer CHAR(1) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(exam_id, question_number)
        );

        -- Índices para performance
        CREATE INDEX idx_questions_exam_subject ON enem_questions.questions(exam_id, subject);
        CREATE INDEX idx_questions_subject ON enem_questions.questions(subject);
        CREATE INDEX idx_alternatives_question ON enem_questions.question_alternatives(question_id);
        CREATE INDEX idx_answer_keys_exam ON enem_questions.answer_keys(exam_id);

        -- Permissões para enem_rag_service
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA enem_questions TO enem_rag_service;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA enem_questions TO enem_rag_service;

        RAISE NOTICE 'Tabelas ENEM criadas com sucesso!';
    ELSE
        RAISE NOTICE 'Tabelas ENEM já existem no schema enem_questions';
    END IF;
END
$$;
SQLEOF

echo "✅ Schema ENEM configurado"

# Verificar se Python venv está ativo
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "��� Ativando Python virtual environment..."
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    else
        echo "⚠️ Virtual environment não encontrado, continuando..."
    fi
fi

# Instalar/atualizar dependências se necessário
if [ -f "requirements.txt" ]; then
    echo "��� Verificando dependências Python..."
    pip install -r requirements.txt > /dev/null 2>&1 || echo "⚠️ Falha ao instalar dependências"
fi

# Executar ingestão dos dados
echo "��� Iniciando ingestão de dados ENEM..."

# 1. Inicializar sistema
echo "1. Inicializando sistema..."
python scripts/init_system.py

# 2. Baixar arquivos se necessário
echo "2. Verificando downloads..."
if [ ! -d "data/downloads" ] || [ -z "$(ls -A data/downloads 2>/dev/null)" ]; then
    echo "��� Baixando arquivos ENEM..."
    python scripts/download_all_files.py
fi

# 3. Processar gabaritos
echo "3. Processando gabaritos..."
python scripts/process_all_answer_keys.py

# 4. Executar limpeza e processamento
echo "4. Executando processamento limpo..."
python scripts/answer_processor_clean.py

# 5. Gerar relatório final
echo "5. Gerando relatório de ingestão..."
python scripts/full_ingestion_report.py

# Verificar resultado final
echo ""
echo "��� Verificando dados ingeridos..."
docker compose exec -T postgres psql -U enem_rag_service -d teachershub_enem << 'CHECKEOF'
SET search_path TO enem_questions, shared_resources, public;

SELECT 
    'exam_metadata' as table_name,
    COUNT(*) as records
FROM exam_metadata
UNION ALL
SELECT 
    'questions' as table_name,
    COUNT(*) as records  
FROM questions
UNION ALL
SELECT 
    'question_alternatives' as table_name,
    COUNT(*) as records
FROM question_alternatives
UNION ALL
SELECT 
    'answer_keys' as table_name,
    COUNT(*) as records
FROM answer_keys
ORDER BY table_name;

-- Mostrar distribuição por ano/matéria
SELECT 
    em.year,
    q.subject,
    COUNT(*) as questions_count
FROM exam_metadata em
JOIN questions q ON em.id = q.exam_id
GROUP BY em.year, q.subject
ORDER BY em.year DESC, q.subject;
CHECKEOF

echo ""
echo "��� Reingestão concluída!"
echo ""
echo "��� Próximos passos:"
echo "  - Testar API: http://localhost:8001/docs (quando ENEM RAG service estiver rodando)"
echo "  - Testar integração: http://localhost:5001/health (quando TeachersHub API estiver rodando)"
echo "  - Ver logs: ./logs.sh"
echo ""
echo "�� Dados agora estão no schema: enem_questions"
echo "��� Conectividade: enem_rag_service@localhost:5433/teachershub_enem"
