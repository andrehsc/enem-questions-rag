#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Common data types and interfaces for AI services.
Following SOLID principles - Interface Segregation and Dependency Inversion.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Union, Protocol
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


@dataclass
class AIRequest:
    """Base class for AI service requests."""
    request_id: str
    context: Optional[Dict[str, Union[str, int]]] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


@dataclass  
class AIResponse:
    """Base class for AI service responses."""
    success: bool
    confidence_score: float  # 0.0 - 1.0
    raw_ai_response: str
    warnings: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class AIServiceInterface(ABC):
    """Interface for AI services following Interface Segregation Principle."""
    
    @abstractmethod
    async def process_request(self, request: AIRequest) -> AIResponse:
        """Process a single AI request."""
        pass
    
    @abstractmethod
    async def process_batch(self, requests: List[AIRequest]) -> List[AIResponse]:
        """Process multiple requests in batch."""
        pass


class LLamaClientInterface(Protocol):
    """Protocol for LLama API clients - Dependency Inversion Principle."""
    
    async def call_api(self, prompt: str, model: str = "llama3") -> str:
        """Call LLama API with given prompt."""
        ...


@dataclass
@dataclass
class EnemQuestionData:
    """Standardized ENEM question data structure."""
    number: Optional[int] = None
    text: str = ""
    alternatives: Optional[List[str]] = None
    metadata: Optional[Dict[str, Union[str, int]]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.alternatives is None:
            self.alternatives = []
    
    def validate(self) -> List[str]:
        """Validate question data and return list of issues."""
        issues = []
        
        if not self.text or len(self.text.strip()) < 10:
            issues.append("Question text is too short or empty")
            
        if not self.alternatives or len(self.alternatives) != 5:
            issues.append("Must have exactly 5 alternatives")
            
        if self.number is not None and (self.number < 1 or self.number > 200):
            issues.append("Question number out of valid range (1-200)")
            
        return issues


class ServiceConfigInterface(Protocol):
    """Configuration interface for AI services."""
    
    @property
    def llama_host(self) -> str: ...
    
    @property 
    def timeout(self) -> int: ...
    
    @property
    def max_retries(self) -> int: ...
    
    @property
    def batch_size(self) -> int: ...


class MetricsTrackerInterface(Protocol):
    """Interface for tracking AI service metrics."""
    
    def record_request(self, service_name: str, processing_time: float, success: bool) -> None: ...
    
    def record_confidence_score(self, service_name: str, confidence: float) -> None: ...
    
    def get_service_stats(self, service_name: str) -> Dict[str, Union[int, float]]: ...