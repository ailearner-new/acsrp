"""Abstract embedding provider interface."""

from abc import ABC, abstractmethod
from typing import List, Optional


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers.

    Supports multiple providers:
    - OpenAI text-embedding-3-large
    - Cohere embedding models
    - HuggingFace transformers
    - Custom/in-house models
    """

    def __init__(self, dimension: int = 1536):
        """Initialize embedding provider.

        Args:
            dimension: Embedding vector dimension
        """
        self.dimension = dimension

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass

    @abstractmethod
    async def aembed_texts(
        self,
        texts: List[str],
        chunk_size: int = 100,
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of text strings to embed
            chunk_size: Number of texts to process at once

        Returns:
            List of embedding vectors
        """
        pass

    async def aembed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Single embedding vector
        """
        results = await self.aembed_texts([text])
        return results[0] if results else []

    @abstractmethod
    def embed_texts(
        self,
        texts: List[str],
        chunk_size: int = 100,
    ) -> List[List[float]]:
        """Synchronous version of embed_texts."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Synchronous version of embed_text."""
        pass