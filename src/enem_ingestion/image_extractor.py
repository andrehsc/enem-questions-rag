#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Extractor for ENEM Questions
==================================
This module handles extraction and storage of images from ENEM PDF questions.
Images are extracted and can be stored as files or in the database.
"""

import logging
import hashlib
import io
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import fitz  # PyMuPDF
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ExtractedImage:
    """Represents an extracted image from a PDF."""
    sequence: int
    data: bytes
    format: str  # PNG, JPEG, etc.
    width: int
    height: int
    size_bytes: int
    hash_md5: str
    page_number: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1


class ImageExtractor:
    """Extracts images from ENEM PDF files."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize image extractor.
        
        Args:
            output_dir: Directory to save extracted images (optional)
        """
        self.output_dir = output_dir
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_images_from_pdf(self, pdf_path: Path) -> List[ExtractedImage]:
        """
        Extract all images from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of ExtractedImage objects
        """
        images = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_images = self._extract_images_from_page(page, page_num)
                images.extend(page_images)
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error extracting images from {pdf_path}: {e}")
        
        return images
    
    def _extract_images_from_page(self, page, page_num: int) -> List[ExtractedImage]:
        """Extract images from a single PDF page."""
        images = []
        
        try:
            # Get image list from page
            image_list = page.get_images()
            temp_images = []
            
            for img_index, img in enumerate(image_list):
                # Get image reference
                xref = img[0]
                
                # Extract image data
                base_image = page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Get image bbox (position on page)
                img_rects = page.get_image_rects(img)
                if img_rects:
                    img_rect = img_rects[0]
                    bbox = (img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1)
                    # Use Y position for ordering (top to bottom)
                    y_position = img_rect.y0
                else:
                    bbox = (0, 0, 0, 0)
                    y_position = float('inf')  # Put images without position at end
                
                # Process image with PIL to get dimensions
                try:
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    width, height = pil_image.size
                    
                    # Convert CMYK to RGB if necessary
                    if pil_image.mode == 'CMYK':
                        pil_image = pil_image.convert('RGB')
                    
                    # Convert to PNG for consistency (optional)
                    if image_ext.lower() != 'png' or pil_image.mode == 'CMYK':
                        png_buffer = io.BytesIO()
                        pil_image.save(png_buffer, format='PNG')
                        image_bytes = png_buffer.getvalue()
                        image_ext = 'png'
                    
                except Exception as e:
                    logger.warning(f"Error processing image {img_index} from page {page_num}: {e}")
                    continue
                
                # Calculate hash for deduplication
                md5_hash = hashlib.md5(image_bytes).hexdigest()
                
                # Create temporary image data with position for sorting
                temp_image_data = {
                    'data': image_bytes,
                    'format': image_ext.upper(),
                    'width': width,
                    'height': height,
                    'size_bytes': len(image_bytes),
                    'hash_md5': md5_hash,
                    'page_number': page_num,
                    'bbox': bbox,
                    'y_position': y_position
                }
                
                temp_images.append(temp_image_data)
            
            # Sort images by Y position (top to bottom) to maintain reading order
            temp_images.sort(key=lambda x: x['y_position'])
            
            # Create ExtractedImage objects with correct sequence
            for sequence, img_data in enumerate(temp_images, 1):
                extracted_image = ExtractedImage(
                    sequence=sequence,
                    data=img_data['data'],
                    format=img_data['format'],
                    width=img_data['width'],
                    height=img_data['height'],
                    size_bytes=img_data['size_bytes'],
                    hash_md5=img_data['hash_md5'],
                    page_number=img_data['page_number'],
                    bbox=img_data['bbox']
                )
                
                images.append(extracted_image)
                
                # Save to file if output directory is specified
                if self.output_dir:
                    self._save_image_to_file(extracted_image, page_num, sequence - 1)
                
        except Exception as e:
            logger.error(f"Error extracting images from page {page_num}: {e}")
        
        return images
    
    def _save_image_to_file(self, image: ExtractedImage, page_num: int, img_index: int):
        """Save extracted image to file."""
        try:
            filename = f"page_{page_num + 1:03d}_img_{img_index + 1:02d}_{image.hash_md5[:8]}.{image.format.lower()}"
            filepath = self.output_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(image.data)
            
            logger.debug(f"Saved image: {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving image to file: {e}")
    
    def extract_images_for_question(self, pdf_path: Path, question_page: int, 
                                  question_bbox: Optional[Tuple[float, float, float, float]] = None
                                 ) -> List[ExtractedImage]:
        """
        Extract images specifically for a question.
        
        Args:
            pdf_path: Path to PDF file
            question_page: Page number where question is located
            question_bbox: Bounding box of question area (optional)
            
        Returns:
            List of images found in the question area
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(question_page - 1)  # Convert to 0-based index
            
            images = self._extract_images_from_page(page, question_page - 1)
            
            # Filter images by question area if bbox is provided
            if question_bbox:
                filtered_images = []
                for img in images:
                    if self._image_in_bbox(img.bbox, question_bbox):
                        filtered_images.append(img)
                images = filtered_images
            
            doc.close()
            return images
            
        except Exception as e:
            logger.error(f"Error extracting question images: {e}")
            return []
    
    def _image_in_bbox(self, img_bbox: Tuple[float, float, float, float], 
                      question_bbox: Tuple[float, float, float, float]) -> bool:
        """Check if image bbox overlaps with question bbox."""
        ix0, iy0, ix1, iy1 = img_bbox
        qx0, qy0, qx1, qy1 = question_bbox
        
        # Check for overlap
        return not (ix1 < qx0 or ix0 > qx1 or iy1 < qy0 or iy0 > qy1)
    
    def deduplicate_images(self, images: List[ExtractedImage]) -> List[ExtractedImage]:
        """Remove duplicate images based on MD5 hash."""
        seen_hashes = set()
        unique_images = []
        
        for img in images:
            if img.hash_md5 not in seen_hashes:
                seen_hashes.add(img.hash_md5)
                unique_images.append(img)
            else:
                logger.debug(f"Skipping duplicate image: {img.hash_md5}")
        
        return unique_images


