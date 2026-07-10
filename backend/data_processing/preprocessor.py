import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    MinMaxScaler,
    OneHotEncoder,
    RobustScaler,
    StandardScaler,
)

from backend.utils.config import settings


class FeatureSelector(BaseEstimator, TransformerMixin):
    def __init__(self, feature_names: list[str] | None = None):
        self.feature_names = feature_names or []
        self.selected_features_ = []

    def fit(self, X: pd.DataFrame, y: np.ndarray | None = None) -> "FeatureSelector":
        if self.feature_names:
            self.selected_features_ = [f for f in self.feature_names if f in X.columns]
        else:
            self.selected_features_ = list(X.columns)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return X[self.selected_features_]

    def get_feature_names_out(self, input_features: list[str] | None = None) -> np.ndarray:
        return np.array(self.selected_features_)


class OutlierCapper(BaseEstimator, TransformerMixin):
    def __init__(self, factor: float = 3.0):
        self.factor = factor
        self.bounds_ = {}

    def fit(self, X: pd.DataFrame, y: np.ndarray | None = None) -> "OutlierCapper":
        for col in X.select_dtypes(include=[np.number]).columns:
            Q1 = X[col].quantile(0.25)
            Q3 = X[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - self.factor * IQR
            upper = Q3 + self.factor * IQR
            self.bounds_[col] = (lower, upper)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        for col, (lower, upper) in self.bounds_.items():
            if col in X.columns:
                X[col] = X[col].clip(lower, upper)
        return X


class Preprocessor:
    def __init__(self, feature_names: list[str] | None = None):
        self.feature_names = feature_names or []
        self.numeric_features: list[str] = []
        self.categorical_features: list[str] = []
        self.pipeline: Pipeline | None = None
        self.is_fitted = False

    def _identify_feature_types(self, X: pd.DataFrame) -> None:
        self.numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_features = X.select_dtypes(include=["object", "category"]).columns.tolist()

        for cat in self.categorical_features[:]:
            if cat in self.numeric_features:
                self.numeric_features.remove(cat)

    def build_pipeline(self) -> Pipeline:
        numeric_transformer = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("outlier_capper", OutlierCapper(factor=3.0)),
            ("scaler", RobustScaler()),
        ])

        categorical_transformer = Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, self.numeric_features),
                ("cat", categorical_transformer, self.categorical_features),
            ],
            remainder="drop",
            sparse_threshold=0,
        )

        pipeline = Pipeline([
            ("feature_selector", FeatureSelector(self.feature_names)),
            ("preprocessor", preprocessor),
        ])

        return pipeline

    def fit(self, X: pd.DataFrame, y: np.ndarray | None = None) -> "Preprocessor":
        self._identify_feature_types(X)
        self.pipeline = self.build_pipeline()
        self.pipeline.fit(X, y)
        self.is_fitted = True
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Preprocessor not fitted. Call fit() first.")
        return self.pipeline.transform(X)

    def fit_transform(self, X: pd.DataFrame, y: np.ndarray | None = None) -> np.ndarray:
        return self.fit(X, y).transform(X)

    def get_feature_names_out(self) -> list[str]:
        if not self.is_fitted:
            raise ValueError("Preprocessor not fitted.")
        return self.pipeline.get_feature_names_out().tolist()

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "pipeline": self.pipeline,
                "feature_names": self.feature_names,
                "numeric_features": self.numeric_features,
                "categorical_features": self.categorical_features,
                "is_fitted": self.is_fitted,
            }, f)

    @classmethod
    def load(cls, path: str | Path) -> "Preprocessor":
        with open(path, "rb") as f:
            data = pickle.load(f)

        preprocessor = cls(feature_names=data["feature_names"])
        preprocessor.pipeline = data["pipeline"]
        preprocessor.numeric_features = data["numeric_features"]
        preprocessor.categorical_features = data["categorical_features"]
        preprocessor.is_fitted = data["is_fitted"]
        return preprocessor


def create_feature_schema() -> dict[str, Any]:
    return {
        "numeric_features": [
            "amount", "amount_zscore", "amount_percentile", "amount_deviation",
            "amount_ratio_to_avg", "log_amount", "time_since_last_tx",
            "tx_count_1h", "tx_count_24h", "tx_count_7d",
            "amount_sum_1h", "amount_sum_24h", "amount_sum_7d",
            "unique_merchants_1h", "unique_merchants_24h",
            "unique_countries_24h", "unique_devices_24h",
            "merchant_risk_score", "country_risk_score", "device_risk_score",
            "channel_risk_score", "hour_of_day", "day_of_week",
            "distance_from_home_km", "velocity_1h", "velocity_24h",
            "structuring_score",
        ],
        "categorical_features": [
            "merchant_category", "merchant_country", "ip_country",
            "channel", "is_weekend", "is_night", "is_business_hours",
            "new_merchant", "new_country", "new_device", "round_amount",
        ],
        "binary_features": [
            "is_weekend", "is_night", "is_business_hours",
            "new_merchant", "new_country", "new_device", "round_amount",
            "card_present",
        ],
        "target": "is_fraud",
    }


def save_feature_schema(path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(create_feature_schema(), f, indent=2)


def load_feature_schema(path: str | Path) -> dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)