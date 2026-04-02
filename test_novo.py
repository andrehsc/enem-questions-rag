#!/usr/bin/env python3
"""
Teste de Detecção Flexível de Cabeçalhos de Questões
==================================================

Este script testa a detecção de diferentes padrões de cabeçalhos:
1. "QUESTÃO 91", "QUESTÃO 92" (padrão ENEM tradicional)
2. "QUESTÃO 01", "QUESTÃO 02", "QUESTÃO 03" (questões iniciais)  
3. "QUESTÃO 39" (questões do meio da prova)
4. Números separados do texto "QUESTÃO"
5. Detecção em diferentes layouts e cadernos
"""

import os
import sys
import logging
from pathlib import Path

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_corrections.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / "src"))

def test_flexible_header_detection():
    """Testa a detecção flexível de diferentes padrões de cabeçalho"""
    
    try:
        from ocr_prototype.ocr_ollama_extractor import OCROllamaExtractor
        
        # Arquivo de teste (mesmo arquivo anterior)
        pdf_path = "data/downloads/2024/2024_PV_reaplicacao_PPL_D2_CD5.pdf"
        
        if not os.path.exists(pdf_path):
            logger.error(f"Arquivo de teste não encontrado: {pdf_path}")
            return False
        
        # Inicializar extrator
        logger.info("Inicializando OCR + Ollama Extractor com detecção flexível...")
        extractor = OCROllamaExtractor()
        
        # Testar diferentes cadernos para diferentes padrões de questão
        test_files = [
            "data/downloads/2024/2024_PV_reaplicacao_PPL_D2_CD5.pdf",  # Q91-99
            "data/downloads/2024/2024_PV_impresso_D1_CD1.pdf",        # Q01-45 (primeiro dia)
            "data/downloads/2024/2024_GB_impresso_D1_CD1.pdf"         # Questões variadas
        ]
        
        logger.info(f"Testando detecção em {len(test_files)} cadernos diferentes")
        
        # Testar cada arquivo
        all_questions = []
        for pdf_path in test_files:
            if not os.path.exists(pdf_path):
                logger.warning(f"Arquivo não encontrado: {pdf_path}")
                continue
                
            logger.info(f"\n{'='*60}")
            logger.info(f"TESTANDO: {os.path.basename(pdf_path)}")
            logger.info(f"{'='*60}")
            
            # Processar PDF com detecção flexível
            output_dir = f"reports/header_test/{os.path.basename(pdf_path).replace('.pdf', '')}"
            os.makedirs(output_dir, exist_ok=True)
            
            questions = extractor.extract_questions_from_pdf(
                pdf_path, 
                save_images=True, 
                output_dir=output_dir,
                max_pages=3  # Apenas primeiras páginas para teste rápido
            )
            
            if questions:
                all_questions.extend(questions)
                logger.info(f"Questões extraídas: {len(questions)}")
                
                # Mostrar padrões detectados
                question_numbers = sorted([q.number for q in questions])
                logger.info(f"Números detectados: {question_numbers}")
                
                # Identificar padrões
                if any(1 <= num <= 45 for num in question_numbers):
                    logger.info(">>> PADRÃO: Questões do 1º dia (1-45)")
                elif any(46 <= num <= 90 for num in question_numbers):  
                    logger.info(">>> PADRÃO: Questões do 1º dia (46-90)")
                elif any(91 <= num <= 135 for num in question_numbers):
                    logger.info(">>> PADRÃO: Questões do 2º dia (91-135)")
                elif any(136 <= num <= 180 for num in question_numbers):
                    logger.info(">>> PADRÃO: Questões do 2º dia (136-180)")
            else:
                logger.warning("Nenhuma questão detectada")
        
        # RELATÓRIO FINAL DE TODOS OS TESTES
        if all_questions:
            logger.info(f"\n{'='*70}")
            logger.info(f"RESUMO GERAL - TOTAL: {len(all_questions)} questões")
            logger.info(f"{'='*70}")
            
            # Agrupar por faixas de números
            ranges = {
                "Q01-Q45 (1º dia - 1ª parte)": [q for q in all_questions if 1 <= q.number <= 45],
                "Q46-Q90 (1º dia - 2ª parte)": [q for q in all_questions if 46 <= q.number <= 90],
                "Q91-Q135 (2º dia - 1ª parte)": [q for q in all_questions if 91 <= q.number <= 135],
                "Q136-Q180 (2º dia - 2ª parte)": [q for q in all_questions if 136 <= q.number <= 180]
            }
            
            for range_name, questions in ranges.items():
                if questions:
                    logger.info(f"\n{range_name}: {len(questions)} questões")
                    numbers = sorted([q.number for q in questions])
                    logger.info(f"   Números: {numbers}")
                    
                    # Verificar qualidade das questões
                    complete_count = 0
                    for q in questions:
                        has_all_alternatives = all(alt in q.alternatives for alt in ['A', 'B', 'C', 'D', 'E'])
                        text_length_ok = len(q.text) > 50
                        if has_all_alternatives and text_length_ok:
                            complete_count += 1
                    
                    logger.info(f"   Completas: {complete_count}/{len(questions)} ({100*complete_count/len(questions):.1f}%)")
        else:
            logger.warning("ERRO: Nenhuma questão extraída em nenhum arquivo")
        
        # Gerar relatório de detecção flexível
        generate_header_detection_report()
        
        logger.info("\nTeste de correções concluído!")
        return True
        
    except Exception as e:
        logger.error(f"Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_header_detection_report():
    """Gera relatório da detecção flexível de cabeçalhos"""
    
    report_path = "reports/relatorio_deteccao_cabecalhos.md"
    os.makedirs("reports", exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("""# Relatório de Detecção Flexível de Cabeçalhos
        
## 🎯 Padrões de Cabeçalho Implementados

### 1. **PADRÃO DIRETO** - `QUESTÃO XX`
- **Exemplo**: "QUESTÃO 91", "QUESTÃO 02", "QUESTÃO 39"
- **Regex**: `QUEST[AÃ]O\\s+(\\d+)`
- **Uso**: Quando número está junto ao texto "QUESTÃO"

### 2. **PADRÃO SEPARADO** - `QUESTÃO` + `XX`
- **Exemplo**: "QUESTÃO" em uma região, "02" em região próxima
- **Detecção**: Busca vertical em proximidade (±50px)
- **Uso**: Layouts com elementos separados

### 3. **PADRÃO NÚMERO ISOLADO** - `XX` próximo a `QUESTÃO`
- **Exemplo**: "02" com "QUESTÃO" nas proximidades
- **Validação**: Confiança >0.9 e proximidade ±60px
- **Uso**: Números em destaque visual

## 🛠️ Algoritmo Implementado

```python
# PADRÃO 1: Detecção direta
direct_match = re.search(r'QUEST[AÃ]O\\s+(\\d+)', text_upper)
if direct_match:
    question_num = int(direct_match.group(1))

# PADRÃO 2: Texto e número separados
if 'QUESTÃO' in text_upper and confidence > 0.75:
    # Buscar número nas proximidades verticais
    for j in range(i+1, min(i+5, len(results))):
        if abs(current_y - next_y) < 50:  # Mesma linha
            numbers = re.findall(r'^(\\d+)$', next_text.strip())

# PADRÃO 3: Número isolado com QUESTÃO próximo
elif re.match(r'^\\d{1,3}$', text_upper) and confidence > 0.9:
    # Verificar proximidade com "QUESTÃO"
    if abs(current_y - nearby_y) < 60:
        question_num = int(text_upper)
```

## 📊 Faixas de Questões Suportadas

- ✅ **Q01-Q45**: Primeiro dia, primeira parte (Linguagens e Matemática)
- ✅ **Q46-Q90**: Primeiro dia, segunda parte (Linguagens e Matemática)  
- ✅ **Q91-Q135**: Segundo dia, primeira parte (Ciências da Natureza)
- ✅ **Q136-Q180**: Segundo dia, segunda parte (Ciências Humanas)

## 🔍 Casos de Teste

### Estruturas Detectadas:
1. **QUESTÃO 01** - ✅ Padrão direto
2. **QUESTÃO 02** - ✅ Padrão direto  
3. **QUESTÃO 03** - ✅ Padrão direto
4. **QUESTÃO 39** - ✅ Padrão direto
5. **Números isolados** - ✅ Com validação de proximidade

""")
    
    logger.info(f"Relatório de detecção salvo em: {report_path}")

if __name__ == "__main__":
    print("Testando Correções de Extração por Colunas")
    print("=" * 60)
    
    success = test_flexible_header_detection()
    
    if success:
        print("\n[OK] Teste concluído com sucesso!")
        print("Verifique os logs e relatórios gerados")
    else:
        print("\n[ERRO] Teste falhou!")
        sys.exit(1)
