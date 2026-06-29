import pytest

from src.agents.llm_provider import OllamaLLMProvider, build_llm_provider
from src.memory.providers import OllamaEmbeddingProvider, build_embedding_provider


def test_build_default_llm_provider(monkeypatch):
    monkeypatch.setattr("src.agents.llm_provider.settings.LLM_PROVIDER", "ollama")
    monkeypatch.setattr("src.agents.llm_provider.settings.LLM_FALLBACK_PROVIDERS", "")
    provider = build_llm_provider()
    assert isinstance(provider, OllamaLLMProvider)


def test_build_default_embedding_provider(monkeypatch):
    monkeypatch.setattr("src.memory.providers.settings.EMBEDDING_PROVIDER", "ollama")
    provider = build_embedding_provider()
    assert isinstance(provider, OllamaEmbeddingProvider)


def test_openai_provider_requires_key(monkeypatch):
    monkeypatch.setattr("src.agents.llm_provider.settings.LLM_PROVIDER", "openai")
    monkeypatch.setattr("src.agents.llm_provider.settings.OPENAI_API_KEY", None)
    with pytest.raises(ValueError):
        build_llm_provider()
