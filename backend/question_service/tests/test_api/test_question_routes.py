import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_question_by_id_success(async_client):
    # questions.json usually has mock data, assuming id 1 exists and is public or accessible
    response = await async_client.get("/api/v1/questions/1")
    
    # If 1 exists, expect 200. If 404, detailed error.
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "title" in data

@pytest.mark.asyncio
async def test_get_question_by_id_not_found(async_client):
    response = await async_client.get("/api/v1/questions/999999")
    assert response.status_code == 404

