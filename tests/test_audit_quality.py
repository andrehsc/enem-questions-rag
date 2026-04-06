"""
Tests for audit extraction quality script (Story 8.6).

Covers:
- detect_issues function
- AuditReport structure
- generate_markdown report generation
- QualityTargets pass/fail logic
"""

import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.audit_extraction_quality import (
    detect_issues,
    AuditReport,
    QualityTargets,
    generate_markdown,
)


# ---------------------------------------------------------------------------
# detect_issues
# ---------------------------------------------------------------------------

class TestDetectIssues:

    def test_clean_question_no_issues(self):
        q = {
            'question_text': 'Este é um enunciado suficientemente longo para a questão de teste do ENEM.',
            'alternatives': ['Alt A longa', 'Alt B longa', 'Alt C longa', 'Alt D longa', 'Alt E longa'],
        }
        issues = detect_issues(q)
        assert issues == []

    def test_placeholder_detected(self):
        q = {
            'question_text': 'Enunciado normal com mais de cinquenta caracteres facilmente.',
            'alternatives': ['A) ok', 'B) ok', 'C) ok', 'D) [Alternative not found]', 'E) ok'],
        }
        issues = detect_issues(q)
        assert 'placeholder' in issues

    def test_placeholder_pt_br(self):
        q = {
            'question_text': 'Enunciado normal com mais de cinquenta caracteres facilmente.',
            'alternatives': ['A) ok', 'B) ok', 'C) [Alternativa não encontrada]', 'D) ok', 'E) ok'],
        }
        issues = detect_issues(q)
        assert 'placeholder' in issues

    def test_cid_token_in_text(self):
        q = {
            'question_text': 'Texto com (cid:42) no meio e mais de cinquenta caracteres facilmente.',
            'alternatives': ['Alt A', 'Alt B', 'Alt C', 'Alt D', 'Alt E'],
        }
        issues = detect_issues(q)
        assert 'cid_token' in issues

    def test_cid_token_in_alternative(self):
        q = {
            'question_text': 'Enunciado normal com mais de cinquenta caracteres facilmente.',
            'alternatives': ['A (cid:1)', 'B ok', 'C ok', 'D ok', 'E ok'],
        }
        issues = detect_issues(q)
        assert 'cid_token' in issues

    def test_indesign_artifact(self):
        q = {
            'question_text': 'Texto com ..iinndd' + 'b artefato e mais de cinquenta caracteres facilmente.',
            'alternatives': ['A', 'B', 'C', 'D', 'E'],
        }
        issues = detect_issues(q)
        assert 'indesign_artifact' in issues

    def test_markdown_artifact(self):
        q = {
            'question_text': '## **Heading** com markdown e mais de cinquenta caracteres facilmente.',
            'alternatives': ['A alt', 'B alt', 'C alt', 'D alt', 'E alt'],
        }
        issues = detect_issues(q)
        assert 'markdown_artifact' in issues

    def test_cascade_detected(self):
        q = {
            'question_text': 'Enunciado normal com mais de cinquenta caracteres facilmente.',
            'alternatives': [
                'A e B e C e D e E',
                'B e C e D e E',
                'C e D e E',
                'D e E',
                'E',
            ],
        }
        issues = detect_issues(q)
        assert 'cascade' in issues

    def test_short_enunciado(self):
        q = {
            'question_text': 'Curto',
            'alternatives': ['A', 'B', 'C', 'D', 'E'],
        }
        issues = detect_issues(q)
        assert 'short_enunciado' in issues

    def test_missing_alternatives(self):
        q = {
            'question_text': 'Enunciado normal com mais de cinquenta caracteres facilmente.',
            'alternatives': ['A ok', 'B ok', 'C ok'],
        }
        issues = detect_issues(q)
        assert 'missing_alternatives' in issues

    def test_multiple_issues(self):
        q = {
            'question_text': 'Curto',
            'alternatives': ['A', 'B', '[Alternative not found]'],
        }
        issues = detect_issues(q)
        assert 'short_enunciado' in issues
        assert 'placeholder' in issues
        assert 'missing_alternatives' in issues

    def test_none_text_no_crash(self):
        q = {'question_text': None, 'alternatives': []}
        issues = detect_issues(q)
        assert 'short_enunciado' in issues
        assert 'missing_alternatives' in issues

    def test_empty_alternatives_list(self):
        q = {
            'question_text': 'Enunciado normal com mais de cinquenta caracteres facilmente.',
            'alternatives': [],
        }
        issues = detect_issues(q)
        assert 'missing_alternatives' in issues


