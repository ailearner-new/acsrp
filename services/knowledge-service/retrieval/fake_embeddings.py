"""In-memory fake embeddings for testing and development."""

import hashlib
from typing import List

from services.knowledge_service.retrieval.embeddings import EmbeddingProvider


class FakeEmbeddings(EmbeddingProvider):
    """Fake embedding provider for testing and demo mode.

    Generates deterministic embeddings based on text hashing.
    This ensures reproducible results in tests while being fast.

    Note: These are NOT real embeddings - they are useful for:
    - Unit testing
    - Development/demo mode
    - Benchmarking retrieval logic (not embedding quality)
    """

    def __init__(self, dimension: int = 1536):
        """Initialize fake embeddings.

        Args:
            dimension: Output embedding dimension (default 1536, matches text-embedding-3-large)
        """
        super().__init__(dimension)
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        """Return model name."""
        return "fake-embeddings"

    def _hash_to_embedding(self, text: str, dim: int = None) -> List[float]:
        """Generate deterministic embedding from hash of text.

        Args:
            text: Text to hash
            dim: Output dimension

        Returns:
            Fake embedding vector
        """
        if dim is None:
            dim = self._dimension

        hash_bytes = hashlib.sha256(text.encode()).digest()
        float_count = len(hash_bytes) // 4

        floats = []
        for i in range(min(float_count, dim)):
            val = int.from_bytes(hash_bytes[i * 4:(i + 1) * 4], 'big')
            floats.append((val / 2**31) * 2 - 1)

        while len(floats) < dim:
            floats.append(0.0)

        return floats[:dim]

    async def aembed_texts(
        self,
        texts: List[str],
        chunk_size: int = 100,
    ) -> List[List[float]]:
        """Generate fake embeddings for multiple texts."""
        return [self._hash_to_embedding(text, self._dimension) for text in texts]

    async def aembed_text(self, text: str) -> List[float]:
        """Generate fake embedding for a single text."""
        return self._hash_to_embedding(text, self._dimension)

    def embed_texts(
        self,
        texts: List[str],
        chunk_size: int = 100,
    ) -> List[List[float]]:
        """Generate fake embeddings for multiple texts (sync)."""
        return [self._hash_to_embedding(text, self._dimension) for text in texts]

    def embed_text(self, text: str) -> List[float]:
        """Generate fake embedding for a single text (sync)."""
        return self._hash_to_embedding(text, self._dimension)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Alias for embed_texts (LangChain compatibility)."""
        return self.embed_texts(texts)

    def embed_query(self, text: str) -> List[float]:
        """Alias for embed_text (LangChain compatibility)."""
        return self.embed_text(text)