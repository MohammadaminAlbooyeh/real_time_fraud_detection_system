from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from backend.api.schemas import TransactionCreate
from backend.utils.config import settings


class RuleSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RuleResult:
    rule_name: str
    triggered: bool
    score: float
    severity: RuleSeverity
    description: str
    details: dict[str, Any] | None = None


class BaseRule(ABC):
    def __init__(self, name: str, weight: float = 1.0, enabled: bool = True):
        self.name = name
        self.weight = weight
        self.enabled = enabled

    @abstractmethod
    def evaluate(
        self,
        transaction: TransactionCreate,
        context: dict[str, Any] | None = None,
    ) -> RuleResult:
        pass


class VelocityRule(BaseRule):
    def evaluate(
        self,
        transaction: TransactionCreate,
        context: dict[str, Any] | None = None,
    ) -> RuleResult:
        recent_tx_count = (context or {}).get("recent_tx_count_1h", 0)
        recent_amount_sum = (context or {}).get("recent_amount_sum_1h", 0.0)

        score = 0.0
        reasons = []

        if recent_tx_count > settings.RULE_VELOCITY_TX_COUNT_THRESHOLD:
            score = min(1.0, recent_tx_count / (settings.RULE_VELOCITY_TX_COUNT_THRESHOLD * 2))
            reasons.append(f"High tx velocity: {recent_tx_count} in 1h")

        if recent_amount_sum > settings.RULE_VELOCITY_AMOUNT_THRESHOLD:
            amount_score = min(1.0, recent_amount_sum / (settings.RULE_VELOCITY_AMOUNT_THRESHOLD * 2))
            score = max(score, amount_score)
            reasons.append(f"High amount velocity: ${recent_amount_sum:.2f} in 1h")

        triggered = score > 0.3
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score=score,
            severity=RuleSeverity.HIGH if score > 0.7 else RuleSeverity.MEDIUM if score > 0.3 else RuleSeverity.LOW,
            description="; ".join(reasons) if reasons else "Normal velocity",
            details={"tx_count_1h": recent_tx_count, "amount_sum_1h": recent_amount_sum},
        )


class AmountRule(BaseRule):
    def evaluate(
        self,
        transaction: TransactionCreate,
        context: dict[str, Any] | None = None,
    ) -> RuleResult:
        amount = transaction.amount
        user_avg_amount = (context or {}).get("user_avg_amount", 0.0)
        user_std_amount = (context or {}).get("user_std_amount", 0.0)

        score = 0.0
        reasons = []
        z_score = 0.0

        if amount > 10000:
            score = min(1.0, amount / 50000)
            reasons.append(f"Large transaction amount: ${amount:.2f}")

        if amount == round(amount) and amount >= 100:
            score = max(score, 0.3)
            reasons.append(f"Round amount: ${amount:.2f}")

        if user_avg_amount > 0 and user_std_amount > 0:
            z_score = (amount - user_avg_amount) / user_std_amount
            if z_score > 2:
                amount_score = min(1.0, z_score / 5)
                score = max(score, amount_score)
                reasons.append(f"Amount {z_score:.1f} std devs above user average of ${user_avg_amount:.2f}")

        if amount <= 5:
            micro_score = 1.0 - (amount / 5)
            score = max(score, micro_score * 0.5)
            reasons.append(f"Micro-testing amount: ${amount:.2f}")

        triggered = score > 0.3
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score=score,
            severity=RuleSeverity.HIGH if score > 0.7 else RuleSeverity.MEDIUM if score > 0.3 else RuleSeverity.LOW,
            description="; ".join(reasons) if reasons else "Normal amount",
            details={"amount": amount, "user_avg_amount": user_avg_amount, "z_score": z_score},
        )


