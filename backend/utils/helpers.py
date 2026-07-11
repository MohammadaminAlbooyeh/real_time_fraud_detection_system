import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np


def generate_transaction_id() -> str:
    return str(uuid.uuid4())


def generate_device_fingerprint(device_id: str) -> str:
    return hashlib.sha256(device_id.encode()).hexdigest()


def hash_ip(ip_address: str) -> str:
    return hashlib.sha256(ip_address.encode()).hexdigest()[:16]


def anonymize_user_id(user_id: str) -> str:
    return f"user_{hashlib.md5(user_id.encode()).hexdigest()[:8]}"


def format_currency(amount: float, currency: str = "USD") -> str:
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
    symbol = symbols.get(currency, "$")
    return f"{symbol}{amount:,.2f}"


def calculate_z_score(value: float, mean: float, std: float, epsilon: float = 1e-6) -> float:
    if std <= epsilon:
        return 0.0
    return (value - mean) / std


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))


def normalize_score(score: float, min_score: float = 0.0, max_score: float = 1.0) -> float:
    return max(min_score, min(max_score, score))


def blend_scores(scores: list[float], weights: list[float] | None = None) -> float:
    if not scores:
        return 0.0
    if weights is None:
        weights = [1.0 / len(scores)] * len(scores)
    weights = np.array(weights) / sum(weights)
    return float(np.dot(scores, weights))


def rolling_window_mean(values: list[float], window: int = 10) -> list[float]:
    if len(values) <= window:
        return [np.mean(values)] * len(values)
    means = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        means.append(float(np.mean(values[start:i + 1])))
    return means


def parse_timestamp(ts: Any) -> datetime:
    if isinstance(ts, datetime):
        return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
    if isinstance(ts, str):
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    return datetime.now(timezone.utc)


def time_since_last_tx(last_tx_time: datetime | None, current_time: datetime | None = None) -> float:
    if last_tx_time is None:
        return float("inf")
    current = current_time or datetime.now(timezone.utc)
    last = last_tx_time.replace(tzinfo=timezone.utc) if last_tx_time.tzinfo is None else last_tx_time
    return (current - last).total_seconds() / 60.0


def ip_to_int(ip: str) -> int:
    parts = ip.split(".")
    return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])


def is_private_ip(ip: str) -> bool:
    try:
        ip_int = ip_to_int(ip)
        private_ranges = [
            (ip_to_int("10.0.0.0"), ip_to_int("10.255.255.255")),
            (ip_to_int("172.16.0.0"), ip_to_int("172.31.255.255")),
            (ip_to_int("192.168.0.0"), ip_to_int("192.168.255.255")),
            (ip_to_int("127.0.0.0"), ip_to_int("127.255.255.255")),
        ]
        return any(start <= ip_int <= end for start, end in private_ranges)
    except (ValueError, IndexError):
        return False


def serialize_datetime(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)