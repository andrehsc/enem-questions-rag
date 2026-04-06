"""Tests for alternative_extractor.py v2 — Story 8.2 enhancements.

Covers: cascade detection/fix, strategy merge, no placeholders,
doubled-letter format, inline math, false-positive filter removal.
"""

import pytest

from src.enem_ingestion.alternative_extractor import (
    EnhancedAlternativeExtractor,
    StandardPatternStrategy,
    MultilinePatternStrategy,
    MathematicalStrategy,
    DoubledLetterStrategy,
    ExtractionStrategy,
    _detect_cascade,
    _fix_cascade,
)


@pytest.fixture
def extractor():
    return EnhancedAlternativeExtractor()


# ------------------------------------------------------------------ #
# Cascade detection & fix (AC: 1)
# ------------------------------------------------------------------ #

class TestCascadeDetection:
    def test_detect_cascade_basic(self):
        alts = {
            'A': 'resposta A resposta B resposta C resposta D resposta E',
            'B': 'resposta B resposta C resposta D resposta E',
            'C': 'resposta C resposta D resposta E',
            'D': 'resposta D resposta E',
            'E': 'resposta E',
        }
        assert _detect_cascade(alts) is True

    def test_no_cascade_normal(self):
        alts = {
            'A': 'criticar o desempenho da economia',
            'B': 'rever a estratégia de desenvolvimento',
            'C': 'apoiar a manutenção da política',
            'D': 'avaliar a capacidade de geração',
            'E': 'propor mudanças na estrutura',
        }
        assert _detect_cascade(alts) is False

    def test_fix_cascade_by_differencing(self):
        alts = {
            'A': 'opção A opção B opção C opção D opção E',
            'B': 'opção B opção C opção D opção E',
            'C': 'opção C opção D opção E',
            'D': 'opção D opção E',
            'E': 'opção E',
        }
        fixed = _fix_cascade(alts)
        assert fixed is not None
        assert fixed['E'] == 'opção E'
        assert fixed['D'] == 'opção D'
        assert fixed['C'] == 'opção C'
        assert fixed['B'] == 'opção B'
        assert fixed['A'] == 'opção A'

    def test_cascade_fixed_in_pipeline(self, extractor):
        text = (
            "Questão sobre economia.\n\n"
            "A opção A opção B opção C opção D opção E\n"
            "B opção B opção C opção D opção E\n"
            "C opção C opção D opção E\n"
            "D opção D opção E\n"
            "E opção E\n"
        )
        result = extractor.extract_alternatives(text)
        assert len(result.alternatives) == 5
        assert "cascade_fixed" in result.issues_found


# ------------------------------------------------------------------ #
# Strategy merge (AC: 2)
# ------------------------------------------------------------------ #

class TestStrategyMerge:
    def test_merge_strategies_basic(self):
        from src.enem_ingestion.alternative_extractor import ExtractedAlternatives

        r1 = ExtractedAlternatives(
            alternatives=["A) opt A", "B) opt B", "C) opt C"],
            confidence=0.6,
            strategy_used=ExtractionStrategy.STANDARD_PATTERN,
            issues_found=[],
            raw_matches={'A': 'opt A', 'B': 'opt B', 'C': 'opt C'},
        )
        r2 = ExtractedAlternatives(
            alternatives=["C) opt C2", "D) opt D", "E) opt E"],
            confidence=0.5,
            strategy_used=ExtractionStrategy.MULTILINE_PATTERN,
            issues_found=[],
            raw_matches={'C': 'opt C2', 'D': 'opt D', 'E': 'opt E'},
        )
        merged = EnhancedAlternativeExtractor._merge_strategies([r1, r2])
        assert len(merged) == 5
        assert 'A' in merged and 'E' in merged
        # C should come from r1 (higher confidence)
        assert merged['C'] == 'opt C'


# ------------------------------------------------------------------ #
# No placeholders (AC: 3)
# ------------------------------------------------------------------ #

class TestNoPlaceholders:
    def test_partial_alternatives_no_padding(self, extractor):
        text = (
            "Questão parcial.\n\n"
            "A primeira alternativa de teste\n"
            "B segunda alternativa de teste\n"
            "C terceira alternativa de teste\n"
        )
        result = extractor.extract_alternatives(text)
        for alt in result.alternatives:
            assert "[Alternative not found]" not in alt
            assert "[Alternativa não encontrada]" not in alt

    def test_no_alternatives_returns_empty(self, extractor):
        text = "Texto sem alternativas visíveis."
        result = extractor.extract_alternatives(text)
        for alt in result.alternatives:
            assert "[Alternative not found]" not in alt


