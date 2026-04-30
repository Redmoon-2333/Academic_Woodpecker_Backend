import pytest
from httpx import AsyncClient


class TestAuth:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "password": "password123",
                "nickname": "新用户",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["username"] == "newuser"

    @pytest.mark.asyncio
    async def test_register_duplicate(self, client: AsyncClient):
        await client.post(
            "/api/auth/register",
            json={
                "username": "dupuser",
                "password": "password123",
                "nickname": "重复用户",
            },
        )
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "dupuser",
                "password": "password123",
                "nickname": "重复用户2",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        # Register first
        await client.post(
            "/api/auth/register",
            json={
                "username": "loginuser",
                "password": "password123",
                "nickname": "登录用户",
            },
        )
        response = await client.post(
            "/api/auth/login",
            json={"username": "loginuser", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "token" in data["data"]
        assert data["data"]["userInfo"]["username"] == "loginuser"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "wrongpass"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_current_user(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/auth/current-user", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_current_user_no_token(self, client: AsyncClient):
        response = await client.get("/api/auth/current-user")
        assert response.status_code == 401
