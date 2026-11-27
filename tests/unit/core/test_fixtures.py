"""Tests for offline pytest harness fixtures."""

import pytest
from tests.conftest import FakeLLM, FakeVectorStore, FakeRedis


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_llm_basic():
    """Test fake LLM returns responses."""
    llm = FakeLLM()
    response = await llm.ainvoke("test prompt")
    assert response.content == "[Fake LLM Response #1]"
    assert llm.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_llm_with_responses():
    """Test fake LLM with predefined responses."""
    llm = FakeLLM(responses={"classify": '{"intent": "test"}'})
    response = await llm.ainvoke("please classify this")
    assert response.content == '{"intent": "test"}'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_vector_store_add_and_search():
    """Test fake vector store add and search operations."""
    store = FakeVectorStore()

    docs = [
        {"id": "doc1", "content": "How to reset password", "metadata": {"category": "account"}},
        {"id": "doc2", "content": "Billing FAQ", "metadata": {"category": "billing"}},
    ]

    ids = await store.add_documents(docs)
    assert len(ids) == 2

    results = await store.similarity_search("password", k=5)
    assert len(results) == 2
    assert results[0]["content"] == "How to reset password"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_vector_store_filter():
    """Test fake vector store with metadata filter."""
    store = FakeVectorStore()

    docs = [
        {"id": "doc1", "content": "Account help", "metadata": {"category": "account"}},
        {"id": "doc2", "content": "Billing help", "metadata": {"category": "billing"}},
    ]
    await store.add_documents(docs)

    results = await store.similarity_search("help", k=5, filter={"category": "account"})
    assert len(results) == 1
    assert results[0]["metadata"]["category"] == "account"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_redis_basic():
    """Test fake Redis basic operations."""
    redis = FakeRedis()

    await redis.set("key1", "value1")
    val = await redis.get("key1")
    assert val == "value1"

    await redis.delete("key1")
    val = await redis.get("key1")
    assert val is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_redis_expiry():
    """Test fake Redis with expiry."""
    redis = FakeRedis()

    await redis.set("key1", "value1", ex=60)
    val = await redis.get("key1")
    assert val == "value1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_redis_incr():
    """Test fake Redis increment."""
    redis = FakeRedis()

    count = await redis.incr("counter")
    assert count == 1
    count = await redis.incr("counter")
    assert count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_redis_pubsub():
    """Test fake Redis pub/sub."""
    redis = FakeRedis()

    pubsub = redis.pubsub()
    await pubsub.subscribe("test-channel")

    await redis.publish("test-channel", "hello")

    msg = await pubsub.get_message()
    assert msg is not None
    assert msg["data"] == "hello"


@pytest.mark.unit
def test_demo_mode_settings(demo_mode_settings):
    """Test that demo mode settings are active."""
    assert demo_mode_settings.demo_mode is True
    assert demo_mode_settings.llm_provider == "fake"
    assert demo_mode_settings.vector_store_type == "memory"