import asyncio
import json
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import Transaction, TransactionCreate, TransactionStatus
from backend.db.models import AlertModel, TransactionModel, UserProfileModel
from backend.services.alert_service import alert_service
from backend.services.fraud_detector import fraud_detector
from backend.services.websocket_manager import ws_manager
from backend.utils.config import settings
from backend.data_processing.data_validator import transaction_validator


class TransactionProcessor:
    def __init__(self):
        self.total_processed = 0
        self.total_fraud = 0
        self._processing_times: list[float] = []
        self.metrics_history: list[dict[str, Any]] = []
        self._running = False
        self._task = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._process_metrics())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def process(self, session: AsyncSession, transaction: TransactionCreate) -> dict[str, Any]:
        start_time = time.time()
        user_id = transaction.user_id

        validation_result = transaction_validator.validate(transaction)
        validation_warnings = validation_result.to_dict()

        recent_txs = await self._get_recent_transactions(session, user_id)
        profile = await self._get_user_profile(session, user_id, recent_txs)

        result = fraud_detector.analyze(transaction, profile, recent_txs)

        db_tx = TransactionModel(
            transaction_id=transaction.transaction_id or "",
            user_id=user_id,
            amount=transaction.amount,
            currency=transaction.currency,
            merchant_id=transaction.merchant_id,
            merchant_category=transaction.merchant_category,
            merchant_country=transaction.merchant_country,
            device_id=transaction.device_id,
            ip_address=transaction.ip_address,
            ip_country=transaction.ip_country,
            card_present=transaction.card_present,
            channel=transaction.channel,
            timestamp=transaction.timestamp,
            fraud_score=result.fraud_score,
            risk_level=result.risk_level,
            rule_scores=result.rule_scores,
            ml_score=result.ml_score,
            triggered_rules=result.triggered_rules,
            status=TransactionStatus.FRAUD.value if result.is_fraud else TransactionStatus.APPROVED.value,
            processing_time_ms=result.processing_time_ms,
            features=result.features,
            created_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )

        session.add(db_tx)
        self.total_processed += 1

        await self._update_user_profile(session, user_id, transaction, result)

        processing_time = (time.time() - start_time) * 1000
        self._processing_times.append(processing_time)
        if len(self._processing_times) > 1000:
            self._processing_times = self._processing_times[-1000:]

        alert = None
        if result.is_fraud:
            alert = await alert_service.create_alert(
                session=session,
                transaction=transaction,
                fraud_score=result.fraud_score,
                rule_scores=result.rule_scores,
                ml_score=result.ml_score,
                triggered_rules=result.triggered_rules,
            )
            self.total_fraud += 1

        tx_dict = {
            "transaction_id": db_tx.transaction_id,
            "user_id": user_id,
            "amount": transaction.amount,
            "fraud_score": result.fraud_score,
            "risk_level": result.risk_level,
            "is_fraud": result.is_fraud,
            "rule_scores": result.rule_scores,
            "ml_score": result.ml_score,
            "triggered_rules": result.triggered_rules,
            "status": TransactionStatus.FRAUD.value if result.is_fraud else TransactionStatus.APPROVED.value,
            "processing_time_ms": result.processing_time_ms,
            "validation_warnings": validation_warnings.get("warnings", []),
        }

        await ws_manager.broadcast_transaction(tx_dict)
        if alert:
            await ws_manager.broadcast_alert(alert)

        return {
            "transaction": tx_dict,
            "fraud_result": result,
            "alert": alert,
        }

    async def get_transaction(self, session: AsyncSession, transaction_id: str) -> dict[str, Any] | None:
        result = await session.execute(select(TransactionModel).where(TransactionModel.transaction_id == transaction_id))
        db_tx = result.scalar_one_or_none()
        if db_tx is None:
            return None
        return self._model_to_dict(db_tx)

    async def get_transactions(
        self,
        session: AsyncSession,
        user_id: str | None = None,
        status: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        query = select(TransactionModel)

        if user_id:
            query = query.where(TransactionModel.user_id == user_id)
        if status:
            query = query.where(TransactionModel.status == status)
        if min_amount is not None:
            query = query.where(TransactionModel.amount >= min_amount)
        if max_amount is not None:
            query = query.where(TransactionModel.amount <= max_amount)
        if start_date:
            query = query.where(TransactionModel.timestamp >= start_date)
        if end_date:
            query = query.where(TransactionModel.timestamp <= end_date)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(TransactionModel.timestamp.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await session.execute(query)
        txs = result.scalars().all()

        return [self._model_to_dict(t) for t in txs], total

    async def get_metrics_summary(self, session: AsyncSession) -> dict[str, Any]:
        alerts, _ = await alert_service.get_alerts(session, page=1, page_size=100000)
        now = datetime.now(timezone.utc)
        alerts_last_24h = [a for a in alerts if a.created_at >= now - timedelta(hours=24)]

        total_tx_result = await session.execute(select(func.count()).select_from(TransactionModel))
        total_transactions = total_tx_result.scalar() or 0

        fraud_count_result = await session.execute(
            select(func.count()).where(TransactionModel.status == TransactionStatus.FRAUD.value)
        )
        total_fraud = fraud_count_result.scalar() or 0

        txs_last_24h_result = await session.execute(
            select(func.count()).where(TransactionModel.timestamp >= now - timedelta(hours=24))
        )
        txs_last_24h = txs_last_24h_result.scalar() or 0

        avg_score_result = await session.execute(select(func.avg(TransactionModel.fraud_score)))
        avg_score = avg_score_result.scalar() or 0.0

        top_rules = await self._get_top_rules(session, 10)

        return {
            "total_transactions": total_transactions,
            "total_alerts": await alert_service.get_alert_count(session),
            "fraud_rate": round(total_fraud / max(total_transactions, 1), 4),
            "avg_fraud_score": round(float(avg_score), 4),
            "alerts_by_severity": await alert_service.get_alerts_by_severity(session),
            "alerts_by_status": await alert_service.get_alerts_by_status(session),
            "top_triggered_rules": top_rules,
            "transactions_last_24h": txs_last_24h,
            "alerts_last_24h": len(alerts_last_24h),
            "avg_processing_time_ms": round(sum(self._processing_times) / max(len(self._processing_times), 1), 2),
        }

    async def get_timeseries(
        self,
        session: AsyncSession,
        metric: str = "transactions",
        granularity: str = "1h",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        start = start_date or (now - timedelta(days=1))
        end = end_date or now

        if granularity == "1m":
            delta = timedelta(minutes=1)
        elif granularity == "5m":
            delta = timedelta(minutes=5)
        elif granularity == "15m":
            delta = timedelta(minutes=15)
        elif granularity == "1h":
            delta = timedelta(hours=1)
        else:
            delta = timedelta(days=1)

        result = await session.execute(select(TransactionModel).where(
            TransactionModel.timestamp >= start,
            TransactionModel.timestamp <= end,
        ).order_by(TransactionModel.timestamp))
        all_txs = result.scalars().all()

        points = []
        current = start
        while current <= end:
            next_slot = current + delta
            count = 0

            for tx in all_txs:
                ts = tx.timestamp
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if current <= ts < next_slot:
                    if metric == "transactions":
                        count += 1
                    elif metric == "alerts":
                        if tx.status == TransactionStatus.FRAUD.value:
                            count += 1
                    elif metric == "fraud_score":
                        score = tx.fraud_score or 0
                        if count == 0:
                            count = score
                        else:
                            count = (count + score) / 2
                    elif metric == "processing_time":
                        count += tx.processing_time_ms or 0

            if metric == "processing_time":
                slot_txs = [t for t in all_txs if current <= (t.timestamp.replace(tzinfo=timezone.utc) if t.timestamp.tzinfo is None else t.timestamp) < next_slot]
                count = round(count / max(len(slot_txs), 1), 2)

            points.append({"timestamp": current.isoformat(), "value": count})
            current = next_slot

        return {"metric": metric, "granularity": granularity, "data": points}

    async def _process_metrics(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _get_recent_transactions(
        self, session: AsyncSession, user_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        result = await session.execute(
            select(TransactionModel)
            .where(TransactionModel.user_id == user_id)
            .order_by(TransactionModel.timestamp.desc())
            .limit(limit)
        )
        return [self._model_to_dict(t) for t in result.scalars().all()]

    async def _get_user_profile(self, session: AsyncSession, user_id: str, recent_txs: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
        result = await session.execute(select(UserProfileModel).where(UserProfileModel.user_id == user_id))
        profile = result.scalar_one_or_none()
        if profile is None:
            return None
        return {
            "user_id": profile.user_id,
            "avg_transaction_amount": profile.avg_transaction_amount or 0.0,
            "std_transaction_amount": profile.std_transaction_amount or 0.0,
            "tx_count_24h": profile.tx_count_24h or 0,
            "tx_count_7d": profile.tx_count_7d or 0,
            "tx_count_30d": profile.tx_count_30d or 0,
            "unique_merchants_30d": profile.unique_merchants_30d or 0,
            "unique_countries_30d": profile.unique_countries_30d or 0,
            "unique_devices_30d": profile.unique_devices_30d or 0,
            "last_tx_timestamp": profile.last_tx_timestamp,
            "last_tx_amount": profile.last_tx_amount,
            "last_tx_country": profile.last_tx_country,
            "last_tx_device": profile.last_tx_device,
            "preferred_channels": profile.preferred_channels or [],
            "preferred_merchants": profile.preferred_merchants or [],
            "preferred_devices": list(set(t.get("device_id") for t in (recent_txs or [])[-100:] if t.get("device_id"))) if recent_txs else [],
            "home_country": profile.home_country,
            "home_city": profile.home_city,
        }

    async def _update_user_profile(
        self,
        session: AsyncSession,
        user_id: str,
        tx: TransactionCreate,
        result: Any,
    ) -> None:
        result_obj = await session.execute(select(UserProfileModel).where(UserProfileModel.user_id == user_id))
        profile = result_obj.scalar_one_or_none()

        recent_txs = await self._get_recent_transactions(session, user_id, limit=100)
        amounts = [float(t.get("amount", 0)) for t in recent_txs if t.get("amount") is not None]

        now = datetime.now(timezone.utc)
        with_tz = lambda ts: ts.replace(tzinfo=timezone.utc) if isinstance(ts, datetime) and ts.tzinfo is None else ts
        all_user_txs = await self._get_recent_transactions(session, user_id, limit=10000)

        avg_amount = sum(amounts) / max(len(amounts), 1) if amounts else 0.0
        std_amount = (sum((a - avg_amount) ** 2 for a in amounts) / max(len(amounts), 1)) ** 0.5 if len(amounts) > 1 else 0.0
        tx_count_24h = sum(1 for t in all_user_txs if with_tz(t.get("timestamp", now)) >= now - timedelta(hours=24))
        tx_count_7d = sum(1 for t in all_user_txs if with_tz(t.get("timestamp", now)) >= now - timedelta(days=7))
        tx_count_30d = sum(1 for t in all_user_txs if with_tz(t.get("timestamp", now)) >= now - timedelta(days=30))
        unique_merchants = len(set(t.get("merchant_id") for t in all_user_txs[-100:] if t.get("merchant_id")))
        unique_countries = len(set(t.get("merchant_country") for t in all_user_txs[-100:] if t.get("merchant_country")))
        unique_devices = len(set(t.get("device_id") for t in all_user_txs[-100:] if t.get("device_id")))
        channels = list(set(t.get("channel") for t in all_user_txs[-100:] if t.get("channel")))
        merchants = list(set(t.get("merchant_id") for t in all_user_txs[-100:] if t.get("merchant_id")))

        if profile is None:
            profile = UserProfileModel(
                user_id=user_id,
                avg_transaction_amount=avg_amount,
                std_transaction_amount=std_amount,
                tx_count_24h=tx_count_24h,
                tx_count_7d=tx_count_7d,
                tx_count_30d=tx_count_30d,
                unique_merchants_30d=unique_merchants,
                unique_countries_30d=unique_countries,
                unique_devices_30d=unique_devices,
                last_tx_timestamp=tx.timestamp,
                last_tx_amount=tx.amount,
                last_tx_country=tx.merchant_country,
                last_tx_device=tx.device_id,
                preferred_channels=channels,
                preferred_merchants=merchants,
                home_country=tx.merchant_country,
                updated_at=now,
            )
            session.add(profile)
        else:
            profile.avg_transaction_amount = avg_amount
            profile.std_transaction_amount = std_amount
            profile.tx_count_24h = tx_count_24h
            profile.tx_count_7d = tx_count_7d
            profile.tx_count_30d = tx_count_30d
            profile.unique_merchants_30d = unique_merchants
            profile.unique_countries_30d = unique_countries
            profile.unique_devices_30d = unique_devices
            profile.last_tx_timestamp = tx.timestamp
            profile.last_tx_amount = tx.amount
            profile.last_tx_country = tx.merchant_country
            profile.last_tx_device = tx.device_id
            profile.preferred_channels = channels
            profile.preferred_merchants = merchants
            if profile.home_country is None:
                profile.home_country = tx.merchant_country
            profile.updated_at = now

        await session.flush()

    async def _get_top_rules(self, session: AsyncSession, n: int = 10) -> dict[str, int]:
        result = await session.execute(
            select(TransactionModel.triggered_rules).where(TransactionModel.triggered_rules.isnot(None))
        )
        rule_counts = defaultdict(int)
        for row in result:
            rules = row[0] or []
            for rule in rules:
                rule_counts[rule] += 1
        return dict(sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:n])

    @staticmethod
    def _model_to_dict(db_tx: TransactionModel) -> dict[str, Any]:
        return {
            "transaction_id": db_tx.transaction_id,
            "user_id": db_tx.user_id,
            "amount": db_tx.amount,
            "currency": db_tx.currency,
            "merchant_id": db_tx.merchant_id,
            "merchant_category": db_tx.merchant_category,
            "merchant_country": db_tx.merchant_country,
            "device_id": db_tx.device_id,
            "ip_address": db_tx.ip_address,
            "ip_country": db_tx.ip_country,
            "card_present": db_tx.card_present,
            "channel": db_tx.channel,
            "timestamp": db_tx.timestamp,
            "fraud_score": db_tx.fraud_score,
            "risk_level": db_tx.risk_level,
            "is_fraud": db_tx.status == TransactionStatus.FRAUD.value,
            "rule_scores": db_tx.rule_scores or {},
            "ml_score": db_tx.ml_score,
            "triggered_rules": db_tx.triggered_rules or [],
            "status": db_tx.status,
            "processing_time_ms": db_tx.processing_time_ms,
            "features": db_tx.features or {},
            "created_at": db_tx.created_at,
            "processed_at": db_tx.processed_at,
        }


transaction_processor = TransactionProcessor()
