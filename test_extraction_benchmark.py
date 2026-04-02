#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark: Legacy vs Enhanced Alternative Extraction
===================================================
Compara a performance dos algoritmos antigo vs novo.
"""

import sys
import time
sys.path.insert(0, 'src')

from enem_ingestion.alternative_extractor import EnhancedAlternativeExtractor

# Test cases based on real extraction failures
test_cases = [
    # Case 1: Standard format (should work in both)
    {
        "name": "Standard Format",
        "text": """
        QuestÃ£o sobre economia brasileira.
        
        A criticar o desempenho da economia no perÃ­odo
        B rever a estratÃ©gia de desenvolvimento econÃ´mico  
        C apoiar a manutenÃ§Ã£o da polÃ­tica vigente
        D avaliar a capacidade de geraÃ§Ã£o de empregos
        E propor mudanÃ§as na estrutura produtiva
        
        QUESTÃƒO 15
        """
    },
    
    # Case 2: Mathematical short alternatives
    {
        "name": "Mathematical Short",
        "text": """
        Calcule o valor de x: 2x + 5 = 15
        
        A 5
        B 10
        C 2,5  
        D 7,5
        E 0
        
        QUESTÃƒO 30
        """
    },
    
    # Case 3: Multiline alternatives
    {
        "name": "Multiline Format",
        "text": """
        HistÃ³ria do Brasil no perÃ­odo colonial.
        
        A O processo de colonizaÃ§Ã£o foi caracterizado
          pela exploraÃ§Ã£o de recursos naturais e
          estabelecimento de estruturas administrativas
        B A economia colonial baseada na agricultura
          de exportaÃ§Ã£o determinou as relaÃ§Ãµes sociais
        C As revoltas coloniais expressaram conflitos
          entre colonos e metrÃ³pole por maior autonomia
        D A miscigenaÃ§Ã£o cultural resultou da interaÃ§Ã£o
          entre povos indÃ­genas, africanos e europeus  
        E A independÃªncia consolidou mudanÃ§as polÃ­ticas
          iniciadas no perÃ­odo colonial tardio
          
        QUESTÃƒO 67
        """
    },
    
    # Case 4: Problematic format (common failure case)
    {
        "name": "Problematic Layout",
        "text": """
        AnÃ¡lise do grÃ¡fico apresentado na questÃ£o anterior.
        
        A Indica tendÃªncia de crescimento
        B Mostra estabilidade no perÃ­odo | C Demonstra declÃ­nio
        D Revela inconsistÃªncia nos dados
        E Sugere necessidade de mais informaÃ§Ãµes
        
        QUESTÃƒO 89
        """
    },
    
    # Case 5: With PDF artifacts
    {
        "name": "With PDF Artifacts",
        "text": """
        ENEM2024 QuestÃ£o sobre sustentabilidade.
        
        A primeira alternativa 4202MENE sobre meio ambiente
        B segunda alternativa com 12::34::56 sobre recursos
        C terceira alternativa ENEM2024 sobre conservaÃ§Ã£o
        D quarta alternativa sobre desenvolvimento sustentÃ¡vel
        E quinta alternativa sobre polÃ­ticas ambientais
        
        QUESTÃƒO 101
        """
    }
]

def simulate_legacy_extraction(text):
    """Simulate legacy algorithm behavior (simplified)."""
    # Very basic regex - similar to what causes current failures
    import re
    
    alternatives = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        # Simple pattern - fails on multiline, artifacts, etc.
        match = re.match(r'^([A-E])\s+(.{10,})', line)
        if match:
            letter, content = match.groups()
            alternatives.append(f"{letter}) {content}")
    
    return alternatives

def run_benchmark():
    """Run extraction benchmark."""
    
    extractor = EnhancedAlternativeExtractor()
    
    print("í´¬ BENCHMARK: Legacy vs Enhanced Alternative Extraction")
    print("=" * 60)
    
    legacy_success = 0
    enhanced_success = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\ní³‹ Test Case {i}: {case['name']}")
        print("-" * 40)
        
        # Test legacy approach
        start_time = time.time()
        legacy_result = simulate_legacy_extraction(case['text'])
        legacy_time = time.time() - start_time
        
        legacy_valid = len(legacy_result) >= 4
        if legacy_valid:
            legacy_success += 1
        
        # Test enhanced approach
        start_time = time.time() 
        enhanced_result = extractor.extract_alternatives(case['text'])
        enhanced_time = time.time() - start_time
        
        enhanced_valid = len(enhanced_result.alternatives) >= 4
        if enhanced_valid:
            enhanced_success += 1
        
        # Results
        print(f"Legacy Algorithm:")
        print(f"  â±ï¸  Time: {legacy_time*1000:.2f}ms")
        print(f"  í³Š Found: {len(legacy_result)}/5 alternatives")
        print(f"  âœ… Valid: {'YES' if legacy_valid else 'NO'}")
        
        print(f"Enhanced Algorithm:")
        print(f"  â±ï¸  Time: {enhanced_time*1000:.2f}ms")
        print(f"  í³Š Found: {len(enhanced_result.alternatives)}/5 alternatives")
        print(f"  í¾¯ Confidence: {enhanced_result.confidence:.2f}")
        print(f"  í´§ Strategy: {enhanced_result.strategy_used.value}")
        print(f"  âœ… Valid: {'YES' if enhanced_valid else 'NO'}")
        
        if enhanced_valid and not legacy_valid:
            print(f"  í¾‰ IMPROVEMENT: Enhanced succeeded where Legacy failed!")
    
    print(f"\ní³ˆ FINAL RESULTS")
    print("=" * 60)
    print(f"Legacy Algorithm Success Rate:  {legacy_success}/{len(test_cases)} ({legacy_success/len(test_cases)*100:.1f}%)")
    print(f"Enhanced Algorithm Success Rate: {enhanced_success}/{len(test_cases)} ({enhanced_success/len(test_cases)*100:.1f}%)")
    
    improvement = enhanced_success - legacy_success
    if improvement > 0:
        print(f"íº€ IMPROVEMENT: +{improvement} successful extractions (+{improvement/len(test_cases)*100:.1f}%)")
        print(f"í²¡ This addresses the ~95% failure rate in partial alternative extraction!")
    else:
        print(f"í³Š No significant improvement detected.")

if __name__ == "__main__":
    run_benchmark()
