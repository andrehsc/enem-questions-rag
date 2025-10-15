#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLama API client implementation following Single Responsibility Principle.
Handles all LLama3 API communication with proper error handling and retries.
"""

import logging
import asyncio
import aiohttp
from typing import Dict, Optional, Any
from .base_types import LLamaClientInterface, ServiceConfigInterface

logger = logging.getLogger(__name__)


class LLamaAPIClient:
    """LLama3 API client with connection management and error handling."""
    
    def __init__(self, config: ServiceConfigInterface):
        """Initialize client with configuration.
        
        Args:
            config: Service configuration implementing ServiceConfigInterface
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def call_api(self, prompt: str, model: str = "llama3") -> str:
        """Call LLama API with retry logic.
        
        Args:
            prompt: Prompt to send to LLama
            model: Model name to use
            
        Returns:
            AI response text
            
        Raises:
            ConnectionError: If API is unreachable after retries
            ValueError: If API returns invalid response
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
            
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "max_tokens": 2000
            }
        }
        
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                async with self.session.post(
                    f"{self.config.llama_host}/api/generate", 
                    json=payload
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "")
                    else:
                        error_msg = f"LLama API error: HTTP {response.status}"
                        logger.warning(f"Attempt {attempt + 1}: {error_msg}")
                        last_error = ConnectionError(error_msg)
                        
            except asyncio.TimeoutError:
                error_msg = f"LLama API timeout (attempt {attempt + 1})"
                logger.warning(error_msg)
                last_error = ConnectionError(error_msg)
                
            except Exception as e:
                error_msg = f"LLama API call failed (attempt {attempt + 1}): {e}"
                logger.warning(error_msg)
                last_error = ConnectionError(error_msg)
            
            # Wait before retry (exponential backoff)
            if attempt < self.config.max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s, etc.
                await asyncio.sleep(wait_time)
        
        # All retries failed
        raise last_error or ConnectionError("LLama API unreachable")


class DefaultServiceConfig:
    """Default configuration for AI services."""
    
    def __init__(self, 
                 llama_host: str = "http://localhost:11434",
                 timeout: int = 30,
                 max_retries: int = 3,
                 batch_size: int = 5):
        self._llama_host = llama_host
        self._timeout = timeout
        self._max_retries = max_retries
        self._batch_size = batch_size
    
    @property
    def llama_host(self) -> str:
        return self._llama_host
    
    @property
    def timeout(self) -> int:
        return self._timeout
        
    @property
    def max_retries(self) -> int:
        return self._max_retries
        
    @property
    def batch_size(self) -> int:
        return self._batch_size


class BatchProcessor:
    """Utility for processing AI requests in batches with concurrency control."""
    
    def __init__(self, max_concurrent: int = 3):
        """Initialize batch processor.
        
        Args:
            max_concurrent: Maximum concurrent AI calls
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def process_batch_with_semaphore(self, 
                                         client: LLamaAPIClient, 
                                         prompts: list[str], 
                                         model: str = "llama3") -> list[str]:
        """Process multiple prompts with concurrency control.
        
        Args:
            client: LLama client instance
            prompts: List of prompts to process
            model: Model to use
            
        Returns:
            List of responses in same order as prompts
        """
        async def process_single(prompt: str) -> str:
            async with self.semaphore:
                return await client.call_api(prompt, model)
        
        tasks = [process_single(prompt) for prompt in prompts]
        return await asyncio.gather(*tasks, return_exceptions=True)