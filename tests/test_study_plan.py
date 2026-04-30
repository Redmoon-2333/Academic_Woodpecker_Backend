import pytest
from httpx import AsyncClient


class TestStudyPlan:
    @pytest.mark.asyncio
    async def test_get_current_plan_no_plan(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get("/api/plan/current", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"] is None

    @pytest.mark.asyncio
    async def test_generate_plan(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/plan/generate",
            headers=auth_headers,
            json={
                "targetDate": "2026-06-30",
                "focusAreas": ["概率论", "算法"],
                "dailyHours": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "planId" in data["data"]

    @pytest.mark.asyncio
    async def test_get_current_plan(self, client: AsyncClient, auth_headers: dict):
        # Generate first
        await client.post(
            "/api/plan/generate",
            headers=auth_headers,
            json={
                "targetDate": "2026-06-30",
                "focusAreas": ["概率论"],
                "dailyHours": 3,
            },
        )
        response = await client.get("/api/plan/current", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"] is not None
