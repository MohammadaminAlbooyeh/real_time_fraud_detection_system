import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    AlertAcknowledge,
    AlertListResponse,
    AlertUpdate,
    HealthResponse,
    MetricsSummary,
    TimeSeriesResponse,
    Transaction,
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionStatus,
)
from backend.services.alert_service import alert_service
from backend.services.fraud_detector import fraud_detector
from backend.services.transaction_processor import transaction_processor
from backend.services.websocket_manager import ws_manager
from backend.utils.config import settings
from backend.utils.database import get_async_session

router = APIRouter(prefix=settings.API_PREFIX)
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        database="connected",
        redis="not_connected",
        model_loaded=fraud_detector.model_loaded,
        model_version=settings.MODEL_VERSION,
        uptime_seconds=time.time() - _start_time,
    )


@router.post("/transactions", response_model=TransactionResponse)
async def submit_transaction(transaction: TransactionCreate, session: AsyncSession = Depends(get_async_session)):
    try:
        result = await transaction_processor.process(session, transaction)

        tx = result["transaction"]
        alert = result["alert"]

        return TransactionResponse(
            transaction_id=tx["transaction_id"],
            status=tx["status"],
            fraud_score=tx["fraud_score"],
            risk_level=tx["risk_level"],
            rule_scores=tx.get("rule_scores", {}),
            ml_score=tx.get("ml_score"),
            alert_id=alert.alert_id if alert else None,
            message="Transaction processed successfully",
            processing_time_ms=tx["processing_time_ms"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/{transaction_id}", response_model=dict[str, Any])
async def get_transaction(transaction_id: str, session: AsyncSession = Depends(get_async_session)):
    tx = await transaction_processor.get_transaction(session, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    user_id: str | None = Query(None),
    status: str | None = Query(None),
    min_amount: float | None = Query(None),
    max_amount: float | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00")) if start_date else None
    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00")) if end_date else None

    txs, total = await transaction_processor.get_transactions(
        session,
        user_id=user_id, status=status,
        min_amount=min_amount, max_amount=max_amount,
        start_date=start_dt, end_date=end_dt,
        page=page, page_size=page_size,
    )

    return TransactionListResponse(
        transactions=[Transaction(**tx) for tx in txs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    user_id: str | None = Query(None),
    severity: str | None = Query(None),
    status: str | None = Query(None),
    min_fraud_score: float | None = Query(None, ge=0, le=1),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    from backend.api.schemas import AlertSeverity, AlertStatus

    severity_enum = AlertSeverity(severity) if severity else None
    status_enum = AlertStatus(status) if status else None
    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00")) if start_date else None
    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00")) if end_date else None

    alerts, total = await alert_service.get_alerts(
        session,
        user_id=user_id, severity=severity_enum,
        status=status_enum, min_fraud_score=min_fraud_score,
        start_date=start_dt, end_date=end_dt,
        page=page, page_size=page_size,
    )

    return AlertListResponse(
        alerts=alerts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/alerts/{alert_id}", response_model=dict[str, Any])
async def get_alert(alert_id: str, session: AsyncSession = Depends(get_async_session)):
    alert = await alert_service.get_alert(session, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert.model_dump()


@router.post("/alerts/{alert_id}/acknowledge", response_model=dict[str, Any])
async def acknowledge_alert(alert_id: str, body: AlertAcknowledge, session: AsyncSession = Depends(get_async_session)):
    alert = await alert_service.acknowledge_alert(session, alert_id, body.acknowledged_by, body.notes)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert.model_dump()


@router.patch("/alerts/{alert_id}", response_model=dict[str, Any])
async def update_alert(alert_id: str, body: AlertUpdate, session: AsyncSession = Depends(get_async_session)):
    if body.status is None:
        raise HTTPException(status_code=400, detail="Status is required")
    alert = await alert_service.update_alert_status(session, alert_id, body.status, body.resolution_notes)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert.model_dump()


@router.get("/metrics/summary", response_model=MetricsSummary)
async def get_metrics_summary(session: AsyncSession = Depends(get_async_session)):
    return await transaction_processor.get_metrics_summary(session)


@router.get("/metrics/timeseries", response_model=TimeSeriesResponse)
async def get_metrics_timeseries(
    metric: str = Query("transactions", pattern="^(transactions|alerts|fraud_score|processing_time)$"),
    granularity: str = Query("1h", pattern="^(1m|5m|15m|1h|1d)$"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00")) if start_date else None
    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00")) if end_date else None
    result = await transaction_processor.get_timeseries(session, metric, granularity, start_dt, end_dt)
    return TimeSeriesResponse(**result)


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await ws_manager.connect(websocket, "alerts")
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, "alerts")


@router.websocket("/ws/transactions")
async def websocket_transactions(websocket: WebSocket):
    await ws_manager.connect(websocket, "transactions")
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, "transactions")


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    await ws_manager.connect(websocket, "metrics")
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, "metrics")


@router.post("/transactions/batch", response_model=list[TransactionResponse])
async def submit_transactions_batch(transactions: list[TransactionCreate], session: AsyncSession = Depends(get_async_session)):
    results = []
    for tx in transactions:
        result = await transaction_processor.process(session, tx)
        tx_data = result["transaction"]
        alert = result["alert"]
        results.append(TransactionResponse(
            transaction_id=tx_data["transaction_id"],
            status=tx_data["status"],
            fraud_score=tx_data["fraud_score"],
            risk_level=tx_data["risk_level"],
            rule_scores=tx_data.get("rule_scores", {}),
            ml_score=tx_data.get("ml_score"),
            alert_id=alert.alert_id if alert else None,
            message="Transaction processed successfully",
            processing_time_ms=tx_data["processing_time_ms"],
        ))
    return results


@router.get("/metrics/realtime/status")
async def get_realtime_status():
    return {
        "websocket_connections": ws_manager.get_connection_count(),
        "channel_counts": ws_manager.get_channel_counts(),
        "total_transactions_processed": transaction_processor.total_processed,
        "total_alerts_generated": 0,
        "fraud_rate": round(transaction_processor.total_fraud / max(transaction_processor.total_processed, 1), 4),
        "avg_processing_time_ms": round(
            sum(transaction_processor._processing_times) / max(len(transaction_processor._processing_times), 1), 2
        ),
    }


@router.get("/rules")
async def list_rules():
    from backend.services.rule_engine import rule_engine
    return {
        "rules": [
            {
                "name": rule.name,
                "weight": rule.weight,
                "enabled": rule.enabled,
                "type": type(rule).__name__,
            }
            for rule in rule_engine.rules
        ]
    }
