"""Hybrid retriever combining vector, BM25, and graph search."""

from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

from services.knowledge_service.retriever.rrf import reciprocal_rank_fusion, RetrievedDocument
from services.knowledge_service.retriever.reranker import Reranker, FakeReranker, get_reranker

logger = logging.getLogger(__name__)


class BM25Retriever(ABC):
    """Abstract base class for BM25 sparse search."""

    @abstractmethod
    async def search(
        self,
        query: str,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search using BM25 algorithm."""
        pass


class GraphRetriever(ABC):
    """Abstract base class for graph-based relationship search."""

    @abstractmethod
    async def search(
        self,
        query: str,
        entity_type: Optional[str] = None,
        relationship_type: Optional[str] = None,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search using graph relationships."""
        pass


@dataclass
class RetrieverConfig:
    """Configuration for hybrid retriever."""
    vector_k: int = 10  # Number of vector search results
    bm25_k: int = 10    # Number of BM25 search results
    graph_k: int = 5    # Number of graph search results
    rrf_k: int = 60     # RRF constant for fusion
    rerank_top_k: int = 10  # Number of results after reranking
    use_bm25: bool = True
    use_graph: bool = False
    use_reranker: bool = True
    rerank_after_fusion: bool = True
    tenant_filter: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vector_k": self.vector_k,
            "bm25_k": self.bm25_k,
            "graph_k": self.graph_k,
            "rrf_k": self.rrf_k,
            "rerank_top_k": self.rerank_top_k,
            "use_bm25": self.use_bm25,
            "use_graph": self.use_graph,
            "use_reranker": self.use_reranker,
            "rerank_after_fusion": self.rerank_after_fusion,
            "tenant_filter": self.tenant_filter,
        }


@dataclass
class HybridRetrieverResult:
    """Result from hybrid retrieval with citations."""
    query: str
    documents: List[Dict[str, Any]] = field(default_factory=list)
    search_sources: List[str] = field(default_factory=list)
    total_hits: int = 0
    latency_ms: float = 0.0
    confidence_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "documents": self.documents,
            "search_sources": self.search_sources,
            "total_hits": self.total_hits,
            "latency_ms": self.latency_ms,
            "confidence_score": self.confidence_score,
        }


