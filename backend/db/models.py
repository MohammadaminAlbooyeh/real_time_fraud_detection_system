import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.utils.database import Base


class TransactionModel(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(100), primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    merchant_id = Column(String(100), nullable=False)
    merchant_category = Column(String(50), nullable=False)
    merchant_country = Column(String(2), nullable=False)
    device_id = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False)
    ip_country = Column(String(2), nullable=False)
    card_present = Column(Boolean, default=False)
    channel = Column(String(20), nullable=False, default="online")
    timestamp = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    fraud_score = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)
    rule_scores = Column(JSON, nullable=True, default=dict)
    ml_score = Column(Float, nullable=True)
    features = Column(JSON, nullable=True, default=dict)
    triggered_rules = Column(JSON, nullable=True, default=list)
    processing_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    alerts = relationship("AlertModel", back_populates="transaction", cascade="all, delete-orphan")


class AlertModel(Base):
    __tablename__ = "alerts"

    alert_id = Column(String(100), primary_key=True, index=True)
    transaction_id = Column(String(100), ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    fraud_score = Column(Float, nullable=False)
    rule_scores = Column(JSON, nullable=True, default=dict)
    ml_score = Column(Float, nullable=True)
    triggered_rules = Column(JSON, nullable=True, default=list)
    description = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True, default=dict)
    status = Column(String(20), nullable=False, default="open")
    assigned_to = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    transaction = relationship("TransactionModel", back_populates="alerts")


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String(100), primary_key=True, index=True)
    avg_transaction_amount = Column(Float, default=0.0)
    std_transaction_amount = Column(Float, default=0.0)
    tx_count_24h = Column(Integer, default=0)
    tx_count_7d = Column(Integer, default=0)
    tx_count_30d = Column(Integer, default=0)
    unique_merchants_30d = Column(Integer, default=0)
    unique_countries_30d = Column(Integer, default=0)
    unique_devices_30d = Column(Integer, default=0)
    last_tx_timestamp = Column(DateTime(timezone=True), nullable=True)
    last_tx_amount = Column(Float, nullable=True)
    last_tx_country = Column(String(2), nullable=True)
    last_tx_device = Column(String(100), nullable=True)
    preferred_channels = Column(JSON, nullable=True, default=list)
    preferred_merchants = Column(JSON, nullable=True, default=list)
    home_country = Column(String(2), nullable=True)
    home_city = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
