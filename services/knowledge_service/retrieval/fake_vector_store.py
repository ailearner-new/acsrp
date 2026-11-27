"""In-memory fake vector store for testing and development."""

import hashlib
from typing import List, Optional, Dict, Any, Tuple

from services.knowledge_service.retrieval.vector_store import VectorStore


class FakeVectorStore(VectorStore):
    """In-memory vector store implementation for testing and demo mode.

    Provides deterministic embeddings for reproducibility in tests.
    """

    def __init__(self, dimension: int = 1536):
        """Initialize fake vector store.

        Args:
            dimension: Embedding vector dimension (default 1536)
        """
        self.dimension = dimension
        self.collections: Dict[str, Dict[str, Dict]] = {"default": {}}
        self._documents: Dict[str, Dict] = {}

    def _hash_to_embedding(self, text: str, dim: int = None) -> List[float]:
        """Generate deterministic embedding from hash of text.

        This creates reproducible embeddings for testing purposes.

        Args:
            text: Text to hash
            dim: Output dimension (uses self.dimension if not provided)

        Returns:
            Fake embedding vector
        """
        if dim is None:
            dim = self.dimension

        hash_bytes = hashlib.sha256(text.encode()).digest()
        float_count = (len(hash_bytes) // 4) * 4 // 4
        floats = []
        for i in range(min(float_count, dim)):
            val = int.from_bytes(hash_bytes[i * 4:(i + 1) * 4], 'big')
            floats.append((val / 2**31) * 2 - 1)

        while len(floats) < dim:
            floats.append(0.0)

        return floats[:dim]

    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        collection: str = "knowledge_documents",
    ) -> List[str]:
        """Add documents to the vector store."""
        if collection not in self.collections:
            self.collections[collection] = {}

        ids = []
        for doc in documents:
            doc_id = doc.get("id") or f"doc-{len(self.collections[collection])}"
            embedding = doc.get("embedding", self._hash_to_embedding(doc.get("content", "")))

            self.collections[collection][doc_id] = {
                "id": doc_id,
                "content": doc.get("content", ""),
                "metadata": doc.get("metadata", {}),
                "embedding": embedding,
            }
            self._documents[doc_id] = self.collections[collection][doc_id]
            ids.append(doc_id)

        return ids

    async def similarity_search(
        self,
        query: str,
        embedding: List[float],
        k: int = 10,
        collection: str = "knowledge_documents",
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using cosine similarity."""
        if collection not in self.collections:
            return []

        docs = list(self.collections[collection].values())

        if filter:
            docs = [
                d for d in docs
                if all(d.get("metadata", {}).get(k) == v for k, v in filter.items())
            ]

        def cosine_similarity(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(y * y for y in b) ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        scored_docs = [
            (doc, cosine_similarity(embedding, doc.get("embedding", [])))
            for doc in docs
        ]
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        return [doc for doc, _ in scored_docs[:k]]

    async def similarity_search_with_score(
        self,
        query: str,
        embedding: List[float],
        k: int = 10,
        collection: str = "knowledge_documents",
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Search with explicit scores."""
        docs = await self.similarity_search(query, embedding, k, collection, filter)

        def cosine_similarity(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(y * y for y in b) ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        return [
            (doc, cosine_similarity(embedding, doc.get("embedding", [])))
            for doc in docs
        ]

    async def delete(
        self,
        ids: List[str],
        collection: str = "knowledge_documents",
    ) -> None:
        """Delete documents from the vector store."""
        if collection in self.collections:
            for doc_id in ids:
                self.collections[collection].pop(doc_id, None)
                self._documents.pop(doc_id, None)

    async def get_by_ids(
        self,
        ids: List[str],
        collection: str = "knowledge_documents",
    ) -> List[Dict[str, Any]]:
        """Get documents by IDs."""
        if collection not in self.collections:
            return []

        return [
            self.collections[collection][doc_id]
            for doc_id in ids
            if doc_id in self.collections[collection]
        ]

    async def upsert(
        self,
        documents: List[Dict[str, Any]],
        collection: str = "knowledge_documents",
    ) -> List[str]:
        """Insert or update documents."""
        return await self.add_documents(documents, collection)

    def clear(self, collection: str = "knowledge_documents") -> None:
        """Clear all documents from a collection."""
        if collection in self.collections:
            self.collections[collection].clear()