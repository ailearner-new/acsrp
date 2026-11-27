"""Knowledge service main entry point."""

import os
import logging
import time
import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Body, Query, HTTPException
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
_documents_store: Dict[str, Dict[str, Any]] = {}


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


# =============================================================================
# Knowledge Article CRUD API
# =============================================================================

class KnowledgeArticleCreate(BaseModel):
    """Request model for creating a knowledge article."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    source_url: Optional[str] = Field(None)
    tenant_id: str = Field(..., description="Tenant ID for multi-tenancy")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class KnowledgeArticleResponse(BaseModel):
    """Response model for a knowledge article."""
    doc_id: str
    title: str
    content: str
    category: Optional[str] = None
    source_url: Optional[str] = None
    tenant_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@app.post("/api/v1/knowledge/articles", response_model=KnowledgeArticleResponse, status_code=201)
async def create_knowledge_article(article: KnowledgeArticleCreate = Body(...)):
    """Create a new knowledge article and index it."""
    doc_id = article.doc_id if hasattr(article, 'doc_id') else str(uuid.uuid4())

    now = datetime.utcnow().isoformat()

    doc_data = {
        "doc_id": doc_id,
        "title": article.title,
        "content": article.content,
        "category": article.category,
        "source_url": article.source_url,
        "tenant_id": article.tenant_id,
        "metadata": article.metadata or {},
        "created_at": now,
        "updated_at": now,
    }

    _documents_store[doc_id] = doc_data

    # Generate embedding and add to vector store
    if embedding_provider and vector_store:
        try:
            embedding = await embedding_provider.aembed_text(article.content)
            await vector_store.upsert([{
                "id": doc_id,
                "content": article.content,
                "metadata": {
                    "tenant_id": article.tenant_id,
                    "title": article.title,
                    "category": article.category,
                    "source_url": article.source_url,
                }
            }])
        except Exception as e:
            logger.warning(f"Failed to embed and index document: {e}")

    return KnowledgeArticleResponse(**{
        "doc_id": doc_id,
        "title": article.title,
        "content": article.content,
        "category": article.category,
        "source_url": article.source_url,
        "tenant_id": article.tenant_id,
        "metadata": article.metadata or {},
        "created_at": now,
        "updated_at": now,
    })


@app.get("/api/v1/knowledge/articles/{doc_id}", response_model=KnowledgeArticleResponse)
async def get_knowledge_article(doc_id: str, tenant_id: Optional[str] = Query(None)):
    """Get a knowledge article by ID."""
    doc = _documents_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Knowledge article {doc_id} not found")

    if doc.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return KnowledgeArticleResponse(**doc)


@app.put("/api/v1/knowledge/articles/{doc_id}", response_model=KnowledgeArticleResponse)
async def update_knowledge_article(doc_id: str, article: KnowledgeArticleCreate = Body(...)):
    """Update a knowledge article."""
    if doc_id not in _documents_store:
        raise HTTPException(status_code=404, detail=f"Knowledge article {doc_id} not found")

    now = datetime.utcnow().isoformat()

    doc_data = {
        "doc_id": doc_id,
        "title": article.title,
        "content": article.content,
        "category": article.category,
        "source_url": article.source_url,
        "tenant_id": article.tenant_id,
        "metadata": article.metadata or {},
        "created_at": _documents_store[doc_id].get("created_at"),
        "updated_at": now,
    }

    _documents_store[doc_id] = doc_data

    # Re-index the document
    if embedding_provider and vector_store:
        try:
            embedding = await embedding_provider.aembed_text(article.content)
            await vector_store.upsert([{
                "id": doc_id,
                "content": article.content,
                "metadata": {
                    "tenant_id": article.tenant_id,
                    "title": article.title,
                    "category": article.category,
                    "source_url": article.source_url,
                }
            }])
        except Exception as e:
            logger.warning(f"Failed to re-index document: {e}")

    return KnowledgeArticleResponse(**doc_data)


@app.delete("/api/v1/knowledge/articles/{doc_id}")
async def delete_knowledge_article(doc_id: str, tenant_id: Optional[str] = Query(None)):
    """Delete a knowledge article."""
    if doc_id not in _documents_store:
        raise HTTPException(status_code=404, detail=f"Knowledge article {doc_id} not found")

    doc = _documents_store[doc_id]
    if doc.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    del _documents_store[doc_id]

    if vector_store:
        await vector_store.delete([doc_id])

    return {"status": "deleted", "doc_id": doc_id}


# =============================================================================
# Knowledge Search API
# =============================================================================

class SearchRequest(BaseModel):
    """Request model for hybrid search."""
    query: str = Field(..., description="Search query text")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for filtering")
    category: Optional[str] = Field(None, description="Category filter")
    limit: int = Field(10, ge=1, le=100, description="Number of top results to return")
    include_citations: bool = Field(True, description="Include citations in response")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")


class SearchResponse(BaseModel):
    """Response model for hybrid search."""
    results: List[Dict[str, Any]] = Field(default_factory=list)
    query_id: str
    latency_ms: float = 0.0


@app.post("/api/v1/knowledge/search", response_model=SearchResponse)
async def knowledge_search(request: SearchRequest = Body(...)):
    """Hybrid search across knowledge base."""
    if hybrid_retriever is None:
        return SearchResponse(query_id=str(uuid.uuid4()), latency_ms=0.0)

    start_time = time.time()
    query_id = str(uuid.uuid4())

    # Generate query embedding
    try:
        embedding = await embedding_provider.aembed_text(request.query)
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return SearchResponse(query_id=query_id, latency_ms=(time.time() - start_time) * 1000)

    # Build filter
    extra_filter = request.filters or {}
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
        top_k=request.limit,
    )

    # Format results with citations
    formatted_results = []
    for doc in result.documents:
        formatted_doc = {
            "doc_id": doc.get("doc_id") or doc.get("id"),
            "title": doc.get("title", ""),
            "content": doc.get("content", ""),
            "score": doc.get("score", doc.get("rrf_score", 0.0)),
            "rrf_score": doc.get("rrf_score", 0.0),
            "source_url": doc.get("metadata", {}).get("source_url") or doc.get("source_url"),
            "category": doc.get("metadata", {}).get("category") or doc.get("category"),
            "updated_at": doc.get("metadata", {}).get("updated_at"),
        }
        if request.include_citations:
            formatted_doc["citation"] = {
                "doc_id": formatted_doc["doc_id"],
                "title": formatted_doc["title"],
                "score": formatted_doc["score"],
            }
        formatted_results.append(formatted_doc)

    return SearchResponse(
        results=formatted_results,
        query_id=query_id,
        latency_ms=(time.time() - start_time) * 1000,
    )


# =============================================================================
# Index Management API
# =============================================================================

class IndexRequest(BaseModel):
    """Request model for triggering reindex."""
    doc_ids: Optional[List[str]] = Field(None, description="Specific doc IDs to reindex, or None for all")
    tenant_id: str = Field(..., description="Tenant ID")
    force: bool = Field(False, description="Force reindex even if already indexed")


class IndexResponse(BaseModel):
    """Response model for index job."""
    index_job_id: str
    status: str
    estimated_docs: int


@app.post("/api/v1/knowledge/index", response_model=IndexResponse, status_code=202)
async def trigger_index(request: IndexRequest = Body(...)):
    """Trigger reindex of documents."""
    import asyncio

    job_id = str(uuid.uuid4())

    # For now, perform synchronous indexing in demo mode
    # In production, this would be an async background job
    if request.doc_ids:
        docs_to_index = [d for d in _documents_store.values() if d["doc_id"] in request.doc_ids]
    else:
        docs_to_index = [
            d for d in _documents_store.values()
            if d.get("tenant_id") == request.tenant_id
        ]

    if embedding_provider and vector_store and docs_to_index:
        try:
            docs_for_index = []
            for doc in docs_to_index:
                docs_for_index.append({
                    "id": doc["doc_id"],
                    "content": doc["content"],
                    "metadata": {
                        "tenant_id": doc["tenant_id"],
                        "title": doc["title"],
                        "category": doc.get("category"),
                        "source_url": doc.get("source_url"),
                    }
                })
            await vector_store.upsert(docs_for_index)
            logger.info(f"Indexed {len(docs_for_index)} documents, job_id={job_id}")
        except Exception as e:
            logger.error(f"Indexing failed: {e}")

    return IndexResponse(
        index_job_id=job_id,
        status="completed",
        estimated_docs=len(docs_to_index),
    )


# =============================================================================
# Document List API
# =============================================================================

class DocumentListItem(BaseModel):
    """Response model for a document in list."""
    doc_id: str
    title: str
    category: Optional[str] = None
    source_url: Optional[str] = None
    updated_at: Optional[str] = None
    chunk_count: int = 1


class DocumentListResponse(BaseModel):
    """Response model for document list."""
    documents: List[DocumentListItem] = Field(default_factory=list)
    total: int


@app.get("/api/v1/knowledge/documents", response_model=DocumentListResponse)
async def list_documents(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List documents with pagination."""
    filtered_docs = list(_documents_store.values())

    if tenant_id:
        filtered_docs = [d for d in filtered_docs if d.get("tenant_id") == tenant_id]

    if category:
        filtered_docs = [d for d in filtered_docs if d.get("category") == category]

    total = len(filtered_docs)
    paginated = filtered_docs[offset:offset + limit]

    documents = []
    for doc in paginated:
        documents.append(DocumentListItem(
            doc_id=doc["doc_id"],
            title=doc["title"],
            category=doc.get("category"),
            source_url=doc.get("source_url"),
            updated_at=doc.get("updated_at"),
            chunk_count=1,  # All documents start as single chunks
        ))

    return DocumentListResponse(documents=documents, total=total)


# =============================================================================
# Backward-compatible search endpoint
# =============================================================================

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


@app.post("/search", response_model=SearchResponse)
async def hybrid_search(request: SearchRequest = Body(...)):
    """Perform hybrid search with vector + BM25 fusion (backward compatible endpoint)."""
    return await knowledge_search(request)