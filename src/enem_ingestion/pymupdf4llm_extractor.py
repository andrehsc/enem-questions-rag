"""
pymupdf4llm-based Extractor for ENEM PDFs.

Replaces pdfplumber as the primary extraction layer, providing:
- Automatic multi-column detection via Layout AI (ONNX)
- OCR in Portuguese for scanned pages
- Image-question association via bounding box overlap
- Output compatible with existing Question dataclass
"""

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Layout AI MUST be imported BEFORE pymupdf4llm
try:
    import pymupdf.layout  # noqa: F401 — activates Layout AI module
except ImportError:
    pass  # Layout AI optional; pymupdf4llm works without it

import pymupdf4llm

from .parser import Question, QuestionMetadata, Subject, EnemPDFParser
from .alternative_extractor import create_enhanced_extractor
from .text_normalizer import normalize_enem_text

logger = logging.getLogger(__name__)

# Regex to split questions from markdown output
QUESTION_SPLIT_RE = re.compile(
    r'(?:QUESTÃO|Questão|questão|QUEST[ÃA]O)\s*(\d+)',
    re.IGNORECASE,
)

# Regex for bold-formatted question headers in markdown
QUESTION_BOLD_RE = re.compile(
    r'\*\*(?:QUESTÃO|Questão|QUEST[ÃA]O)\s*(\d+)\*\*',
    re.IGNORECASE,
)


