#!/usr/bin/env python3
"""
Audit extraction quality and generate report (Story 8.6).

Inspects all questions in the database, detects residual issues,
and generates a markdown quality report with pass/fail against targets.

Usage:
    python scripts/audit_extraction_quality.py --db-url $DATABASE_URL [--output reports/]
"""

import argparse
import logging
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from enem_ingestion.text_sanitizer import TextSanitizer

logger = logging.getLogger(__name__)

_sanitizer = TextSanitizer()


# ------------------------------------------------------------------ #
# Quality targets
# ------------------------------------------------------------------ #

@dataclass
class QualityTargets:
    max_placeholder_rate: float = 0.0
    max_header_rate: float = 0.0
    max_cascade_rate: float = 0.0
    max_cid_rate: float = 0.0
    min_clean_rate: float = 0.90
    min_dedup_rate: float = 0.80


@dataclass
class AuditReport:
    total: int = 0
    clean: int = 0
    issues_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    breakdown_year: Dict[int, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    breakdown_extractor: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    problematic: List[dict] = field(default_factory=list)
    dedup_total: int = 0
    dedup_unique: int = 0


# ------------------------------------------------------------------ #
# Issue detection
# ------------------------------------------------------------------ #

_PLACEHOLDER_RE = re.compile(r'\[Alternative not found\]|\[Alternativa não encontrada\]', re.IGNORECASE)
_CID_RE = re.compile(r'\(cid:\d+\)')
_INDESIGN_RE = re.compile(r'\.\.iinndd[db]')
_MARKDOWN_RE = re.compile(r'#{1,3}\s*\*{1,2}')


def detect_issues(question: dict) -> List[str]:
    """Detect quality issues in a single question row."""
    issues = []
    text = question.get('question_text') or ''
    alts = question.get('alternatives') or []

    full_text = text + ' ' + ' '.join(alts)

    if any(_PLACEHOLDER_RE.search(a) for a in alts):
        issues.append('placeholder')

    if _sanitizer.has_contamination(text):
        issues.append('header_pollution')

    if _CID_RE.search(full_text):
        issues.append('cid_token')

    if _INDESIGN_RE.search(full_text):
        issues.append('indesign_artifact')

    if _MARKDOWN_RE.search(full_text):
        issues.append('markdown_artifact')

    # Cascade: A much longer than E
    if len(alts) >= 5 and len(alts[0]) > 3 * len(alts[4]) and len(alts[4]) > 0:
        if alts[1] in alts[0] and alts[2] in alts[1]:
            issues.append('cascade')

    if len(text) < 50:
        issues.append('short_enunciado')

    if len(alts) < 5:
        issues.append('missing_alternatives')

    return issues


# ------------------------------------------------------------------ #
# Database fetch
# ------------------------------------------------------------------ #

def fetch_all_questions(conn) -> List[dict]:
    """Fetch all questions with their alternatives from the database."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT q.id, q.question_number, q.question_text, q.subject,
                   q.confidence_score, q.extraction_method, q.content_hash,
                   q.canonical_question_id,
                   em.year, em.day, em.caderno,
                   COALESCE(
                       (SELECT array_agg(alternative_text ORDER BY alternative_order)
                        FROM enem_questions.question_alternatives qa
                        WHERE qa.question_id = q.id), '{}'
                   ) AS alternatives
            FROM enem_questions.questions q
            JOIN enem_questions.exam_metadata em ON em.id = q.exam_metadata_id
            ORDER BY em.year, em.day, q.question_number
        """)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


# ------------------------------------------------------------------ #
# Audit
# ------------------------------------------------------------------ #

def audit_questions(conn) -> AuditReport:
    """Run full audit on all questions."""
    questions = fetch_all_questions(conn)
    report = AuditReport()
    report.total = len(questions)

    seen_hashes = set()
    for q in questions:
        issues = detect_issues(q)
        year = q.get('year', 0)
        extractor = q.get('extraction_method', 'unknown')

        report.breakdown_year[year]['total'] = report.breakdown_year[year].get('total', 0) + 1
        report.breakdown_extractor[extractor]['total'] = report.breakdown_extractor[extractor].get('total', 0) + 1

        if issues:
            for issue in issues:
                report.issues_by_type[issue] += 1
                report.breakdown_year[year][issue] = report.breakdown_year[year].get(issue, 0) + 1
                report.breakdown_extractor[extractor][issue] = report.breakdown_extractor[extractor].get(issue, 0) + 1
            if len(issues) >= 2:
                report.problematic.append({
                    'id': q['id'],
                    'number': q['question_number'],
                    'year': year,
                    'issues': issues,
                    'score': q.get('confidence_score'),
                })
        else:
            report.clean += 1

        ch = q.get('content_hash')
        if ch:
            seen_hashes.add(ch)

    report.dedup_total = report.total
    report.dedup_unique = len(seen_hashes) if seen_hashes else report.total
    return report


