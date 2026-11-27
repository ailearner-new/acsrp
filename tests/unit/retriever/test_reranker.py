"""Tests for the reranker module."""

import pytest

from services.knowledge_service.retriever.reranker import (
    Reranker,
    FakeReranker,
    CohereReranker,
    get_reranker,
    RerankedResult,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_reranker_is_available():
    """Test that fake reranker is always available."""
    reranker = FakeReranker()
    assert reranker.is_available is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_reranker_simple_similarity():
    """Test simple similarity calculation in fake reranker."""
    reranker = FakeReranker()

    # Test with overlapping terms
    score = reranker._simple_similarity("password reset", "How to reset password")
    assert 0 < score <= 1.0

    # Test with no overlap
    score_no_overlap = reranker._simple_similarity("password reset", "completely unrelated")
    assert score_no_overlap == 0.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_reranker_arerank():
    """Test async reranking with fake reranker."""
    reranker = FakeReranker()

    query = "password reset"
    documents = [
        {"doc_id": "doc1", "content": "How to reset your password in the account settings"},
        {"doc_id": "doc2", "content": "Billing FAQ section"},
        {"doc_id": "doc3", "content": "Reset password using the forgot password link"},
    ]

    reranked = await reranker.arerank(query, documents)

    assert len(reranked) == 3
    # Documents should be sorted by rerank_score
    for i in range(len(reranked) - 1):
        assert reranked[i]["rerank_score"] >= reranked[i + 1]["rerank_score"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_reranker_top_k():
    """Test that top_k parameter limits results."""
    reranker = FakeReranker()

    query = "password reset"
    documents = [
        {"doc_id": f"doc{i}", "content": f"Content {i}"}
        for i in range(10)
    ]

    reranked = await reranker.arerank(query, documents, top_k=5)

    assert len(reranked) == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_reranker_deterministic():
    """Test that fake reranker produces deterministic results."""
    reranker = FakeReranker()

    query = "password reset"
    documents = [
        {"doc_id": "doc1", "content": "Password reset instructions"},
        {"doc_id": "doc2", "content": "Billing information"},
    ]

    reranked1 = await reranker.arerank(query, documents)
    reranked2 = await reranker.arerank(query, documents)

    assert reranked1 == reranked2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reranked_result_to_dict():
    """Test RerankedResult dict conversion."""
    result = RerankedResult(
        doc_id="test-doc",
        title="Test Title",
        content="Test Content",
        score=0.95,
        source_url="https://example.com/test",
    )

    d = result.to_dict()

    assert d["doc_id"] == "test-doc"
    assert d["score"] == 0.95


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reranked_result_from_dict():
    """Test RerankedResult creation from dict."""
    data = {
        "doc_id": "test-doc",
        "title": "Test Title",
        "content": "Test Content",
        "score": 0.95,
    }

    result = RerankedResult.from_dict(data)

    assert result.doc_id == "test-doc"
    assert result.score == 0.95


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_reranker_fake():
    """Test getting fake reranker from factory."""
    reranker = get_reranker(provider="fake")
    assert isinstance(reranker, FakeReranker)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_reranker_default():
    """Test that default reranker is fake."""
    reranker = get_reranker()
    assert isinstance(reranker, FakeReranker)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_reranker_model_name():
    """Test fake reranker model name configuration."""
    reranker = FakeReranker(model_name="custom-model")
    assert reranker.model_name == "custom-model"
    assert reranker.is_available is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reranker_empty_documents():
    """Test reranker with empty document list."""
    reranker = FakeReranker()

    reranked = await reranker.arerank("query", [])
    assert reranked == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reranker_preserves_original_data():
    """Test that reranker preserves original document data."""
    reranker = FakeReranker()

    query = "test"
    documents = [
        {
            "doc_id": "doc1",
            "content": "Test content",
            "metadata": {"category": "support"},
            "source_url": "https://example.com",
        },
    ]

    reranked = await reranker.arerank(query, documents)

    assert reranked[0]["doc_id"] == "doc1"
    assert reranked[0]["metadata"]["category"] == "support"
    assert reranked[0]["source_url"] == "https://example.com"
    assert "rerank_score" in reranked[0]