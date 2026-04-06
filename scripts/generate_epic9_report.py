#!/usr/bin/env python3
"""Generate full report with complete questions — no content truncation."""

import sys
import io
import psycopg2
from datetime import datetime

# Force UTF-8 on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_URL = "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"
OUTPUT = "reports/relatorio-epic9-pos-extracao.md"


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # --- Summary stats ---
    cur.execute("SELECT COUNT(*) FROM enem_questions.questions")
    total_q = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM enem_questions.question_alternatives")
    total_alts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM enem_questions.exam_metadata")
    total_exams = cur.fetchone()[0]

    cur.execute("""
        SELECT em.year, em.caderno, em.day, COUNT(q.id),
               AVG(q.confidence_score)::numeric(4,2),
               MIN(q.question_number), MAX(q.question_number)
        FROM enem_questions.questions q
        JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
        GROUP BY em.year, em.caderno, em.day
        ORDER BY em.year, em.caderno
    """)
    caderno_stats = cur.fetchall()

    # --- Score distribution ---
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE confidence_score >= 0.95) as perfect,
            COUNT(*) FILTER (WHERE confidence_score >= 0.85 AND confidence_score < 0.95) as good,
            COUNT(*) FILTER (WHERE confidence_score >= 0.55 AND confidence_score < 0.85) as fallback,
            COUNT(*) FILTER (WHERE confidence_score < 0.55) as dead
        FROM enem_questions.questions
    """)
    score_dist = cur.fetchone()

    # --- All questions with full details ---
    cur.execute("""
        SELECT q.question_number, q.question_text, q.confidence_score,
               q.subject, q.context_text, q.extraction_method,
               em.year, em.caderno, em.day,
               q.id
        FROM enem_questions.questions q
        JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
        ORDER BY em.year, em.caderno, q.question_number
    """)
    questions = cur.fetchall()

    # Build report
    lines = []
    lines.append(f"# Relatório de Extração Epic 9 — Pós-Ingestão 2020-2021")
    lines.append(f"")
    lines.append(f"**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Pipeline:** Epic 9 (Qualidade de Extração v2)")
    lines.append(f"**PDFs processados:** 10 cadernos (2020 D1 CD1-CD4, D2 CD5-CD8, 2021 D1 CD1-CD2)")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Resumo Geral")
    lines.append(f"")
    lines.append(f"| Métrica | Valor |")
    lines.append(f"|---------|-------|")
    lines.append(f"| Questões aceitas (banco) | {total_q} |")
    lines.append(f"| Alternativas no banco | {total_alts} |")
    lines.append(f"| Cadernos processados | {total_exams} |")
    lines.append(f"| Score >= 0.95 (perfeito) | {score_dist[0]} |")
    lines.append(f"| Score 0.85-0.94 (bom) | {score_dist[1]} |")
    lines.append(f"| Score 0.55-0.84 (fallback) | {score_dist[2]} |")
    lines.append(f"| Score < 0.55 (dead letter) | {score_dist[3]} |")
    lines.append(f"")
    lines.append(f"## Distribuição por Caderno")
    lines.append(f"")
    lines.append(f"| Ano | Caderno | Dia | Questões | Score Médio | Range |")
    lines.append(f"|-----|---------|-----|----------|-------------|-------|")
    for row in caderno_stats:
        lines.append(f"| {row[0]} | {row[1]} | D{row[2]} | {row[3]} | {row[4]} | Q{row[5]}-Q{row[6]} |")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Questões na Íntegra")
    lines.append(f"")

    current_caderno = None
    for q in questions:
        q_num, q_text, score, subject, context, method, year, caderno, day, q_id = q

        caderno_key = f"{year}_{caderno}"
        if caderno_key != current_caderno:
            current_caderno = caderno_key
            lines.append(f"### {year} — {caderno} (Dia {day})")
            lines.append(f"")

        # Fetch alternatives for this question
        cur.execute("""
            SELECT alternative_letter, alternative_text
            FROM enem_questions.question_alternatives
            WHERE question_id = %s
            ORDER BY alternative_letter
        """, (q_id,))
        alts = cur.fetchall()

        lines.append(f"#### Questão {q_num} — score={score:.2f} | {subject or 'N/A'} | método={method or 'N/A'}")
        lines.append(f"")

        if context:
            lines.append(f"**Contexto:**")
            lines.append(f"")
            lines.append(f"{context}")
            lines.append(f"")

        lines.append(f"**Enunciado:**")
        lines.append(f"")
        lines.append(f"{q_text}")
        lines.append(f"")

        if alts:
            lines.append(f"**Alternativas:**")
            lines.append(f"")
            for letter, alt_text in alts:
                lines.append(f"- **{letter})** {alt_text}")
            lines.append(f"")
        else:
            lines.append(f"*Sem alternativas no banco*")
            lines.append(f"")

        lines.append(f"---")
        lines.append(f"")

    # Write report
    report = "\n".join(lines)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Relatório gerado: {OUTPUT}")
    print(f"  {total_q} questões, {total_alts} alternativas")
    print(f"  {len(lines)} linhas no relatório")

    conn.close()


if __name__ == "__main__":
    main()
