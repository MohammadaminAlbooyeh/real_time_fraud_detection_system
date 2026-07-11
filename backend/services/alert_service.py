import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    Alert,
    AlertCreate,
    AlertSeverity,
    AlertStatus,
    TransactionCreate,
)
from backend.db.models import AlertModel
from backend.utils.config import settings


class AlertService:
    def __init__(self):
        self._alert_counter = 0

    async def create_alert(
        self,
        session: AsyncSession,
        transaction: TransactionCreate,
        fraud_score: float,
        rule_scores: dict[str, float],
        ml_score: float | None = None,
        triggered_rules: list[str] | None = None,
    ) -> Alert:
        severity = self._determine_severity(fraud_score)

        description_parts = [f"Fraud score: {fraud_score:.2f}"]
        if triggered_rules:
            description_parts.append(f"Triggered rules: {', '.join(triggered_rules)}")
        if ml_score is not None:
            description_parts.append(f"ML score: {ml_score:.2f}")

        alert_id = str(uuid4())
        now = datetime.now(timezone.utc)

        db_alert = AlertModel(
            alert_id=alert_id,
            transaction_id=transaction.transaction_id or "",
            user_id=transaction.user_id,
            severity=severity.value,
            fraud_score=fraud_score,
            rule_scores=rule_scores,
            ml_score=ml_score,
            triggered_rules=triggered_rules or [],
            description="; ".join(description_parts),
            status=AlertStatus.OPEN.value,
            created_at=now,
            updated_at=now,
        )

        session.add(db_alert)
        await session.flush()

        alert = Alert(
            alert_id=alert_id,
            transaction_id=transaction.transaction_id or "",
            user_id=transaction.user_id,
            severity=severity,
            fraud_score=fraud_score,
            rule_scores=rule_scores,
            ml_score=ml_score,
            triggered_rules=triggered_rules or [],
            description="; ".join(description_parts),
            status=AlertStatus.OPEN,
            created_at=now,
            updated_at=now,
        )

        self._alert_counter += 1
        return alert

    async def get_alert(self, session: AsyncSession, alert_id: str) -> Optional[Alert]:
        result = await session.execute(select(AlertModel).where(AlertModel.alert_id == alert_id))
        db_alert = result.scalar_one_or_none()
        if db_alert is None:
            return None
        return self._model_to_schema(db_alert)

    async def get_alerts(
        self,
        session: AsyncSession,
        user_id: str | None = None,
        severity: AlertSeverity | None = None,
        status: AlertStatus | None = None,
        min_fraud_score: float | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Alert], int]:
        query = select(AlertModel)

        if user_id:
            query = query.where(AlertModel.user_id == user_id)
        if severity:
            query = query.where(AlertModel.severity == severity.value)
        if status:
            query = query.where(AlertModel.status == status.value)
        if min_fraud_score is not None:
            query = query.where(AlertModel.fraud_score >= min_fraud_score)
        if start_date:
            query = query.where(AlertModel.created_at >= start_date)
        if end_date:
            query = query.where(AlertModel.created_at <= end_date)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(AlertModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await session.execute(query)
        db_alerts = result.scalars().all()

        return [self._model_to_schema(a) for a in db_alerts], total

    async def acknowledge_alert(
        self,
        session: AsyncSession,
        alert_id: str,
        acknowledged_by: str,
        notes: str | None = None,
    ) -> Optional[Alert]:
        result = await session.execute(select(AlertModel).where(AlertModel.alert_id == alert_id))
        db_alert = result.scalar_one_or_none()
        if not db_alert:
            return None

        now = datetime.now(timezone.utc)
        db_alert.status = AlertStatus.ACKNOWLEDGED.value
        db_alert.acknowledged_at = now
        db_alert.updated_at = now
        metadata = dict(db_alert.metadata_ or {})
        metadata["acknowledged_by"] = acknowledged_by
        if notes:
            metadata["acknowledgment_notes"] = notes
        db_alert.metadata_ = metadata
        await session.flush()

        return self._model_to_schema(db_alert)

    async def update_alert_status(
        self,
        session: AsyncSession,
        alert_id: str,
        status: AlertStatus,
        resolution_notes: str | None = None,
    ) -> Optional[Alert]:
        result = await session.execute(select(AlertModel).where(AlertModel.alert_id == alert_id))
        db_alert = result.scalar_one_or_none()
        if not db_alert:
            return None

        now = datetime.now(timezone.utc)
        db_alert.status = status.value
        db_alert.updated_at = now

        if status in (AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE):
            db_alert.resolved_at = now
            if resolution_notes:
                db_alert.resolution_notes = resolution_notes

        await session.flush()
        return self._model_to_schema(db_alert)

    async def get_alert_count(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(AlertModel))
        return result.scalar() or 0

    async def get_alerts_by_severity(self, session: AsyncSession) -> dict[str, int]:
        result = await session.execute(
            select(AlertModel.severity, func.count()).group_by(AlertModel.severity)
        )
        counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for severity, count in result:
            counts[severity] = count
        return counts

    async def get_alerts_by_status(self, session: AsyncSession) -> dict[str, int]:
        result = await session.execute(
            select(AlertModel.status, func.count()).group_by(AlertModel.status)
        )
        counts = {}
        for status, count in result:
            counts[status] = count
        return counts

    def _determine_severity(self, fraud_score: float) -> AlertSeverity:
        if fraud_score >= settings.ALERT_HIGH_THRESHOLD:
            return AlertSeverity.CRITICAL if fraud_score >= 0.95 else AlertSeverity.HIGH
        if fraud_score >= settings.ALERT_MEDIUM_THRESHOLD:
            return AlertSeverity.MEDIUM
        return AlertSeverity.LOW

    @staticmethod
    def _model_to_schema(db_alert: AlertModel) -> Alert:
        return Alert(
            alert_id=db_alert.alert_id,
            transaction_id=db_alert.transaction_id,
            user_id=db_alert.user_id,
            severity=AlertSeverity(db_alert.severity),
            fraud_score=db_alert.fraud_score,
            rule_scores=db_alert.rule_scores or {},
            ml_score=db_alert.ml_score,
            triggered_rules=db_alert.triggered_rules or [],
            description=db_alert.description or "",
            metadata=db_alert.metadata_ or {},
            status=AlertStatus(db_alert.status),
            assigned_to=db_alert.assigned_to,
            acknowledged_at=db_alert.acknowledged_at,
            resolved_at=db_alert.resolved_at,
            resolution_notes=db_alert.resolution_notes,
            created_at=db_alert.created_at,
            updated_at=db_alert.updated_at,
        )


alert_service = AlertService()