class GeographicRule(BaseRule):
    def evaluate(
        self,
        transaction: TransactionCreate,
        context: dict[str, Any] | None = None,
    ) -> RuleResult:
        score = 0.0
        reasons = []
        high_risk_countries = set(settings.RULE_HIGH_RISK_COUNTRIES)

        if transaction.merchant_country in high_risk_countries:
            score += 0.4
            reasons.append(f"High-risk merchant country: {transaction.merchant_country}")

        if transaction.ip_country in high_risk_countries:
            score += 0.3
            reasons.append(f"High-risk IP country: {transaction.ip_country}")

        if transaction.merchant_country != transaction.ip_country:
            score += 0.2
            reasons.append(f"Country mismatch: merchant={transaction.merchant_country}, ip={transaction.ip_country}")

        last_tx_country = (context or {}).get("last_tx_country")
        last_tx_time = (context or {}).get("last_tx_timestamp")

        if last_tx_country and last_tx_time and transaction.merchant_country != last_tx_country:
            if last_tx_time.tzinfo is None:
                last_tx_time = last_tx_time.replace(tzinfo=timezone.utc)
            tx_time = transaction.timestamp
            if tx_time.tzinfo is None:
                tx_time = tx_time.replace(tzinfo=timezone.utc)
            time_diff_hours = (tx_time - last_tx_time).total_seconds() / 3600
            if time_diff_hours > 0:
                speed = 5000 / max(time_diff_hours, 0.1)
                if speed > settings.RULE_IMPOSSIBLE_TRAVEL_SPEED_KMH:
                    score += 0.5
                    reasons.append(f"Impossible travel: {last_tx_country} -> {transaction.merchant_country} in {time_diff_hours:.1f}h")

        score = min(1.0, score)
        triggered = score > 0.3
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score=score,
            severity=RuleSeverity.HIGH if score > 0.7 else RuleSeverity.MEDIUM if score > 0.3 else RuleSeverity.LOW,
            description="; ".join(reasons) if reasons else "Normal geography",
            details={"merchant_country": transaction.merchant_country, "ip_country": transaction.ip_country, "last_tx_country": last_tx_country},
        )


class BehavioralRule(BaseRule):
    def evaluate(
        self,
        transaction: TransactionCreate,
        context: dict[str, Any] | None = None,
    ) -> RuleResult:
        score = 0.0
        reasons = []
        known_devices = (context or {}).get("known_devices", [])
        known_channels = (context or {}).get("known_channels", [])
        account_age_days = (context or {}).get("account_age_days", 365)

        if transaction.device_id not in known_devices:
            score += settings.RULE_NEW_DEVICE_RISK_SCORE
            reasons.append("Unknown device")

        if transaction.channel not in known_channels:
            score += 0.15
            reasons.append(f"Unusual channel: {transaction.channel}")

        if account_age_days < 7:
            score += 0.25
            reasons.append("New account (<7 days)")

        score = min(1.0, score)
        triggered = score > 0.3
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score=score,
            severity=RuleSeverity.MEDIUM if score > 0.3 else RuleSeverity.LOW,
            description="; ".join(reasons) if reasons else "Normal behavior",
        )


class StructuringRule(BaseRule):
    def evaluate(
        self,
        transaction: TransactionCreate,
        context: dict[str, Any] | None = None,
    ) -> RuleResult:
        score = 0.0
        reasons = []
        recent_amounts = (context or {}).get("recent_amounts_1h", [])
        structuring_threshold = settings.RULE_VELOCITY_AMOUNT_THRESHOLD / 2

        if transaction.amount > structuring_threshold and transaction.amount >= 5000:
            score += 0.3
            reasons.append(f"Amount ${transaction.amount:.2f} near structuring threshold")
            if recent_amounts:
                similar = sum(1 for a in recent_amounts if a < structuring_threshold and a >= 5000)
                if similar >= settings.RULE_VELOCITY_TX_COUNT_THRESHOLD - 1:
                    score += 0.4
                    reasons.append(f"Multiple structured transactions: {similar + 1} in 1h")

        if transaction.amount > 9000 and transaction.amount < 10000:
            score += 0.2
            reasons.append(f"Amount ${transaction.amount:.2f} just below $10k reporting threshold")

        score = min(1.0, score)
        triggered = score > 0.3
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score=score,
            severity=RuleSeverity.HIGH if score > 0.5 else RuleSeverity.MEDIUM if score > 0.3 else RuleSeverity.LOW,
            description="; ".join(reasons) if reasons else "No structuring detected",
        )


