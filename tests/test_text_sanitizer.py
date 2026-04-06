"""Tests for TextSanitizer — ENEM content-level pollution removal."""

import pytest

from src.enem_ingestion.text_sanitizer import TextSanitizer, sanitize_enem_text, sanitize_alternative


# ------------------------------------------------------------------
# Singleton (AC: 5)
# ------------------------------------------------------------------

class TestSingleton:
    def test_singleton_identity(self):
        """TextSanitizer() always returns the same instance."""
        a = TextSanitizer()
        b = TextSanitizer()
        assert a is b

    def test_convenience_function_uses_singleton(self):
        """sanitize_enem_text uses the singleton, not a new instance."""
        result = sanitize_enem_text("clean text")
        assert result == "clean text"


# ------------------------------------------------------------------
# ENEM Page Headers (AC: 1)
# ------------------------------------------------------------------

class TestHeaderRemoval:
    @pytest.mark.parametrize("dirty,expected", [
        # "2º DIA • CADERNO 8 • VERDE • MAT" variants
        (
            "Dentre essas duas embalagens 2º DIA • CADERNO 8 • VERDE • MAT",
            "Dentre essas duas embalagens",
        ),
        (
            "resultado 1o DIA . CADERNO 2 . AMARELO . LINGUAGENS",
            "resultado",
        ),
        # "DERNO 1 . AZUL-"
        (
            "necessidade de capacitação profissional. DERNO 1 . AZUL-",
            "necessidade de capacitação profissional.",
        ),
        # NEM2024 / ENEM2024
        (
            "resultado NEM2024 17",
            "resultado",
        ),
        (
            "texto ENEM2024",
            "texto",
        ),
        # ENEM20E
        (
            "resposta E. ENEM20E 26",
            "resposta E.",
        ),
        # 4202 MENE (reversed)
        (
            "texto final 4202 MENE",
            "texto final",
        ),
        # MENE 2024
        (
            "texto MENE 2024 final",
            "texto final",
        ),
        # LC page marker
        (
            "texto CH - 1º dia | Caderno 3 - BRANCO - Página 5 mais",
            "texto mais",
        ),
        # Color-application format
        (
            "texto 4 - ROSA - 1a Aplicação fim",
            "texto fim",
        ),
        # Standalone page marker
        (
            "texto da questão Página 25",
            "texto da questão",
        ),
    ])
    def test_header_variants(self, dirty, expected):
        result = sanitize_enem_text(dirty)
        assert result.strip() == expected.strip()

    def test_preserves_legitimate_caderno(self):
        """'CADERNO' in literary context should NOT be removed."""
        text = "O aluno abriu o caderno e começou a escrever"
        assert sanitize_enem_text(text) == text


# ------------------------------------------------------------------
# Area/Subject Headers (AC: 1)
# ------------------------------------------------------------------

class TestAreaHeaderRemoval:
    @pytest.mark.parametrize("dirty,expected", [
        (
            "A resposta é 5. CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS",
            "A resposta é 5.",
        ),
        (
            "texto LINGUAGENS, CÓDIGOS E SUAS TECNOLOGIAS mais",
            "texto mais",
        ),
        (
            "resposta MATEMÁTICA E SUAS TECNOLOGIAS",
            "resposta",
        ),
        (
            "fim E4 TEMÁTICA",
            "fim",
        ),
        (
            "texto Questões de 1 a 45 mais",
            "texto mais",
        ),
        # Partial area header at boundary
        (
            "resposta E. UAS TECNOLOGIAS",
            "resposta E.",
        ),
    ])
    def test_area_variants(self, dirty, expected):
        result = sanitize_enem_text(dirty)
        assert result.strip() == expected.strip()


# ------------------------------------------------------------------
# InDesign Artifacts (AC: 2)
# ------------------------------------------------------------------

class TestInDesignRemoval:
    @pytest.mark.parametrize("dirty,expected", [
        # Full InDesign filename
        (
            "feitas durante o processo criativo. PP22__11__DDiiaa__LLCCTT__RREEGG__22__AAmmaarreelloo..iinndddd",
            "feitas durante o processo criativo.",
        ),
        # Trailing iinnddbb
        (
            "texto final ..iinnddbb 16",
            "texto final",
        ),
        # Doubled timestamp
        (
            "texto 2233//0088//22002244 1188::1111::2211",
            "texto",
        ),
        # Generic doubled char + iinndddd
        (
            "resposta VVeerrddee..iinndddd 2255",
            "resposta",
        ),
    ])
    def test_indesign_variants(self, dirty, expected):
        result = sanitize_enem_text(dirty)
        assert result.strip() == expected.strip()


