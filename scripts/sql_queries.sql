-- ============================================================
-- CONSULTAS SQL DIRETAS PARA O BANCO ENEM RAG
-- ============================================================

-- 1. VISÃO GERAL - Estatísticas básicas
SELECT 
    'Arquivos processados' as categoria,
    COUNT(*) as total
FROM exam_metadata
UNION ALL
SELECT 
    'Total de questões' as categoria,
    COUNT(*) as total
FROM questions
UNION ALL
SELECT 
    'Total de alternativas' as categoria,
    COUNT(*) as total
FROM question_alternatives
UNION ALL
SELECT 
    'Gabaritos disponíveis' as categoria,
    COUNT(*) as total
FROM answer_keys;

-- 2. DISTRIBUIÇÃO POR ANO E MATÉRIA
SELECT 
    em.year,
    q.subject,
    COUNT(*) as questoes
FROM questions q
JOIN exam_metadata em ON q.exam_metadata_id = em.id
GROUP BY em.year, q.subject
ORDER BY em.year, questoes DESC;

-- 3. QUESTÕES COMPLETAS COM ALTERNATIVAS (TOP 5)
SELECT 
    q.question_number,
    q.subject,
    LEFT(q.question_text, 200) as texto_resumo,
    em.year,
    em.day,
    em.caderno,
    STRING_AGG(
        qa.alternative_letter || ') ' || LEFT(qa.alternative_text, 80) || '...', 
        E'\n' ORDER BY qa.alternative_letter
    ) as alternativas
FROM questions q
JOIN exam_metadata em ON q.exam_metadata_id = em.id
LEFT JOIN question_alternatives qa ON q.id = qa.question_id
GROUP BY q.id, q.question_number, q.subject, q.question_text, 
         em.year, em.day, em.caderno
ORDER BY q.question_number
LIMIT 5;

-- 4. QUESTÕES COM GABARITO (agora disponível!)
SELECT 
    q.question_number,
    q.subject,
    LEFT(q.question_text, 150) as texto_resumo,
    ak.correct_answer as gabarito,
    ak.language_option as idioma,
    em.year,
    em.caderno
FROM questions q
JOIN exam_metadata em ON q.exam_metadata_id = em.id
JOIN answer_keys ak ON ak.question_number = q.question_number 
    AND ak.exam_metadata_id = em.id
ORDER BY q.question_number
LIMIT 10;

-- 5. DISTRIBUIÇÃO PERFEITA DAS ALTERNATIVAS
SELECT 
    alternative_letter,
    COUNT(*) as quantidade,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentual
FROM question_alternatives
GROUP BY alternative_letter
ORDER BY alternative_letter;

-- 6. QUESTÕES COM PROBLEMAS (menos de 5 alternativas)
SELECT 
    q.question_number,
    COUNT(qa.alternative_letter) as num_alternativas,
    em.year,
    em.caderno
FROM questions q
LEFT JOIN question_alternatives qa ON q.id = qa.question_id
JOIN exam_metadata em ON q.exam_metadata_id = em.id
GROUP BY q.id, q.question_number, em.year, em.caderno
HAVING COUNT(qa.alternative_letter) != 5
ORDER BY q.question_number;

-- 7. UMA QUESTÃO COMPLETA ALEATÓRIA
SELECT 
    q.question_number,
    q.subject,
    q.question_text,
    em.year,
    em.day,
    em.caderno,
    em.pdf_filename
FROM questions q
JOIN exam_metadata em ON q.exam_metadata_id = em.id
ORDER BY RANDOM()
LIMIT 1;

-- Para pegar as alternativas da questão acima, use o question_number:
-- SELECT 
--     alternative_letter, 
--     alternative_text
-- FROM question_alternatives qa
-- JOIN questions q ON qa.question_id = q.id
-- WHERE q.question_number = [NUMERO_DA_QUESTAO]
-- ORDER BY alternative_letter;

-- 8. VIEW CONSOLIDADA - QUESTÃO + ALTERNATIVAS + GABARITO
CREATE OR REPLACE VIEW vw_questoes_completas AS
SELECT 
    q.question_number,
    q.subject,
    q.question_text,
    em.year,
    em.day,
    em.caderno,
    em.pdf_filename,
    COALESCE(ak.correct_answer, 'Não disponível') as gabarito,
    ak.language_option as idioma,
    STRING_AGG(
        qa.alternative_letter || ') ' || qa.alternative_text, 
        E'\n' ORDER BY qa.alternative_letter
    ) as todas_alternativas
