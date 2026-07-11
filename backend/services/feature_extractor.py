import math
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from backend.api.schemas import FeatureVector, TransactionCreate
from backend.utils.config import settings


class FeatureExtractor:
    def __init__(self):
        self.high_risk_countries = set(settings.RULE_HIGH_RISK_COUNTRIES)
        self.high_risk_mcc = {"4829", "5962", "5966", "5967", "5993", "6051", "7995"}

    def extract(
        self,
        transaction: TransactionCreate,
        user_profile: dict[str, Any] | None = None,
        recent_transactions: list[dict[str, Any]] | None = None,
    ) -> dict[str, float]:
        features = {}
        features.update(self._time_features(transaction.timestamp))
        features.update(self._amount_features(transaction, user_profile, recent_transactions))
        features.update(self._velocity_features(transaction, recent_transactions))
        features.update(self._merchant_features(transaction, user_profile, recent_transactions))
        features.update(self._geographic_features(transaction, user_profile))
        features.update(self._device_features(transaction, user_profile))
        features.update(self._behavioral_features(transaction, user_profile, recent_transactions))
        features.update(self._risk_score_features(transaction))
        features.update(self._structuring_features(transaction, recent_transactions))
        return features

    def extract_for_ml(self, features: dict[str, float]) -> FeatureVector:
        return FeatureVector(
            transaction_id=features.get("transaction_id", ""),
            user_id=features.get("user_id", ""),
            features={k: v for k, v in features.items() if isinstance(v, (int, float))},
            feature_names=[k for k in features if isinstance(features[k], (int, float))],
            timestamp=datetime.now(timezone.utc),
        )

    def _time_features(self, timestamp: datetime) -> dict[str, float]:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        return {
            "hour_of_day": float(hour),
            "day_of_week": float(day_of_week),
            "is_weekend": 1.0 if day_of_week >= 5 else 0.0,
            "is_night": 1.0 if hour < 6 or hour >= 22 else 0.0,
            "is_business_hours": 1.0 if 9 <= hour <= 17 else 0.0,
            "sin_hour": math.sin(2 * math.pi * hour / 24),
            "cos_hour": math.cos(2 * math.pi * hour / 24),
            "sin_day": math.sin(2 * math.pi * day_of_week / 7),
            "cos_day": math.cos(2 * math.pi * day_of_week / 7),
        }

    def _amount_features(
        self,
        tx: TransactionCreate,
        profile: dict[str, Any] | None,
        recent_txs: list[dict[str, Any]] | None,
    ) -> dict[str, float]:
        amount = float(tx.amount)
        features = {"amount": amount, "log_amount": math.log1p(amount)}
        if profile and profile.get("avg_transaction_amount", 0.0) > 0:
            avg_amount = profile.get("avg_transaction_amount", 0.0)
            std_amount = profile.get("std_transaction_amount", 0.0)
            std = max(std_amount, 1.0)
            features["amount_deviation"] = (amount - avg_amount) / std
            features["amount_zscore"] = features["amount_deviation"]
            features["amount_ratio_to_avg"] = amount / max(avg_amount, 1.0)
            if recent_txs:
                amounts = [float(t.get("amount", 0)) for t in recent_txs[-100:]]
                features["amount_percentile"] = sum(1 for a in amounts if a <= amount) / max(len(amounts), 1)
            else:
                features["amount_percentile"] = 0.5
        else:
            features.update({"amount_deviation": 0.0, "amount_zscore": 0.0, "amount_ratio_to_avg": 1.0, "amount_percentile": 0.5})
        features["round_amount"] = 1.0 if amount == round(amount) and amount >= 10 else 0.0
        return features

    def _velocity_features(
        self,
        tx: TransactionCreate,
        recent_txs: list[dict[str, Any]] | None,
    ) -> dict[str, float]:
        features = {"tx_count_1h": 0.0, "tx_count_24h": 0.0, "tx_count_7d": 0.0,
                     "amount_sum_1h": 0.0, "amount_sum_24h": 0.0, "amount_sum_7d": 0.0,
                     "velocity_1h": 0.0, "velocity_24h": 0.0}
        if not recent_txs:
            return features
        now = tx.timestamp
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        windows = [("1h", timedelta(hours=1)), ("24h", timedelta(hours=24)), ("7d", timedelta(days=7))]
        for name, delta in windows:
            cutoff = now - delta
            window_txs = [t for t in recent_txs if self._parse_ts(t.get("timestamp")) >= cutoff]
            count = len(window_txs)
            amount_sum = sum(float(t.get("amount", 0)) for t in window_txs)
            features[f"tx_count_{name}"] = float(count)
            features[f"amount_sum_{name}"] = amount_sum
            if name == "1h":
                features["velocity_1h"] = float(count)
            elif name == "24h":
                features["velocity_24h"] = float(count) / 24.0
        return features

    def _merchant_features(
        self,
        tx: TransactionCreate,
        profile: dict[str, Any] | None,
        recent_txs: list[dict[str, Any]] | None,
    ) -> dict[str, float]:
        features = {"unique_merchants_1h": 0.0, "unique_merchants_24h": 0.0,
                     "merchant_tx_count_30d": 0.0, "merchant_amount_avg_30d": 0.0, "new_merchant": 0.0,
                     "merchant_risk_score": 1.0 if tx.merchant_category in self.high_risk_mcc else 0.0}
        if not recent_txs:
            return features
        now = tx.timestamp
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        window_1h = [t for t in recent_txs if self._parse_ts(t.get("timestamp")) >= now - timedelta(hours=1)]
        window_24h = [t for t in recent_txs if self._parse_ts(t.get("timestamp")) >= now - timedelta(hours=24)]
        features["unique_merchants_1h"] = float(len(set(t.get("merchant_id") for t in window_1h)))
        features["unique_merchants_24h"] = float(len(set(t.get("merchant_id") for t in window_24h)))
        merchant_txs = [t for t in recent_txs if t.get("merchant_id") == tx.merchant_id]
        features["merchant_tx_count_30d"] = float(len(merchant_txs))
        features["merchant_amount_avg_30d"] = float(np.mean([float(t.get("amount", 0)) for t in merchant_txs]) if merchant_txs else 0)
        if profile:
            features["new_merchant"] = 0.0 if tx.merchant_id in (profile.get("preferred_merchants") or []) else 1.0
        return features

    def _geographic_features(
        self,
        tx: TransactionCreate,
        profile: dict[str, Any] | None,
    ) -> dict[str, float]:
        features = {"country_risk_score": 1.0 if tx.merchant_country in self.high_risk_countries else 0.0,
                     "ip_country_risk_score": 1.0 if tx.ip_country in self.high_risk_countries else 0.0,
                     "new_country": 0.0, "distance_from_home_km": 0.0, "impossible_travel": 0.0}
        if profile:
            home_country = profile.get("home_country")
            last_tx_country = profile.get("last_tx_country")
            last_tx_timestamp = profile.get("last_tx_timestamp")
            features["new_country"] = 1.0 if tx.merchant_country != home_country else 0.0
            if home_country and tx.merchant_country != home_country:
                features["distance_from_home_km"] = float(self._approx_distance(home_country, tx.merchant_country))
            if last_tx_country and last_tx_country != tx.merchant_country and last_tx_timestamp:
                time_diff = (tx.timestamp - last_tx_timestamp).total_seconds() / 3600
                if time_diff > 0 and self._approx_distance(last_tx_country, tx.merchant_country) / time_diff > settings.RULE_IMPOSSIBLE_TRAVEL_SPEED_KMH:
                    features["impossible_travel"] = 1.0
        return features

    def _device_features(
        self,
        tx: TransactionCreate,
        profile: dict[str, Any] | None,
    ) -> dict[str, float]:
        new_device = 0.0
        if profile and tx.device_id not in (profile.get("preferred_channels") or []):
            new_device = 1.0
        if not profile:
            new_device = 0.0
        return {"new_device": new_device, "device_risk_score": 0.0}

    def _behavioral_features(
        self,
        tx: TransactionCreate,
        profile: dict[str, Any] | None,
        recent_txs: list[dict[str, Any]] | None,
    ) -> dict[str, float]:
        features = {"time_since_last_tx": 1440.0, "tx_count_24h_profile": 0.0,
                     "tx_count_7d_profile": 0.0, "tx_count_30d_profile": 0.0}
        if profile:
            last_tx_timestamp = profile.get("last_tx_timestamp")
            if last_tx_timestamp:
                features["time_since_last_tx"] = max(0.0, (tx.timestamp - last_tx_timestamp).total_seconds() / 60)
            features["tx_count_24h_profile"] = float(profile.get("tx_count_24h", 0))
            features["tx_count_7d_profile"] = float(profile.get("tx_count_7d", 0))
            features["tx_count_30d_profile"] = float(profile.get("tx_count_30d", 0))
        return features

    def _risk_score_features(self, tx: TransactionCreate) -> dict[str, float]:
        return {"merchant_risk_score": 1.0 if tx.merchant_category in self.high_risk_mcc else 0.0,
                "country_risk_score": 1.0 if tx.merchant_country in self.high_risk_countries else 0.0,
                "channel_risk_score": 0.5 if tx.channel in ("online", "card_not_present") else 0.1}

    def _structuring_features(self, tx: TransactionCreate, recent_txs: list[dict[str, Any]] | None) -> dict[str, float]:
        features = {"structuring_score": 0.0}
        features["round_amount"] = 1.0 if tx.amount == round(tx.amount) and tx.amount >= 100 else 0.0
        if recent_txs:
            now = tx.timestamp
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
            window = [t for t in recent_txs if self._parse_ts(t.get("timestamp")) >= now - timedelta(hours=1)]
            amounts = [float(t.get("amount", 0)) for t in window]
            if len(amounts) >= 3:
                near = sum(1 for a in amounts if abs(a - tx.amount) / max(a, 1) < 0.1)
                if near >= 3:
                    features["structuring_score"] = min(1.0, near / 10.0)
        return features

    def _parse_ts(self, ts: Any) -> datetime:
        if isinstance(ts, datetime):
            return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
        if isinstance(ts, str):
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        return datetime.now(timezone.utc)

    def _approx_distance(self, country1: str, country2: str) -> float:
        if country1 == country2:
            return 0.0
        distances = {
            ("CA", "US"): 500, ("MX", "US"): 1000, ("GB", "US"): 5500,
            ("FR", "GB"): 350, ("DE", "GB"): 900, ("DE", "FR"): 500,
            ("CN", "RU"): 3000, ("KR", "CN"): 1000, ("GB", "RU"): 2500,
            ("CN", "US"): 11000, ("RU", "US"): 8000,
        }
        key = tuple(sorted([country1, country2]))
        return float(distances.get(key, 5000))


feature_extractor = FeatureExtractor()