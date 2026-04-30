import pytest
from httpx import AsyncClient


class TestDashboard:
    @pytest.mark.asyncio
    async def test_overview(
        self, client: AsyncClient, auth_headers: dict, seed_knowledge
    ):
        response = await client.get(
            "/api/dashboard/overview", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "knowledgeRate" in data["data"]
        assert "docCount" in data["data"]

    @pytest.mark.asyncio
    async def test_knowledge_graph(
        self, client: AsyncClient, auth_headers: dict, seed_knowledge
    ):
        response = await client.get(
            "/api/dashboard/knowledge-graph", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "nodes" in data["data"]

    @pytest.mark.asyncio
    async def test_knowledge_detail(
        self, client: AsyncClient, auth_headers: dict, seed_knowledge
    ):
        response = await client.get(
            "/api/dashboard/knowledge/101", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["id"] == 101

    @pytest.mark.asyncio
    async def test_knowledge_detail_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get(
            "/api/dashboard/knowledge/99999", headers=auth_headers
        )
        assert response.status_code == 404