FROM questions q
JOIN exam_metadata em ON q.exam_metadata_id = em.id
LEFT JOIN question_alternatives qa ON q.id = qa.question_id
LEFT JOIN answer_keys ak ON ak.question_number = q.question_number 
    AND ak.exam_metadata_id = em.id
GROUP BY q.id, q.question_number, q.subject, q.question_text, 
         em.year, em.day, em.caderno, em.pdf_filename, 
         ak.correct_answer, ak.language_option
ORDER BY q.question_number;

-- 9. USAR A VIEW CRIADA
SELECT * FROM vw_questoes_completas LIMIT 3;

-- 10. QUESTÕES POR MATÉRIA E ANO
SELECT 
    em.year,
    CASE 
        WHEN q.subject LIKE '%LINGUAGENS%' THEN 'Linguagens'
        WHEN q.subject LIKE '%HUMANAS%' THEN 'Ciências Humanas'
        WHEN q.subject LIKE '%NATUREZA%' THEN 'Ciências Natureza'
        WHEN q.subject LIKE '%MATEMATICA%' THEN 'Matemática'
        ELSE q.subject
    END as materia,
    COUNT(*) as questoes,
    MIN(q.question_number) as primeira_questao,
    MAX(q.question_number) as ultima_questao
FROM questions q
JOIN exam_metadata em ON q.exam_metadata_id = em.id
GROUP BY em.year, q.subject
ORDER BY em.year, primeira_questao;

-- 11. ANÁLISE DE QUALIDADE DOS DADOS
SELECT 
    'Questões com texto vazio' as problema,
    COUNT(*) as quantidade
FROM questions 
WHERE question_text IS NULL OR TRIM(question_text) = ''
UNION ALL
SELECT 
    'Alternativas com texto vazio' as problema,
    COUNT(*) as quantidade
FROM question_alternatives 
WHERE alternative_text IS NULL OR TRIM(alternative_text) = ''
UNION ALL
SELECT 
    'Questões sem alternativas' as problema,
    COUNT(*) as quantidade
FROM questions q
LEFT JOIN question_alternatives qa ON q.id = qa.question_id
WHERE qa.question_id IS NULL;

-- 12. EXPORTAR DADOS PARA ANÁLISE (formato tabular)
SELECT 
    q.question_number as "Número",
    CASE 
        WHEN q.subject LIKE '%LINGUAGENS%' THEN 'Linguagens'
        WHEN q.subject LIKE '%HUMANAS%' THEN 'Ciências Humanas'
        ELSE q.subject
    END as "Matéria",
    em.year as "Ano",
    em.day as "Dia",
    em.caderno as "Caderno",
    LEFT(q.question_text, 100) || '...' as "Texto (resumo)",
    COALESCE(ak.correct_answer, '-') as "Gabarito"
FROM questions q
JOIN exam_metadata em ON q.exam_metadata_id = em.id
LEFT JOIN answer_keys ak ON ak.question_number = q.question_number 
    AND ak.exam_metadata_id = em.id
ORDER BY q.question_number;

-- 13. QUESTÃO COMPLETA COM TODAS AS INFORMAÇÕES (Nova!)
SELECT 
    q.question_number,
    CASE 
        WHEN q.subject LIKE '%LINGUAGENS%' THEN 'Linguagens'
        WHEN q.subject LIKE '%HUMANAS%' THEN 'Ciências Humanas'
        WHEN q.subject LIKE '%NATUREZA%' THEN 'Ciências Natureza'
        WHEN q.subject LIKE '%MATEMATICA%' THEN 'Matemática'
        ELSE q.subject
    END as materia,
    q.question_text,
    STRING_AGG(
        qa.alternative_letter || ') ' || qa.alternative_text, 
        E'\n' ORDER BY qa.alternative_letter
    ) as todas_alternativas,
    ak.correct_answer as gabarito,
    ak.language_option as idioma,
    em.year,
    em.caderno
FROM questions q
JOIN exam_metadata em ON q.exam_metadata_id = em.id
LEFT JOIN question_alternatives qa ON q.id = qa.question_id
LEFT JOIN answer_keys ak ON ak.question_number = q.question_number 
    AND ak.exam_metadata_id = em.id
GROUP BY q.id, q.question_number, q.subject, q.question_text, 
         ak.correct_answer, ak.language_option, em.year, em.caderno
ORDER BY q.question_number
LIMIT 3;

-- 14. ANÁLISE ESTATÍSTICA DOS GABARITOS
SELECT 
    'Distribuição dos gabaritos' as analise,
    correct_answer as alternativa,
    COUNT(*) as quantidade,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentual
FROM answer_keys
GROUP BY correct_answer
ORDER BY correct_answer;
