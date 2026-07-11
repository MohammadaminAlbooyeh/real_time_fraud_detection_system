from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    REVIEW = "review"
    FRAUD = "fraud"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class TransactionBase(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100, description="Unique user identifier")
    amount: float = Field(..., gt=0, description="Transaction amount in USD")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO 4217 currency code")
    merchant_id: str = Field(..., min_length=1, max_length=100, description="Merchant identifier")
    merchant_category: str = Field(..., min_length=1, max_length=50, description="Merchant category code")
    merchant_country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    device_id: str = Field(..., min_length=1, max_length=100, description="Device fingerprint")
    ip_address: str = Field(..., description="IP address of the transaction")
    ip_country: str = Field(..., min_length=2, max_length=2, description="Country from IP geolocation")
    card_present: bool = Field(default=False, description="Whether card was physically present")
    channel: str = Field(default="online", pattern="^(online|pos|atm|mobile)$")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("merchant_country", "ip_country", mode="before")
    @classmethod
    def upper_country(cls, v: str) -> str:
        return v.upper()


class TransactionCreate(TransactionBase):
    transaction_id: str = Field(default_factory=lambda: str(uuid4()), description="Transaction ID")


class Transaction(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str
    status: TransactionStatus = TransactionStatus.PENDING
    fraud_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    risk_level: Optional[str] = None
    rule_scores: dict[str, float] = Field(default_factory=dict)
    ml_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    features: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    processed_at: Optional[datetime] = None


class TransactionResponse(BaseModel):
    transaction_id: str
    status: TransactionStatus
    fraud_score: Optional[float] = None
    risk_level: Optional[str] = None
    rule_scores: dict[str, float] = Field(default_factory=dict)
    ml_score: Optional[float] = None
    alert_id: Optional[str] = None
    message: str
    processing_time_ms: float


class TransactionListRequest(BaseModel):
    user_id: Optional[str] = None
    status: Optional[TransactionStatus] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TransactionListResponse(BaseModel):
    transactions: list[Transaction]
    total: int
    page: int
    page_size: int
    total_pages: int


class FraudResult(BaseModel):
    transaction_id: str
    fraud_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: str = Field(..., pattern="^(low|medium|high|critical)$")
    is_fraud: bool
    rule_scores: dict[str, float] = Field(default_factory=dict)
    ml_score: Optional[float] = None
    triggered_rules: list[str] = Field(default_factory=list)
    features: dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: float
    model_version: str


class AlertBase(BaseModel):
    transaction_id: str
    user_id: str
    severity: AlertSeverity
    fraud_score: float = Field(..., ge=0.0, le=1.0)
    rule_scores: dict[str, float] = Field(default_factory=dict)
    ml_score: Optional[float] = None
    triggered_rules: list[str] = Field(default_factory=list)
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlertCreate(AlertBase):
    pass


class Alert(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    alert_id: str
    status: AlertStatus = AlertStatus.OPEN
    assigned_to: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


class AlertAcknowledge(BaseModel):
    acknowledged_by: str
    notes: Optional[str] = None


class AlertListRequest(BaseModel):
    user_id: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    status: Optional[AlertStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_fraud_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AlertListResponse(BaseModel):
    alerts: list[Alert]
    total: int
    page: int
    page_size: int
    total_pages: int


class MetricsSummary(BaseModel):
    total_transactions: int
    total_alerts: int
    fraud_rate: float
    avg_fraud_score: float
    alerts_by_severity: dict[str, int]
    alerts_by_status: dict[str, int]
    top_triggered_rules: dict[str, int]
    transactions_last_24h: int
    alerts_last_24h: int
    avg_processing_time_ms: float


class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    value: float


class TimeSeriesResponse(BaseModel):
    metric: str
    granularity: str
    data: list[TimeSeriesPoint]


class TimeSeriesRequest(BaseModel):
    metric: str = Field(..., pattern="^(transactions|alerts|fraud_score|processing_time)$")
    granularity: str = Field(default="1h", pattern="^(1m|5m|15m|1h|1d)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    model_loaded: bool
    model_version: str
    uptime_seconds: float


class WebSocketMessage(BaseModel):
    type: str = Field(..., pattern="^(alert|transaction|metrics|heartbeat|error)$")
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserProfile(BaseModel):
    user_id: str
    avg_transaction_amount: float
    std_transaction_amount: float
    tx_count_24h: int
    tx_count_7d: int
    tx_count_30d: int
    unique_merchants_30d: int
    unique_countries_30d: int
    unique_devices_30d: int
    last_tx_timestamp: Optional[datetime] = None
    last_tx_amount: Optional[float] = None
    last_tx_country: Optional[str] = None
    last_tx_device: Optional[str] = None
    preferred_channels: list[str] = Field(default_factory=list)
    preferred_merchants: list[str] = Field(default_factory=list)
    home_country: Optional[str] = None
    home_city: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeatureVector(BaseModel):
    transaction_id: str
    user_id: str
    features: dict[str, float]
    feature_names: list[str]
    timestamp: datetime