#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text Normalizer for ENEM Questions
=================================
Módulo para normalização e correção de problemas de encoding em textos do ENEM
"""

import re
import unicodedata
from typing import Dict, List, Optional


class EnemTextNormalizer:
    """Normalizador de texto específico para documentos do ENEM."""
    
    def __init__(self):
        """Inicializar o normalizador com correções específicas do ENEM."""
        
        # Correções de mojibake UTF-8 comuns
        self.mojibake_corrections = {
            # Acentos básicos
            'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
            'Ã ': 'à', 'Ãª': 'ê', 'Ã´': 'ô', 'Ã§': 'ç', 'Ã£': 'ã',
            'Ã¢': 'â', 'Ã®': 'î', 'Ã¹': 'ù', 'Ã¨': 'è', 'Ã¼': 'ü',
            
            # Caracteres especiais comuns
            'â€™': "'", 'â€œ': '"', 'â€': '"', 'â€¢': '•',
            
            # Pontuação
            'â€¦': '...', 'â€"': '—', 'â€"': '–',
            
            # Símbolos matemáticos
            'Ã—': '×', 'Ã·': '÷', 'âˆš': '√', 'âˆž': '∞'
        }
        
        # Correções de caracteres problemáticos
        self.character_replacements = {
            # Aspas e apóstrofos
            '"': '"', '"': '"', ''': "'", ''': "'",
            '„': '"', '‚': "'", '«': '"', '»': '"',
            
            # Hífen e traços
            '—': '-', '–': '-', '―': '-',
            
            # Espaços especiais
            '\u00a0': ' ',  # Non-breaking space
            '\u2009': ' ',  # Thin space
            '\u200b': '',   # Zero-width space
            
            # Outros caracteres problemáticos
            '…': '...', '•': '•', '◦': '•',
        }
        
        # Padrões regex para limpeza
        self.cleanup_patterns = [
            # Múltiplos espaços
            (r'\s+', ' '),
            
            # Quebras de linha excessivas
            (r'\n{3,}', '\n\n'),
            
            # Espaços no início/fim de linhas
            (r'^\s+|\s+$', ''),
            
            # Códigos de controle PDF
            (r'\*\d+[A-Z]+\d+\*', ''),
            
            # Marcadores de página
            (r'LC\s*-\s*\d+°?\s*dia\s*\|\s*Caderno\s*\d+.*?Página\s*\d+', ''),
            
            # Caracteres de controle invisíveis
            (r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', ''),
        ]
    
    def normalize_encoding(self, text: str) -> str:
        """Corrigir problemas de encoding no texto."""
        if not text:
            return text
        
        # Aplicar correções de mojibake
        for wrong, correct in self.mojibake_corrections.items():
            text = text.replace(wrong, correct)
        
        # Aplicar correções de caracteres
        for wrong, correct in self.character_replacements.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def clean_pdf_artifacts(self, text: str) -> str:
        """Remove artifacts específicos de extração de PDF."""
        if not text:
            return text
        
        # Aplicar padrões de limpeza
        for pattern, replacement in self.cleanup_patterns:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        
        return text.strip()
    
    def normalize_unicode(self, text: str) -> str:
        """Normalizar representação Unicode do texto."""
        if not text:
            return text
        
        # Normalizar para forma canônica composta (NFC)
        text = unicodedata.normalize('NFC', text)
        
        return text
    
    def validate_portuguese_text(self, text: str) -> Dict:
        """Validar se o texto contém caracteres válidos para português."""
        if not text:
            return {'valid': True, 'issues': []}
        
        issues = []
        
        # Verificar sequências de ? (indicam problemas de encoding)
        question_marks = re.findall(r'\?{2,}', text)
        if question_marks:
            issues.append(f"Sequências de '?': {len(question_marks)} ocorrências")
        
        # Verificar mojibake patterns
        mojibake_patterns = ['Ã', 'â€', 'Â']
        for pattern in mojibake_patterns:
            if pattern in text:
                count = text.count(pattern)
                issues.append(f"Padrão mojibake '{pattern}': {count} ocorrências")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'text_length': len(text)
        }
    
    def normalize_full(self, text: str) -> Dict:
        """Aplicar todas as normalizações e retornar resultado com métricas."""
        if not text:
            return {
                'original': text,
                'normalized': text,
                'changes_applied': [],
                'validation': {'valid': True, 'issues': []}
            }
        
        original = text
        changes_applied = []
        
        # Validação inicial
        initial_validation = self.validate_portuguese_text(text)
        
        # 1. Correção de encoding
        text_after_encoding = self.normalize_encoding(text)
        if text_after_encoding != text:
            changes_applied.append('encoding_correction')
        text = text_after_encoding
        
        # 2. Limpeza de artifacts PDF
        text_after_cleanup = self.clean_pdf_artifacts(text)
        if text_after_cleanup != text:
            changes_applied.append('pdf_cleanup')
        text = text_after_cleanup
        
        # 3. Normalização Unicode
        text_after_unicode = self.normalize_unicode(text)
        if text_after_unicode != text:
            changes_applied.append('unicode_normalization')
        text = text_after_unicode
        
        # Validação final
        final_validation = self.validate_portuguese_text(text)
        
        return {
            'original': original,
            'normalized': text,
            'changes_applied': changes_applied,
            'original_validation': initial_validation,
            'final_validation': final_validation,
            'improvement_score': self._calculate_improvement_score(initial_validation, final_validation)
        }
    
    def _calculate_improvement_score(self, initial: Dict, final: Dict) -> float:
        """Calcular score de melhoria (0-1, onde 1 é melhor)."""
        initial_issues = len(initial.get('issues', []))
        final_issues = len(final.get('issues', []))
        
        if initial_issues == 0:
            return 1.0  # Já estava bom
        
        improvement = (initial_issues - final_issues) / initial_issues
        return max(0.0, improvement)


# Função de conveniência para uso direto
def normalize_enem_text(text: str) -> str:
    """Função de conveniência para normalização simples."""
    normalizer = EnemTextNormalizer()
    result = normalizer.normalize_full(text)
    return result['normalized']


if __name__ == "__main__":
    # Teste básico
    normalizer = EnemTextNormalizer()
    
    # Texto de exemplo com problemas
    test_text = "Questão sobre área e perímetro — análise gráfica → resultado é 25²"
    
    print("🔧 ENEM Text Normalizer - Teste")
    print("=" * 50)
    print(f"Texto original: {test_text}")
    
    result = normalizer.normalize_full(test_text)
    
    print(f"Texto normalizado: {result['normalized']}")
    print(f"Mudanças aplicadas: {result['changes_applied']}")
    print(f"Score de melhoria: {result['improvement_score']:.2f}")
    
    if result['final_validation']['issues']:
        print(f"Problemas restantes: {result['final_validation']['issues']}")
    else:
        print("✅ Texto normalizado com sucesso!")