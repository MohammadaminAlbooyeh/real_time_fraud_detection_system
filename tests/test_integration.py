from datetime import datetime, timezone

import pytest

from backend.api.schemas import FraudResult, TransactionCreate
from backend.db.models import AlertModel, TransactionModel
from backend.utils.database import Base, async_session_maker, engine
from backend.services.alert_service import alert_service
from backend.services.fraud_detector import fraud_detector
from backend.services.transaction_processor import transaction_processor
from backend.utils.redis_client import redis_client


@pytest.fixture(autouse=True)
async def clean_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_transaction_process_persists_transaction_and_alert(monkeypatch):
    tx = TransactionCreate(
        user_id="integration_user_1",
        amount=250.0,
        merchant_id="merchant_1",
        merchant_category="5411",
        merchant_country="US",
        device_id="dev_12345678",
        ip_address="192.168.1.1",
        ip_country="US",
        channel="online",
        timestamp=datetime.now(timezone.utc),
    )

    fake_result = FraudResult(
        transaction_id=tx.transaction_id,
        fraud_score=0.91,
        risk_level="high",
        is_fraud=True,
        rule_scores={"velocity": 0.2},
        ml_score=0.8,
        triggered_rules=["velocity"],
        features={"amount": 250.0},
        processing_time_ms=12.3,
        model_version="test",
    )

    async def fake_noop(*args, **kwargs):
        return None

    monkeypatch.setattr(fraud_detector, "analyze", lambda *args, **kwargs: fake_result)
    monkeypatch.setattr(alert_service, "create_alert", fake_noop)
    monkeypatch.setattr("backend.services.websocket_manager.ws_manager.broadcast_transaction", fake_noop)
    monkeypatch.setattr("backend.services.websocket_manager.ws_manager.broadcast_alert", fake_noop)

    async with async_session_maker() as session:
        result = await transaction_processor.process(session, tx)
        await session.commit()

        db_tx = await transaction_processor.get_transaction(session, tx.transaction_id)
        alerts, total_alerts = await alert_service.get_alerts(session)

    assert result["transaction"]["transaction_id"] == tx.transaction_id
    assert db_tx is not None
    assert db_tx["user_id"] == tx.user_id
    assert db_tx["status"] == "fraud"
    assert total_alerts == 0
    assert alerts == []


@pytest.mark.asyncio
async def test_redis_client_state_transitions(monkeypatch):
    class FakePool:
        async def disconnect(self):
            return None

    class FakeRedis:
        def __init__(self, connection_pool):
            self.connection_pool = connection_pool
            self.closed = False

        async def close(self):
            self.closed = True

    monkeypatch.setattr("backend.utils.redis_client.redis.ConnectionPool.from_url", lambda *args, **kwargs: FakePool())
    monkeypatch.setattr("backend.utils.redis_client.redis.Redis", FakeRedis)

    await redis_client.connect()
    assert redis_client.connected is True
    assert redis_client.client is not None

    await redis_client.disconnect()
    assert redis_client.connected is False
