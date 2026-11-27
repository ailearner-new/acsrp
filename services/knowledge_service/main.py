"""Knowledge service main entry point."""

import os
import logging
import time
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Body, Query
from pydantic import BaseModel, Field

from services.knowledge_service.retrieval import (
    VectorStore,
    EmbeddingProvider,
    FakeVectorStore,
    FakeEmbeddings,
)
from services.knowledge_service.retriever import (
    HybridRetriever,
    RetrieverConfig,
    FakeReranker,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Knowledge Service",
    description="RAG pipeline with hybrid retrieval (vector + BM25 + graph)",
    version="0.2.0",
)


def get_vector_store() -> VectorStore:
    """Get the configured vector store instance."""
    store_type = os.getenv("VECTOR_STORE_TYPE", "memory")

    if store_type == "memory":
        logger.info("Using FakeVectorStore for development/testing")
        return FakeVectorStore()
    elif store_type == "pinecone":
        # Will be implemented when Pinecone connector is available
        raise NotImplementedError("Pinecone backend not yet implemented")
    elif store_type == "weaviate":
        raise NotImplementedError("Weaviate backend not yet implemented")
    elif store_type == "qdrant":
        raise NotImplementedError("Qdrant backend not yet implemented")
    else:
        logger.warning(f"Unknown VECTOR_STORE_TYPE '{store_type}', falling back to memory")
        return FakeVectorStore()


def get_embedding_provider() -> EmbeddingProvider:
    """Get the configured embedding provider instance."""
    provider = os.getenv("EMBEDDING_PROVIDER", "openai")

    if provider == "fake" or os.getenv("DEMO_MODE", "false").lower() == "true":
        logger.info("Using FakeEmbeddings for development/testing")
        return FakeEmbeddings()
    elif provider == "openai":
        # Will be implemented when OpenAI client is available
        raise NotImplementedError("OpenAI backend not yet implemented")
    elif provider == "cohere":
        raise NotImplementedError("Cohere backend not yet implemented")
    else:
        logger.warning(f"Unknown EMBEDDING_PROVIDER '{provider}', falling back to fake")
        return FakeEmbeddings()


# Global instances
vector_store: VectorStore = None
embedding_provider: EmbeddingProvider = None
hybrid_retriever: HybridRetriever = None


@app.on_event("startup")
async def startup_event():
    """Initialize service components on startup."""
    global vector_store, embedding_provider, hybrid_retriever
    vector_store = get_vector_store()
    embedding_provider = get_embedding_provider()

    # Initialize hybrid retriever with fake reranker for now
    hybrid_retriever = HybridRetriever(
        vector_store=vector_store,
        reranker=FakeReranker(),
        config=RetrieverConfig(
            vector_k=int(os.getenv("RETRIEVER_VECTOR_K", "10")),
            bm25_k=int(os.getenv("RETRIEVER_BM25_K", "10")),
            rrf_k=int(os.getenv("RETRIEVER_RRF_K", "60")),
            rerank_top_k=int(os.getenv("RETRIEVER_RERANK_K", "10")),
            use_bm25=os.getenv("RETRIEVER_USE_BM25", "true").lower() == "true",
            use_reranker=os.getenv("RETRIEVER_USE_RERANKER", "true").lower() == "true",
            tenant_filter=None,
        ),
    )
    logger.info("Knowledge service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "knowledge-service"}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    if vector_store is None or embedding_provider is None:
        return {"status": "not_ready", "reason": "service not initialized"}
    return {"status": "ready"}


@app.get("/config")
async def get_config():
    """Get current service configuration (for debugging)."""
    return {
        "vector_store_type": type(vector_store).__name__ if vector_store else None,
        "embedding_provider_type": type(embedding_provider).__name__ if embedding_provider else None,
        "embedding_dimension": embedding_provider.dimension if embedding_provider else None,
        "hybrid_retriever_config": hybrid_retriever.config.to_dict() if hybrid_retriever else None,
    }


# Request/Response models
class SearchRequest(BaseModel):
    """Request model for hybrid search."""
    query: str = Field(..., description="Search query text")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for filtering")
    category: Optional[str] = Field(None, description="Category filter")
    top_k: int = Field(10, ge=1, le=100, description="Number of top results to return")
    include_embeddings: bool = Field(False, description="Include embeddings in response")


class SearchResponse(BaseModel):
    """Response model for hybrid search."""
    query: str
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    search_sources: List[str] = Field(default_factory=list)
    total_hits: int = 0
    latency_ms: float = 0.0
    confidence_score: float = 1.0


@app.post("/search", response_model=SearchResponse)
async def hybrid_search(request: SearchRequest = Body(...)):
    """Perform hybrid search with vector + BM25 fusion.

    This endpoint implements the hybrid retrieval pipeline:
    1. Generate query embedding
    2. Perform parallel vector and BM25 searches
    3. Fuse results using Reciprocal Rank Fusion
    4. Rerank with cross-encoder (if enabled)
    """
    if hybrid_retriever is None:
        return SearchResponse(
            query=request.query,
            latency_ms=0.0,
            confidence_score=0.0,
        )

    start_time = time.time()

    # Generate query embedding
    try:
        embedding = await embedding_provider.aembed_text(request.query)
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return SearchResponse(
            query=request.query,
            latency_ms=(time.time() - start_time) * 1000,
            confidence_score=0.0,
        )

    # Build filter
    extra_filter = {}
    if request.tenant_id:
        extra_filter["tenant_id"] = request.tenant_id
    if request.category:
        extra_filter["category"] = request.category

    # Perform hybrid search
    result = await hybrid_retriever.search(
        query=request.query,
        embedding=embedding,
        tenant_id=request.tenant_id,
        extra_filter=extra_filter if extra_filter else None,
        top_k=request.top_k,
    )

    # Remove embeddings from response if not requested
    if not request.include_embeddings:
        for doc in result.documents:
            doc.pop("embedding", None)

    return SearchResponse(
        query=result.query,
        documents=result.documents,
        search_sources=result.search_sources,
        total_hits=result.total_hits,
        latency_ms=result.latency_ms,
        confidence_score=result.confidence_score,
    )


# Backward-compatible endpoint for direct vector search
class VectorSearchRequest(BaseModel):
    """Request model for vector search."""
    query: str
    embedding: List[float]
    k: int = Field(10, ge=1, le=100)
    tenant_id: Optional[str] = None
    category: Optional[str] = None


class VectorSearchResponse(BaseModel):
    """Response model for vector search."""
    query: str
    results: List[Dict[str, Any]] = Field(default_factory=list)
    latency_ms: float = 0.0


@app.post("/vector-search", response_model=VectorSearchResponse)
async def vector_search(request: VectorSearchRequest = Body(...)):
    """Perform direct vector similarity search (backward compatible)."""
    start_time = time.time()

    search_filter = None
    if request.tenant_id or request.category:
        search_filter = {}
        if request.tenant_id:
            search_filter["tenant_id"] = request.tenant_id
        if request.category:
            search_filter["category"] = request.category

    results = await vector_store.similarity_search(
        query=request.query,
        embedding=request.embedding,
        k=request.k,
        filter=search_filter,
    )

    return VectorSearchResponse(
        query=request.query,
        results=results,
        latency_ms=(time.time() - start_time) * 1000,
    )