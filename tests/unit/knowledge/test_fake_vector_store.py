"""Tests for fake vector store implementation."""

import pytest

from services.knowledge_service.retrieval.fake_vector_store import FakeVectorStore


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_vector_store_add_and_search():
    """Test adding and searching documents in fake vector store."""
    store = FakeVectorStore()

    docs = [
        {
            "id": "doc1",
            "content": "How to reset password",
            "metadata": {"category": "account", "tenant_id": "tenant-1"},
        },
        {
            "id": "doc2",
            "content": "Billing FAQ",
            "metadata": {"category": "billing", "tenant_id": "tenant-1"},
        },
    ]

    ids = await store.add_documents(docs)
    assert len(ids) == 2
    assert "doc1" in ids
    assert "doc2" in ids

    results = await store.similarity_search(
        "password reset",
        embedding=[0.1] * 1536,
        k=5
    )
    assert len(results) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_vector_store_with_filter():
    """Test vector store search with metadata filter."""
    store = FakeVectorStore()

    docs = [
        {
            "id": "doc1",
            "content": "Account help",
            "metadata": {"category": "account", "tenant_id": "tenant-1"},
        },
        {
            "id": "doc2",
            "content": "Billing help",
            "metadata": {"category": "billing", "tenant_id": "tenant-1"},
        },
    ]

    await store.add_documents(docs)

    results = await store.similarity_search(
        "help",
        embedding=[0.1] * 1536,
        k=5,
        filter={"category": "account"}
    )
    assert len(results) == 1
    assert results[0]["id"] == "doc1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_vector_store_tenant_isolation():
    """Test that tenant filtering works correctly."""
    store = FakeVectorStore()

    docs = [
        {
            "id": "doc1",
            "content": "Doc for tenant A",
            "metadata": {"tenant_id": "tenant-a"},
        },
        {
            "id": "doc2",
            "content": "Doc for tenant B",
            "metadata": {"tenant_id": "tenant-b"},
        },
    ]

    await store.add_documents(docs)

    results_a = await store.similarity_search(
        "doc",
        embedding=[0.1] * 1536,
        k=5,
        filter={"tenant_id": "tenant-a"}
    )
    assert len(results_a) == 1
    assert results_a[0]["metadata"]["tenant_id"] == "tenant-a"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_vector_store_delete():
    """Test deleting documents from vector store."""
    store = FakeVectorStore()

    docs = [
        {"id": "doc1", "content": "Content 1"},
        {"id": "doc2", "content": "Content 2"},
    ]
    await store.add_documents(docs)

    results = await store.similarity_search("content", [0.1] * 1536, k=5)
    assert len(results) == 2

    await store.delete(["doc1"])

    results = await store.similarity_search("content", [0.1] * 1536, k=5)
    assert len(results) == 1
    assert results[0]["id"] == "doc2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_vector_store_get_by_ids():
    """Test getting documents by IDs."""
    store = FakeVectorStore()

    docs = [
        {"id": "doc1", "content": "Content 1"},
        {"id": "doc2", "content": "Content 2"},
    ]
    await store.add_documents(docs)

    results = await store.get_by_ids(["doc1", "doc2"])
    assert len(results) == 2

    results = await store.get_by_ids(["doc1", "non-existent"])
    assert len(results) == 1
    assert results[0]["id"] == "doc1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_vector_store_upsert():
    """Test upserting documents."""
    store = FakeVectorStore()

    docs_new = [{"id": "doc1", "content": "New content 1"}]
    ids = await store.upsert(docs_new)
    assert len(ids) == 1

    results = await store.similarity_search("new", [0.1] * 1536, k=5)
    assert len(results) == 1

    docs_update = [{"id": "doc1", "content": "Updated content 1"}]
    await store.upsert(docs_update)

    results = await store.similarity_search("updated", [0.1] * 1536, k=5)
    assert len(results) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_vector_store_clear():
    """Test clearing the vector store."""
    store = FakeVectorStore()

    docs = [{"id": "doc1", "content": "Content 1"}]
    await store.add_documents(docs, collection="test_collection")

    results = await store.similarity_search("content", [0.1] * 1536, k=5, collection="test_collection")
    assert len(results) == 1

    store.clear("test_collection")

    results = await store.similarity_search("content", [0.1] * 1536, k=5, collection="test_collection")
    assert len(results) == 0