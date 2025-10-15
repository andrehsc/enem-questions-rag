#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Image Extractor for ENEM Questions
===========================================
Improvements over base ImageExtractor with better quality detection,
optimization, and processing capabilities.

Addresses image extraction quality issues and processing efficiency.
"""

import logging
import hashlib
import io
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from PIL import Image, ImageEnhance, ImageFilter
import fitz  # PyMuPDF
from .image_extractor import ExtractedImage, ImageExtractor

logger = logging.getLogger(__name__)


@dataclass 
class EnhancedImageMetrics:
    """Extended metrics for enhanced image analysis."""
    sharpness_score: float
    contrast_score: float
    brightness_score: float
    noise_level: float
    text_likelihood: float
    diagram_likelihood: float
    recommended_processing: List[str] = field(default_factory=list)


@dataclass
class OptimizedImage:
    """Container for optimized image with original."""
    original: ExtractedImage
    optimized_data: bytes
    optimization_applied: List[str]
    quality_improvement: float
    final_size_bytes: int
    metrics: EnhancedImageMetrics


class ImageQualityAnalyzer:
    """Analyzes image quality and recommends optimizations."""
    
    def __init__(self):
        self.min_sharpness = 50.0
        self.min_contrast = 30.0
        self.max_noise_level = 0.3
    
    def analyze_image_quality(self, image_data: bytes) -> EnhancedImageMetrics:
        """
        Analyze image quality and provide enhancement recommendations.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            EnhancedImageMetrics with analysis results
        """
        try:
            # Convert to PIL and numpy for analysis
            pil_image = Image.open(io.BytesIO(image_data))
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to OpenCV format for analysis
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # Calculate quality metrics
            sharpness = self._calculate_sharpness(cv_image)
            contrast = self._calculate_contrast(cv_image) 
            brightness = self._calculate_brightness(cv_image)
            noise = self._estimate_noise_level(cv_image)
            
            # Content analysis
            text_likelihood = self._analyze_text_content(cv_image)
            diagram_likelihood = self._analyze_diagram_content(cv_image)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                sharpness, contrast, brightness, noise, text_likelihood, diagram_likelihood
            )
            
            return EnhancedImageMetrics(
                sharpness_score=sharpness,
                contrast_score=contrast,
                brightness_score=brightness,
                noise_level=noise,
                text_likelihood=text_likelihood,
                diagram_likelihood=diagram_likelihood,
                recommended_processing=recommendations
            )
            
        except Exception as e:
            logger.warning(f"Image quality analysis failed: {e}")
            # Return default metrics
            return EnhancedImageMetrics(
                sharpness_score=0.0,
                contrast_score=0.0,
                brightness_score=50.0,
                noise_level=1.0,
                text_likelihood=0.5,
                diagram_likelihood=0.5,
                recommended_processing=[]
            )
    
    def _calculate_sharpness(self, cv_image: np.ndarray) -> float:
        """Calculate image sharpness using Laplacian variance."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return min(100.0, laplacian_var)
    
    def _calculate_contrast(self, cv_image: np.ndarray) -> float:
        """Calculate image contrast using standard deviation."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        contrast = gray.std()
        return min(100.0, contrast)
    
    def _calculate_brightness(self, cv_image: np.ndarray) -> float:
        """Calculate average brightness."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        return gray.mean()
    
    def _estimate_noise_level(self, cv_image: np.ndarray) -> float:
        """Estimate noise level using local variance."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur and calculate difference
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = cv2.absdiff(gray, blurred)
        
        return min(1.0, noise.mean() / 255.0)
    
    def _analyze_text_content(self, cv_image: np.ndarray) -> float:
        """Analyze likelihood of containing text."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Look for text-like patterns (edges with specific orientations)
        edges = cv2.Canny(gray, 50, 150)
        
        # Count edge pixels as text indicator
        edge_density = np.sum(edges > 0) / edges.size
        
        return min(1.0, edge_density * 2.0)
    
    def _analyze_diagram_content(self, cv_image: np.ndarray) -> float:
        """Analyze likelihood of containing diagrams/graphics."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Look for geometric shapes
        edges = cv2.Canny(gray, 100, 200)
        
        # Find contours (shapes)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analyze contour characteristics
        geometric_score = 0.0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # Ignore noise
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    # Measure how "geometric" the shape is
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    geometric_score += min(1.0, circularity)
        
        return min(1.0, geometric_score / max(1, len(contours)))
    
    def _generate_recommendations(self, sharpness: float, contrast: float, 
                                brightness: float, noise: float,
                                text_likelihood: float, diagram_likelihood: float) -> List[str]:
        """Generate processing recommendations based on analysis."""
        recommendations = []
        
        # Sharpness recommendations
        if sharpness < self.min_sharpness:
            recommendations.append('sharpen')
        
        # Contrast recommendations
        if contrast < self.min_contrast:
            recommendations.append('enhance_contrast')
        
        # Brightness recommendations
        if brightness < 80:
            recommendations.append('brighten')
        elif brightness > 200:
            recommendations.append('darken')
        
        # Noise recommendations
        if noise > self.max_noise_level:
            recommendations.append('denoise')
        
        # Content-specific recommendations
        if text_likelihood > 0.7:
            recommendations.append('optimize_for_text')
        elif diagram_likelihood > 0.7:
            recommendations.append('optimize_for_diagrams')
        
        return recommendations


class ImageOptimizer:
    """Optimizes images based on quality analysis."""
    
    def __init__(self):
        self.max_dimension = 1200  # Max width/height for optimization
        self.jpeg_quality = 85
        self.png_compress_level = 6
    
    def optimize_image(self, extracted_image: ExtractedImage, 
                      metrics: EnhancedImageMetrics) -> OptimizedImage:
        """
        Optimize image based on quality metrics and recommendations.
        
        Args:
            extracted_image: Original extracted image
            metrics: Quality analysis metrics
            
        Returns:
            OptimizedImage with optimized data
        """
        try:
            # Load image
            pil_image = Image.open(io.BytesIO(extracted_image.data))
            if pil_image.mode == 'CMYK':
                pil_image = pil_image.convert('RGB')
            
            applied_optimizations = []
            
            # Apply recommended processing
            for recommendation in metrics.recommended_processing:
                pil_image, optimization_name = self._apply_optimization(pil_image, recommendation)
                applied_optimizations.append(optimization_name)
            
            # Resize if too large
            if max(pil_image.size) > self.max_dimension:
                pil_image = self._resize_image(pil_image)
                applied_optimizations.append('resize')
            
            # Convert to optimal format and compress
            optimized_data = self._compress_image(pil_image, extracted_image.format)
            
            # Calculate quality improvement
            quality_improvement = self._calculate_improvement_score(metrics, applied_optimizations)
            
            return OptimizedImage(
                original=extracted_image,
                optimized_data=optimized_data,
                optimization_applied=applied_optimizations,
                quality_improvement=quality_improvement,
                final_size_bytes=len(optimized_data),
                metrics=metrics
            )
            
        except Exception as e:
            logger.warning(f"Image optimization failed: {e}")
            # Return original as fallback
            return OptimizedImage(
                original=extracted_image,
                optimized_data=extracted_image.data,
                optimization_applied=[],
                quality_improvement=0.0,
                final_size_bytes=extracted_image.size_bytes,
                metrics=metrics
            )
    
    def _apply_optimization(self, image: Image.Image, optimization: str) -> Tuple[Image.Image, str]:
        """Apply specific optimization to image."""
        
        if optimization == 'sharpen':
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.5)
            return image, 'sharpening'
        
        elif optimization == 'enhance_contrast':
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.3)
            return image, 'contrast_enhancement'
        
        elif optimization == 'brighten':
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.2)
            return image, 'brightness_adjustment'
        
        elif optimization == 'darken':
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(0.8)
            return image, 'brightness_adjustment'
        
        elif optimization == 'denoise':
            image = image.filter(ImageFilter.MedianFilter(size=3))
            return image, 'noise_reduction'
        
        elif optimization == 'optimize_for_text':
            # High contrast, sharp edges for text
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.4)
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.3)
            return image, 'text_optimization'
        
        elif optimization == 'optimize_for_diagrams':
            # Balanced enhancement for diagrams
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            return image, 'diagram_optimization'
        
        return image, optimization
    
    def _resize_image(self, image: Image.Image) -> Image.Image:
        """Resize image while maintaining aspect ratio."""
        width, height = image.size
        max_dim = max(width, height)
        
        if max_dim > self.max_dimension:
            ratio = self.max_dimension / max_dim
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def _compress_image(self, image: Image.Image, original_format: str) -> bytes:
        """Compress image to optimal format."""
        buffer = io.BytesIO()
        
        # Choose format based on content and original format
        if original_format.upper() in ['PNG'] or image.mode == 'RGBA':
            image.save(buffer, format='PNG', optimize=True, compress_level=self.png_compress_level)
        else:
            # Convert to RGB for JPEG
            if image.mode in ['RGBA', 'P']:
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    rgb_image.paste(image, mask=image.split()[-1])
                else:
                    rgb_image.paste(image)
                image = rgb_image
            
            image.save(buffer, format='JPEG', quality=self.jpeg_quality, optimize=True)
        
        return buffer.getvalue()
    
    def _calculate_improvement_score(self, metrics: EnhancedImageMetrics, 
                                   optimizations: List[str]) -> float:
        """Calculate estimated quality improvement score."""
        base_score = 0.0
        
        # Base quality score from metrics
        quality_factors = [
            metrics.sharpness_score / 100.0,
            metrics.contrast_score / 100.0,
            (255 - abs(metrics.brightness_score - 128)) / 255.0,  # Optimal brightness around 128
            1.0 - metrics.noise_level
        ]
        
        base_score = sum(quality_factors) / len(quality_factors)
        
        # Improvement from optimizations
        improvement_bonus = len(optimizations) * 0.1
        
        return min(1.0, base_score + improvement_bonus)


class EnhancedImageExtractor(ImageExtractor):
    """Enhanced image extractor with quality analysis and optimization."""
    
    def __init__(self, output_dir: Optional[Path] = None, enable_optimization: bool = True):
        """
        Initialize enhanced image extractor.
        
        Args:
            output_dir: Directory to save extracted images
            enable_optimization: Whether to enable image optimization
        """
        super().__init__(output_dir)
        
        self.enable_optimization = enable_optimization
        self.quality_analyzer = ImageQualityAnalyzer()
        self.optimizer = ImageOptimizer()
        
        # Statistics
        self.processed_count = 0
        self.optimized_count = 0
        self.total_size_reduction = 0
    
    def extract_images_enhanced(self, pdf_path: Path, 
                              quality_threshold: float = 0.4) -> List[Union[ExtractedImage, OptimizedImage]]:
        """
        Extract and optionally optimize images from PDF.
        
        Args:
            pdf_path: Path to PDF file
            quality_threshold: Minimum quality threshold for optimization
            
        Returns:
            List of ExtractedImage or OptimizedImage objects
        """
        logger.info(f"Starting enhanced image extraction from {pdf_path.name}")
        
        # Extract images using base extractor
        base_images = self.extract_images_from_pdf(pdf_path)
        
        if not self.enable_optimization:
            return base_images
        
        enhanced_images = []
        
        for image in base_images:
            self.processed_count += 1
            
            try:
                # Analyze image quality
                metrics = self.quality_analyzer.analyze_image_quality(image.data)
                
                # Optimize if quality is below threshold or if recommendations exist
                should_optimize = (
                    len(metrics.recommended_processing) > 0 or
                    metrics.sharpness_score < 50 or
                    metrics.contrast_score < 30 or
                    metrics.noise_level > 0.3
                )
                
                if should_optimize:
                    optimized_image = self.optimizer.optimize_image(image, metrics)
                    
                    # Use optimized version if it shows improvement
                    if optimized_image.quality_improvement >= quality_threshold:
                        enhanced_images.append(optimized_image)
                        self.optimized_count += 1
                        
                        size_reduction = image.size_bytes - optimized_image.final_size_bytes
                        self.total_size_reduction += size_reduction
                        
                        logger.debug(f"Optimized image {image.sequence}: "
                                   f"quality +{optimized_image.quality_improvement:.2f}, "
                                   f"size {size_reduction:+d} bytes")
                    else:
                        enhanced_images.append(image)
                else:
                    enhanced_images.append(image)
                    
            except Exception as e:
                logger.warning(f"Enhanced processing failed for image {image.sequence}: {e}")
                enhanced_images.append(image)  # Use original as fallback
        
        logger.info(f"Enhanced extraction completed: {len(enhanced_images)} images, "
                   f"{self.optimized_count}/{self.processed_count} optimized")
        
        return enhanced_images
    
    def get_processing_stats(self) -> Dict[str, Union[int, float]]:
        """Get processing statistics."""
        return {
            'processed_count': self.processed_count,
            'optimized_count': self.optimized_count,
            'optimization_rate': self.optimized_count / max(1, self.processed_count),
            'total_size_reduction_bytes': self.total_size_reduction,
            'avg_size_reduction_bytes': self.total_size_reduction / max(1, self.optimized_count)
        }


# Factory function for easy integration
def create_enhanced_image_extractor(output_dir: Optional[Path] = None,
                                  enable_optimization: bool = True) -> EnhancedImageExtractor:
    """Create and return enhanced image extractor."""
    return EnhancedImageExtractor(output_dir, enable_optimization)