class HybridRetriever:
    """Hybrid retriever combining multiple search modalities.

    Combines dense vector search with sparse BM25 and graph-based search,
    fuses results using Reciprocal Rank Fusion, and optionally reranks
    with a cross-encoder model.
    """

    def __init__(
        self,
        vector_store: Any,
        bm25_retriever: Optional[BM25Retriever] = None,
        graph_retriever: Optional[GraphRetriever] = None,
        reranker: Optional[Reranker] = None,
        config: Optional[RetrieverConfig] = None,
    ):
        """Initialize the hybrid retriever.

        Args:
            vector_store: Vector store with similarity_search method
            bm25_retriever: Optional BM25 retriever for keyword search
            graph_retriever: Optional graph retriever for relationship search
            reranker: Optional cross-encoder reranker
            config: Retriever configuration
        """
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever
        self.graph_retriever = graph_retriever
        self.reranker = reranker or FakeReranker()
        self.config = config or RetrieverConfig()

        # Build filter for tenant isolation
        self._filter = None
        if self.config.tenant_filter:
            self._filter = {"tenant_id": self.config.tenant_filter}

    def _build_filter(self, extra_filter: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Build filter combining tenant isolation and extra filters."""
        base_filter = self._filter.copy() if self._filter else {}
        if extra_filter:
            base_filter.update(extra_filter)
        return base_filter if base_filter else None

    async def search(
        self,
        query: str,
        embedding: List[float],
        tenant_id: Optional[str] = None,
        extra_filter: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> HybridRetrieverResult:
        """Perform hybrid search with the given query.

        Args:
            query: The search query text
            embedding: Query embedding vector
            tenant_id: Optional tenant ID for tenant-scoped search
            extra_filter: Additional metadata filters
            top_k: Number of top results to return

        Returns:
            HybridRetrieverResult with documents and metadata
        """
        import time
        start_time = time.time()

        # Build filter
        search_filter = self._build_filter(extra_filter)
        if tenant_id:
            if search_filter is None:
                search_filter = {}
            search_filter["tenant_id"] = tenant_id

        search_sources = []
        all_docs = []

        # 1. Vector search (dense semantic)
        vector_results = await self._search_vector(query, embedding, search_filter)
        if vector_results:
            search_sources.append("vector")
            logger.debug(f"Vector search returned {len(vector_results)} results")

        # 2. BM25 search (sparse lexical)
        bm25_results = []
        if self.config.use_bm25 and self.bm25_retriever:
            bm25_results = await self._search_bm25(query, search_filter)
            if bm25_results:
                search_sources.append("bm25")
                logger.debug(f"BM25 search returned {len(bm25_results)} results")

        # 3. Graph search (relationships)
        graph_results = []
        if self.config.use_graph and self.graph_retriever:
            graph_results = await self._search_graph(query, search_filter)
            if graph_results:
                search_sources.append("graph")
                logger.debug(f"Graph search returned {len(graph_results)} results")

        # 4. RRF Fusion
        fused_results = self._fuse_results(vector_results, bm25_results, graph_results)

        # 5. Reranking
        if self.config.use_reranker and fused_results:
            if self.config.rerank_after_fusion:
                reranked_results = await self._rerank(query, fused_results)
                final_results = reranked_results[:top_k]
            else:
                final_results = fused_results[:top_k]
                # Add rerank_score from RRF if not reranked
                for doc in final_results:
                    if "rerank_score" not in doc:
                        doc["rerank_score"] = doc.get("rrf_score", 0.0)
        else:
            final_results = fused_results[:top_k]
            for doc in final_results:
                doc["rerank_score"] = doc.get("rrf_score", 0.0)

        latency_ms = (time.time() - start_time) * 1000

        return HybridRetrieverResult(
            query=query,
            documents=final_results,
            search_sources=list(set(search_sources)),
            total_hits=len(fused_results),
            latency_ms=latency_ms,
            confidence_score=self._compute_confidence(final_results),
        )

    async def _search_vector(
        self,
        query: str,
        embedding: List[float],
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform vector search using dense embeddings."""
        try:
            results = await self.vector_store.similarity_search(
                query=query,
                embedding=embedding,
                k=self.config.vector_k,
                filter=filter,
            )
            return results
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _search_bm25(
        self,
        query: str,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform BM25 sparse search."""
        if not self.bm25_retriever:
            return []
        try:
            results = await self.bm25_retriever.search(
                query=query,
                k=self.config.bm25_k,
                filter=filter,
            )
            return results
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    async def _search_graph(
        self,
        query: str,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform graph-based relationship search."""
        if not self.graph_retriever:
            return []
        try:
            results = await self.graph_retriever.search(
                query=query,
                k=self.config.graph_k,
                filter=filter,
            )
            return results
        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            return []

    def _fuse_results(
        self,
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Fuse results using Reciprocal Rank Fusion."""
        if bm25_results:
            return reciprocal_rank_fusion(vector_results, bm25_results, self.config.rrf_k)
        elif graph_results:
            # If we have graph results but no BM25, fuse vector + graph
            # Treat graph results uniformly with BM25
            return reciprocal_rank_fusion(vector_results, graph_results, self.config.rrf_k)
        else:
            # Only vector search results
            return vector_results

    async def _rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Rerank documents using cross-encoder."""
        try:
            return await self.reranker.arerank(query, documents, top_k=self.config.rerank_top_k)
        except Exception as e:
            logger.warning(f"Reranking failed, returning original results: {e}")
            return documents

    def _compute_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Compute confidence score based on result quality."""
        if not results:
            return 0.0

        # Average RRF score as confidence proxy
        rrf_scores = [doc.get("rrf_score", 0.0) for doc in results]
        avg_rrf = sum(rrf_scores) / len(rrf_scores)

        # Weight confidence by RRF score (0-1 scale)
        # Normalize RRF: typically ranges from ~0.001 to ~1.0
        confidence = min(1.0, avg_rrf * 10)  # Scale factor

        return round(confidence, 3)