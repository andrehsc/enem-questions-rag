"""Pytest fixtures for RAG evaluation tests.

Provides golden eval dataset, LLM provider, and related fixtures.
"""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def golden_eval_dataset():
    """Load the golden evaluation dataset for RAG tests."""
    path = FIXTURES_DIR / "golden_eval_dataset.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def retrieval_pairs(golden_eval_dataset):
    """Retrieval pairs: query → expected question IDs."""
    return golden_eval_dataset["retrieval_pairs"]


@pytest.fixture(scope="session")
def generation_references(golden_eval_dataset):
    """Generation references: topic → expected question format."""
    return golden_eval_dataset["generation_references"]


@pytest.fixture(scope="session")
def eval_llm():
    """Get evaluation LLM instance based on EVAL_LLM_PROVIDER."""
    from src.rag_evaluation.llm_provider import get_eval_llm, is_ollama_available

    llm = get_eval_llm()

    # If using Ollama, check availability
    if hasattr(llm, "base_url") and not is_ollama_available(llm.base_url):
        pytest.skip("Ollama is not available — start Docker or set EVAL_LLM_PROVIDER")

    return llm