class MerchantRule(BaseRule):
    def evaluate(
        self,
        transaction: TransactionCreate,
        context: dict[str, Any] | None = None,
    ) -> RuleResult:
        score = 0.0
        reasons = []
        high_risk_mcc = {"4829", "5962", "5966", "5967", "5993", "6051", "7995"}

        if transaction.merchant_category in high_risk_mcc:
            score += 0.5
            reasons.append(f"High-risk merchant category: {transaction.merchant_category}")

        known_merchants = (context or {}).get("known_merchants", [])
        if transaction.merchant_id not in known_merchants:
            score += 0.15
            reasons.append("New/unusual merchant")

        score = min(1.0, score)
        triggered = score > 0.3
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score=score,
            severity=RuleSeverity.MEDIUM if score > 0.3 else RuleSeverity.LOW,
            description="; ".join(reasons) if reasons else "Normal merchant",
        )


class ChannelRule(BaseRule):
    def evaluate(
        self,
        transaction: TransactionCreate,
        context: dict[str, Any] | None = None,
    ) -> RuleResult:
        score = 0.0
        reasons = []
        known_channels = (context or {}).get("known_channels", [])

        if not transaction.card_present and transaction.channel == "online" and transaction.amount > 1000:
            score += 0.2
            reasons.append(f"Large CNP transaction: ${transaction.amount:.2f}")

        if transaction.channel == "atm" and transaction.amount > 1000:
            score += 0.3
            reasons.append(f"High ATM withdrawal: ${transaction.amount:.2f}")

        if known_channels and transaction.channel not in known_channels:
            score += 0.3
            reasons.append(f"Unusual channel for user: {transaction.channel}")

        score = min(1.0, score)
        triggered = score > 0.3
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score=score,
            severity=RuleSeverity.MEDIUM if score > 0.3 else RuleSeverity.LOW,
            description="; ".join(reasons) if reasons else "Normal channel",
        )


class RuleEngine:
    def __init__(self):
        self.rules: list[BaseRule] = [
            VelocityRule(name="velocity", weight=1.5),
            AmountRule(name="amount_anomaly", weight=1.2),
            GeographicRule(name="geo_anomaly", weight=1.0),
            BehavioralRule(name="behavioral_anomaly", weight=1.0),
            StructuringRule(name="structuring", weight=1.3),
            MerchantRule(name="merchant_risk", weight=1.0),
            ChannelRule(name="channel_risk", weight=0.8),
        ]

    def evaluate(
        self,
        transaction: TransactionCreate,
        context: dict[str, Any] | None = None,
    ) -> list[RuleResult]:
        results = []
        for rule in self.rules:
            if rule.enabled:
                result = rule.evaluate(transaction, context)
                results.append(result)
        return results

    def get_aggregate_score(self, results: list[RuleResult]) -> float:
        if not results:
            return 0.0
        total_weight = 0.0
        weighted_score = 0.0
        for result in results:
            rule = next((r for r in self.rules if r.name == result.rule_name), None)
            weight = rule.weight if rule else 1.0
            weighted_score += result.score * weight
            total_weight += weight
        return weighted_score / total_weight if total_weight > 0 else 0.0

    def get_triggered_rules(self, results: list[RuleResult], threshold: float = 0.3) -> list[RuleResult]:
        return [r for r in results if r.triggered and r.score >= threshold]

    def get_rule_scores_dict(self, results: list[RuleResult]) -> dict[str, float]:
        return {r.rule_name: r.score for r in results}


rule_engine = RuleEngine()