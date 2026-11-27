"""Pytest configuration and fixtures for offline testing."""

import os
import sys
from typing import AsyncGenerator, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from faker import Faker

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set environment variables for offline/demo mode BEFORE importing app modules
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ.setdefault("VECTOR_STORE", "memory")
os.environ.setdefault("USE_FAKE_REDIS", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="session")
def faker() -> Faker:
    """Provide a Faker instance for test data generation."""
    return Faker()


# =============================================================================
# Fake LLM Fixtures
# =============================================================================

class FakeLLMResponse:
    """Mock LLM response."""

    def __init__(self, content: str = "", tool_calls: List[Dict] = None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeLLM:
    """Fake LLM that returns deterministic responses for testing."""

    def __init__(self, responses: Dict[str, str] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = ""

    async def ainvoke(self, prompt: str, **kwargs) -> FakeLLMResponse:
        self.call_count += 1
        self.last_prompt = prompt

        # Return specific response if configured, otherwise generic
        for key, response in self.responses.items():
            if key in prompt:
                return FakeLLMResponse(content=response)

        return FakeLLMResponse(content=f"[Fake LLM Response #{self.call_count}]")

    def invoke(self, prompt: str, **kwargs) -> FakeLLMResponse:
        import asyncio
        return asyncio.run(self.ainvoke(prompt, **kwargs))

    async def abatch(self, prompts: List[str], **kwargs) -> List[FakeLLMResponse]:
        return [await self.ainvoke(p, **kwargs) for p in prompts]


@pytest.fixture
def fake_llm() -> FakeLLM:
    """Provide a fake LLM instance."""
    return FakeLLM()


@pytest.fixture
def fake_llm_with_responses() -> FakeLLM:
    """Provide a fake LLM with predefined responses."""
    return FakeLLM(responses={
        "classify": '{"intent": "billing.refund", "entities": {"amount": 50}}',
        "summarize": "Customer requests refund for $50 charge.",
        "resolve": "I have processed your refund of $50. It will appear in 3-5 business days.",
    })


# =============================================================================
# Fake Vector Store Fixtures
# =============================================================================

class FakeVectorStore:
    """In-memory fake vector store for testing."""

    def __init__(self):
        self.documents: Dict[str, Dict] = {}
        self.collections: Dict[str, Dict] = {"default": {}}

    async def add_documents(self, documents: List[Dict], collection: str = "default") -> List[str]:
        ids = []
        for doc in documents:
            doc_id = doc.get("id") or f"doc-{len(self.collections[collection])}"
            self.collections[collection][doc_id] = {
                "id": doc_id,
                "content": doc.get("content", ""),
                "metadata": doc.get("metadata", {}),
                "embedding": doc.get("embedding", [0.0] * 1536),
            }
            ids.append(doc_id)
        return ids

    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        collection: str = "default",
        filter: Dict = None,
    ) -> List[Dict]:
        # Return first k documents (deterministic for testing)
        docs = list(self.collections[collection].values())
        if filter:
            docs = [d for d in docs if all(d["metadata"].get(k) == v for k, v in filter.items())]
        return docs[:k]

    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        collection: str = "default",
        filter: Dict = None,
    ) -> List[tuple]:
        docs = await self.similarity_search(query, k, collection, filter)
        return [(d, 0.9 - i * 0.1) for i, d in enumerate(docs)]

    async def delete(self, ids: List[str], collection: str = "default") -> None:
        for doc_id in ids:
            self.collections[collection].pop(doc_id, None)

    async def get_by_ids(self, ids: List[str], collection: str = "default") -> List[Dict]:
        return [self.collections[collection][doc_id] for doc_id in ids if doc_id in self.collections[collection]]


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    """Provide a fake vector store instance."""
    return FakeVectorStore()


# =============================================================================
# Fake Redis Fixtures
# =============================================================================

