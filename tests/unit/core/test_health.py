"""Tests for health endpoints and request ID middleware."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_endpoint():
    """Test basic health endpoint returns expected structure."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data
    assert "request_id" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_readiness_endpoint():
    """Test readiness endpoint returns expected structure."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "version" in data
    assert "database" in data
    assert "redis" in data
    assert "request_id" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_id_header_propagation():
    """Test that request ID is propagated in response headers."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send request with custom request ID
        response = await client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "custom-req-123"}
        )

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "custom-req-123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_id_generated_when_missing():
    """Test that request ID is generated when not provided."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert request_id.startswith("req-")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_id_in_response_body():
    """Test that request ID appears in response body."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "body-req-456"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "body-req-456"