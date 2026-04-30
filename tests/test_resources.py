import pytest
from httpx import AsyncClient


class TestResources:
    @pytest.mark.asyncio
    async def test_list_resources(self, client: AsyncClient, seed_resources):
        response = await client.get("/api/resources")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["resources"]) >= 2

    @pytest.mark.asyncio
    async def test_resource_detail(self, client: AsyncClient, seed_resources):
        response = await client.get("/api/resources/100")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["title"] == "测试视频"

    @pytest.mark.asyncio
    async def test_search(self, client: AsyncClient, seed_resources):
        response = await client.get("/api/resources/search?keyword=视频")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["resources"]) >= 1

    @pytest.mark.asyncio
    async def test_favorite_toggle(
        self, client: AsyncClient, auth_headers: dict, seed_resources
    ):
        response = await client.post(
            "/api/resources/100/favorite", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["favorited"] is True

    @pytest.mark.asyncio
    async def test_get_favorites(
        self, client: AsyncClient, auth_headers: dict, seed_resources
    ):
        # Toggle favorite first
        await client.post(
            "/api/resources/100/favorite", headers=auth_headers
        )
        response = await client.get(
            "/api/resources/favorites", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["resources"]) >= 1
