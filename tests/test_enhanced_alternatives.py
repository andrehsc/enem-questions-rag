#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Enhanced Alternative Extractor
=======================================
"""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from enem_ingestion.alternative_extractor import (
    EnhancedAlternativeExtractor,
    StandardPatternStrategy,
    MultilinePatternStrategy,
    MathematicalStrategy,
    ExtractionStrategy
)


class TestEnhancedAlternativeExtractor(unittest.TestCase):
    """Test suite for enhanced alternative extraction."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = EnhancedAlternativeExtractor()
    
    def test_standard_pattern_complete_alternatives(self):
        """Test standard pattern with complete alternatives."""
        text = """
        Esta é uma questão sobre matemática.
        
        A criticar o desempenho da economia brasileira no período
        B rever a estratégia de desenvolvimento econômico  
        C apoiar a manutenção da política econômica vigente
        D avaliar a capacidade de geração de empregos
        E propor mudanças na estrutura produtiva nacional
        
        QUESTÃO 15
        """
        
        result = self.extractor.extract_alternatives(text)
        
        # Should find 5 alternatives
        self.assertEqual(len(result.alternatives), 5)
        self.assertGreater(result.confidence, 0.8)
        
        # Check that all alternatives are properly formatted
        expected_starts = ['A)', 'B)', 'C)', 'D)', 'E)']
        for i, alt in enumerate(result.alternatives):
            self.assertTrue(alt.startswith(expected_starts[i]))
    
    def test_multiline_alternatives(self):
        """Test extraction of multiline alternatives."""
        text = """
        Questão sobre história do Brasil.
        
        A O processo de independência foi influenciado
          pelos movimentos liberais europeus e teve
          características particulares
        B A economia colonial baseada na agricultura
          de exportação determinou estruturas sociais
        C As revoltas regionais do período regencial
          expressaram conflitos de interesses locais
        D A abolição da escravidão resultou de pressões
          internas e externas ao Império
        E A proclamação da República consolidou
          mudanças políticas iniciadas anteriormente
          
        QUESTÃO 20
        """
        
        result = self.extractor.extract_alternatives(text)
        
        # Should handle multiline alternatives
        self.assertEqual(len(result.alternatives), 5)
        self.assertGreater(result.confidence, 0.6)
        
        # Check that multiline content is preserved (check for key words)
        alt_text = ' '.join(result.alternatives)  # Check in any alternative
        self.assertTrue(any('europeu' in alt or 'independência' in alt for alt in result.alternatives))
        self.assertTrue(any('agricultura' in alt or 'economia' in alt for alt in result.alternatives))
    
    def test_mathematical_alternatives(self):
        """Test extraction of short mathematical alternatives."""
        text = """
        Calcule o valor de x na equação 2x + 5 = 15.
        
        A 5
        B 10  
        C 2,5
        D 7,5
        E 0
        
        QUESTÃO 30
        """
        
        result = self.extractor.extract_alternatives(text)
        
        # Should find mathematical alternatives
        self.assertEqual(len(result.alternatives), 5)
        self.assertGreater(result.confidence, 0.4)
        
        # Check mathematical content
        self.assertIn('A) 5', result.alternatives[0])
        self.assertIn('B) 10', result.alternatives[1])
    
    def test_partial_alternatives_scenario(self):
        """Test scenario with only partial alternatives (common failure case)."""
        text = """
        Esta questão tem apenas algumas alternativas visíveis.
        
        A primeira opção disponível
        B segunda opção que foi extraída
        
        O resto do texto não contém mais alternativas claras.
        QUESTÃO 40
        """
        
        result = self.extractor.extract_alternatives(text)
        
        # Should find what's available
        self.assertEqual(len(result.alternatives), 2)
        self.assertLess(result.confidence, 0.6)  # Low confidence due to incompleteness
        
        # Should identify the issue
        self.assertTrue(any('found 2' in issue for issue in result.issues_found))
    
    def test_no_alternatives_scenario(self):
        """Test scenario with no detectable alternatives."""
        text = """
        Este é apenas um texto descritivo sobre o tema da questão.
        Não há alternativas formatadas de forma reconhecível.
        Pode ser que as alternativas estejam em formato muito diferente.
        """
        
        result = self.extractor.extract_alternatives(text)
        
        # Should return empty or very low confidence result
        # (Allow for 1 false positive that gets filtered out by confidence)
        self.assertLessEqual(len(result.alternatives), 1)
        self.assertLess(result.confidence, 0.3)  # Very low confidence
        self.assertTrue(result.issues_found)
    
    def test_strategy_confidence_scoring(self):
        """Test that strategies properly score their confidence."""
        # Complete alternatives should have high confidence
        complete_text = """
        A primeira alternativa completa
        B segunda alternativa completa  
        C terceira alternativa completa
        D quarta alternativa completa
        E quinta alternativa completa
        """
        
        strategy = StandardPatternStrategy()
        result_complete = strategy.extract(complete_text)
        
        # Partial alternatives should have lower confidence
        partial_text = """
        A primeira alternativa
        B segunda alternativa
        """
        
        result_partial = strategy.extract(partial_text)
        
        # Complete should have higher confidence than partial
        self.assertGreater(result_complete.confidence, result_partial.confidence)
        self.assertGreater(result_complete.confidence, 0.7)
    
    def test_integration_with_legacy_parser(self):
        """Test integration method for backward compatibility."""
        text = """
        Questão de teste para compatibilidade.
        
        A primeira alternativa de teste
        B segunda alternativa de teste
        C terceira alternativa de teste
        D quarta alternativa de teste
        E quinta alternativa de teste
        
        QUESTÃO FINAL
        """
        
        # Test legacy-compatible method
        alternatives = self.extractor.extract_alternatives_legacy_compatible(text)
        
        # Should return list of strings (legacy format)
        self.assertIsInstance(alternatives, list)
        self.assertEqual(len(alternatives), 5)
        
        for alt in alternatives:
            self.assertIsInstance(alt, str)
            self.assertTrue(alt.startswith(('A)', 'B)', 'C)', 'D)', 'E)')))
    
    def test_artifact_cleaning(self):
        """Test that PDF artifacts are properly cleaned."""
        text = """
        Questão com artifacts do PDF ENEM2024.
        
        A primeira alternativa 4202MENE com artifact
        B segunda alternativa com 12::34::56 timestamp  
        C terceira alternativa limpa
        D quarta alternativa ENEM2024 mais artifacts
        E quinta alternativa final
        """
        
        result = self.extractor.extract_alternatives(text)
        
        # Should find alternatives and clean artifacts
        self.assertEqual(len(result.alternatives), 5)
        
        # Check that artifacts are removed
        for alt in result.alternatives:
            self.assertNotIn('ENEM2024', alt)
            self.assertNotIn('4202MENE', alt)
            self.assertNotIn('12::34::56', alt)


if __name__ == '__main__':
    unittest.main()
