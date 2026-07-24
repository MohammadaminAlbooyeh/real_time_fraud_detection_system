import json
import os
import pickle
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import mlflow
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
import pandas as pd
import xgboost as xgb
from lightgbm import LGBMClassifier
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.utils.class_weight import compute_class_weight

from backend.data_processing.preprocessor import Preprocessor, create_feature_schema
from backend.ml_models.hyperparameter_tuning import optimize_hyperparameters
from backend.ml_models.model_evaluation import evaluate_model
from backend.utils.config import settings

warnings.filterwarnings("ignore")


def generate_synthetic_data(n_samples: int = 100000, fraud_rate: float = 0.01) -> tuple[pd.DataFrame, pd.Series]:
    np.random.seed(42)

    n_fraud = int(n_samples * fraud_rate)
    n_normal = n_samples - n_fraud

    data = []

    for i in range(n_normal):
        tx = _generate_normal_transaction(i)
        data.append(tx)

    for i in range(n_fraud):
        tx = _generate_fraud_transaction(n_normal + i)
        data.append(tx)

    df = pd.DataFrame(data)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    y = df.pop("is_fraud")
    return df, y


def _generate_normal_transaction(idx: int) -> dict[str, Any]:
    user_id = f"user_{np.random.randint(1, 10000)}"
    base_amount = np.random.lognormal(3.5, 1.2)
    amount = round(max(1.0, min(base_amount, 5000.0)), 2)

    hour = np.random.choice(range(24), p=_hour_distribution())
    timestamp = datetime(2024, 1, 1) + pd.Timedelta(
        days=np.random.randint(0, 365),
        hours=hour,
        minutes=np.random.randint(0, 60),
        seconds=np.random.randint(0, 60),
    )

    return {
        "user_id": user_id,
        "amount": amount,
        "merchant_category": np.random.choice(
            ["5411", "5812", "5999", "4814", "5541", "5311", "5732", "5912", "7230", "8999"],
            p=[0.25, 0.15, 0.12, 0.10, 0.08, 0.08, 0.05, 0.05, 0.06, 0.06],
        ),
        "merchant_country": "US",
        "ip_country": "US",
        "channel": np.random.choice(["online", "pos", "mobile"], p=[0.5, 0.3, 0.2]),
        "device_id": f"dev_{np.random.randint(1, 5000)}",
        "card_present": np.random.choice([True, False], p=[0.3, 0.7]),
        "hour_of_day": hour,
        "day_of_week": timestamp.weekday(),
        "is_fraud": 0,
    }


def _generate_fraud_transaction(idx: int) -> dict[str, Any]:
    fraud_type = np.random.choice(["card_testing", "account_takeover", "merchant_collusion", "stolen_card"])

    if fraud_type == "card_testing":
        amount = round(np.random.uniform(1, 10), 2)
        channel = "online"
        tx_count_1h = np.random.randint(10, 50)
    elif fraud_type == "account_takeover":
        amount = round(np.random.uniform(500, 5000), 2)
        channel = np.random.choice(["online", "mobile"])
        tx_count_1h = np.random.randint(1, 5)
    elif fraud_type == "merchant_collusion":
        amount = round(np.random.uniform(100, 2000), 2)
        channel = "pos"
        tx_count_1h = np.random.randint(1, 10)
    else:
        amount = round(np.random.uniform(50, 3000), 2)
        channel = np.random.choice(["online", "pos"])
        tx_count_1h = np.random.randint(1, 20)

    user_id = f"user_{np.random.randint(1, 10000)}"
    hour = np.random.choice(range(24), p=_hour_distribution(night_bias=0.4))
    timestamp = datetime(2024, 1, 1) + pd.Timedelta(
        days=np.random.randint(0, 365),
        hours=hour,
        minutes=np.random.randint(0, 60),
        seconds=np.random.randint(0, 60),
    )

    return {
        "user_id": user_id,
        "amount": amount,
        "merchant_category": np.random.choice(
            ["5993", "4816", "5962", "5967", "7995", "6051"],
        ),
        "merchant_country": np.random.choice(["CN", "RU", "US", "GB", "DE"]),
        "ip_country": np.random.choice(["CN", "RU", "KP", "IR", "SY", "US"]),
        "channel": channel,
        "device_id": f"dev_{np.random.randint(5001, 10000)}",
        "card_present": False,
        "hour_of_day": hour,
        "day_of_week": timestamp.weekday(),
        "is_fraud": 1,
    }


