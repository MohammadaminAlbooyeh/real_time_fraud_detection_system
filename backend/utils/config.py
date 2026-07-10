from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "Real-Time Fraud Detection System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # CORS
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: list[str] = Field(default_factory=lambda: ["*"])

    # Database (PostgreSQL)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fraud_detection"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5

    # Kafka (optional - using Redis Streams as alternative)
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TRANSACTIONS_TOPIC: str = "transactions"
    KAFKA_ALERTS_TOPIC: str = "alerts"
    KAFKA_CONSUMER_GROUP: str = "fraud-detector"
    KAFKA_ENABLED: bool = False

    # ML Model
    MODEL_PATH: str = "/app/models/fraud_model.onnx"
    MODEL_VERSION: str = "1.0.0"
    MODEL_THRESHOLD: float = 0.5
    FEATURE_STORE_PATH: str = "/app/models/feature_store.pkl"

    # Feature Engineering
    FEATURE_WINDOW_SIZES: list[int] = Field(default_factory=lambda: [3600, 86400, 604800])  # 1h, 24h, 7d
    VELOCITY_WINDOW_SECONDS: int = 3600
    USER_PROFILE_TTL: int = 86400 * 30  # 30 days

    # Rule Engine
    RULE_VELOCITY_TX_COUNT_THRESHOLD: int = 10
    RULE_VELOCITY_AMOUNT_THRESHOLD: float = 10000.0
    RULE_ROUND_AMOUNT_THRESHOLD: float = 0.01
    RULE_HIGH_RISK_COUNTRIES: list[str] = Field(default_factory=lambda: ["KP", "IR", "SY", "CU", "VE"])
    RULE_IMPOSSIBLE_TRAVEL_SPEED_KMH: float = 1000.0
    RULE_NEW_DEVICE_RISK_SCORE: float = 0.3
    RULE_NEW_LOCATION_RISK_SCORE: float = 0.2
    RULE_STRUCTURING_THRESHOLD: int = 3
    RULE_STRUCTURING_WINDOW_SECONDS: int = 3600

    # Alerting
    ALERT_HIGH_THRESHOLD: float = 0.8
    ALERT_MEDIUM_THRESHOLD: float = 0.5
    ALERT_LOW_THRESHOLD: float = 0.3
    ALERT_DEDUP_WINDOW_SECONDS: int = 300
    ALERT_WEBHOOK_URL: Optional[str] = None
    ALERT_EMAIL_ENABLED: bool = False
    ALERT_EMAIL_SMTP_HOST: str = "smtp.gmail.com"
    ALERT_EMAIL_SMTP_PORT: int = 587
    ALERT_EMAIL_USERNAME: Optional[str] = None
    ALERT_EMAIL_PASSWORD: Optional[str] = None
    ALERT_EMAIL_FROM: str = "alerts@fraud-detection.local"
    ALERT_EMAIL_TO: list[str] = Field(default_factory=list)

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 10000

    # Metrics & Monitoring
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9090
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "fraud-detection"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("FEATURE_WINDOW_SIZES", mode="before")
    @classmethod
    def parse_feature_windows(cls, v: str | list[int]) -> list[int]:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",")]
        return v

    @field_validator("HIGH_RISK_COUNTRIES", mode="before")
    @classmethod
    def parse_high_risk_countries(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [c.strip().upper() for c in v.split(",")]
        return [c.upper() for c in v]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()