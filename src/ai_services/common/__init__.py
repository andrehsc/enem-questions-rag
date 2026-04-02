#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Common utilities and base types for AI Services.
Provides shared interfaces, types, and utilities following SOLID principles.
"""

from .base_types import (
    AIRequest,
    AIResponse,
    AIServiceInterface,
    EnemQuestionData,
    ServiceConfigInterface,
    LLamaClientInterface,
    MetricsTrackerInterface
)
from .llama_client import (
    LLamaAPIClient,
    DefaultServiceConfig,
    BatchProcessor
)

__all__ = [
    # Base Types and Interfaces
    "AIRequest",
    "AIResponse", 
    "AIServiceInterface",
    "EnemQuestionData",
    "ServiceConfigInterface",
    "LLamaClientInterface",
    "MetricsTrackerInterface",
    
    # Client Implementation
    "LLamaAPIClient",
    "DefaultServiceConfig",
    "BatchProcessor"
]