# ------------------------------------------------------------------
# (cid:XX) Tokens (AC: 3)
# ------------------------------------------------------------------

class TestCidRemoval:
    def test_cid_tokens_replaced(self):
        text = "retrata horror (cid:3)(cid:10)(cid:5)"
        result = sanitize_enem_text(text)
        assert result == "retrata horror"

    def test_cid_mid_text(self):
        text = "texto (cid:42) mais (cid:99) conteúdo"
        result = sanitize_enem_text(text)
        assert result == "texto mais conteúdo"

    def test_no_cid_preserved(self):
        text = "texto normal sem cid"
        assert sanitize_enem_text(text) == text


# ------------------------------------------------------------------
# Markdown Artifacts (AC: 4)
# ------------------------------------------------------------------

class TestMarkdownRemoval:
    def test_trailing_hash_star(self):
        text = "apelido jocoso. ## **"
        result = sanitize_enem_text(text)
        assert result == "apelido jocoso."

    def test_isolated_double_star(self):
        text = "linha anterior\n**\nlinha seguinte"
        result = sanitize_enem_text(text)
        assert result == "linha anterior\n\nlinha seguinte"

    def test_hash_star_end_of_line(self):
        text = "texto da questão ## **\nMais conteúdo"
        result = sanitize_enem_text(text)
        assert result == "texto da questão\nMais conteúdo"


# ------------------------------------------------------------------
# Alternative-level cleaning
# ------------------------------------------------------------------

class TestSanitizeAlternative:
    def test_strips_trailing_page_number(self):
        text = "opção correta 25"
        result = sanitize_alternative(text)
        assert result == "opção correta"

    def test_strips_trailing_header(self):
        text = "a resposta. ENEM20E 26"
        result = sanitize_alternative(text)
        assert result == "a resposta."


# ------------------------------------------------------------------
# Idempotency (AC general)
# ------------------------------------------------------------------

class TestIdempotency:
    @pytest.mark.parametrize("text", [
        "texto com DERNO 1 . AZUL- poluição",
        "texto (cid:3)(cid:10) com cid",
        "texto PP22__11__DDiiaa..iinndddd artefato",
        "texto limpo sem poluição",
    ])
    def test_double_sanitize_is_idempotent(self, text):
        once = sanitize_enem_text(text)
        twice = sanitize_enem_text(once)
        assert once == twice


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# 2021 Caderno artifacts (Story 9.5)
# ------------------------------------------------------------------

class TestCaderno2021Artifacts:
    @pytest.mark.parametrize("input_text,expected", [
        ("texto enem2o02/ continuação", "texto continuação"),
        ("texto enem2o2/ continuação", "texto continuação"),
        ("6 LC - 1º dia | Caderno 1 - AZUL - 1º Aplicação", ""),
        ("20 LC - 1º dia | Caderno 2 - AMARELO - 1º Aplicação", ""),
        ("15 CN - 2º dia | Caderno 5 - AMARELO - 1ª Aplicação", ""),
    ])
    def test_sanitize_caderno_2021_artifacts(self, input_text, expected):
        assert sanitize_enem_text(input_text).strip() == expected

    def test_has_contamination_enem_ocr_logo(self):
        assert TextSanitizer().has_contamination("texto enem2o02/ test")

    def test_has_contamination_lc_header_2021(self):
        assert TextSanitizer().has_contamination("6 LC - 1º dia | Caderno 1 - AZUL - 1º Aplicação")

    def test_existing_headers_still_removed(self):
        """Regression: existing patterns not broken."""
        assert sanitize_enem_text("NEM2024 17 texto").strip() == "texto"
        assert sanitize_enem_text("LC - 1º dia | Caderno 1 - AZUL - Página 5").strip() == ""


class TestEdgeCases:
    def test_empty_string(self):
        assert sanitize_enem_text("") == ""

    def test_none_returns_none(self):
        assert sanitize_enem_text(None) is None

    def test_only_pollution(self):
        text = "NEM2024 17"
        result = sanitize_enem_text(text)
        assert result == ""

    def test_combined_pollution(self):
        """Real-world example with multiple pollution types."""
        text = (
            "O valor aproximado é A 11. B 15. C 17. D 62. E 66. "
            "ENEM20E 26 2º DIA • CADERNO 8 • VERDE • MAT "
            "VVeerrddee..iinndddd 2266"
        )
        result = sanitize_enem_text(text)
        assert "ENEM20E" not in result
        assert "CADERNO" not in result
        assert "iinndddd" not in result
        # The actual question content preserved
        assert "O valor aproximado" in result
