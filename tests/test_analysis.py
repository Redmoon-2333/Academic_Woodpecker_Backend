import pytest
from httpx import AsyncClient


class TestAnalysis:
    @pytest.mark.asyncio
    async def test_upload_file(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/analysis/upload",
            headers=auth_headers,
            files={
                "file": (
                    "test.txt",
                    "高等数学 85分，线性代数 72分，概率论 58分".encode("utf-8"),
                    "text/plain",
                )
            },
            data={"fileType": "成绩单"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "fileId" in data["data"]

    @pytest.mark.asyncio
    async def test_upload_wrong_type(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/analysis/upload",
            headers=auth_headers,
            files={
                "file": ("test.exe", b"fake content", "application/x-msdownload")
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_progress(self, client: AsyncClient, auth_headers: dict):
        # Upload first
        upload_resp = await client.post(
            "/api/analysis/upload",
            headers=auth_headers,
            files={
                "file": ("test.txt", b"test content", "text/plain")
            },
        )
        file_id = upload_resp.json()["data"]["fileId"]

        response = await client.get(
            f"/api/analysis/progress/{file_id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "stage" in data["data"]

    @pytest.mark.asyncio
    async def test_history(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/analysis/history", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "records" in data["data"]
