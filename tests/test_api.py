import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_health_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_rules():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert len(data["rules"]) == 7


@pytest.mark.asyncio
async def test_submit_transaction():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tx_data = {
            "user_id": "api_test_user_1",
            "amount": 150.00,
            "merchant_id": "merchant_1",
            "merchant_category": "5411",
            "merchant_country": "US",
            "device_id": "dev_12345678",
            "ip_address": "192.168.1.1",
            "ip_country": "US",
            "channel": "online",
        }
        response = await client.post("/api/v1/transactions", json=tx_data)
        assert response.status_code == 200
        data = response.json()
        assert "transaction_id" in data
        assert "fraud_score" in data
        assert data["status"] in ("approved", "fraud")


@pytest.mark.asyncio
async def test_submit_invalid_transaction():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/transactions", json={"amount": 100.0})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_transactions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/transactions")
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_get_nonexistent_transaction():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/transactions/nonexistent_id")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_alerts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_metrics_summary():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/metrics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_transactions" in data


@pytest.mark.asyncio
async def test_metrics_timeseries():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/metrics/timeseries",
            params={"metric": "transactions", "granularity": "1h"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "metric" in data
        assert "data" in data


@pytest.mark.asyncio
async def test_realtime_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/metrics/realtime/status")
        assert response.status_code == 200
        data = response.json()
        assert "websocket_connections" in data


@pytest.mark.asyncio
async def test_batch_submission():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        txs = [
            {
                "user_id": "batch_user_api_1",
                "amount": 100.0,
                "merchant_id": "m1",
                "merchant_category": "5411",
                "merchant_country": "US",
                "device_id": "dev_111",
                "ip_address": "192.168.1.1",
                "ip_country": "US",
                "channel": "online",
            },
            {
                "user_id": "batch_user_api_2",
                "amount": 200.0,
                "merchant_id": "m2",
                "merchant_category": "5812",
                "merchant_country": "US",
                "device_id": "dev_222",
                "ip_address": "10.0.0.1",
                "ip_country": "US",
                "channel": "pos",
            },
        ]
        response = await client.post("/api/v1/transactions/batch", json=txs)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
