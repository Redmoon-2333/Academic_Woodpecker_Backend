import pytest
from httpx import AsyncClient


class TestMentor:
    @pytest.mark.asyncio
    async def test_get_suggested_actions(self, client: AsyncClient):
        response = await client.get("/api/mentor/suggested-actions")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]) == 4

    @pytest.mark.asyncio
    async def test_chat(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/mentor/chat",
            headers=auth_headers,
            json={
                "message": "帮我解释一下贝叶斯定理",
                "context": {
                    "weakPoints": ["概率论"],
                    "currentTopic": ["贝叶斯定理"],
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "content" in data["data"]

    @pytest.mark.asyncio
    async def test_history(self, client: AsyncClient, auth_headers: dict):
        # First send a message
        await client.post(
            "/api/mentor/chat",
            headers=auth_headers,
            json={"message": "你好", "context": {}},
        )
        response = await client.get(
            "/api/mentor/history", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    @pytest.mark.asyncio
    async def test_clear_history(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete(
            "/api/mentor/history", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
