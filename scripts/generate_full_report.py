#!/usr/bin/env python3
"""
Generate a full extraction report with all questions from the database.

Usage:
    python scripts/generate_full_report.py --db-url $DATABASE_URL
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


def fetch_all_questions(conn):
    """Fetch all questions with alternatives, ordered by year/day/number."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT q.id, q.question_number, q.question_text, q.subject,
                   q.confidence_score, q.extraction_method, q.content_hash,
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


def fetch_dead_letter(conn):
    """Fetch dead letter questions."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, question_number, confidence_score,
                   extraction_method, failed_layers, extraction_errors,
                   pdf_filename, created_at
            FROM enem_questions.dead_letter_questions
            ORDER BY pdf_filename, question_number
        """)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def generate_report(conn):
    """Generate the full extraction report."""
    questions = fetch_all_questions(conn)
    dead_letters = fetch_dead_letter(conn)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_accepted = len(questions)
    total_dead = len(dead_letters)
    total_all = total_accepted + total_dead

    lines = [
        f"# Relatório Completo de Extração ENEM",
        f"> Data: {ts}",
        f"> PDFs processados: 10 cadernos (2020 D1 CD1-CD4, 2020 D2 CD5-CD8, 2021 D1 CD1-CD2)",
        "",
        "---",
        "",
        "## Resumo Geral",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Total questões detectadas | {total_all} |",
        f"| Aceitas (banco) | {total_accepted} ({total_accepted/max(total_all,1):.1%}) |",
        f"| Dead letter | {total_dead} ({total_dead/max(total_all,1):.1%}) |",
    ]

    # Breakdown by year
    years = {}
    for q in questions:
        key = (q['year'], q['day'])
        years.setdefault(key, {'accepted': 0, 'scores': []})
        years[key]['accepted'] += 1
        if q['confidence_score']:
            years[key]['scores'].append(q['confidence_score'])

    for dl in dead_letters:
        fname = dl.get('pdf_filename', '')
        # parse year/day from filename like 2020_PV_impresso_D1_CD1.pdf
        parts = fname.split('_')
        if len(parts) >= 4:
            try:
                y = int(parts[0])
                d = int(parts[3].replace('D', ''))
                key = (y, d)
                years.setdefault(key, {'accepted': 0, 'scores': []})
                years[key].setdefault('dead', 0)
                years[key]['dead'] = years[key].get('dead', 0) + 1
            except ValueError:
                pass

    lines.extend([
        "",
        "## Breakdown por Ano/Dia",
        "",
        "| Ano | Dia | Aceitas | Dead Letter | Média Score |",
        "|-----|-----|---------|-------------|-------------|",
    ])
    for (y, d) in sorted(years.keys()):
        info = years[(y, d)]
        avg = sum(info['scores']) / len(info['scores']) if info['scores'] else 0
        dead = info.get('dead', 0)
        lines.append(f"| {y} | {d} | {info['accepted']} | {dead} | {avg:.3f} |")

    # Confidence score distribution
    scores = [q['confidence_score'] for q in questions if q['confidence_score'] is not None]
    perfect = sum(1 for s in scores if s == 1.0)
    high = sum(1 for s in scores if 0.85 <= s < 1.0)
    medium = sum(1 for s in scores if 0.55 <= s < 0.85)

    lines.extend([
        "",
        "## Distribuição de Scores",
        "",
        "| Faixa | Quantidade | Percentual |",
        "|-------|-----------|------------|",
        f"| 1.00 (perfeito) | {perfect} | {perfect/max(len(scores),1):.1%} |",
        f"| 0.85-0.99 | {high} | {high/max(len(scores),1):.1%} |",
        f"| 0.55-0.84 | {medium} | {medium/max(len(scores),1):.1%} |",
    ])

    # Subject distribution
    subjects = {}
    for q in questions:
        s = q['subject'] or 'indefinido'
        subjects[s] = subjects.get(s, 0) + 1

    lines.extend([
        "",
        "## Distribuição por Área",
        "",
        "| Área | Quantidade |",
        "|------|-----------|",
    ])
    for s in sorted(subjects.keys()):
        lines.append(f"| {s} | {subjects[s]} |")

    # Full question listing
    lines.extend([
        "",
        "---",
        "",
        "## Questões Aceitas (detalhado)",
        "",
    ])

    current_year = None
    current_day = None
    for q in questions:
        if q['year'] != current_year or q['day'] != current_day:
            current_year = q['year']
            current_day = q['day']
            lines.extend([
                f"### {current_year} — Dia {current_day} ({q['caderno']})",
                "",
            ])

        alts = q['alternatives'] or []
        letters = ['A', 'B', 'C', 'D', 'E']
        score = f"{q['confidence_score']:.2f}" if q['confidence_score'] else "?"
        subject = q['subject'] or '-'

        # Full text — no truncation
        text = (q['question_text'] or '').strip()

        lines.append(f"**Q{q['question_number']}** | Score: {score} | Área: {subject}")
        lines.append(f"> {text}")
        lines.append("")

        for i, alt in enumerate(alts[:5]):
            letter = letters[i] if i < len(letters) else '?'
            lines.append(f"- **{letter})** {alt}")

        lines.append("")

    # Dead letter summary
    if dead_letters:
        lines.extend([
            "---",
            "",
            "## Dead Letter (questões rejeitadas)",
            "",
            "| PDF | Q# | Score | Motivo |",
            "|-----|----|-------|--------|",
        ])
        for dl in dead_letters[:50]:  # limit to top 50
            score = f"{dl['confidence_score']:.2f}" if dl['confidence_score'] else "?"
            errors = dl.get('extraction_errors') or []
            if isinstance(errors, list):
                reason = ', '.join(str(e) for e in errors[:3])
            else:
                reason = str(errors)[:80]
            lines.append(f"| {dl.get('pdf_filename', '?')[:30]} | Q{dl['question_number']} | {score} | {reason} |")

        if len(dead_letters) > 50:
            lines.append(f"| ... | ... | ... | (mais {len(dead_letters) - 50} questões) |")

    lines.append("")
    return "\n".join(lines)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate full extraction report")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--output", default="reports", help="Output directory")
    args = parser.parse_args()

    if not args.db_url:
        parser.error("--db-url required (or set DATABASE_URL)")

    conn = psycopg2.connect(args.db_url)
    try:
        report = generate_report(conn)
        os.makedirs(args.output, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        out_path = Path(args.output) / f"relatorio-extracao-completo-{date_str}.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"Report saved to {out_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
