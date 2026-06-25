from abc import ABC, abstractmethod
from typing import List

class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Embeds a single query string into a vector."""
        pass
        
    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of document strings into a list of vectors."""
        pass