class DatabaseImageHandler:
    """Handles storage of images in database."""
    
    def __init__(self, db_connection_or_url):
        """
        Initialize database image handler.
        
        Args:
            db_connection_or_url: Database connection object or connection URL string
        """
        if isinstance(db_connection_or_url, str):
            import psycopg2
            self.connection = psycopg2.connect(db_connection_or_url)
            self._owns_connection = True
        else:
            self.connection = db_connection_or_url
            self._owns_connection = False
    
    def store_question_images(self, question_id: str, images: List[ExtractedImage]) -> int:
        """
        Store images for a question in database.
        
        Args:
            question_id: UUID of the question
            images: List of ExtractedImage objects
            
        Returns:
            Number of images stored
        """
        stored_count = 0
        
        if not images:
            return stored_count
        
        try:
            with self.connection.cursor() as cur:
                # Clear existing images for this question
                cur.execute("""
                    DELETE FROM enem_questions.question_images WHERE question_id = %s
                """, (question_id,))
                
                deleted_count = cur.rowcount
                if deleted_count > 0:
                    logger.debug(f"Deleted {deleted_count} existing images for question {question_id}")
                
                # Insert new images using UPSERT to handle any race conditions
                for img in images:
                    cur.execute("""
                        INSERT INTO enem_questions.question_images (
                            id, question_id, image_sequence, image_data, 
                            image_format, image_width, image_height, 
                            image_size_bytes, extracted_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                        )
                        ON CONFLICT (question_id, image_sequence) 
                        DO UPDATE SET
                            image_data = EXCLUDED.image_data,
                            image_format = EXCLUDED.image_format,
                            image_width = EXCLUDED.image_width,
                            image_height = EXCLUDED.image_height,
                            image_size_bytes = EXCLUDED.image_size_bytes,
                            extracted_at = NOW()
                    """, (
                        str(uuid.uuid4()),
                        question_id,
                        img.sequence,
                        img.data,
                        img.format,
                        img.width,
                        img.height,
                        img.size_bytes
                    ))
                    stored_count += 1
                
                self.connection.commit()
                logger.debug(f"Successfully stored {stored_count} images for question {question_id}")
                
        except Exception as e:
            logger.error(f"Error storing images in database: {e}")
            self.connection.rollback()
            return 0  # Return 0 instead of raising to continue processing
        
        return stored_count
    
    def get_question_images(self, question_id: str) -> List[Dict]:
        """
        Retrieve images for a question from database.
        
        Args:
            question_id: UUID of the question
            
        Returns:
            List of image dictionaries
        """
        try:
            with self.connection.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id, image_sequence, image_format, 
                        image_width, image_height, image_size_bytes,
                        extracted_at
                    FROM enem_questions.question_images 
                    WHERE question_id = %s 
                    ORDER BY image_sequence
                """, (question_id,))
                
                return cur.fetchall()
                
        except Exception as e:
            logger.error(f"Error retrieving images from database: {e}")
            return []
    
    def get_image_data(self, image_id: str) -> Optional[bytes]:
        """
        Get image data by image ID.
        
        Args:
            image_id: UUID of the image
            
        Returns:
            Image data as bytes or None
        """
        try:
            with self.connection.cursor() as cur:
                cur.execute("""
                    SELECT image_data FROM enem_questions.question_images WHERE id = %s
                """, (image_id,))
                
                result = cur.fetchone()
                return result['image_data'] if result else None
                
        except Exception as e:
            logger.error(f"Error retrieving image data: {e}")
            return None
