"""
Text Sanitizer for ENEM Questions
==================================
Content-level cleaning for ENEM-specific pollution:
headers/footers, InDesign artifacts, (cid:XX) tokens, markdown residual.

Complementary to text_normalizer.py (which handles encoding/mojibake).
Pipeline order: normalize_enem_text() → sanitize_enem_text() → extract_alternatives()
"""

import re
from typing import List, Tuple


class TextSanitizer:
    """Singleton sanitizer for ENEM content-level pollution."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_patterns()
        return cls._instance

    def _init_patterns(self):
        """Compile all regex patterns once."""

        # --- ENEM page headers/footers ---
        self._header_patterns: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in [
                # "2º DIA • CADERNO 8 • VERDE • MAT"
                r'\d+[°ºo]?\s*DIA\s*[•·.]\s*CADERNO\s*\d+\s*[•·.].*?(?:LIN|MAT|HUM|NAT|RED)\w*',
                # "DERNO 1 . AZUL-"
                r'DERNO\s*\d+\s*[.\s]+(?:AZUL|AMARELO|AMARELA|BRANCO|BRANCA|VERDE|ROSA|CINZA)\w*\s*-?',
                # "LC - 1º dia | Caderno 1 - AZUL - Página 5"
                r'(?:LC|MT|CN|CH)\s*-\s*\d+[°ºo]?\s*dia\s*\|\s*Caderno\s*\d+.*?(?:Página|Pagina)\s*\d+',
                # "4 - ROSA - 1a Aplicação"
                r'\d+\s*-\s*(?:ROSA|AZUL|AMARELO|AMARELA|BRANCO|BRANCA|VERDE|CINZA)\s*-\s*\d*[aª]?\s*(?:Aplicação|Aplicacao)',
                # "Página 25" standalone page marker
                r'(?:Página|Pagina)\s*\d+',
            ]
        ]

        self._header_patterns_nocase: List[re.Pattern] = [
            re.compile(p) for p in [
                # "NEM2024 17", "ENEM2024"
                r'(?:NEM|ENEM)\d{4}\s*\d*',
                # "ENEM20E 26"
                r'ENEM20[A-Z]\s*\d*',
                # "4202 MENE" / "MENE 2024" (reversed)
                r'4202\s*MENE',
                r'MENE\s*\d{4}',
                # OCR artifacts: "enem2o02/", "enenm"-02/"
                r'enenn?m[\W\d]*\d+/?',
            ]
        ]

        # --- Area/subject thematic headers ---
        self._area_patterns: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in [
                r'LINGUAGENS,?\s*C[OÓ]DIGOS\s+E\s+SUAS\s+TECNOLOGIAS',
                r'CI[EÊ]NCIAS\s+(?:HUMANAS|DA\s+NATUREZA)\s+E\s+SUAS\s+TECNOLOGIAS',
                r'MATEM[AÁ]TICA\s+E\s+SUAS\s+TECNOLOGIAS',
                r'(?:^|\s)E\d\s+TEM[AÁ]TICA(?:\s+E\s+SUAS\s+TECNOLOGIAS)?',
                r'Quest[oõ]es\s+de\s+\d+\s+a\s+\d+',
                r'(?:^|\s)REDA[CÇ][AÃ]O(?:\s|$)',
            ]
        ]

        # Partial area headers that appear at boundaries (less anchored)
        self._partial_area_re = re.compile(
            r'(?:UAS|AS)\s+TECNOLOGIAS\s*(?:[•·.].*)?$',
            re.IGNORECASE,
        )

        # --- InDesign artifacts (doubled characters) ---
        self._indesign_patterns: List[re.Pattern] = [
            # "PP22__22__DDiiaa__MMTTTT__RREEGG__88__VVeerrddee..iinndddd 25"
            re.compile(r'PP\d{2}__\d{2}__.*?\.\.iinndd[db]\w*\s*\d*'),
            # Generic doubled-char InDesign filename ending with ..iinndd*
            re.compile(r'(?:[A-Za-z]{2}){3,}\.\.iinndd[db]\w*\s*\d*'),
            # Trailing "..iinnddbb 16"
            re.compile(r'\.\.iinndd[db]\w*\s*\d*'),
            # Doubled timestamps "2233//0088//22002244 1188::1111::2211"
            re.compile(r'\d{4}//\d{4}//\d{8}\s+\d{4}::\d{4}::\d{4,6}'),
        ]

        # --- (cid:XX) tokens ---
        self._cid_re = re.compile(r'\(cid:\d+\)')

        # --- Markdown artifacts ---
        self._markdown_patterns: List[Tuple[re.Pattern, str]] = [
            # "## **" at end of line (consume preceding horizontal whitespace)
            (re.compile(r'[ \t]*#{1,3}\s*\*{1,2}\s*$', re.MULTILINE), ''),
            # "**" as isolated line
            (re.compile(r'^\*{1,2}\s*$', re.MULTILINE), ''),
        ]

        # --- Control characters and replacement char U+FFFD ---
        # Matches C0 control chars (except \t \n \r) and C1 control block (\x80-\x9f)
        self._control_char_re = re.compile(
            r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]'
        )
        # U+FFFD replacement character (single or consecutive runs)
        self._replacement_char_re = re.compile(r'\ufffd+')

        # --- Whitespace collapse ---
        self._multi_space_re = re.compile(r'[ \t]{2,}')
        self._multi_newline_re = re.compile(r'\n{3,}')

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sanitize(self, text: str) -> str:
        """Remove all ENEM content-level pollution from text.

        Args:
            text: Text already encoding-normalized via normalize_enem_text().

        Returns:
            Cleaned text with headers, InDesign, cid, markdown artifacts removed.
        """
        if not text:
            return text

        text = self._remove_control_chars(text)
        text = self._remove_replacement_chars(text)
        text = self._remove_indesign_artifacts(text)
        text = self._remove_cid_tokens(text)
        text = self._remove_headers(text)
        text = self._remove_area_headers(text)
        text = self._remove_markdown_artifacts(text)
        text = self._collapse_whitespace(text)

        return text.strip()

    def sanitize_alternative(self, text: str) -> str:
        """More aggressive cleaning for individual alternative text.

        Strips trailing pollution that commonly attaches to the last alternative.
        """
        if not text:
            return text

        # Run the full sanitizer
        text = self.sanitize(text)

        # Additional trailing cleanup for alternatives
        # Remove trailing page numbers like " 25" at end
        text = re.sub(r'\s+\d{1,3}\s*$', '', text)

        return text.strip()

    def has_contamination(self, text: str) -> bool:
        """Check if text contains any known contamination patterns.

        Used by the confidence scorer to detect polluted questions.
        """
        if not text:
            return False

        # Garbled text detection: high ratio of replacement/control characters
        if self.garble_ratio(text) > 0.10:
            return True

        if self._cid_re.search(text):
            return True
        for pat in self._indesign_patterns:
            if pat.search(text):
                return True
        for pat in self._header_patterns:
            if pat.search(text):
                return True
        for pat in self._header_patterns_nocase:
            if pat.search(text):
                return True
        for pat in self._area_patterns:
            if pat.search(text):
                return True
        return False

    def garble_ratio(self, text: str) -> float:
        """Return ratio of garbled characters (U+FFFD + control) to total."""
        if not text:
            return 0.0
        garbled = len(self._replacement_char_re.findall(text))
        garbled += len(self._control_char_re.findall(text))
        return garbled / len(text)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _remove_control_chars(self, text: str) -> str:
        """Remove C0/C1 control characters (keep \\t \\n \\r)."""
        return self._control_char_re.sub('', text)

    def _remove_replacement_chars(self, text: str) -> str:
        """Replace runs of U+FFFD with a single space."""
        return self._replacement_char_re.sub(' ', text)

    def _remove_headers(self, text: str) -> str:
        for pat in self._header_patterns:
            text = pat.sub('', text)
        for pat in self._header_patterns_nocase:
            text = pat.sub('', text)
        return text

    def _remove_area_headers(self, text: str) -> str:
        for pat in self._area_patterns:
            text = pat.sub('', text)
        text = self._partial_area_re.sub('', text)
        return text

    def _remove_indesign_artifacts(self, text: str) -> str:
        for pat in self._indesign_patterns:
            text = pat.sub('', text)
        return text

    def _remove_cid_tokens(self, text: str) -> str:
        return self._cid_re.sub(' ', text)

    def _remove_markdown_artifacts(self, text: str) -> str:
        for pat, repl in self._markdown_patterns:
            text = pat.sub(repl, text)
        return text

    def _collapse_whitespace(self, text: str) -> str:
        text = self._multi_space_re.sub(' ', text)
        text = self._multi_newline_re.sub('\n\n', text)
        return text


# Module-level singleton convenience functions

def sanitize_enem_text(text: str) -> str:
    """Convenience function using the TextSanitizer singleton."""
    return TextSanitizer().sanitize(text)


def sanitize_alternative(text: str) -> str:
    """Convenience function for alternative-level cleaning."""
    return TextSanitizer().sanitize_alternative(text)
