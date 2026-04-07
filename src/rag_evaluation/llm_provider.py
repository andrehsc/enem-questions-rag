"""LLM provider abstraction for RAG evaluation pipeline.

Supports three providers via EVAL_LLM_PROVIDER env var:
- ollama (default): Llama 3 via local Ollama, zero cost
- github-models: GPT-4o via GitHub token, rate-limited
- openai: GPT-4o via OpenAI API key, pay-per-use
"""

import os
from typing import Optional

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EVAL_LLM_PROVIDER = os.getenv("EVAL_LLM_PROVIDER", "ollama")


def _get_ollama_url() -> str:
    """Get Ollama URL, preferring env var."""
    return os.getenv("OLLAMA_URL", "http://localhost:11434")


class OllamaEvalLLM:
    """Ollama adapter for DeepEval LLM-as-judge.

    Implements the DeepEvalBaseLLM interface for use with
    DeepEval metrics (G-Eval, Faithfulness, etc.).
    """

    def __init__(self, model: str = "llama3", base_url: Optional[str] = None):
        self.model_name = model
        self.base_url = base_url or _get_ollama_url()

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str, **kwargs) -> str:
        """Synchronous generation via Ollama API."""
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["response"]

    async def a_generate(self, prompt: str, **kwargs) -> str:
        """Async generation via Ollama API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json()["response"]

    def get_model_name(self) -> str:
        return f"ollama/{self.model_name}"


def _try_import_deepeval_base():
    """Try to make OllamaEvalLLM a proper DeepEval subclass at runtime."""
    try:
        from deepeval.models import DeepEvalBaseLLM

        if not issubclass(OllamaEvalLLM, DeepEvalBaseLLM):
            # Dynamically register as subclass if needed
            OllamaEvalLLM.__bases__ = (DeepEvalBaseLLM,)
    except ImportError:
        pass


# Attempt to register on module load (no-op if deepeval not installed)
_try_import_deepeval_base()


def get_eval_llm(provider: Optional[str] = None) -> "OllamaEvalLLM":
    """Factory: returns LLM instance based on provider.

    Args:
        provider: Override for EVAL_LLM_PROVIDER env var.
                  One of: "ollama", "github-models", "openai".

    Returns:
        LLM instance compatible with DeepEval metrics.
    """
    provider = provider or os.getenv("EVAL_LLM_PROVIDER", "ollama")

    if provider == "ollama":
        return OllamaEvalLLM()
    elif provider == "github-models":
        from deepeval.models import GPTModel

        return GPTModel(model="gpt-4o")
    elif provider == "openai":
        from deepeval.models import GPTModel

        return GPTModel(model="gpt-4o")
    else:
        raise ValueError(
            f"Unknown EVAL_LLM_PROVIDER: {provider}. "
            "Valid options: ollama, github-models, openai"
        )


def is_ollama_available(base_url: Optional[str] = None) -> bool:
    """Check if Ollama is reachable."""
    url = base_url or _get_ollama_url()
    try:
        resp = httpx.get(f"{url}/api/version", timeout=5)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False
