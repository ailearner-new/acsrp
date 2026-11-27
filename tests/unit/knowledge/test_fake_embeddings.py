"""Tests for fake embeddings implementation."""

import pytest

from services.knowledge_service.retrieval.fake_embeddings import FakeEmbeddings


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_embeddings_dimension():
    """Test that embeddings have correct dimension."""
    embedder = FakeEmbeddings(dimension=1536)

    assert embedder.dimension == 1536
    assert embedder.model_name == "fake-embeddings"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_embeddings_embed_text():
    """Test embedding a single text."""
    embedder = FakeEmbeddings(dimension=1536)

    embedding = await embedder.aembed_text("Hello, world!")

    assert len(embedding) == 1536
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_embeddings_embed_texts():
    """Test embedding multiple texts."""
    embedder = FakeEmbeddings(dimension=1536)

    texts = ["First text", "Second text", "Third text"]
    embeddings = await embedder.aembed_texts(texts)

    assert len(embeddings) == 3
    for emb in embeddings:
        assert len(emb) == 1536


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_embeddings_deterministic():
    """Test that same input produces same embedding."""
    embedder = FakeEmbeddings(dimension=1536)

    emb1 = await embedder.aembed_text("Same text")
    emb2 = await embedder.aembed_text("Same text")

    assert emb1 == emb2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_embeddings_different_texts_differ():
    """Test that different texts produce different embeddings."""
    embedder = FakeEmbeddings(dimension=1536)

    emb1 = await embedder.aembed_text("First text")
    emb2 = await embedder.aembed_text("Completely different text")

    assert emb1 != emb2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_embeddings_sync_methods():
    """Test synchronous embedding methods."""
    embedder = FakeEmbeddings(dimension=1536)

    embedding = embedder.embed_text("Hello, world!")
    assert len(embedding) == 1536

    embeddings = embedder.embed_texts(["Text 1", "Text 2"])
    assert len(embeddings) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_embeddings_langchain_compatibility():
    """Test LangChain compatibility methods."""
    embedder = FakeEmbeddings(dimension=1536)

    embeddings = embedder.embed_documents(["Doc 1", "Doc 2"])
    assert len(embeddings) == 2

    embedding = embedder.embed_query("Query text")
    assert len(embedding) == 1536


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_embeddings_custom_dimension():
    """Test embeddings with custom dimension."""
    for dim in [768, 1024, 1536]:
        embedder = FakeEmbeddings(dimension=dim)
        embedding = await embedder.aembed_text("test")

        assert len(embedding) == dim