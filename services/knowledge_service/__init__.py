"""Knowledge service for RAG and hybrid retrieval."""

# Lazy imports - only import when actually needed
__all__ = ["HybridRetriever"]


def __getattr__(name):
    """Lazy import for main app and retriever."""
    if name == "app":
        from services.knowledge_service.main import app
        return app
    elif name == "HybridRetriever":
        from services.knowledge_service.retriever import HybridRetriever
        return HybridRetriever
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")