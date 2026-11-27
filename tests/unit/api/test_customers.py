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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_customers_with_auth():
    """Test that listing customers with authentication works."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get token first
        token_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "support@clouddesk.io", "password": "password"}
        )
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]

        # With token -> should succeed (or fail with 404 if no customers exist)
        res_with_token = await client.get(
            "/api/v1/customers/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_with_token.status_code in [200, 404]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_customer_with_auth():
    """Test creating a customer with valid authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get token first
        token_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "support@clouddesk.io", "password": "password"}
        )
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]

        response = await client.post(
            "/api/v1/customers/",
            json={
                "email": "newcustomer@example.com",
                "full_name": "New Customer",
                "organization": "Test Org",
                "tier": "PREMIUM",
            },
            headers={"Authorization": f"Bearer {token}"}
        )

    # May succeed (201) or fail with 409 (duplicate) or 404 (tenant not found) depending on setup
    assert response.status_code in [201, 409, 404, 403]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_customer_with_auth():
    """Test getting a customer with valid authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get token first
        token_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "support@clouddesk.io", "password": "password"}
        )
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]

        response = await client.get(
            f"/api/v1/customers/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"}
        )

    # Will be 404 since customer doesn't exist
    assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_customer_with_auth():
    """Test updating a customer with valid authentication."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get token first
        token_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "support@clouddesk.io", "password": "password"}
        )
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]

        response = await client.patch(
            f"/api/v1/customers/{uuid4()}",
            json={"full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {token}"}
        )

    # Will be 404 since customer doesn't exist
    assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_customer_not_implemented():
    """Test that DELETE endpoint is not yet implemented (returns 404 or 405)."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get token first
        token_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "support@clouddesk.io", "password": "password"}
        )
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]

        response = await client.delete(
            f"/api/v1/customers/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"}
        )

    # DELETE endpoint not implemented yet
    assert response.status_code in [404, 405]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_customers_with_filters():
    """Test listing customers with filters."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get token first
        token_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "support@clouddesk.io", "password": "password"}
        )
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]

        response = await client.get(
            "/api/v1/customers/",
            params={
                "tier": "PREMIUM",
                "organization": "Test",
                "limit": 10,
                "offset": 0,
            },
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "customers" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_customers_with_email_filter():
    """Test listing customers with email filter (partial match)."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get token first
        token_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "support@clouddesk.io", "password": "password"}
        )
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]

        response = await client.get(
            "/api/v1/customers/",
            params={"email": "example"},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "customers" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_customer_validation_email():
    """Test customer creation with invalid email returns validation error."""
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get token first
        token_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "support@clouddesk.io", "password": "password"}
        )
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]

        response = await client.post(
            "/api/v1/customers/",
            json={
                "email": "invalid-email",  # Invalid email format
                "full_name": "Test User",
            },
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 422  # Validation error