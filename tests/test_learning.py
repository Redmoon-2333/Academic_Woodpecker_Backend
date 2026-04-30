"""Tests for learning records API."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_create_learning_record(auth_headers, client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/learning/records", json={
            "resource_id": 1,
            "action": "viewed",
            "duration_seconds": 300,
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["data"]["action"] == "viewed"


@pytest.mark.asyncio
async def test_list_learning_records(auth_headers, client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create one first
        await ac.post("/api/learning/records", json={
            "resource_id": 1,
            "action": "studied",
            "duration_seconds": 600,
        }, headers=auth_headers)

        resp = await ac.get("/api/learning/records", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["data"]["total"] >= 1


@pytest.mark.asyncio
async def test_learning_stats(auth_headers, client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/learning/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert "total_viewed" in data["data"]


@pytest.mark.asyncio
async def test_filter_by_action(auth_headers, client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/learning/records?action=studied", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200


@pytest.mark.asyncio
async def test_learning_record_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/learning/records", json={
            "resource_id": 1,
            "action": "viewed",
        })
        assert resp.status_code == 403
