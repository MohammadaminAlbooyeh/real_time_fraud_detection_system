from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from backend.api.schemas import TransactionCreate, TransactionStatus
from backend.utils.config import settings


class ValidationResult:
    def __init__(self, is_valid: bool, errors: list[str] = None, warnings: list[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class TransactionValidator:
    HIGH_RISK_MCC_CODES = {
        "4829", "5962", "5966", "5967", "5993", "6051", "7995",
    }

    HIGH_RISK_COUNTRIES = set(settings.RULE_HIGH_RISK_COUNTRIES)

    def __init__(self):
        self.max_amount = 1_000_000.0
        self.min_amount = 0.01

    def validate(self, transaction: TransactionCreate) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        self._validate_required_fields(transaction, result)
        self._validate_amount(transaction, result)
        self._validate_currency(transaction, result)
        self._validate_countries(transaction, result)
        self._validate_timestamp(transaction, result)
        self._validate_ip_address(transaction, result)
        self._validate_device_id(transaction, result)
        self._validate_merchant(transaction, result)

        return result

    def _validate_required_fields(self, tx: TransactionCreate, result: ValidationResult) -> None:
        required_fields = [
            "user_id", "amount", "merchant_id", "merchant_category",
            "merchant_country", "device_id", "ip_address", "ip_country",
        ]
        for field in required_fields:
            value = getattr(tx, field, None)
            if not value or (isinstance(value, str) and not value.strip()):
                result.add_error(f"Missing required field: {field}")

    def _validate_amount(self, tx: TransactionCreate, result: ValidationResult) -> None:
        if tx.amount < self.min_amount:
            result.add_error(f"Amount {tx.amount} is below minimum {self.min_amount}")
        if tx.amount > self.max_amount:
            result.add_error(f"Amount {tx.amount} exceeds maximum {self.max_amount}")

        if tx.amount == round(tx.amount) and tx.amount >= 100:
            result.add_warning(f"Round amount detected: {tx.amount}")

    def _validate_currency(self, tx: TransactionCreate, result: ValidationResult) -> None:
        valid_currencies = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "CNY", "INR", "BRL"}
        if tx.currency not in valid_currencies:
            result.add_warning(f"Uncommon currency: {tx.currency}")

    def _validate_countries(self, tx: TransactionCreate, result: ValidationResult) -> None:
        if tx.merchant_country in self.HIGH_RISK_COUNTRIES:
            result.add_warning(f"High-risk merchant country: {tx.merchant_country}")
        if tx.ip_country in self.HIGH_RISK_COUNTRIES:
            result.add_warning(f"High-risk IP country: {tx.ip_country}")

        if tx.merchant_country != tx.ip_country:
            result.add_warning(f"Country mismatch: merchant={tx.merchant_country}, ip={tx.ip_country}")

    def _validate_timestamp(self, tx: TransactionCreate, result: ValidationResult) -> None:
        now = datetime.now(timezone.utc)
        tx_time = tx.timestamp

        if tx_time.tzinfo is None:
            tx_time = tx_time.replace(tzinfo=timezone.utc)

        time_diff = abs((now - tx_time).total_seconds())
        if time_diff > 86400:
            result.add_warning(f"Transaction timestamp is {time_diff/3600:.1f} hours from now")

        if tx_time > now:
            result.add_error("Transaction timestamp is in the future")

    def _validate_ip_address(self, tx: TransactionCreate, result: ValidationResult) -> None:
        ip = tx.ip_address.strip()
        parts = ip.split(".")
        if len(parts) != 4:
            result.add_error(f"Invalid IP address format: {ip}")
            return

        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    result.add_error(f"Invalid IP address octet: {part}")
                    return
        except ValueError:
            result.add_error(f"Invalid IP address format: {ip}")
            return

        private_ranges = [
            ("10.0.0.0", "10.255.255.255"),
            ("172.16.0.0", "172.31.255.255"),
            ("192.168.0.0", "192.168.255.255"),
        ]
        ip_int = self._ip_to_int(ip)
        for start, end in private_ranges:
            if self._ip_to_int(start) <= ip_int <= self._ip_to_int(end):
                result.add_warning(f"Private IP address detected: {ip}")
                break

    def _validate_device_id(self, tx: TransactionCreate, result: ValidationResult) -> None:
        if len(tx.device_id) < 8:
            result.add_warning(f"Short device ID: {tx.device_id}")

    def _validate_merchant(self, tx: TransactionCreate, result: ValidationResult) -> None:
        if tx.merchant_category in self.HIGH_RISK_MCC_CODES:
            result.add_warning(f"High-risk merchant category: {tx.merchant_category}")

    @staticmethod
    def _ip_to_int(ip: str) -> int:
        parts = ip.split(".")
        return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])


class FraudFeatureValidator:
    def __init__(self):
        self.expected_features = {
            "amount",
            "amount_zscore",
            "amount_percentile",
            "time_since_last_tx",
            "tx_count_1h",
            "tx_count_24h",
            "tx_count_7d",
            "amount_sum_1h",
            "amount_sum_24h",
            "amount_sum_7d",
            "unique_merchants_1h",
            "unique_merchants_24h",
            "unique_countries_24h",
            "unique_devices_24h",
            "merchant_risk_score",
            "country_risk_score",
            "device_risk_score",
            "channel_risk_score",
            "hour_of_day",
            "day_of_week",
            "is_weekend",
            "is_night",
            "distance_from_home_km",
            "velocity_1h",
            "velocity_24h",
            "amount_deviation",
            "new_merchant",
            "new_country",
            "new_device",
            "round_amount",
            "structuring_score",
        }

    def validate_features(self, features: dict[str, float]) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        missing = self.expected_features - set(features.keys())
        if missing:
            result.add_warning(f"Missing features: {missing}")

        extra = set(features.keys()) - self.expected_features
        if extra:
            result.add_warning(f"Unexpected features: {extra}")

        for name, value in features.items():
            if not isinstance(value, (int, float)):
                result.add_error(f"Feature {name} is not numeric: {type(value)}")
            elif isinstance(value, float) and (value != value or value == float("inf") or value == float("-inf")):
                result.add_error(f"Feature {name} has invalid value: {value}")

        return result


transaction_validator = TransactionValidator()
feature_validator = FraudFeatureValidator()