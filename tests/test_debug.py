import asyncio
import os
os.environ["PYTHONPATH"] = "/Users/amin/Documents/MyProjects/real_time_fraud_detection_system"

from httpx import ASGITransport, AsyncClient
from backend.main import app


async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tx_data = {
            "user_id": "debug_test_user_1",
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
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")


if __name__ == "__main__":
    asyncio.run(main())