# ------------------------------------------------------------------ #
# False-positive filter replaced (AC: 4)
# ------------------------------------------------------------------ #

class TestFalsePositiveFilter:
    def test_ptbr_words_no_longer_rejected(self):
        """Words like 'este', 'esta', 'não há' are valid in alternatives."""
        strategy = StandardPatternStrategy()
        text = (
            "Analise o texto e responda.\n\n"
            "A Esta análise demonstra a influência\n"
            "B Não há contradição entre os textos\n"
            "C Pode ser observado que o autor expõe\n"
            "D Sobre o tema proposto pelo enunciado\n"
            "E Este parágrafo finaliza o argumento\n"
        )
        result = strategy.extract(text)
        assert len(result.alternatives) == 5

    def test_question_bleed_still_rejected(self):
        """Text containing QUESTÃO should be rejected."""
        assert StandardPatternStrategy._is_likely_false_positive(
            "QUESTÃO 15 do caderno"
        ) is True

    def test_very_long_text_rejected(self):
        """Very long text (>500 chars) still rejected."""
        long_text = "x" * 501
        assert StandardPatternStrategy._is_likely_false_positive(long_text) is True


# ------------------------------------------------------------------ #
# Doubled-letter format (AC: 5)
# ------------------------------------------------------------------ #

class TestDoubledLetterStrategy:
    def test_compact_doubled_letters(self):
        strategy = DoubledLetterStrategy()
        text = (
            "AA primeira resposta\n"
            "BB segunda resposta\n"
            "CC terceira resposta\n"
            "DD quarta resposta\n"
            "EE quinta resposta\n"
        )
        result = strategy.extract(text)
        assert len(result.alternatives) == 5
        assert result.alternatives[0].startswith("primeira")
        assert result.alternatives[4].startswith("quinta")

    def test_spaced_doubled_letters(self):
        strategy = DoubledLetterStrategy()
        text = (
            "A A primeira resposta\n"
            "B B segunda resposta\n"
            "C C terceira resposta\n"
            "D D quarta resposta\n"
            "E E quinta resposta\n"
        )
        result = strategy.extract(text)
        assert len(result.alternatives) >= 3


# ------------------------------------------------------------------ #
# Math short alternatives (AC: 6)
# ------------------------------------------------------------------ #

class TestMathShortAlternatives:
    def test_pi_alternatives(self, extractor):
        text = (
            "Calcule o perímetro.\n\n"
            "A π\n"
            "B 2π\n"
            "C 3π\n"
            "D 4π\n"
            "E 5π\n"
        )
        result = extractor.extract_alternatives(text)
        assert len(result.alternatives) == 5

    def test_numeric_alternatives(self, extractor):
        text = (
            "Qual o resultado?\n\n"
            "A 7\n"
            "B 8\n"
            "C 9\n"
            "D 10\n"
            "E 11\n"
        )
        result = extractor.extract_alternatives(text)
        assert len(result.alternatives) == 5


# ------------------------------------------------------------------ #
# Inline alternatives (AC: 6)
# ------------------------------------------------------------------ #

class TestInlineAlternatives:
    def test_inline_with_dots(self, extractor):
        text = "A 7. B 8. C 9. D 10. E 11."
        result = extractor.extract_alternatives(text)
        # Should find at least some
        assert len(result.alternatives) >= 3


# ------------------------------------------------------------------ #
# Complete pipeline (regression)
# ------------------------------------------------------------------ #

class TestCompletePipeline:
    def test_standard_complete(self, extractor):
        text = (
            "Em relação ao texto, a análise correta é:\n\n"
            "A criticar o desempenho da economia brasileira\n"
            "B rever a estratégia de desenvolvimento econômico\n"
            "C apoiar a manutenção da política econômica vigente\n"
            "D avaliar a capacidade de geração de empregos\n"
            "E propor mudanças na estrutura produtiva nacional\n"
        )
        result = extractor.extract_alternatives(text)
        assert len(result.alternatives) == 5
        assert result.confidence > 0.7

    def test_legacy_compatible_returns_list(self, extractor):
        text = (
            "Questão.\n\n"
            "A opção A de teste completa\n"
            "B opção B de teste completa\n"
            "C opção C de teste completa\n"
            "D opção D de teste completa\n"
            "E opção E de teste completa\n"
        )
        alts = extractor.extract_alternatives_legacy_compatible(text)
        assert isinstance(alts, list)
        assert len(alts) == 5
        for alt in alts:
            assert isinstance(alt, str)
