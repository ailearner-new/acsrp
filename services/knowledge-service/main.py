"""Knowledge service main entry point."""

import os
import logging

from fastapi import FastAPI

from services.knowledge_service.retrieval import (
    VectorStore,
    EmbeddingProvider,
    FakeVectorStore,
    FakeEmbeddings,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Knowledge Service",
    description="RAG pipeline with hybrid retrieval (vector + BM25 + graph)",
    version="0.1.0",
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


@app.on_event("startup")
async def startup_event():
    """Initialize service components on startup."""
    global vector_store, embedding_provider
    vector_store = get_vector_store()
    embedding_provider = get_embedding_provider()
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
    }