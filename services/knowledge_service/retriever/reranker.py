"""Cross-encoder reranker for refining retrieval results."""

from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RerankedResult:
    """A reranked document result with refined score."""
    doc_id: str
    title: str
    content: str
    score: float
    source_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content,
            "score": self.score,
            "source_url": self.source_url,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RerankedResult":
        """Create from dictionary."""
        return cls(
            doc_id=data["doc_id"],
            title=data.get("title", ""),
            content=data.get("content", ""),
            score=data.get("score", 0.0),
            source_url=data.get("source_url"),
            metadata=data.get("metadata"),
        )


class Reranker(ABC):
    """Abstract base class for cross-encoder rerankers.

    Cross-encoders compute relevance scores between query and document pairs,
    typically providing better precision than bi-encoders (vector search).
    """

    def __init__(self, model_name: str = "rerank-multilingual-v2.37", dimension: int = 1536):
        """Initialize the reranker.

        Args:
            model_name: Name of the cross-encoder model
            dimension: Output dimension (for compatibility with other components)
        """
        self.model_name = model_name
        self.dimension = dimension

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the reranker is available and can be used."""
        pass

    @abstractmethod
    async def arerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Rerank documents using cross-encoder.

        Args:
            query: The search query
            documents: List of documents with 'doc_id', 'content' (and optionally 'metadata')
            top_k: Number of top results to return (None = all)

        Returns:
            Reranked documents sorted by relevance score, with 'rerank_score' added
        """
        pass

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Synchronous version of arerank."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # We're in an async context, need to use async
                raise RuntimeError("Use arerank() when already in an async context")
        except RuntimeError:
            return asyncio.run(self.arerank(query, documents, top_k))
        else:
            return asyncio.run(self.arerank(query, documents, top_k))


class FakeReranker(Reranker):
    """Fake reranker for testing and development.

    Uses a simple similarity-based scoring that is deterministic and fast.
    """

    def __init__(self, model_name: str = "fake-reranker"):
        super().__init__(model_name=model_name)

    @property
    def is_available(self) -> bool:
        """Fake reranker is always available."""
        return True

    def _simple_similarity(self, query: str, content: str) -> float:
        """Compute a simple similarity score based on term overlap."""
        query_terms = set(query.lower().split())
        content_terms = set(content.lower().split())

        if not query_terms:
            return 0.0

        overlap = query_terms & content_terms
        if not content_terms:
            return 0.0

        # Jaccard similarity
        jaccard = len(overlap) / len(content_terms)

        # Boost for exact term matches
        exact_matches = sum(1 for term in query_terms if term in content_terms)
        boost = 1.0 + (exact_matches * 0.1)

        return min(1.0, jaccard * boost)

    async def arerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fake rerank using simple similarity."""
        scored_docs = []

        for doc in documents:
            content = doc.get("content", "")
            score = self._simple_similarity(query, content)

            reranked_doc = doc.copy()
            reranked_doc["rerank_score"] = score
            scored_docs.append(reranked_doc)

        # Sort by rerank score descending
        scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)

        if top_k is not None:
            scored_docs = scored_docs[:top_k]

        return scored_docs


class CohereReranker(Reranker):
    """Cohere cross-encoder reranker.

    Uses Cohere's rerank API for high-quality reranking.
    Requires COHERE_API_KEY environment variable.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "rerank-v3.0",
        api_base: Optional[str] = None,
    ):
        super().__init__(model_name=model_name)
        self.api_key = api_key
        self.api_base = api_base or "https://api.cohere.ai/v1"
        self._client = None

    @property
    def is_available(self) -> bool:
        """Check if Cohere client is initialized."""
        return self._client is not None

    def _get_client(self):
        """Lazily initialize Cohere client."""
        if self._client is None and self.api_key:
            try:
                import cohere
                self._client = cohere.Client(self.api_key, base_url=self.api_base)
            except ImportError:
                raise ImportError(
                    "cohere package required for CohereReranker. "
                    "Install with: pip install cohere"
                )
        return self._client

    async def arerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Rerank using Cohere API."""
        client = self._get_client()
        if client is None:
            raise RuntimeError("Cohere client not initialized. Check API key.")

        # Extract documents for Cohere API
        texts = [doc.get("content", "") for doc in documents]

        # Call Cohere rerank API
        import asyncio

        def _sync_rerank():
            return client.rerank(
                model=self.model_name,
                query=query,
                documents=texts,
                top_n=top_k or len(texts),
                return_documents=True,
            )

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _sync_rerank)

        # Process results
        reranked = []
        for result in response.results:
            doc = documents[result.document["index"]].copy()
            doc["rerank_score"] = result.score
            reranked.append(doc)

        # Sort by rerank score (Cohere already does this, but ensure consistency)
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)

        return reranked


def get_reranker(
    provider: str = "fake",
    api_key: Optional[str] = None,
    model_name: str = "rerank-multilingual-v2.37",
) -> Reranker:
    """Factory function to get the appropriate reranker.

    Args:
        provider: "fake", "cohere", or other supported providers
        api_key: API key for the provider (if needed)
        model_name: Model name to use

    Returns:
        Reranker instance
    """
    if provider == "fake" or provider == "cohere":
        if provider == "cohere" and api_key:
            return CohereReranker(api_key=api_key, model_name=model_name)
        return FakeReranker(model_name=model_name)

    # Default to fake reranker for unknown providers
    return FakeReranker(model_name=model_name or "fake-reranker")