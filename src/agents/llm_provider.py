from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """
    Provider-agnostic interface for LLM completions.
    Agents must never depend on a specific model runtime.
    """

    @abstractmethod
    async def complete(self, system_prompt: str, user_message: str) -> str:
        """
        Returns the model's raw text response.
        Callers are responsible for parsing structured content from the string.
        """
        pass


class OllamaLLMProvider(BaseLLMProvider):
    """
    Concrete provider backed by a local Ollama runtime.
    Default model: qwen2.5 (as declared in agents.md Model Strategy).
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5", timeout: float | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout if timeout is not None else settings.OLLAMA_REQUEST_TIMEOUT

    async def complete(self, system_prompt: str, user_message: str) -> str:
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_message,
            "stream": False,
            "format": "json",
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=3.0)) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")


class OpenAICompatibleLLMProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        extra_headers: dict[str, str] | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.extra_headers = extra_headers or {}

    async def complete(self, system_prompt: str, user_message: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class AnthropicLLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, system_prompt: str, user_message: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return "".join(block.get("text", "") for block in data.get("content", []))


class AzureOpenAILLMProvider(OpenAICompatibleLLMProvider):
    def __init__(self, api_key: str, endpoint: str, deployment: str, api_version: str):
        base_url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}"
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=deployment,
            extra_headers={"api-key": api_key},
        )
        self.api_version = api_version

    async def complete(self, system_prompt: str, user_message: str) -> str:
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions?api-version={self.api_version}",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class MockLLMProvider(BaseLLMProvider):
    async def complete(self, system_prompt: str, user_message: str) -> str:
        import json

        if "Planner Agent" in system_prompt:
            return json.dumps({
                "selected_agents": ["architecture", "maintainability", "technical_debt"],
                "rationale": "All specialists activated for comprehensive repository analysis.",
            })

        severity = "HIGH" if "Architecture Agent" in system_prompt else "MEDIUM"
        agent_label = "Architecture" if "Architecture Agent" in system_prompt else (
            "Maintainability" if "Maintainability Agent" in system_prompt else (
                "Technical Debt" if "Technical Debt Agent" in system_prompt else "Analysis"
            )
        )
        return json.dumps({
            "findings": [{
                "issue": f"{agent_label} review completed via fallback provider",
                "evidence": "Deterministic graph context was assembled before agent invocation.",
                "reasoning": f"The {agent_label} agent identified patterns in the assembled structural context.",
                "impact": "Unreviewed changes may increase architectural drift without multi-agent analysis.",
                "recommendation": "Review graph impact and address high-severity findings first.",
                "severity": severity,
            }]
        })


class FallbackLLMProvider(BaseLLMProvider):
    """Try providers in order; log and continue when one fails."""

    def __init__(self, providers: list[BaseLLMProvider]):
        if not providers:
            raise ValueError("FallbackLLMProvider requires at least one provider")
        self.providers = providers

    async def complete(self, system_prompt: str, user_message: str) -> str:
        last_error: Exception | None = None
        for index, provider in enumerate(self.providers):
            try:
                return await provider.complete(system_prompt, user_message)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM provider %s failed (%s/%s): %s",
                    provider.__class__.__name__,
                    index + 1,
                    len(self.providers),
                    exc,
                )
        if last_error:
            raise last_error
        raise RuntimeError("No LLM providers available")


def _build_single_llm_provider(provider_name: str, model: str | None = None) -> BaseLLMProvider | None:
    provider = provider_name.lower()
    resolved_model = model or settings.LLM_MODEL
    if provider == "mock":
        return MockLLMProvider()
    if provider == "ollama":
        return OllamaLLMProvider(settings.OLLAMA_URL, resolved_model)
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            return None
        return OpenAICompatibleLLMProvider(settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL, resolved_model)
    if provider == "openrouter":
        if not settings.OPENROUTER_API_KEY:
            return None
        return OpenAICompatibleLLMProvider(settings.OPENROUTER_API_KEY, settings.OPENROUTER_BASE_URL, resolved_model)
    if provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            return None
        return AnthropicLLMProvider(settings.ANTHROPIC_API_KEY, settings.ANTHROPIC_BASE_URL, resolved_model)
    if provider == "azure_openai":
        if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT:
            return None
        return AzureOpenAILLMProvider(
            settings.AZURE_OPENAI_API_KEY,
            settings.AZURE_OPENAI_ENDPOINT,
            resolved_model,
            settings.AZURE_OPENAI_API_VERSION,
        )
    return None


def build_llm_provider() -> BaseLLMProvider:
    primary = _build_single_llm_provider(settings.LLM_PROVIDER)
    if primary is None:
        raise ValueError(f"Unsupported or misconfigured LLM_PROVIDER: {settings.LLM_PROVIDER}")

    if not settings.LLM_FALLBACK_PROVIDERS:
        return primary

    fallbacks: list[BaseLLMProvider] = [primary]
    seen = {settings.LLM_PROVIDER.lower()}
    for name in settings.LLM_FALLBACK_PROVIDERS.split(","):
        normalized = name.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        fallback_model = settings.LLM_FALLBACK_MODEL if normalized == "openrouter" else None
        candidate = _build_single_llm_provider(normalized, model=fallback_model)
        if candidate is not None:
            fallbacks.append(candidate)

    if len(fallbacks) == 1:
        return primary
    return FallbackLLMProvider(fallbacks)
