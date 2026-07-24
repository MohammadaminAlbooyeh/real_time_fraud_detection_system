import os

import pytest

pytest.importorskip("playwright.async_api")

from playwright.async_api import async_playwright


@pytest.mark.asyncio
async def test_browser_api_health_smoke():
    base_url = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8000")

    async with async_playwright() as pw:
        request = await pw.request.new_context(base_url=base_url)
        try:
            response = await request.get("/api/v1/health")
            assert response.ok
            data = await response.json()
            assert data["status"] == "healthy"
        finally:
            await request.dispose()
