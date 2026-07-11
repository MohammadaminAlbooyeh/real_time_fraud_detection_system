import json
import warnings
from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_curve,
)

warnings.filterwarnings("ignore")


def evaluate_model(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None,
    threshold: float = 0.5,
) -> dict[str, float]:
    if y_proba is not None:
        y_pred_binary = (y_proba >= threshold).astype(int)
    else:
        y_pred_binary = y_pred
        y_proba = y_pred

    metrics = {}

    metrics["precision"] = precision_score(y_true, y_pred_binary, zero_division=0)
    metrics["recall"] = recall_score(y_true, y_pred_binary, zero_division=0)
    metrics["f1_score"] = f1_score(y_true, y_pred_binary, zero_division=0)
    metrics["mcc"] = matthews_corrcoef(y_true, y_pred_binary)

    try:
        metrics["roc_auc"] = roc_auc_score(y_true, y_proba)
    except Exception:
        metrics["roc_auc"] = 0.0

    try:
        metrics["pr_auc"] = average_precision_score(y_true, y_proba)
    except Exception:
        metrics["pr_auc"] = 0.0

    try:
        metrics["log_loss"] = log_loss(y_true, y_proba)
    except Exception:
        metrics["log_loss"] = float("inf")

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred_binary).ravel()

    metrics["true_negatives"] = int(tn)
    metrics["false_positives"] = int(fp)
    metrics["false_negatives"] = int(fn)
    metrics["true_positives"] = int(tp)

    metrics["specificity"] = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    metrics["false_positive_rate"] = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    metrics["false_discovery_rate"] = fp / (fp + tp) if (fp + tp) > 0 else 0.0
    metrics["negative_predictive_value"] = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    metrics["accuracy"] = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

    return metrics


def find_optimal_threshold(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    metric: str = "f1",
) -> tuple[float, dict[str, Any]]:
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
    thresholds = np.append(thresholds, 1.0)

    best_threshold = 0.5
    best_score = 0.0

    results = []
    for threshold in np.arange(0.1, 0.95, 0.05):
        y_pred = (y_proba >= threshold).astype(int)

        if metric == "f1":
            score = f1_score(y_true, y_pred, zero_division=0)
        elif metric == "mcc":
            score = matthews_corrcoef(y_true, y_pred)
        elif metric == "youden":
            tpr = recall_score(y_true, y_pred, zero_division=0)
            tnr = 1.0 - (fp := np.sum((y_pred == 1) & (y_true == 0)) / max(np.sum(y_true == 0), 1))
            score = tpr + tnr - 1
        else:
            raise ValueError(f"Unknown metric: {metric}")

        results.append({"threshold": threshold, "score": score, metric: score})

        if score > best_score:
            best_score = score
            best_threshold = threshold

    return best_threshold, {"best_threshold": best_threshold, "best_score": best_score, "results": results}


def evaluate_at_thresholds(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    thresholds: list[float] | None = None,
) -> dict[str, list[dict[str, float]]]:
    if thresholds is None:
        thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    results = []
    for threshold in thresholds:
        y_pred = (y_proba >= threshold).astype(int)
        metrics = evaluate_model(y_true, y_pred, y_proba, threshold)
        metrics["threshold"] = threshold
        results.append(metrics)

    return {"threshold_results": results}


def generate_classification_report(y_true: np.ndarray, y_pred: np.ndarray) -> str:
    return classification_report(y_true, y_pred, zero_division=0)


def get_precision_recall_data(y_true: np.ndarray, y_proba: np.ndarray) -> dict[str, list[float]]:
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
    return {
        "precision": precisions.tolist(),
        "recall": recalls.tolist(),
        "thresholds": np.append(thresholds, 1.0).tolist(),
    }


def get_roc_data(y_true: np.ndarray, y_proba: np.ndarray) -> dict[str, list[float]]:
    fpr, tpr, thresholds = roc_curve(y_true, y_proba)
    return {
        "fpr": fpr.tolist(),
        "tpr": tpr.tolist(),
        "thresholds": thresholds.tolist(),
    }


def print_metrics_summary(metrics: dict[str, Any], title: str = "Model Evaluation") -> None:
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")
    print(f"  {'Metric':<25} {'Value':<10}")
    print(f"  {'-'*35}")

    key_metrics = [
        ("PR-AUC", "pr_auc"),
        ("ROC-AUC", "roc_auc"),
        ("F1 Score", "f1_score"),
        ("Precision", "precision"),
        ("Recall", "recall"),
        ("MCC", "mcc"),
        ("Accuracy", "accuracy"),
        ("Specificity", "specificity"),
        ("Log Loss", "log_loss"),
    ]

    for display_name, key in key_metrics:
        if key in metrics:
            value = metrics[key]
            if isinstance(value, float):
                print(f"  {display_name:<25} {value:.4f}")
            else:
                print(f"  {display_name:<25} {value}")

    print(f"\n  Confusion Matrix:")
    print(f"    TN: {metrics.get('true_negatives', 'N/A')}")
    print(f"    FP: {metrics.get('false_positives', 'N/A')}")
    print(f"    FN: {metrics.get('false_negatives', 'N/A')}")
    print(f"    TP: {metrics.get('true_positives', 'N/A')}")
    print(f"{'='*50}\n")