class Pymupdf4llmExtractor:
    """Primary PDF extractor using pymupdf4llm with Layout AI."""

    def __init__(self, output_dir: str = "data/extracted_images"):
        self._output_dir = Path(output_dir)
        self._alt_extractor = create_enhanced_extractor()
        self._parser = EnemPDFParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_questions(
        self,
        pdf_path: str,
        metadata: Optional[QuestionMetadata] = None,
    ) -> List[Question]:
        """Extract all questions from a single ENEM PDF.

        Args:
            pdf_path: Path to the PDF file.
            metadata: Pre-parsed metadata (from filename). If *None*, the
                      filename is parsed automatically.

        Returns:
            List of Question dataclass instances.
        """
        pdf_path = str(pdf_path)
        if metadata is None:
            metadata = self._parser.parse_filename(Path(pdf_path).name)

        logger.info("Extracting questions from %s via pymupdf4llm", pdf_path)

        # 1. Extract markdown with pymupdf4llm
        md_chunks = self._extract_markdown(pdf_path)

        # 2. Concatenate all page texts
        full_text = "\n\n".join(chunk.get("text", "") for chunk in md_chunks)

        # 3. Split into per-question blocks
        question_blocks = self._split_questions(full_text)
        if not question_blocks:
            logger.warning("No questions found in %s", pdf_path)
            return []

        # 4. Extract image bounding boxes for association
        image_bboxes = self._get_image_bboxes(pdf_path)

        # 5. Build Question objects
        questions: List[Question] = []
        for q_num, q_text in question_blocks.items():
            question = self._build_question(
                q_num, q_text, metadata, image_bboxes, pdf_path,
            )
            if question is not None:
                questions.append(question)

        logger.info(
            "Extracted %d questions from %s",
            len(questions),
            Path(pdf_path).name,
        )
        return questions

    # ------------------------------------------------------------------
    # Markdown extraction
    # ------------------------------------------------------------------

    def _extract_markdown(self, pdf_path: str) -> List[Dict]:
        """Call pymupdf4llm.to_markdown with optimal ENEM settings."""
        image_dir = str(self._output_dir)
        os.makedirs(image_dir, exist_ok=True)

        needs_ocr = self._detect_scanned_pages(pdf_path)

        chunks = pymupdf4llm.to_markdown(
            pdf_path,
            page_chunks=True,
            header=False,
            footer=False,
            write_images=True,
            image_path=image_dir,
            image_format="png",
            dpi=150,
            force_ocr=needs_ocr,
            ocr_language="por",
        )
        return chunks

    def _detect_scanned_pages(self, pdf_path: str) -> bool:
        """Check if the PDF has scanned (image-only) pages needing OCR."""
        try:
            import pymupdf
            with pymupdf.open(pdf_path) as doc:
                for page in doc:
                    text = page.get_text("text").strip()
                    if len(text) < 50:
                        return True
        except Exception as exc:
            logger.warning("OCR detection failed for %s: %s", pdf_path, exc)
        return False

    # ------------------------------------------------------------------
    # Question splitting
    # ------------------------------------------------------------------

    def _split_questions(self, full_text: str) -> Dict[int, str]:
        """Split markdown text into question blocks keyed by number."""
        # Find all question header positions
        matches = list(QUESTION_SPLIT_RE.finditer(full_text))
        if not matches:
            # Try bold-formatted headers
            matches = list(QUESTION_BOLD_RE.finditer(full_text))

        if not matches:
            return {}

        blocks: Dict[int, str] = {}
        for i, m in enumerate(matches):
            q_num = int(m.group(1))
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            text = full_text[start:end].strip()
            if text:
                blocks[q_num] = text

        return blocks

    # ------------------------------------------------------------------
    # Image bounding-box association
    # ------------------------------------------------------------------

    def _get_image_bboxes(self, pdf_path: str) -> List[Dict]:
        """Extract image bounding boxes from all pages for association."""
        bboxes: List[Dict] = []
        try:
            import pymupdf
            with pymupdf.open(pdf_path) as doc:
                for page_idx, page in enumerate(doc):
                    for img in page.get_images(full=True):
                        xref = img[0]
                        rects = page.get_image_rects(xref)
                        for rect in rects:
                            bboxes.append({
                                "page": page_idx,
                                "x0": rect.x0,
                                "y0": rect.y0,
                                "x1": rect.x1,
                                "y1": rect.y1,
                                "xref": xref,
                            })
        except Exception as exc:
            logger.warning("Failed to extract image bboxes: %s", exc)
        return bboxes

    def _associate_images(
        self,
        q_num: int,
        q_text: str,
        image_bboxes: List[Dict],
        pdf_path: str,
    ) -> List[str]:
        """Associate images with a question via Y-range overlap.

        Returns list of image file paths saved to disk.
        """
        # For now, images are saved by pymupdf4llm.to_markdown(write_images=True)
        # and referenced in the markdown text. Extract image references.
        image_refs = re.findall(r'!\[.*?\]\((.*?)\)', q_text)
        return image_refs

    # ------------------------------------------------------------------
    # Question building
    # ------------------------------------------------------------------

    def _build_question(
        self,
        q_num: int,
        q_text: str,
        metadata: QuestionMetadata,
        image_bboxes: List[Dict],
        pdf_path: str,
    ) -> Optional[Question]:
        """Build a Question dataclass from a text block."""
        # Normalize text
        normalized = normalize_enem_text(q_text)

        # Extract alternatives using the enhanced strategy extractor
        alt_result = self._alt_extractor.extract_alternatives(normalized)
        alternatives = alt_result.alternatives if alt_result.alternatives else []

        # If enhanced extractor failed, try simple regex fallback
        if len(alternatives) != 5:
            alternatives = self._extract_alternatives_simple(normalized)

        # Separate enunciado from alternatives text
        enunciado = self._extract_enunciado(normalized)

        # Determine subject
        subject = self._parser._determine_subject(q_num, metadata.day)

        # Extract context (texto-base) if present
        context = self._extract_context(normalized)

        # Associate images
        image_refs = self._associate_images(q_num, q_text, image_bboxes, pdf_path)
        if image_refs:
            # Append image references to context
            img_note = "\n".join(f"[Imagem: {ref}]" for ref in image_refs)
            context = f"{context}\n{img_note}" if context else img_note

        return Question(
            number=q_num,
            text=enunciado,
            alternatives=alternatives,
            metadata=metadata,
            subject=subject,
            context=context,
        )

    def _extract_alternatives_simple(self, text: str) -> List[str]:
        """Simple regex fallback for alternative extraction from markdown."""
        # Pattern for **(A)** text or (A) text formats in markdown
        pattern = re.compile(
            r'\*{0,2}\(([A-E])\)\*{0,2}\s+(.+?)(?=\s*\*{0,2}\([A-E]\)\*{0,2}\s|$)',
            re.DOTALL,
        )
        matches = pattern.findall(text)
        if len(matches) == 5:
            return [m[1].strip() for m in matches]
        return []

    def _extract_enunciado(self, text: str) -> str:
        """Extract the question statement (enunciado) from the text block."""
        # Remove alternative lines from end
        lines = text.split('\n')
        enunciado_lines = []
        for line in lines:
            stripped = line.strip()
            # Stop at first alternative marker: (A), **(A)**, A), etc.
            if re.match(r'^\*{0,2}\(?[A-E]\)\*{0,2}\s', stripped):
                break
            enunciado_lines.append(line)

        enunciado = '\n'.join(enunciado_lines).strip()
        # Remove image markdown references for clean text
        enunciado = re.sub(r'!\[.*?\]\(.*?\)', '', enunciado).strip()
        return enunciado if len(enunciado) >= 10 else text[:500]

    def _extract_context(self, text: str) -> Optional[str]:
        """Extract texto-base (context) if it precedes the main question."""
        # Context blocks often appear before the actual question prompt.
        # In ENEM, the pattern is: context text, then the actual question.
        # We look for common patterns like "TEXTO I", "Texto para as questões"
        context_markers = [
            r'(?:TEXTO\s+[IVX]+)',
            r'(?:Texto\s+para\s+as?\s+quest)',
            r'(?:Leia\s+o\s+texto)',
            r'(?:Observe\s+a\s+figura)',
            r'(?:Analise\s+o\s+gráfico)',
        ]
        for marker in context_markers:
            match = re.search(marker, text, re.IGNORECASE)
            if match:
                # Return text from marker to first alternative
                start = match.start()
                alt_match = re.search(r'\(?[A-E]\)\s', text[start:])
                if alt_match:
                    return text[start:start + alt_match.start()].strip()
        return None
