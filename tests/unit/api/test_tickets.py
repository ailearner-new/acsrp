"""Tests for ticket API routes."""

import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingest_ticket_requires_auth():
    """Test that ticket ingest requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tickets/ingest",
            json={
                "tenant_id": str(uuid4()),
                "channel": "EMAIL",
                "customer_email": "test@example.com",
                "body": "Test ticket",
            }
        )
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ticket_requires_auth():
    """Test that getting a ticket requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/tickets/{uuid4()}")
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ticket_messages_requires_auth():
    """Test that getting ticket messages requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/tickets/{uuid4()}/messages")
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tickets_requires_auth():
    """Test that listing tickets requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/tickets/")
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agent_action_requires_auth():
    """Test that agent action requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/tickets/{uuid4()}/agent-action",
            json={"action": "accept", "suggestion_id": "test"}
        )
    assert response.status_code == 401