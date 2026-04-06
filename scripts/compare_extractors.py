#!/usr/bin/env python3
"""
Compare pdfplumber vs pymupdf4llm extractors per PDF (Story 8.5).

Runs both extractors on each PDF in the input directory, scores the
results, and produces a markdown decision matrix.

Usage:
    python scripts/compare_extractors.py --input data/downloads/ [--output reports/]
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from enem_ingestion.pymupdf4llm_extractor import Pymupdf4llmExtractor
from enem_ingestion.parser import EnemPDFParser
from enem_ingestion.confidence_scorer import ExtractionConfidenceScorer

logger = logging.getLogger(__name__)


def compare_pdf(pdf_path: Path) -> dict:
    """Run both extractors on a single PDF and return comparative metrics."""
    scorer = ExtractionConfidenceScorer()

    # pymupdf4llm
    try:
        ext = Pymupdf4llmExtractor(output_dir="data/tmp_compare")
        qs_pymupdf = ext.extract_questions(str(pdf_path))
        scores_pymupdf = [scorer.score(q).score for q in qs_pymupdf]
    except Exception as e:
        logger.error("pymupdf4llm failed on %s: %s", pdf_path.name, e)
        qs_pymupdf, scores_pymupdf = [], []

    # pdfplumber
    try:
        parser = EnemPDFParser()
        qs_pdfplumber = parser.parse_questions(str(pdf_path))
        scores_pdfplumber = [scorer.score(q).score for q in qs_pdfplumber]
    except Exception as e:
        logger.error("pdfplumber failed on %s: %s", pdf_path.name, e)
        qs_pdfplumber, scores_pdfplumber = [], []

    avg_pymupdf = mean(scores_pymupdf) if scores_pymupdf else 0.0
    avg_pdfplumber = mean(scores_pdfplumber) if scores_pdfplumber else 0.0

    return {
        'pdf': pdf_path.name,
        'pymupdf4llm': {'count': len(qs_pymupdf), 'avg_score': round(avg_pymupdf, 3)},
        'pdfplumber': {'count': len(qs_pdfplumber), 'avg_score': round(avg_pdfplumber, 3)},
        'recommended': 'pymupdf4llm' if avg_pymupdf >= avg_pdfplumber else 'pdfplumber',
    }


def generate_report(results: list, output_dir: str) -> str:
    """Generate a markdown decision matrix from comparison results."""
    lines = [
        "# Extractor Decision Matrix",
        "",
        "| PDF | pymupdf4llm (count/avg) | pdfplumber (count/avg) | Recommended |",
        "|-----|------------------------|----------------------|-------------|",
    ]

    for r in results:
        pm = r['pymupdf4llm']
        pp = r['pdfplumber']
        lines.append(
            f"| {r['pdf']} | {pm['count']} / {pm['avg_score']:.3f} "
            f"| {pp['count']} / {pp['avg_score']:.3f} | **{r['recommended']}** |"
        )

    lines.append("")
    content = "\n".join(lines)

    os.makedirs(output_dir, exist_ok=True)
    out_path = Path(output_dir) / "extractor-decision-matrix.md"
    out_path.write_text(content, encoding="utf-8")
    return str(out_path)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Compare ENEM PDF extractors")
    parser.add_argument("--input", required=True, help="Directory with PDF files")
    parser.add_argument("--output", default="reports", help="Output directory for reports")
    args = parser.parse_args()

    pdfs = sorted(Path(args.input).glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {args.input}")
        return

    print(f"Comparing {len(pdfs)} PDFs...")
    results = []
    for pdf in pdfs:
        print(f"  Processing {pdf.name}...")
        r = compare_pdf(pdf)
        results.append(r)
        print(f"    pymupdf4llm: {r['pymupdf4llm']['count']} qs, avg {r['pymupdf4llm']['avg_score']:.3f}")
        print(f"    pdfplumber:  {r['pdfplumber']['count']} qs, avg {r['pdfplumber']['avg_score']:.3f}")
        print(f"    -> {r['recommended']}")

    out_path = generate_report(results, args.output)
    print(f"\nDecision matrix saved to {out_path}")


if __name__ == "__main__":
    main()
