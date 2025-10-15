#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Missing Question Detection Service Package.
Provides AI-powered detection for missing ENEM questions in PDFs.
"""

from .service import (
    MissingQuestionDetector,
    DetectionRequest,
    DetectionResponse,
    MissingQuestionCandidate,
    DetectionMethod,
    GapAnalyzer,
    TextChunkProcessor,
    DetectionPromptBuilder,
    DetectionResponseParser,
    CandidateDeduplicator,
    MissingQuestionIntegrator
)

__all__ = [
    "MissingQuestionDetector",
    "DetectionRequest",
    "DetectionResponse",
    "MissingQuestionCandidate",
    "DetectionMethod",
    "GapAnalyzer",
    "TextChunkProcessor", 
    "DetectionPromptBuilder",
    "DetectionResponseParser",
    "CandidateDeduplicator",
    "MissingQuestionIntegrator"
]