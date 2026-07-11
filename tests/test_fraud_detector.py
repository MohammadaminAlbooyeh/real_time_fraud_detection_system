from datetime import datetime, timezone

import pytest

from backend.api.schemas import TransactionCreate
from backend.services.rule_engine import (
    VelocityRule,
    AmountRule,
    GeographicRule,
    BehavioralRule,
    StructuringRule,
    MerchantRule,
    ChannelRule,
    RuleEngine,
    RuleSeverity,
)


@pytest.fixture
def normal_transaction():
    return TransactionCreate(
        user_id="user_1",
        amount=50.00,
        merchant_id="merchant_1",
        merchant_category="5411",
        merchant_country="US",
        device_id="dev_12345678",
        ip_address="192.168.1.1",
        ip_country="US",
        card_present=False,
        channel="online",
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def rule_engine():
    return RuleEngine()


class TestVelocityRule:
    def test_normal_velocity(self, normal_transaction):
        rule = VelocityRule(name="velocity")
        result = rule.evaluate(normal_transaction, {"recent_tx_count_1h": 2, "recent_amount_sum_1h": 200.0})
        assert result.score < 0.3
        assert not result.triggered

    def test_high_velocity(self, normal_transaction):
        rule = VelocityRule(name="velocity")
        result = rule.evaluate(normal_transaction, {"recent_tx_count_1h": 20, "recent_amount_sum_1h": 50000.0})
        assert result.score > 0.3
        assert result.triggered

    def test_high_amount_velocity(self, normal_transaction):
        rule = VelocityRule(name="velocity")
        result = rule.evaluate(normal_transaction, {"recent_tx_count_1h": 2, "recent_amount_sum_1h": 50000.0})
        assert result.score > 0.3


class TestAmountRule:
    def test_normal_amount(self, normal_transaction):
        rule = AmountRule(name="amount")
        result = rule.evaluate(normal_transaction, {"user_avg_amount": 45.0, "user_std_amount": 10.0})
        assert not result.triggered

    def test_large_amount(self, normal_transaction):
        tx = normal_transaction.model_copy(update={"amount": 50000.0})
        rule = AmountRule(name="amount")
        result = rule.evaluate(tx, {})
        assert result.triggered
        assert result.score > 0.7

    def test_high_zscore(self, normal_transaction):
        rule = AmountRule(name="amount")
        result = rule.evaluate(normal_transaction, {"user_avg_amount": 10.0, "user_std_amount": 5.0})
        assert result.triggered


class TestGeographicRule:
    def test_normal_geography(self, normal_transaction):
        rule = GeographicRule(name="geo")
        result = rule.evaluate(normal_transaction, {})
        assert not result.triggered

    def test_high_risk_country(self, normal_transaction):
        tx = normal_transaction.model_copy(update={"merchant_country": "KP", "ip_country": "KP"})
        rule = GeographicRule(name="geo")
        result = rule.evaluate(tx, {})
        assert result.triggered
        assert result.score > 0.3

    def test_impossible_travel(self, normal_transaction):
        from datetime import timedelta
        last_time = datetime.now(timezone.utc) - timedelta(hours=1)
        rule = GeographicRule(name="geo")
        result = rule.evaluate(normal_transaction, {
            "last_tx_country": "CN",
            "last_tx_timestamp": last_time,
        })
        assert result.triggered
        assert result.score > 0.3


class TestBehavioralRule:
    def test_normal_behavior(self, normal_transaction):
        rule = BehavioralRule(name="behavioral")
        result = rule.evaluate(normal_transaction, {"known_devices": ["dev_12345678"], "known_channels": ["online"]})
        assert not result.triggered

    def test_unknown_device_and_channel_triggers(self, normal_transaction):
        rule = BehavioralRule(name="behavioral")
        result = rule.evaluate(normal_transaction, {"known_devices": [], "known_channels": []})
        assert round(result.score, 2) == 0.45
        assert result.triggered

    def test_new_account_alone_not_enough(self, normal_transaction):
        rule = BehavioralRule(name="behavioral")
        result = rule.evaluate(normal_transaction, {"known_devices": ["dev_12345678"], "known_channels": ["online"], "account_age_days": 1})
        assert result.score == 0.25
        assert not result.triggered


class TestStructuringRule:
    def test_normal(self, normal_transaction):
        rule = StructuringRule(name="structuring")
        result = rule.evaluate(normal_transaction, {})
        assert not result.triggered

    def test_near_threshold(self, normal_transaction):
        tx = normal_transaction.model_copy(update={"amount": 9500.0})
        rule = StructuringRule(name="structuring")
        result = rule.evaluate(tx, {})
        assert result.triggered


class TestMerchantRule:
    def test_normal_merchant(self, normal_transaction):
        rule = MerchantRule(name="merchant")
        result = rule.evaluate(normal_transaction, {"known_merchants": ["merchant_1"]})
        assert not result.triggered

    def test_high_risk_mcc(self, normal_transaction):
        tx = normal_transaction.model_copy(update={"merchant_category": "7995"})
        rule = MerchantRule(name="merchant")
        result = rule.evaluate(tx, {"known_merchants": ["merchant_1"]})
        assert result.triggered


class TestChannelRule:
    def test_normal_channel(self, normal_transaction):
        rule = ChannelRule(name="channel")
        result = rule.evaluate(normal_transaction, {"known_channels": ["online"]})
        assert not result.triggered

    def test_large_cnp_score(self, normal_transaction):
        tx = normal_transaction.model_copy(update={"amount": 5000.0})
        rule = ChannelRule(name="channel")
        result = rule.evaluate(tx, {"known_channels": ["online"]})
        assert round(result.score, 2) == 0.2
        assert not result.triggered

    def test_large_cnp_with_unusual_channel_triggers(self, normal_transaction):
        tx = normal_transaction.model_copy(update={"amount": 5000.0})
        rule = ChannelRule(name="channel")
        result = rule.evaluate(tx, {"known_channels": ["pos", "atm"]})
        assert result.triggered


class TestRuleEngine:
    def test_evaluate_returns_all_rules(self, rule_engine, normal_transaction):
        results = rule_engine.evaluate(normal_transaction, {})
        assert len(results) == 7

    def test_aggregate_score_range(self, rule_engine, normal_transaction):
        results = rule_engine.evaluate(normal_transaction, {})
        score = rule_engine.get_aggregate_score(results)
        assert 0.0 <= score <= 1.0

    def test_triggered_rules_empty_normal(self, rule_engine, normal_transaction):
        results = rule_engine.evaluate(normal_transaction, {
            "known_devices": ["dev_12345678"],
            "known_channels": ["online"],
            "known_merchants": ["merchant_1"],
        })
        triggered = rule_engine.get_triggered_rules(results)
        assert len(triggered) == 0

    def test_high_risk_triggers_rules(self, rule_engine, normal_transaction):
        tx = normal_transaction.model_copy(update={
            "amount": 50000.0,
            "merchant_country": "KP",
            "ip_country": "KP",
            "merchant_category": "7995",
        })
        results = rule_engine.evaluate(tx, {})
        triggered = rule_engine.get_triggered_rules(results)
        assert len(triggered) > 0


class TestRuleSeverity:
    def test_severity_contains_valid_values(self):
        assert RuleSeverity.LOW.value == "low"
        assert RuleSeverity.MEDIUM.value == "medium"
        assert RuleSeverity.HIGH.value == "high"
        assert RuleSeverity.CRITICAL.value == "critical"
