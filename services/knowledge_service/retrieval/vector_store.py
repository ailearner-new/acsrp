"""Abstract vector store interface for hybrid retrieval."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple


class VectorStore(ABC):
    """Abstract base class for vector stores.

    Supports multiple backends:
    - Pinecone
    - Weaviate
    - Qdrant
    - In-memory (for testing)
    - PostgreSQL with pgvector
    """

    @abstractmethod
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        collection: str = "knowledge_documents",
    ) -> List[str]:
        """Add documents to the vector store.

        Args:
            documents: List of documents with 'id', 'content', 'metadata', and 'embedding' keys
            collection: Collection/namespace name

        Returns:
            List of document IDs
        """
        pass

    @abstractmethod
    async def similarity_search(
        self,
        query: str,
        embedding: List[float],
        k: int = 10,
        collection: str = "knowledge_documents",
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents.

        Args:
            query: The search query text
            embedding: Query embedding vector
            k: Number of results to return
            collection: Collection/namespace name
            filter: Metadata filter for tenant isolation

        Returns:
            List of matching documents with scores
        """
        pass

    @abstractmethod
    async def similarity_search_with_score(
        self,
        query: str,
        embedding: List[float],
        k: int = 10,
        collection: str = "knowledge_documents",
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Search for similar documents with explicit scores.

        Args:
            query: The search query text
            embedding: Query embedding vector
            k: Number of results to return
            collection: Collection/namespace name
            filter: Metadata filter

        Returns:
            List of (document, score) tuples
        """
        pass

    @abstractmethod
    async def delete(
        self,
        ids: List[str],
        collection: str = "knowledge_documents",
    ) -> None:
        """Delete documents from the vector store.

        Args:
            ids: List of document IDs to delete
            collection: Collection/namespace name
        """
        pass

    @abstractmethod
    async def get_by_ids(
        self,
        ids: List[str],
        collection: str = "knowledge_documents",
    ) -> List[Dict[str, Any]]:
        """Get documents by IDs.

        Args:
            ids: List of document IDs
            collection: Collection/namespace name

        Returns:
            List of documents
        """
        pass

    @abstractmethod
    async def upsert(
        self,
        documents: List[Dict[str, Any]],
        collection: str = "knowledge_documents",
    ) -> List[str]:
        """Insert or update documents.

        Args:
            documents: List of documents with embeddings
            collection: Collection/namespace name

        Returns:
            List of document IDs
        """
        pass