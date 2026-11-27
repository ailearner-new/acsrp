"""Tests for Reciprocal Rank Fusion implementation."""

import pytest

from services.knowledge_service.retriever.rrf import (
    reciprocal_rank_fusion,
    reciprocal_rank_fusion_documents,
    RetrievedDocument,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rrf_basic_fusion():
    """Test basic RRF fusion of vector and BM25 results."""
    vector_results = [
        {"doc_id": "doc1", "content": "Document 1 content", "score": 0.9},
        {"doc_id": "doc2", "content": "Document 2 content", "score": 0.8},
        {"doc_id": "doc3", "content": "Document 3 content", "score": 0.7},
    ]

    bm25_results = [
        {"doc_id": "doc1", "content": "Document 1 content", "score": 0.95},
        {"doc_id": "doc4", "content": "Document 4 content", "score": 0.85},
    ]

    fused = reciprocal_rank_fusion(vector_results, bm25_results, k=60)

    # doc1 appears in both, should have higher score
    assert len(fused) == 4  # 3 unique docs from vector + 1 new from BM25
    assert fused[0]["doc_id"] == "doc1"  # doc1 has highest RRF score
    assert "rrf_score" in fused[0]
    assert fused[0]["rrf_score"] > 0.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rrf_same_rank_both_results():
    """Test RRF when same document is top in both vector and BM25."""
    vector_results = [
        {"doc_id": "doc1", "content": "Content 1"},
        {"doc_id": "doc2", "content": "Content 2"},
    ]

    bm25_results = [
        {"doc_id": "doc1", "content": "Content 1"},
        {"doc_id": "doc2", "content": "Content 2"},
    ]

    fused = reciprocal_rank_fusion(vector_results, bm25_results, k=60)

    # Document appearing in both at rank 0 should get 2 * (1/60) = 2/60 score
    assert len(fused) == 2
    assert fused[0]["doc_id"] == "doc1"
    # Each appearance adds 1/(k + rank + 1), so top rank adds 1/61 twice
    assert fused[0]["rrf_score"] == 2.0 / 61


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rrf_different_k_values():
    """Test RRF with different k values."""
    vector_results = [
        {"doc_id": "doc1", "content": "Content 1"},
        {"doc_id": "doc2", "content": "Content 2"},
    ]

    bm25_results = [
        {"doc_id": "doc1", "content": "Content 1"},
        {"doc_id": "doc2", "content": "Content 2"},
    ]

    # Higher k = less aggressive fusion
    fused_low_k = reciprocal_rank_fusion(vector_results, bm25_results, k=10)
    fused_high_k = reciprocal_rank_fusion(vector_results, bm25_results, k=100)

    assert len(fused_low_k) == len(fused_high_k) == 2

    # Both should produce same ranking order since both docs appear in both results
    assert fused_low_k[0]["doc_id"] == fused_high_k[0]["doc_id"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rrf_no_overlap():
    """Test RRF when there's no overlap between results."""
    vector_results = [
        {"doc_id": "doc1", "content": "Content 1"},
        {"doc_id": "doc2", "content": "Content 2"},
    ]

    bm25_results = [
        {"doc_id": "doc3", "content": "Content 3"},
        {"doc_id": "doc4", "content": "Content 4"},
    ]

    fused = reciprocal_rank_fusion(vector_results, bm25_results, k=60)

    assert len(fused) == 4
    # All docs should have positive RRF scores
    for doc in fused:
        assert doc["rrf_score"] > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rrf_empty_results():
    """Test RRF with empty results."""
    fused = reciprocal_rank_fusion([], [])
    assert fused == []

    fused = reciprocal_rank_fusion([{"doc_id": "doc1"}], [])
    assert len(fused) == 1
    assert fused[0]["doc_id"] == "doc1"

    fused = reciprocal_rank_fusion([], [{"doc_id": "doc1"}])
    assert len(fused) == 1
    assert fused[0]["doc_id"] == "doc1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rrf_preserves_document_data():
    """Test that RRF preserves original document data."""
    vector_results = [
        {
            "doc_id": "doc1",
            "content": "Content 1",
            "title": "Title 1",
            "metadata": {"category": "account"},
            "source_url": "https://example.com/doc1",
        },
    ]

    bm25_results = [
        {
            "doc_id": "doc2",
            "content": "Content 2",
            "title": "Title 2",
            "metadata": {"category": "billing"},
        },
    ]

    fused = reciprocal_rank_fusion(vector_results, bm25_results, k=60)

    # First doc should have data from vector result
    assert fused[0]["title"] == "Title 1"
    assert fused[0]["source_url"] == "https://example.com/doc1"

    # Second doc should have data from BM25 result
    second_doc = [d for d in fused if d["doc_id"] == "doc2"][0]
    assert second_doc["title"] == "Title 2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieved_document_to_dict():
    """Test RetrievedDocument dict conversion."""
    doc = RetrievedDocument(
        doc_id="test-doc",
        title="Test Title",
        content="Test Content",
        score=0.95,
        source_url="https://example.com/test",
        metadata={"category": "support"},
    )

    d = doc.to_dict()

    assert d["doc_id"] == "test-doc"
    assert d["title"] == "Test Title"
    assert d["content"] == "Test Content"
    assert d["score"] == 0.95
    assert d["source_url"] == "https://example.com/test"
    assert d["metadata"]["category"] == "support"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieved_document_from_dict():
    """Test RetrievedDocument creation from dict."""
    data = {
        "doc_id": "test-doc",
        "title": "Test Title",
        "content": "Test Content",
        "score": 0.95,
        "source_url": "https://example.com/test",
        "metadata": {"category": "support"},
    }

    doc = RetrievedDocument.from_dict(data)

    assert doc.doc_id == "test-doc"
    assert doc.title == "Test Title"
    assert doc.content == "Test Content"
    assert doc.score == 0.95
    assert doc.source_url == "https://example.com/test"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rrf_fusion_with_retrieved_documents():
    """Test RRF fusion with RetrievedDocument objects."""
    vector_docs = [
        RetrievedDocument(
            doc_id="doc1",
            title="Title 1",
            content="Content 1",
            score=0.9,
        ),
        RetrievedDocument(
            doc_id="doc2",
            title="Title 2",
            content="Content 2",
            score=0.8,
        ),
    ]

    bm25_docs = [
        RetrievedDocument(
            doc_id="doc1",
            title="Title 1 Updated",
            content="Content 1",
            score=0.95,
        ),
        RetrievedDocument(
            doc_id="doc3",
            title="Title 3",
            content="Content 3",
            score=0.7,
        ),
    ]

    fused = reciprocal_rank_fusion_documents(vector_docs, bm25_docs, k=60)

    assert len(fused) == 3  # 3 unique documents
    assert all(isinstance(d, RetrievedDocument) for d in fused)