#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_text_normalizer.py
TDD Test Suite for ENEM Text Normalizer
======================================
"""

import pytest
import time
from src.enem_ingestion.text_normalizer import EnemTextNormalizer, normalize_enem_text


class TestEnemTextNormalizerMojibakeCorrection:
    """RED PHASE: Testes para correção de mojibake."""
    
    def test_normalize_encoding_basic_mojibake_correction_returns_clean_text(self):
        """RED: Deve corrigir mojibake básico"""
        # Arrange
        normalizer = EnemTextNormalizer()
        input_text = "Questão sobre área"
        expected_output = "Questão sobre área"
        
        # Act
        result = normalizer.normalize_encoding(input_text)
        
        # Assert
        assert result == expected_output


class TestEnemTextNormalizerIntegration:
    """RED PHASE: Testes de integração com parser."""
    
    def test_parser_clean_question_text_integration_with_normalizer_returns_clean_text(self):
        """RED: Parser deve usar normalizador na função _clean_question_text"""
        # Arrange
        from src.enem_ingestion.parser import EnemPDFParser
        parser = EnemPDFParser()
        # Texto com mojibake real que deve ser corrigido
        corrupted_text = "O grÃ¡fico mostra â€œdados importantesâ€"
        
        # Act
        clean_text = parser._clean_question_text(corrupted_text)
        
        # Assert
        # Se o normalizador estiver integrado, não deve ter mojibake
        assert "Ã¡" not in clean_text, "Mojibake Ã¡ deve ser corrigido pelo normalizador"
        assert "â€œ" not in clean_text, "Aspas smart devem ser corrigidas"
        assert "â€" not in clean_text, "Aspas de fechamento devem ser corrigidas"
        # E deve ter o texto corrigido
        assert "gráfico" in clean_text, "Deve conter 'gráfico' corrigido"


class TestEnemTextNormalizerFunctionalTests:
    """GREEN PHASE: Testes funcionais completos."""
    
    def test_normalize_full_with_mojibake_returns_complete_result(self):
        """GREEN: normalize_full deve retornar resultado completo com métricas"""
        # Arrange
        normalizer = EnemTextNormalizer()
        problematic_text = "Questão sobre Ã¡rea e â€œproblemas de encoding"
        
        # Act
        result = normalizer.normalize_full(problematic_text)
        
        # Assert
        assert 'original' in result, "Deve conter texto original"
        assert 'normalized' in result, "Deve conter texto normalizado"
        assert 'changes_applied' in result, "Deve conter mudanças aplicadas"
        assert 'improvement_score' in result, "Deve conter score de melhoria"
        assert result['normalized'] != result['original'], "Texto deve ter sido modificado"
        assert len(result['changes_applied']) > 0, "Deve ter aplicado correções"
    
    def test_validate_portuguese_text_detects_issues(self):
        """GREEN: Deve detectar problemas no texto"""
        # Arrange
        normalizer = EnemTextNormalizer()
        problematic_text = "Texto com Ã¡reas problemÃ¡ticas"
        
        # Act
        validation = normalizer.validate_portuguese_text(problematic_text)
        
        # Assert
        assert 'valid' in validation, "Deve conter validação"
        assert 'issues' in validation, "Deve conter lista de problemas"
        assert validation['valid'] is False, "Texto problemático deve ser inválido"
        assert len(validation['issues']) > 0, "Deve identificar problemas"


class TestEnemTextNormalizerEdgeCases:
    """GREEN PHASE: Testes de casos extremos."""
    
    def test_normalize_encoding_empty_string_returns_empty_string(self):
        """GREEN: String vazia deve retornar string vazia"""
        # Arrange
        normalizer = EnemTextNormalizer()
        
        # Act
        result = normalizer.normalize_encoding("")
        
        # Assert
        assert result == ""
    
    def test_normalize_encoding_none_input_handles_gracefully(self):
        """GREEN: Input None deve ser tratado graciosamente"""
        # Arrange
        normalizer = EnemTextNormalizer()
        
        # Act & Assert
        result = normalizer.normalize_encoding(None)
        assert result in [None, ""]
    
    def test_normalize_full_with_clean_text_returns_no_changes(self):
        """GREEN: Texto limpo não deve ser modificado"""
        # Arrange
        normalizer = EnemTextNormalizer()
        clean_text = "Texto completamente limpo e sem problemas"
        
        # Act
        result = normalizer.normalize_full(clean_text)
        
        # Assert
        assert result['original'] == result['normalized'], "Texto limpo deve permanecer igual"
        assert result['improvement_score'] == 1.0, "Score deve ser perfeito"