class FakeRedis:
    """In-memory fake Redis for testing."""

    def __init__(self):
        self.data: Dict[str, str] = {}
        self.expire_times: Dict[str, float] = {}
        self.pubsub_channels: Dict[str, List] = {}
        self.subscribers: Dict[str, List] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int = None) -> bool:
        self.data[key] = value
        if ex:
            import time
            self.expire_times[key] = time.time() + ex
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                count += 1
        return count

    async def exists(self, *keys: str) -> int:
        return sum(1 for k in keys if k in self.data)

    async def expire(self, key: str, seconds: int) -> bool:
        if key in self.data:
            import time
            self.expire_times[key] = time.time() + seconds
            return True
        return False

    async def keys(self, pattern: str) -> List[str]:
        import fnmatch
        return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]

    async def incr(self, key: str) -> int:
        val = int(self.data.get(key, 0)) + 1
        self.data[key] = str(val)
        return val

    async def decr(self, key: str) -> int:
        val = int(self.data.get(key, 0)) - 1
        self.data[key] = str(val)
        return val

    # Pub/Sub
    def pubsub(self) -> "FakePubSub":
        return FakePubSub(self)

    async def publish(self, channel: str, message: str) -> int:
        if channel in self.subscribers:
            for sub in self.subscribers[channel]:
                sub.messages.append(message)
        return len(self.subscribers.get(channel, []))


class FakePubSub:
    """Fake pub/sub for testing."""

    def __init__(self, redis: FakeRedis):
        self.redis = redis
        self.channels: List[str] = []

    async def subscribe(self, *channels: str) -> None:
        for channel in channels:
            if channel not in self.redis.subscribers:
                self.redis.subscribers[channel] = []
            self.redis.subscribers[channel].append(self)
            self.channels.append(channel)

    async def unsubscribe(self, *channels: str) -> None:
        for channel in channels:
            if channel in self.redis.subscribers:
                self.redis.subscribers[channel].remove(self)
            if channel in self.channels:
                self.channels.remove(channel)

    async def get_message(self, ignore_subscribe_messages: bool = False) -> dict | None:
        if self.messages:
            return {"type": "message", "channel": self.channels[0], "data": self.messages.pop(0)}
        return None

    def __init__(self, redis: FakeRedis):
        self.redis = redis
        self.channels: List[str] = []
        self.messages: List[str] = []

    async def __aiter__(self):
        return self

    async def __anext__(self):
        msg = await self.get_message()
        if msg:
            return msg
        raise StopAsyncIteration


@pytest.fixture
def fake_redis() -> FakeRedis:
    """Provide a fake Redis instance."""
    return FakeRedis()


# =============================================================================
# Demo Mode Settings Fixture
# =============================================================================

@pytest.fixture(autouse=True)
def demo_mode_settings(monkeypatch):
    """Ensure demo mode settings are active for all tests."""
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("VECTOR_STORE", "memory")
    monkeypatch.setenv("USE_FAKE_REDIS", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    # Reload settings to pick up env vars
    from backend.app.core.config import Settings, get_settings
    get_settings.cache_clear()
    settings = Settings()
    return settings


# =============================================================================
# Async Database Fixtures (for future use)
# =============================================================================

@pytest_asyncio.fixture
async def async_db_session():
    """Async database session for testing (SQLite in-memory)."""
    # This will be implemented when database layer is added
    # For now, return None
    return None


# =============================================================================
# Test Client Fixture
# =============================================================================

@pytest.fixture
def test_client():
    """Provide a test client for the FastAPI app."""
    from httpx import ASGITransport, AsyncClient
    from backend.app.main import app

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client


# =============================================================================
# Auth Fixtures
# =============================================================================

@pytest.fixture
def agent_headers() -> Dict[str, str]:
    """Headers for a Tier 1 agent."""
    return {"Authorization": "Bearer fake-agent-token", "X-Request-ID": "test-req-1"}


@pytest.fixture
def admin_headers() -> Dict[str, str]:
    """Headers for an admin user."""
    return {"Authorization": "Bearer fake-admin-token", "X-Request-ID": "test-req-admin"}


@pytest.fixture
def viewer_headers() -> Dict[str, str]:
    """Headers for a viewer user."""
    return {"Authorization": "Bearer fake-viewer-token", "X-Request-ID": "test-req-viewer"}


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_ticket_data() -> Dict[str, Any]:
    """Sample ticket data for testing."""
    return {
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "channel": "CHAT",
        "customer_email": "customer@example.com",
        "customer_name": "John Doe",
        "subject": "Billing issue",
        "body": "I was charged twice for my subscription.",
        "attachments": [],
        "metadata": {"source_ip": "192.168.1.1"},
    }


@pytest.fixture
def sample_customer_data() -> Dict[str, Any]:
    """Sample customer data for testing."""
    return {
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "email": "customer@example.com",
        "full_name": "John Doe",
        "organization": "Acme Corp",
        "tier": "PREMIUM",
    }


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "demo: Demo mode tests")


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on path."""
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)