# ---------------------------------------------------------------------------
# AuditReport
# ---------------------------------------------------------------------------

class TestAuditReport:

    def test_default_values(self):
        r = AuditReport()
        assert r.total == 0
        assert r.clean == 0
        assert r.dedup_total == 0
        assert r.dedup_unique == 0
        assert r.problematic == []

    def test_issues_by_type_defaultdict(self):
        r = AuditReport()
        r.issues_by_type['placeholder'] += 1
        assert r.issues_by_type['placeholder'] == 1


# ---------------------------------------------------------------------------
# QualityTargets
# ---------------------------------------------------------------------------

class TestQualityTargets:

    def test_defaults(self):
        t = QualityTargets()
        assert t.max_placeholder_rate == 0.0
        assert t.max_header_rate == 0.0
        assert t.max_cascade_rate == 0.0
        assert t.max_cid_rate == 0.0
        assert t.min_clean_rate == 0.90
        assert t.min_dedup_rate == 0.80


# ---------------------------------------------------------------------------
# generate_markdown
# ---------------------------------------------------------------------------

class TestGenerateMarkdown:

    def _make_report(self, total=100, clean=95, placeholders=2, headers=1, cid=0, cascade=1):
        r = AuditReport()
        r.total = total
        r.clean = clean
        r.issues_by_type['placeholder'] = placeholders
        r.issues_by_type['header_pollution'] = headers
        r.issues_by_type['cid_token'] = cid
        r.issues_by_type['cascade'] = cascade
        r.dedup_total = total
        r.dedup_unique = total - 5
        r.breakdown_year[2024] = {'total': total, 'placeholder': placeholders}
        r.breakdown_extractor['pymupdf4llm'] = {'total': total, 'placeholder': placeholders}
        return r

    def test_contains_header(self):
        md = generate_markdown(self._make_report(), QualityTargets())
        assert '# Relatório de Qualidade' in md

    def test_contains_summary_table(self):
        md = generate_markdown(self._make_report(), QualityTargets())
        assert '| Métrica | Valor | Target | Status |' in md

    def test_clean_rate_pass(self):
        r = self._make_report(total=100, clean=95)
        md = generate_markdown(r, QualityTargets())
        assert '| Clean rate | 95.0%' in md
        assert 'PASS' in md

    def test_clean_rate_fail(self):
        r = self._make_report(total=100, clean=50)
        md = generate_markdown(r, QualityTargets())
        # 50% < 90% target → FAIL
        assert 'FAIL' in md

    def test_placeholder_rate_fail(self):
        r = self._make_report(total=100, clean=90, placeholders=10)
        md = generate_markdown(r, QualityTargets())
        # 10% > 0% target → FAIL
        lines = [l for l in md.split('\n') if 'Placeholder rate' in l]
        assert len(lines) == 1
        assert 'FAIL' in lines[0]

    def test_breakdown_year(self):
        md = generate_markdown(self._make_report(), QualityTargets())
        assert '## Breakdown por Ano' in md
        assert '| 2024 |' in md

    def test_breakdown_extractor(self):
        md = generate_markdown(self._make_report(), QualityTargets())
        assert '## Breakdown por Extrator' in md
        assert '| pymupdf4llm |' in md

    def test_problematic_section_present_when_problematic(self):
        r = self._make_report()
        r.problematic = [
            {'id': 'uuid1', 'number': 10, 'year': 2024, 'issues': ['placeholder', 'cascade'], 'score': 0.40},
        ]
        md = generate_markdown(r, QualityTargets())
        assert '## Questões Mais Problemáticas' in md
        assert 'Q10' in md

    def test_no_problematic_section_when_empty(self):
        r = self._make_report()
        r.problematic = []
        md = generate_markdown(r, QualityTargets())
        assert 'Questões Mais Problemáticas' not in md

    def test_dedup_rate(self):
        r = self._make_report(total=100)
        r.dedup_total = 100
        r.dedup_unique = 80
        md = generate_markdown(r, QualityTargets())
        assert 'Dedup rate' in md

    def test_zero_total_no_crash(self):
        r = AuditReport()
        r.total = 0
        md = generate_markdown(r, QualityTargets())
        assert '# Relatório de Qualidade' in md
