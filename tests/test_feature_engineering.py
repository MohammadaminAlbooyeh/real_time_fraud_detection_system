from datetime import datetime, timezone

import pytest

from backend.api.schemas import TransactionCreate, UserProfile
from backend.services.feature_extractor import FeatureExtractor


@pytest.fixture
def extractor():
    return FeatureExtractor()


@pytest.fixture
def base_transaction():
    return TransactionCreate(
        user_id="user_1",
        amount=150.00,
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


class TestTimeFeatures:
    def test_hour_of_day_range(self, extractor, base_transaction):
        features = extractor.extract(base_transaction)
        assert 0 <= features["hour_of_day"] <= 23

    def test_day_of_week_range(self, extractor, base_transaction):
        features = extractor.extract(base_transaction)
        assert 0 <= features["day_of_week"] <= 6

    def test_is_weekend_binary(self, extractor, base_transaction):
        features = extractor.extract(base_transaction)
        assert features["is_weekend"] in (0.0, 1.0)

    def test_is_night_binary(self, extractor, base_transaction):
        features = extractor.extract(base_transaction)
        assert features["is_night"] in (0.0, 1.0)


class TestAmountFeatures:
    def test_log_amount_positive(self, extractor, base_transaction):
        features = extractor.extract(base_transaction)
        assert features["log_amount"] > 0

    def test_amount_deviation_zero_no_profile(self, extractor, base_transaction):
        features = extractor.extract(base_transaction)
        assert features["amount_deviation"] == 0.0

    def test_zscore_zero_no_profile(self, extractor, base_transaction):
        features = extractor.extract(base_transaction)
        assert features["amount_zscore"] == 0.0

    def test_amount_percentile_default(self, extractor, base_transaction):
        features = extractor.extract(base_transaction)
        assert features["amount_percentile"] == 0.5

    def test_with_profile(self, extractor, base_transaction):
        profile = UserProfile(
            user_id="user_1",
            avg_transaction_amount=100.0,
            std_transaction_amount=30.0,
            tx_count_24h=5,
            tx_count_7d=20,
            tx_count_30d=80,
            unique_merchants_30d=10,
            unique_countries_30d=2,
            unique_devices_30d=3,
        ).model_dump()
        features = extractor.extract(base_transaction, profile)
        assert features["amount_deviation"] != 0.0
        assert features["amount_zscore"] != 0.0
        assert features["amount_ratio_to_avg"] == 150.0 / 100.0


class TestVelocityFeatures:
    def test_empty_recent_txs(self, extractor, base_transaction):
        features = extractor.extract(base_transaction, recent_transactions=[])
        assert features["tx_count_1h"] == 0.0
        assert features["velocity_1h"] == 0.0

    def test_with_recent_txs(self, extractor, base_transaction):
        recent = [
            {"amount": 50.0, "merchant_id": "m1", "channel": "online", "merchant_country": "US",
             "device_id": "d1", "timestamp": datetime.now(timezone.utc)},
            {"amount": 75.0, "merchant_id": "m1", "channel": "online", "merchant_country": "US",
             "device_id": "d1", "timestamp": datetime.now(timezone.utc)},
        ]
        features = extractor.extract(base_transaction, recent_transactions=recent)
        assert features["tx_count_1h"] >= 2.0


class TestMerchantFeatures:
    def test_new_merchant_defaults_zero_without_profile(self, extractor, base_transaction):
        recent = [{"amount": 50.0, "merchant_id": "old_merchant", "channel": "online", "merchant_country": "US",
                   "device_id": "d1", "timestamp": datetime.now(timezone.utc)}]
        features = extractor.extract(base_transaction, recent_transactions=recent)
        assert features["new_merchant"] == 0.0

    def test_known_merchant(self, extractor, base_transaction):
        profile = UserProfile(
            user_id="user_1",
            avg_transaction_amount=100.0,
            std_transaction_amount=30.0,
            tx_count_24h=5,
            tx_count_7d=20,
            tx_count_30d=80,
            unique_merchants_30d=10,
            unique_countries_30d=2,
            unique_devices_30d=3,
            preferred_merchants=["merchant_1"],
        ).model_dump()
        features = extractor.extract(base_transaction, profile)
        assert features["new_merchant"] == 0.0


class TestGeographicFeatures:
    def test_country_risk_normal(self, extractor, base_transaction):
        features = extractor.extract(base_transaction)
        assert features["country_risk_score"] == 0.0

    def test_high_risk_country(self, extractor, base_transaction):
        tx = TransactionCreate(
            user_id="user_1",
            amount=100.0,
            merchant_id="m1",
            merchant_category="5411",
            merchant_country="KP",
            device_id="dev_12345678",
            ip_address="192.168.1.1",
            ip_country="KP",
            card_present=False,
            channel="online",
            timestamp=datetime.now(timezone.utc),
        )
        features = extractor.extract(tx)
        assert features["country_risk_score"] == 1.0
        assert features["ip_country_risk_score"] == 1.0

    def test_new_country(self, extractor, base_transaction):
        profile = UserProfile(
            user_id="user_1",
            avg_transaction_amount=100.0,
            std_transaction_amount=30.0,
            tx_count_24h=5,
            tx_count_7d=20,
            tx_count_30d=80,
            unique_merchants_30d=10,
            unique_countries_30d=2,
            unique_devices_30d=3,
            home_country="CA",
        ).model_dump()
        features = extractor.extract(base_transaction, profile)
        assert features["new_country"] == 1.0


class TestFeatureCount:
    def test_total_features_count(self, extractor, base_transaction):
        features = extractor.extract(base_transaction)
        assert len(features) > 10


class TestExtractForML:
    def test_extract_for_ml_returns_feature_vector(self, extractor, base_transaction):
        features = extractor.extract(base_transaction)
        fv = extractor.extract_for_ml(features)
        assert fv.feature_names
        assert all(isinstance(v, float) for v in fv.features.values())