# ------------------------------------------------------------------ #
# Report generation
# ------------------------------------------------------------------ #

def generate_markdown(report: AuditReport, targets: QualityTargets) -> str:
    """Generate a markdown quality report."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = max(report.total, 1)

    def rate(count):
        return count / total

    def status(value, target, higher_is_better=True):
        if higher_is_better:
            return "PASS" if value >= target else "FAIL"
        return "PASS" if value <= target else "FAIL"

    placeholder_rate = rate(report.issues_by_type.get('placeholder', 0))
    header_rate = rate(report.issues_by_type.get('header_pollution', 0))
    cascade_rate = rate(report.issues_by_type.get('cascade', 0))
    cid_rate = rate(report.issues_by_type.get('cid_token', 0))
    clean_rate = report.clean / total
    dedup_rate = 1 - (report.dedup_unique / total) if total > 0 else 0

    lines = [
        f"# Relatório de Qualidade — Extração ENEM",
        f"> Data: {ts}",
        f"> Total questões: {report.total}",
        "",
        "## Resumo",
        "",
        "| Métrica | Valor | Target | Status |",
        "|---------|-------|--------|--------|",
        f"| Placeholder rate | {placeholder_rate:.1%} | {targets.max_placeholder_rate:.0%} | {status(placeholder_rate, targets.max_placeholder_rate, False)} |",
        f"| Header pollution | {header_rate:.1%} | {targets.max_header_rate:.0%} | {status(header_rate, targets.max_header_rate, False)} |",
        f"| Cascade rate | {cascade_rate:.1%} | {targets.max_cascade_rate:.0%} | {status(cascade_rate, targets.max_cascade_rate, False)} |",
        f"| CID token rate | {cid_rate:.1%} | {targets.max_cid_rate:.0%} | {status(cid_rate, targets.max_cid_rate, False)} |",
        f"| Clean rate | {clean_rate:.1%} | {targets.min_clean_rate:.0%} | {status(clean_rate, targets.min_clean_rate, True)} |",
        f"| Dedup rate | {dedup_rate:.1%} | {targets.min_dedup_rate:.0%} | {status(dedup_rate, targets.min_dedup_rate, True)} |",
        "",
        "## Breakdown por Ano",
        "",
        "| Ano | Total | Clean | Placeholder | Header | CID | Cascade |",
        "|-----|-------|-------|-------------|--------|-----|---------|",
    ]

    for year in sorted(report.breakdown_year.keys()):
        d = report.breakdown_year[year]
        t = d.get('total', 0)
        lines.append(
            f"| {year} | {t} | {t - sum(v for k,v in d.items() if k != 'total')} "
            f"| {d.get('placeholder',0)} | {d.get('header_pollution',0)} "
            f"| {d.get('cid_token',0)} | {d.get('cascade',0)} |"
        )

    lines.extend([
        "",
        "## Breakdown por Extrator",
        "",
        "| Extrator | Total | Clean | Issues |",
        "|----------|-------|-------|--------|",
    ])

    for ext in sorted(report.breakdown_extractor.keys()):
        d = report.breakdown_extractor[ext]
        t = d.get('total', 0)
        issues = sum(v for k, v in d.items() if k != 'total')
        lines.append(f"| {ext} | {t} | {t - issues} | {issues} |")

    if report.problematic:
        lines.extend([
            "",
            "## Questões Mais Problemáticas (top 20)",
            "",
            "| Ano | Q# | Score | Issues |",
            "|-----|----| ------|--------|",
        ])
        for p in sorted(report.problematic, key=lambda x: len(x['issues']), reverse=True)[:20]:
            score = f"{p['score']:.2f}" if p['score'] else "?"
            lines.append(f"| {p['year']} | Q{p['number']} | {score} | {', '.join(p['issues'])} |")

    lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------ #
# CLI
# ------------------------------------------------------------------ #

def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Audit ENEM extraction quality")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--output", default="reports", help="Output directory")
    args = parser.parse_args()

    if not args.db_url:
        parser.error("--db-url required (or set DATABASE_URL)")

    conn = psycopg2.connect(args.db_url)
    try:
        report = audit_questions(conn)
        targets = QualityTargets()
        md = generate_markdown(report, targets)

        os.makedirs(args.output, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        out_path = Path(args.output) / f"quality-audit-{date_str}.md"
        out_path.write_text(md, encoding="utf-8")

        print(f"Audit complete: {report.total} questions")
        print(f"  Clean: {report.clean} ({report.clean/max(report.total,1):.1%})")
        print(f"  Issues: {dict(report.issues_by_type)}")
        print(f"  Report saved to {out_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
