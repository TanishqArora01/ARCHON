import httpx
from typing import List

from src.core.config import settings
from src.memory.interfaces import BaseEmbeddingProvider

class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        
    async def embed_query(self, text: str) -> List[float]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
            
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Ollama /api/embeddings only takes one prompt at a time in standard API, 
        # but we can execute them concurrently using httpx.
        # Alternatively, we could use /api/embed if the Ollama version supports it (which takes 'input': List[str]).
        # To be safe and compatible, we'll hit /api/embeddings concurrently.
        import asyncio
        
        async def fetch_embedding(client, text):
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            response.raise_for_status()
            return response.json().get("embedding", [])
            
        async with httpx.AsyncClient() as client:
            tasks = [fetch_embedding(client, text) for text in texts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            final_embeddings = []
            for res in results:
                if isinstance(res, Exception):
                    # For production, we should handle this better. 
                    # For now, append an empty list or raise.
                    raise res
                import typing
                final_embeddings.append(typing.cast(List[float], res))
                
            return final_embeddings


class OpenAICompatibleEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def embed_query(self, text: str) -> List[float]:
        return (await self.embed_documents([text]))[0]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "input": texts}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/embeddings", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in sorted(data["data"], key=lambda item: item["index"])]


def build_embedding_provider() -> BaseEmbeddingProvider:
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "ollama":
        return OllamaEmbeddingProvider(settings.OLLAMA_URL, settings.EMBEDDING_MODEL)
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        return OpenAICompatibleEmbeddingProvider(settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL, settings.EMBEDDING_MODEL)
    if provider == "openrouter":
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is required when EMBEDDING_PROVIDER=openrouter")
        return OpenAICompatibleEmbeddingProvider(settings.OPENROUTER_API_KEY, settings.OPENROUTER_BASE_URL, settings.EMBEDDING_MODEL)
    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")
