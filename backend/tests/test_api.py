import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone
from app.models import User, Firewall, UserIPMapping, Group

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["db_connected"] is True
    
@pytest.mark.asyncio
async def test_api_users_not_found(client: AsyncClient):
    response = await client.get("/api/v1/users/unknown_user")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"

@pytest.mark.asyncio
async def test_api_firewalls_not_found(client: AsyncClient):
    response = await client.get(f"/api/v1/firewalls/{uuid4()}")
    assert response.status_code == 404
    
@pytest.mark.asyncio
async def test_search_unknown(client: AsyncClient):
    response = await client.get("/api/v1/search?q=unknown_string")
    assert response.status_code == 200
    assert response.json()["total"] == 0

@pytest.mark.asyncio
async def test_diagnostic_user_invalid(client: AsyncClient):
    response = await client.post("/api/v1/diagnostics/user", json={})
    assert response.status_code == 422
