#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Services Package for ENEM Question Processing.

This package provides AI-powered services for ENEM question extraction,
following SOLID principles and Clean Code practices.

Modules:
- validation: AI-powered question validation
- repair: AI-powered question repair and correction
- detection: AI-powered missing question detection
- common: Shared types, interfaces, and utilities
"""

# Import main service classes for convenient access
from .validation import QuestionValidationService, ValidationRequest, ValidationResponse
from .repair import QuestionRepairService, RepairRequest, RepairResponse, RepairType
from .detection import MissingQuestionDetector, DetectionRequest, DetectionResponse
from .common.base_types import EnemQuestionData, AIServiceInterface
from .common.llama_client import LLamaAPIClient, DefaultServiceConfig

__version__ = "1.0.0"

__all__ = [
    # Main Services
    "QuestionValidationService",
    "QuestionRepairService", 
    "MissingQuestionDetector",
    
    # Request/Response Types
    "ValidationRequest",
    "ValidationResponse",
    "RepairRequest", 
    "RepairResponse",
    "DetectionRequest",
    "DetectionResponse",
    
    # Common Types
    "EnemQuestionData",
    "RepairType",
    "AIServiceInterface",
    
    # Infrastructure
    "LLamaAPIClient",
    "DefaultServiceConfig"
]