def _hour_distribution(night_bias: float = 0.1) -> np.ndarray:
    probs = np.ones(24)
    night_hours = list(range(0, 6)) + list(range(22, 24))
    probs[night_hours] *= (1 - night_bias) / len(night_hours)
    day_hours = list(range(6, 22))
    probs[day_hours] *= night_bias / len(day_hours)
    return probs / probs.sum()


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["amount_zscore"] = (df["amount"] - df["amount"].mean()) / (df["amount"].std() + 1e-6)
    df["amount_percentile"] = df["amount"].rank(pct=True)
    df["log_amount"] = np.log1p(df["amount"])

    user_stats = df.groupby("user_id")["amount"].agg(["mean", "std", "count"]).reset_index()
    user_stats.columns = ["user_id", "user_avg_amount", "user_std_amount", "user_tx_count"]
    df = df.merge(user_stats, on="user_id", how="left")

    df["amount_deviation"] = (df["amount"] - df["user_avg_amount"]) / (df["user_std_amount"] + 1e-6)
    df["amount_ratio_to_avg"] = df["amount"] / (df["user_avg_amount"] + 1e-6)

    df["round_amount"] = (df["amount"] == df["amount"].round()).astype(int)
    df["is_night"] = ((df["hour_of_day"] < 6) | (df["hour_of_day"] >= 22)).astype(int)
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["is_business_hours"] = ((df["hour_of_day"] >= 9) & (df["hour_of_day"] <= 17)).astype(int)

    high_risk_mcc = {"4829", "5962", "5966", "5967", "5993", "6051", "7995"}
    high_risk_countries = {"CN", "RU", "KP", "IR", "SY"}

    df["merchant_risk_score"] = df["merchant_category"].apply(lambda x: 1.0 if x in high_risk_mcc else 0.0)
    df["country_risk_score"] = df["merchant_country"].apply(lambda x: 1.0 if x in high_risk_countries else 0.0)
    df["ip_country_risk_score"] = df["ip_country"].apply(lambda x: 1.0 if x in high_risk_countries else 0.0)

    df["country_mismatch"] = (df["merchant_country"] != df["ip_country"]).astype(int)

    return df


