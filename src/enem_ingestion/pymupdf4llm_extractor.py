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

import pymupdf4llm

from .parser import Question, QuestionMetadata, Subject, EnemPDFParser
from .alternative_extractor import create_enhanced_extractor
from .text_normalizer import normalize_enem_text
from .text_sanitizer import sanitize_enem_text, sanitize_alternative

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
        """Call pymupdf4llm.to_markdown with optimal ENEM settings.

        NOTE: write_images=False is required — pymupdf4llm>=1.27.2 has an infinite
        loop bug in add_image_orphans when write_images=True.

        If the extracted text contains a high ratio of garbled characters
        (control chars, U+FFFD), falls back to Tesseract OCR page-by-page.
        """
        os.makedirs(str(self._output_dir), exist_ok=True)
        needs_ocr = self._detect_scanned_pages(pdf_path)

        chunks = pymupdf4llm.to_markdown(
            pdf_path,
            page_chunks=True,
            header=False,
            footer=False,
            write_images=False,
            dpi=150,
            force_ocr=needs_ocr,
            ocr_language="por",
        )

        # Check for garbled output and fallback to Tesseract OCR
        if self._has_garbled_text(chunks):
            logger.warning(
                "Garbled text detected in %s — falling back to Tesseract OCR",
                pdf_path,
            )
            ocr_chunks = self._tesseract_ocr_fallback(pdf_path)
            if ocr_chunks:
                return ocr_chunks

        return chunks

    def _has_garbled_text(self, chunks: List[Dict]) -> bool:
        """Check if pymupdf4llm output has excessive garbled characters."""
        sample_text = "".join(c.get("text", "") for c in chunks[:5])
        if not sample_text:
            return False
        garbled = sum(
            1 for ch in sample_text
            if (ord(ch) < 32 and ch not in '\n\r\t') or ord(ch) == 0xFFFD
            or (0x80 <= ord(ch) <= 0x9F)
        )
        return (garbled / len(sample_text)) > 0.05

    def _tesseract_ocr_fallback(self, pdf_path: str) -> List[Dict]:
        """OCR all pages via Tesseract and return as page_chunks format.

        Post-processes OCR output to fix alternative letter detection:
        Tesseract renders circled A/B/C/D/E icons as 'A' for all letters,
        so we detect runs of 5 lines starting with 'A' and re-assign them
        as A through E sequentially.
        """
        try:
            import pytesseract
            import pymupdf
            from PIL import Image
            import io

            pytesseract.pytesseract.tesseract_cmd = (
                r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            )

            chunks = []
            with pymupdf.open(pdf_path) as doc:
                for page_idx in range(len(doc)):
                    page = doc[page_idx]
                    pix = page.get_pixmap(dpi=300)
                    img = Image.open(io.BytesIO(pix.tobytes('png')))
                    text = pytesseract.image_to_string(img, lang='por')
                    text = self._fix_ocr_alternative_letters(text)
                    chunks.append({
                        "text": text,
                        "metadata": {"page": page_idx},
                    })

            logger.info(
                "Tesseract OCR completed: %d pages from %s",
                len(chunks), Path(pdf_path).name,
            )
            return chunks
        except ImportError:
            logger.warning("pytesseract not available for OCR fallback")
            return []
        except Exception as exc:
            logger.warning("Tesseract OCR fallback failed: %s", exc)
            return []

    @staticmethod
    def _fix_ocr_alternative_letters(text: str) -> str:
        """Fix OCR-produced alternative letters.

        Tesseract renders ENEM circled-letter icons as the same letter
        (usually 'A') for all five alternatives. This method detects runs of
        lines starting with the same single capital letter and reassigns them
        as A, B, C, D, E sequentially.

        Tolerates blank lines and short noise lines between alternatives.
        """
        lines = text.split('\n')
        result_lines = []
        i = 0
        while i < len(lines):
            match = re.match(r'^([A-E])\s+(\S.{2,})', lines[i])
            if match:
                letter = match.group(1)
                run_indices = [i]
                run_texts = [match.group(2)]
                # Scan ahead: allow blank lines or short noise between matches
                j = i + 1
                while j < len(lines) and len(run_texts) < 5:
                    stripped = lines[j].strip()
                    m = re.match(
                        r'^' + re.escape(letter) + r'\s+(\S.{2,})', lines[j],
                    )
                    if m:
                        run_indices.append(j)
                        run_texts.append(m.group(1))
                        j += 1
                    elif stripped == '' or len(stripped) < 12:
                        # Skip blank or short noise lines (OCR artifacts)
                        j += 1
                    else:
                        break

                if len(run_texts) >= 3:
                    target_letters = 'ABCDE'
                    # Output all lines up to the first run entry as-is
                    written = set()
                    run_pos = 0
                    for k in range(i, j):
                        if k in run_indices and run_pos < len(run_texts):
                            result_lines.append(
                                f"{target_letters[run_pos]} {run_texts[run_pos]}"
                            )
                            written.add(k)
                            run_pos += 1
                        elif k not in written:
                            # Skip noise lines between alternatives
                            pass
                    i = j
                    continue

            result_lines.append(lines[i])
            i += 1

        return '\n'.join(result_lines)


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
        # Normalize text (encoding/mojibake layer)
        normalized = normalize_enem_text(q_text)
        # Sanitize text (content-level cleaning layer)
        normalized = sanitize_enem_text(normalized)

        # Extract alternatives using the enhanced strategy extractor
        alt_result = self._alt_extractor.extract_alternatives(normalized)
        alternatives = alt_result.alternatives if alt_result.alternatives else []

        # If enhanced extractor failed, try simple regex fallback
        if len(alternatives) != 5:
            alternatives = self._extract_alternatives_simple(normalized)

        # Sanitize each alternative individually
        alternatives = [sanitize_alternative(a) for a in alternatives]

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

        # Pattern for `- A texto` markdown list format (pymupdf4llm output)
        md_list_pattern = re.compile(
            r'(?:^|\n)\s*-\s+([A-E])\s+(.+?)(?=\n\s*-\s+[A-E]\s|\n\n|$)',
            re.DOTALL,
        )
        md_matches = md_list_pattern.findall(text)
        if len(md_matches) == 5:
            return [m[1].strip() for m in md_matches]
        if len(md_matches) >= 3:
            return [m[1].strip() for m in md_matches]

        # Pattern for single-line `- A texto - B texto` (after normalize_enem_text)
        sl_pattern = re.compile(r'-\s+([A-E])\s+(.+?)(?=\s+-\s+[A-E]\s|$)', re.DOTALL)
        sl_matches = sl_pattern.findall(text)
        if len(sl_matches) >= 4:
            return [m[1].strip() for m in sl_matches]
        return []

    def _extract_enunciado(self, text: str) -> str:
        """Extract the question statement (enunciado) from the text block."""
        # Remove alternative lines from end
        lines = text.split('\n')
        enunciado_lines = []
        for line in lines:
            stripped = line.strip()
            # Stop at first alternative marker: (A), **(A)**, A), or `- A` markdown list
            if re.match(r'^\*{0,2}\(?[A-E]\)\*{0,2}\s', stripped):
                break
            if re.match(r'^-\s+[A-E]\s', stripped):
                break
            enunciado_lines.append(line)

        enunciado = '\n'.join(enunciado_lines).strip()
        # Remove image markdown references for clean text
        enunciado = re.sub(r'!\[.*?\]\(.*?\)', '', enunciado).strip()

        # Also cut inline alternatives: "... text - A alt1 - B alt2 ..."
        inline_match = re.search(r'\s-\s+[A-E]\s+\S', enunciado)
        if inline_match:
            enunciado = enunciado[:inline_match.start()].strip()

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
