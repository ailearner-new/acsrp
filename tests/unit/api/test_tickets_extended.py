"""Extended tests for ticket API routes."""

import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_ticket_requires_auth():
    """Test that updating a ticket requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/tickets/{uuid4()}",
            json={"status": "PROCESSING"}
        )
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assign_ticket_requires_auth():
    """Test that assigning a ticket requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/tickets/{uuid4()}/assign",
            json={"agent_id": str(uuid4())}
        )
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_ticket_message_requires_auth():
    """Test that adding a message to a ticket requires authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/tickets/{uuid4()}/messages",
            json={
                "sender_type": "HUMAN_AGENT",
                "sender_id": "agent@test.com",
                "content": "Test message",
            }
        )
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_websocket_endpoint_exists():
    """Test that WebSocket endpoint is registered."""
    from backend.app.main import app

    # Check if WebSocket route exists in the app
    ws_routes = [r for r in app.routes if hasattr(r, 'path') and '/ws/tickets' in r.path]
    assert len(ws_routes) > 0