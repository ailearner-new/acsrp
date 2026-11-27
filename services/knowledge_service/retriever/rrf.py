"""Reciprocal Rank Fusion for combining search results."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RetrievedDocument:
    """A retrieved document with source and score information."""
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
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievedDocument":
        """Create from dictionary."""
        return cls(
            doc_id=data["doc_id"],
            title=data.get("title", ""),
            content=data.get("content", ""),
            score=data.get("score", 0.0),
            source_url=data.get("source_url"),
            metadata=data.get("metadata"),
        )


def reciprocal_rank_fusion(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """Combine vector search and BM25 search results using Reciprocal Rank Fusion.

    RRF assigns higher scores to documents that appear in multiple result sets
    at high ranks. The formula is: score = sum(1/(k + rank_i)) for each retrieval result i.

    Args:
        vector_results: Results from dense vector search, each with 'doc_id' key
        bm25_results: Results from sparse BM25 search, each with 'doc_id' key
        k: RRF constant (higher = less aggressive fusion, default 60)

    Returns:
        List of documents merged and ranked by RRF score, sorted descending.
        Each result includes the document data from either source and 'rrf_score'.
    """
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict[str, Any]] = {}

    # Process vector search results
    for rank, doc in enumerate(vector_results):
        doc_id = doc.get("doc_id") or doc.get("id")
        if doc_id is None:
            continue
        # Preserve original document data
        if doc_id not in doc_map:
            doc_map[doc_id] = doc.copy()
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))

    # Process BM25 search results
    for rank, doc in enumerate(bm25_results):
        doc_id = doc.get("doc_id") or doc.get("id")
        if doc_id is None:
            continue
        # Preserve original document data, but don't overwrite existing more complete data
        if doc_id not in doc_map:
            doc_map[doc_id] = doc.copy()
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))

    # Sort by RRF score descending
    sorted_docs = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    # Build fused results with RRF score
    fused_results = []
    for doc_id, rrf_score in sorted_docs:
        retrieved_item = doc_map[doc_id].copy()
        retrieved_item["rrf_score"] = rrf_score
        fused_results.append(retrieved_item)

    return fused_results


def reciprocal_rank_fusion_documents(
    vector_results: List[RetrievedDocument],
    bm25_results: List[RetrievedDocument],
    k: int = 60,
) -> List[RetrievedDocument]:
    """Combine RetrievedDocument objects using RRF.

    This is a type-safe version that works with RetrievedDocument objects.

    Args:
        vector_results: Results from dense vector search
        bm25_results: Results from sparse BM25 search
        k: RRF constant (default 60)

    Returns:
        List of RetrievedDocument objects ranked by RRF score
    """
    # Convert to dict format for RRF processing
    vector_dicts = [doc.to_dict() for doc in vector_results]
    bm25_dicts = [doc.to_dict() for doc in bm25_results]

    # Apply RRF
    fused_dicts = reciprocal_rank_fusion(vector_dicts, bm25_dicts, k)

    # Convert back to RetrievedDocument
    return [RetrievedDocument.from_dict(d) for d in fused_dicts]