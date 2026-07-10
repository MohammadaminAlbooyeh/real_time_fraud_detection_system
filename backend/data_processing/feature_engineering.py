import math
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

from backend.api.schemas import TransactionCreate, UserProfile
from backend.utils.config import settings


class FeatureEngineer:
    def __init__(self):
        self.high_risk_countries = set(settings.RULE_HIGH_RISK_COUNTRIES)
        self.high_risk_mcc = {
            "4829", "5962", "5966", "5967", "5993", "6051", "7995",
        }

    def extract_features(
        self,
        transaction: TransactionCreate,
        user_profile: UserProfile | None = None,
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
        profile: UserProfile | None,
        recent_txs: list[dict[str, Any]] | None,
    ) -> dict[str, float]:
        amount = float(tx.amount)
        features = {"amount": amount}

        if profile and profile.avg_transaction_amount > 0:
            features["amount_deviation"] = (
                amount - profile.avg_transaction_amount
            ) / max(profile.std_transaction_amount, 1.0)
            features["amount_zscore"] = features["amount_deviation"]
            features["amount_ratio_to_avg"] = amount / max(profile.avg_transaction_amount, 1.0)

            if recent_txs:
                recent_amounts = [float(t.get("amount", 0)) for t in recent_txs[-100:]]
                if recent_amounts:
                    features["amount_percentile"] = self._percentile(amount, recent_amounts)
                else:
                    features["amount_percentile"] = 0.5
            else:
                features["amount_percentile"] = 0.5
        else:
            features["amount_deviation"] = 0.0
            features["amount_zscore"] = 0.0
            features["amount_ratio_to_avg"] = 1.0
            features["amount_percentile"] = 0.5

        features["log_amount"] = math.log1p(amount)
        features["round_amount"] = 1.0 if amount == round(amount) and amount >= 10 else 0.0

        return features

    def _velocity_features(
        self,
        tx: TransactionCreate,
        recent_txs: list[dict[str, Any]] | None,
    ) -> dict[str, float]:
        now = tx.timestamp
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        features = {
            "tx_count_1h": 0.0,
            "tx_count_24h": 0.0,
            "tx_count_7d": 0.0,
            "amount_sum_1h": 0.0,
            "amount_sum_24h": 0.0,
            "amount_sum_7d": 0.0,
            "velocity_1h": 0.0,
            "velocity_24h": 0.0,
        }

        if not recent_txs:
            return features

        windows = [
            ("1h", timedelta(hours=1)),
            ("24h", timedelta(hours=24)),
            ("7d", timedelta(days=7)),
        ]

        for window_name, window_delta in windows:
            cutoff = now - window_delta
            window_txs = [
                t for t in recent_txs
                if self._parse_timestamp(t.get("timestamp")) >= cutoff
            ]

            count = len(window_txs)
            amount_sum = sum(float(t.get("amount", 0)) for t in window_txs)

            features[f"tx_count_{window_name}"] = float(count)
            features[f"amount_sum_{window_name}"] = amount_sum

            if window_name == "1h":
                features["velocity_1h"] = float(count)
            elif window_name == "24h":
                features["velocity_24h"] = float(count) / 24.0

        return features

    def _merchant_features(
        self,
        tx: TransactionCreate,
        profile: UserProfile | None,
        recent_txs: list[dict[str, Any]] | None,
    ) -> dict[str, float]:
        features = {}

        if recent_txs:
            window_1h = self._get_window_txs(recent_txs, tx.timestamp, timedelta(hours=1))
            window_24h = self._get_window_txs(recent_txs, tx.timestamp, timedelta(hours=24))

            features["unique_merchants_1h"] = float(len(set(t.get("merchant_id") for t in window_1h)))
            features["unique_merchants_24h"] = float(len(set(t.get("merchant_id") for t in window_24h)))

            merchant_txs = [t for t in recent_txs if t.get("merchant_id") == tx.merchant_id]
            features["merchant_tx_count_30d"] = float(len(merchant_txs))
            features["merchant_amount_avg_30d"] = float(
                np.mean([float(t.get("amount", 0)) for t in merchant_txs]) if merchant_txs else 0
            )
        else:
            features["unique_merchants_1h"] = 0.0
            features["unique_merchants_24h"] = 0.0
            features["merchant_tx_count_30d"] = 0.0
            features["merchant_amount_avg_30d"] = 0.0

        features["new_merchant"] = 1.0 if (
            not profile or tx.merchant_id not in (profile.preferred_merchants or [])
        ) else 0.0

        features["merchant_risk_score"] = 1.0 if tx.merchant_category in self.high_risk_mcc else 0.0

        return features

    def _geographic_features(
        self,
        tx: TransactionCreate,
        profile: UserProfile | None,
    ) -> dict[str, float]:
        features = {}

        features["country_risk_score"] = 1.0 if tx.merchant_country in self.high_risk_countries else 0.0
        features["ip_country_risk_score"] = 1.0 if tx.ip_country in self.high_risk_countries else 0.0

        if recent_txs := getattr(tx, "_recent_txs", None):
            window_24h = self._get_window_txs(recent_txs, tx.timestamp, timedelta(hours=24))
            features["unique_countries_24h"] = float(
                len(set(t.get("merchant_country") for t in window_24h))
            )
        else:
            features["unique_countries_24h"] = 0.0

        features["new_country"] = 1.0 if (
            not profile or tx.merchant_country != profile.home_country
        ) else 0.0

        if profile and profile.home_country and tx.merchant_country != profile.home_country:
            features["distance_from_home_km"] = self._estimate_distance(
                profile.home_country, tx.merchant_country
            )
        else:
            features["distance_from_home_km"] = 0.0

        features["impossible_travel"] = 1.0 if (
            profile and profile.last_tx_timestamp and profile.last_tx_country
            and profile.last_tx_country != tx.merchant_country
            and self._estimate_distance(profile.last_tx_country, tx.merchant_country)
            / max(1, (tx.timestamp - profile.last_tx_timestamp).total_seconds() / 3600)
            > settings.RULE_IMPOSSIBLE_TRAVEL_KM_PER_HOUR
        ) else 0.0

        return features

    def _device_features(
        self,
        tx: TransactionCreate,
        profile: UserProfile | None,
    ) -> dict[str, float]:
        features = {}

        if recent_txs := getattr(tx, "_recent_txs", None):
            window_24h = self._get_window_txs(recent_txs, tx.timestamp, timedelta(hours=24))
            features["unique_devices_24h"] = float(
                len(set(t.get("device_id") for t in window_24h))
            )
        else:
            features["unique_devices_24h"] = 0.0

        features["new_device"] = 1.0 if (
            not profile or tx.device_id not in (profile.preferred_channels or [])
        ) else 0.0

        features["device_risk_score"] = 0.0

        return features

    def _behavioral_features(
        self,
        tx: TransactionCreate,
        profile: UserProfile | None,
        recent_txs: list[dict[str, Any]] | None,
    ) -> dict[str, float]:
        features = {}

        if profile and profile.last_tx_timestamp:
            time_diff = (tx.timestamp - profile.last_tx_timestamp).total_seconds() / 60
            features["time_since_last_tx"] = max(0.0, time_diff)
        else:
            features["time_since_last_tx"] = 1440.0

        if profile:
            features["tx_count_24h_profile"] = float(profile.tx_count_24h)
            features["tx_count_7d_profile"] = float(profile.tx_count_7d)
            features["tx_count_30d_profile"] = float(profile.tx_count_30d)
        else:
            features["tx_count_24h_profile"] = 0.0
            features["tx_count_7d_profile"] = 0.0
            features["tx_count_30d_profile"] = 0.0

        if recent_txs:
            channel_txs = [t for t in recent_txs if t.get("channel") == tx.channel]
            features["channel_tx_count_24h"] = float(len(channel_txs))
            features["channel_amount_sum_24h"] = float(sum(float(t.get("amount", 0)) for t in channel_txs))
        else:
            features["channel_tx_count_24h"] = 0.0
            features["channel_amount_sum_24h"] = 0.0

        return features

    def _risk_score_features(self, tx: TransactionCreate) -> dict[str, float]:
        return {
            "merchant_risk_score": 1.0 if tx.merchant_category in self.high_risk_mcc else 0.0,
            "country_risk_score": 1.0 if tx.merchant_country in self.high_risk_countries else 0.0,
            "channel_risk_score": 0.5 if tx.channel in ["online", "card_not_present"] else 0.1,
        }

    def _structuring_features(
        self,
        tx: TransactionCreate,
        recent_txs: list[dict[str, Any]] | None,
    ) -> dict[str, float]:
        features = {
            "structuring_score": 0.0,
            "round_amount": 1.0 if tx.amount == round(tx.amount) and tx.amount >= 100 else 0.0,
        }

        if not recent_txs:
            return features

        now = tx.timestamp
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        window_1h = self._get_window_txs(recent_txs, now, timedelta(hours=1))
        window_24h = self._get_window_txs(recent_txs, now, timedelta(hours=24))

        recent_amounts = [float(t.get("amount", 0)) for t in window_1h]
        if len(recent_amounts) >= 3:
            amounts_near = sum(1 for a in recent_amounts if abs(a - tx.amount) / max(a, 1) < 0.1)
            if amounts_near >= 3:
                features["structuring_score"] = min(1.0, amounts_near / 10.0)

        return features

    def _get_window_txs(
        self,
        transactions: list[dict[str, Any]],
        reference_time: datetime,
        window: timedelta,
    ) -> list[dict[str, Any]]:
        cutoff = reference_time - window
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)

        return [
            t for t in transactions
            if self._parse_timestamp(t.get("timestamp")) >= cutoff
        ]

    def _parse_timestamp(self, ts: Any) -> datetime:
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                return ts.replace(tzinfo=timezone.utc)
            return ts
        if isinstance(ts, str):
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        return datetime.now(timezone.utc)

    def _percentile(self, value: float, data: list[float]) -> float:
        if not data:
            return 0.5
        sorted_data = sorted(data)
        count = sum(1 for x in sorted_data if x <= value)
        return count / len(sorted_data)

    def _estimate_distance(self, country1: str, country2: str) -> float:
        if country1 == country2:
            return 0.0

        distances = {
            ("US", "CA"): 500, ("US", "MX"): 1000, ("US", "GB"): 5500,
            ("GB", "FR"): 350, ("GB", "DE"): 900, ("FR", "DE"): 500,
            ("CN", "US"): 11000, ("RU", "US"): 8000,
        }

        key = tuple(sorted([country1, country2]))
        return float(distances.get(key, 5000))


feature_engineer = FeatureEngineer()