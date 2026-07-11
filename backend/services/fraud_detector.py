import pickle
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort

from backend.api.schemas import FraudResult, TransactionCreate
from backend.data_processing.feature_engineering import feature_engineer
from backend.services.feature_extractor import FeatureExtractor
from backend.services.rule_engine import RuleEngine, RuleResult, rule_engine
from backend.utils.config import settings


class FraudDetector:
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.rule_engine = RuleEngine()
        self.model = None
        self.model_type = None
        self.preprocessor = None
        self.feature_names = None
        self.model_loaded = False
        self.session = None
        self.input_name = None
        self.output_name = None

    def load_model(self, model_path: str | None = None) -> bool:
        path = model_path or settings.MODEL_PATH
        path = Path(path)

        if not path.exists():
            fallback = path.parent / "fraud_model.pkl"
            if fallback.exists():
                path = fallback
            else:
                print(f"Model not found at {path}")
                return False

        try:
            if path.suffix == ".onnx":
                self.session = ort.InferenceSession(str(path))
                self.input_name = self.session.get_inputs()[0].name
                self.output_name = self.session.get_outputs()[0].name
                self.model_type = "onnx"
                self.model_loaded = True
            elif path.suffix == ".pkl":
                with open(path, "rb") as f:
                    data = pickle.load(f)
                self.model = data.get("model")
                self.model_type = data.get("model_type", "xgboost")
                self.feature_names = data.get("feature_names", [])
                self.preprocessor = data.get("preprocessor")
                self.model_loaded = True
            else:
                print(f"Unsupported model format: {path.suffix}")
                return False

            print(f"Model loaded from {path} (type: {self.model_type})")
            return True

        except Exception as e:
            print(f"Failed to load model: {e}")
            return False

    def predict(self, features: np.ndarray) -> float:
        if self.session:
            input_data = features.astype(np.float32)
            outputs = self.session.run([self.output_name], {self.input_name: input_data})
            if outputs[0].shape[1] >= 2:
                return float(outputs[0][0][1])
            return float(outputs[0][0][0])
        if self.model is not None:
            if hasattr(self.model, "predict_proba"):
                proba = self.model.predict_proba(features)
                if proba.shape[1] >= 2:
                    return float(proba[0][1])
                return float(proba[0][0])
            if hasattr(self.model, "decision_function"):
                return float(self.model.decision_function(features)[0])
            return 0.0
        return 0.0

    def analyze(
        self,
        transaction: TransactionCreate,
        user_profile: dict[str, Any] | None = None,
        recent_transactions: list[dict[str, Any]] | None = None,
    ) -> FraudResult:
        start_time = time.time()

        features = self.feature_extractor.extract(transaction, user_profile, recent_transactions)

        rule_results = self.rule_engine.evaluate(transaction, user_profile)
        rule_scores = {r.rule_name: r.score for r in rule_results}
        rule_aggregate = self.rule_engine.get_aggregate_score(rule_results)
        triggered = self.rule_engine.get_triggered_rules(rule_results)

        ml_score = self._predict_ml(features)
        combined_score = self._combine_scores(rule_aggregate, ml_score)

        threshold = settings.MODEL_THRESHOLD
        is_fraud = combined_score >= threshold

        risk_level = self._get_risk_level(combined_score)

        processing_time = (time.time() - start_time) * 1000

        return FraudResult(
            transaction_id=transaction.transaction_id or "",
            fraud_score=round(combined_score, 4),
            risk_level=risk_level,
            is_fraud=is_fraud,
            rule_scores=rule_scores,
            ml_score=ml_score,
            triggered_rules=[r.rule_name for r in triggered],
            features=features,
            processing_time_ms=round(processing_time, 2),
            model_version=settings.MODEL_VERSION,
        )

    def _predict_ml(self, features: dict[str, float]) -> float | None:
        if not self.model_loaded:
            return None

        try:
            feature_vector = self._build_feature_vector(features)
            if feature_vector is None:
                return None

            score = self.predict(feature_vector)
            return round(float(score), 4)
        except Exception as e:
            print(f"ML prediction failed: {e}")
            return None

    def _build_feature_vector(self, features: dict[str, float]) -> np.ndarray | None:
        if self.feature_names:
            values = [features.get(name, 0.0) for name in self.feature_names]
            return np.array([values], dtype=np.float32)
        if self.preprocessor:
            import pandas as pd
            df = pd.DataFrame([features])
            return self.preprocessor.transform(df)
        values = list(features.values())
        return np.array([values], dtype=np.float32)

    def _combine_scores(self, rule_score: float, ml_score: float | None) -> float:
        if ml_score is not None:
            return 0.4 * rule_score + 0.6 * ml_score
        return rule_score

    def _get_risk_level(self, score: float) -> str:
        if score >= 0.8:
            return "critical"
        if score >= 0.6:
            return "high"
        if score >= 0.3:
            return "medium"
        return "low"


fraud_detector = FraudDetector()