def train_model(
    X: pd.DataFrame,
    y: pd.Series,
    model_type: str = "xgboost",
    optimize: bool = True,
    cv_folds: int = 5,
) -> dict[str, Any]:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    preprocessor = Preprocessor()
    X_train_processed = preprocessor.fit_transform(X_train, y_train)
    X_test_processed = preprocessor.transform(X_test)

    feature_names = preprocessor.get_feature_names_out()

    classes = np.unique(y_train)
    class_weights = compute_class_weight("balanced", classes=classes, y=y_train)
    weight_dict = dict(zip(classes, class_weights))

    if model_type == "xgboost":
        if optimize:
            best_params = optimize_hyperparameters(
                X_train_processed, y_train, "xgboost", n_trials=50
            )
            model = xgb.XGBClassifier(
                **best_params,
                scale_pos_weight=weight_dict.get(1, 1) / weight_dict.get(0, 1),
                random_state=42,
                n_jobs=-1,
                eval_metric="aucpr",
            )
        else:
            model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=weight_dict.get(1, 1) / weight_dict.get(0, 1),
                random_state=42,
                n_jobs=-1,
                eval_metric="aucpr",
            )

    elif model_type == "lightgbm":
        if optimize:
            best_params = optimize_hyperparameters(
                X_train_processed, y_train, "lightgbm", n_trials=50
            )
            model = LGBMClassifier(
                **best_params,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
                verbose=-1,
            )
        else:
            model = LGBMClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                num_leaves=31,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
                verbose=-1,
            )

    elif model_type == "random_forest":
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

    elif model_type == "isolation_forest":
        model = IsolationForest(
            n_estimators=200,
            contamination=0.01,
            random_state=42,
            n_jobs=-1,
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    run_id = "none"
    try:
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)
        mlflow.start_run(run_name=f"{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        mlflow.log_param("model_type", model_type)
        mlflow.log_param("train_samples", len(X_train))
        mlflow.log_param("test_samples", len(X_test))
        mlflow.log_param("fraud_rate", y.mean())
        mlflow.log_param("n_features", len(feature_names))
        run_id = mlflow.active_run().info.run_id
    except Exception:
        pass

    if model_type != "isolation_forest":
        model.fit(X_train_processed, y_train)

        y_pred = model.predict(X_test_processed)
        y_proba = model.predict_proba(X_test_processed)[:, 1]

        metrics = evaluate_model(y_test, y_pred, y_proba)

        try:
            preprocessor_path = Path(settings.MODEL_PATH).parent / "preprocessor.pkl"
            preprocessor.save(preprocessor_path)
            for metric_name, metric_value in metrics.items():
                mlflow.log_metric(metric_name, metric_value)
            mlflow.sklearn.log_model(model, "model")
            mlflow.log_artifact(str(preprocessor_path), "preprocessor.pkl")
        except Exception:
            pass

    else:
        model.fit(X_train_processed[y_train == 0])
        anomaly_scores = -model.score_samples(X_test_processed)

        from sklearn.metrics import roc_auc_score, average_precision_score
        metrics = {
            "roc_auc": roc_auc_score(y_test, anomaly_scores),
            "pr_auc": average_precision_score(y_test, anomaly_scores),
        }

        try:
            for metric_name, metric_value in metrics.items():
                mlflow.log_metric(metric_name, metric_value)
            mlflow.sklearn.log_model(model, "model")
            preprocessor_path = Path(settings.MODEL_PATH).parent / "preprocessor.pkl"
            preprocessor.save(preprocessor_path)
            mlflow.log_artifact(str(preprocessor_path), "preprocessor.pkl")
        except Exception:
            pass

    try:
        mlflow.end_run()
    except Exception:
        pass

    model_path = Path(settings.MODEL_PATH).parent / f"{model_type}_model.pkl"
    model_path.parent.mkdir(parents=True, exist_ok=True)

    with open(model_path, "wb") as f:
        pickle.dump({
            "model": model,
            "preprocessor": preprocessor,
            "feature_names": feature_names,
            "model_type": model_type,
            "metrics": metrics,
            "run_id": run_id,
        }, f)

    print(f"Model saved to {model_path}")
    print(f"MLflow run ID: {run_id}")
    print(f"Metrics: {metrics}")

    return {
        "model": model,
        "preprocessor": preprocessor,
        "feature_names": feature_names,
        "metrics": metrics,
        "run_id": run_id,
        "model_path": str(model_path),
    }


def export_to_onnx(model_dict: dict[str, Any], output_path: str | Path) -> str:
    import onnx
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    model = model_dict["model"]
    preprocessor = model_dict["preprocessor"]
    feature_names = model_dict["feature_names"]

    initial_type = [("float_input", FloatTensorType([None, len(feature_names)]))]

    onnx_model = convert_sklearn(
        model,
        initial_types=initial_type,
        target_opset=15,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())

    onnx.save(onnx_model, str(output_path))

    print(f"ONNX model saved to {output_path}")
    return str(output_path)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Train fraud detection models")
    parser.add_argument("--model-type", choices=["xgboost", "lightgbm", "random_forest", "isolation_forest"],
                       default="xgboost", help="Model type to train")
    parser.add_argument("--samples", type=int, default=100000, help="Number of synthetic samples")
    parser.add_argument("--fraud-rate", type=float, default=0.01, help="Fraud rate in synthetic data")
    parser.add_argument("--optimize", action="store_true", help="Run hyperparameter optimization")
    parser.add_argument("--export-onnx", action="store_true", help="Export model to ONNX format")

    args = parser.parse_args()

    print(f"Generating {args.samples} synthetic transactions with {args.fraud_rate:.2%} fraud rate...")
    X, y = generate_synthetic_data(args.samples, args.fraud_rate)

    print("Engineering features...")
    X = engineer_features(X)

    print(f"Training {args.model_type} model...")
    result = train_model(X, y, args.model_type, args.optimize)

    if args.export_onnx and args.model_type != "isolation_forest":
        print("Exporting to ONNX...")
        export_to_onnx(result, settings.MODEL_PATH)

    print("Training complete!")


if __name__ == "__main__":
    main()