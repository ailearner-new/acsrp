"""Tests for customer API routes."""

import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_customer_requires_auth():
    """Test that creating a customer requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/customers/",
            json={
                "email": "test@example.com",
                "full_name": "Test User",
            }
        )
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_customer_requires_auth():
    """Test that getting a customer requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/customers/{uuid4()}")
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_customer_requires_auth():
    """Test that updating a customer requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/customers/{uuid4()}",
            json={"full_name": "Updated Name"}
        )
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_customers_requires_auth():
    """Test that listing customers requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/customers/")
    assert response.status_code == 401