"""Tests for authentication routes and tokens."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.unit
@pytest.mark.asyncio
async def test_demo_token_endpoint():
    """Test getting an access token via demo login."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": "admin@clouddesk.io", "password": "password"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_me_protected_route():
    """Test accessing protected /auth/me route with and without token."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Without token -> 401
        res_no_token = await client.get("/api/v1/auth/me")
        assert res_no_token.status_code == 401

        # Get token first
        token_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "support@clouddesk.io", "password": "password"}
        )
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]

        # With token -> 200
        res_with_token = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_with_token.status_code == 200
        user_data = res_with_token.json()
        assert user_data["sub"] == "support@clouddesk.io"
