#!/usr/bin/env python3
"""
Deduplicate existing questions in the database (Story 8.4).

Groups questions by content_hash, keeps the one with the highest
confidence score as canonical, and marks the rest with canonical_question_id.

Usage:
    python scripts/deduplicate_existing.py --db-url $DATABASE_URL [--dry-run]
"""

import argparse
import hashlib
import logging
import os
import re
import sys

import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

logger = logging.getLogger(__name__)


def compute_content_hash(enunciado: str, year: int, day: int) -> str:
    """Compute a stable content hash for cross-booklet deduplication."""
    normalized = (enunciado or "").lower().strip()
    normalized = re.sub(r'quest[ãa]o\s*\d+', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    payload = f"{year}:{day}:{normalized}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]


def backfill_content_hashes(conn, dry_run: bool) -> int:
    """Compute and store content_hash for all questions that lack one."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT q.id, q.question_text, em.year, em.day
            FROM enem_questions.questions q
            JOIN enem_questions.exam_metadata em ON em.id = q.exam_metadata_id
            WHERE q.content_hash IS NULL
        """)
        rows = cur.fetchall()

    updated = 0
    for qid, text, year, day in rows:
        ch = compute_content_hash(text, year, day)
        if not dry_run:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE enem_questions.questions SET content_hash = %s WHERE id = %s",
                    (ch, qid),
                )
        updated += 1

    if not dry_run:
        conn.commit()
    return updated


def deduplicate(conn, dry_run: bool) -> dict:
    """Group by content_hash, keep best, mark rest as canonical."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT content_hash, array_agg(id ORDER BY confidence_score DESC NULLS LAST),
                   array_agg(confidence_score ORDER BY confidence_score DESC NULLS LAST)
            FROM enem_questions.questions
            WHERE content_hash IS NOT NULL
            GROUP BY content_hash
            HAVING COUNT(*) > 1
        """)
        groups = cur.fetchall()

    stats = {"groups": len(groups), "canonical": 0, "duplicates_marked": 0}

    for content_hash, ids, scores in groups:
        canonical_id = ids[0]
        duplicate_ids = ids[1:]
        stats["canonical"] += 1
        stats["duplicates_marked"] += len(duplicate_ids)

        logger.info(
            "[DEDUP] hash=%s canonical=%s duplicates=%d (scores: %s)",
            content_hash, canonical_id, len(duplicate_ids),
            [f"{s:.2f}" if s else "?" for s in scores],
        )

        if not dry_run:
            with conn.cursor() as cur:
                for dup_id in duplicate_ids:
                    cur.execute(
                        "UPDATE enem_questions.questions SET canonical_question_id = %s WHERE id = %s",
                        (canonical_id, dup_id),
                    )

    if not dry_run:
        conn.commit()
    return stats


def main():
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Deduplicate ENEM questions")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()

    if not args.db_url:
        parser.error("--db-url required (or set DATABASE_URL)")

    conn = psycopg2.connect(args.db_url)
    try:
        prefix = "[DRY-RUN] " if args.dry_run else ""

        # Step 1: backfill content hashes
        updated = backfill_content_hashes(conn, args.dry_run)
        print(f"{prefix}Backfilled content_hash for {updated} questions")

        # Step 2: deduplicate
        stats = deduplicate(conn, args.dry_run)
        print(
            f"{prefix}Dedup complete: {stats['groups']} groups, "
            f"{stats['canonical']} canonical, "
            f"{stats['duplicates_marked']} duplicates marked"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
