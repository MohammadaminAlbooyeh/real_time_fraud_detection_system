import warnings
from typing import Any

import numpy as np
import optuna
import xgboost as xgb
from lightgbm import LGBMClassifier
from optuna.samplers import TPESampler
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score

warnings.filterwarnings("ignore")


def objective_xgboost(
    trial: optuna.Trial,
    X: np.ndarray,
    y: np.ndarray,
    cv_folds: int = 5,
) -> float:
    param = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma": trial.suggest_float("gamma", 0, 5),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 100.0),
        "random_state": 42,
        "n_jobs": -1,
        "eval_metric": "aucpr",
        "use_label_encoder": False,
    }

    model = xgb.XGBClassifier(**param)
    try:
        scores = cross_val_score(
            model, X, y,
            cv=StratifiedKFold(cv_folds, shuffle=True, random_state=42),
            scoring="average_precision",
            n_jobs=1,
        )
        return scores.mean()
    except Exception:
        return 0.0


def objective_lightgbm(
    trial: optuna.Trial,
    X: np.ndarray,
    y: np.ndarray,
    cv_folds: int = 5,
) -> float:
    param = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 16, 255),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        "class_weight": trial.suggest_categorical("class_weight", [None, "balanced"]),
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1,
    }

    model = LGBMClassifier(**param)
    try:
        scores = cross_val_score(
            model, X, y,
            cv=StratifiedKFold(cv_folds, shuffle=True, random_state=42),
            scoring="average_precision",
            n_jobs=1,
        )
        return scores.mean()
    except Exception:
        return 0.0


def optimize_hyperparameters(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str = "xgboost",
    n_trials: int = 50,
    cv_folds: int = 5,
    timeout: int | None = None,
    study_name: str | None = None,
) -> dict[str, Any]:
    sampler = TPESampler(seed=42)

    if model_type == "xgboost":
        objective = lambda trial: objective_xgboost(trial, X, y, cv_folds)
        direction = "maximize"
    elif model_type == "lightgbm":
        objective = lambda trial: objective_lightgbm(trial, X, y, cv_folds)
        direction = "maximize"
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    study = optuna.create_study(
        direction=direction,
        sampler=sampler,
        study_name=study_name,
    )

    study.optimize(
        objective,
        n_trials=n_trials,
        timeout=timeout,
        show_progress_bar=True,
    )

    print(f"Best trial: {study.best_trial.number}")
    print(f"Best value (PR-AUC): {study.best_trial.value:.4f}")
    print(f"Best parameters: {study.best_trial.params}")

    return study.best_trial.params


def plot_optimization_history(study: optuna.Study, figsize: tuple = (10, 6)):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    trials = [t for t in study.trials if t.value is not None]
    values = [t.value for t in trials]
    params = study.best_trial.params

    axes[0].plot(range(len(values)), values, "b-", alpha=0.7)
    axes[0].axhline(y=study.best_trial.value, color="r", linestyle="--", alpha=0.5)
    axes[0].set_xlabel("Trial")
    axes[0].set_ylabel("PR-AUC")
    axes[0].set_title("Optimization History")

    importances = optuna.importance.get_param_importances(study)
    if importances:
        param_names = list(importances.keys())
        param_importances = list(importances.values())
        axes[1].barh(range(len(param_importances)), param_importances)
        axes[1].set_yticks(range(len(param_names)))
        axes[1].set_yticklabels(param_names)
        axes[1].set_xlabel("Importance")
        axes[1].set_title("Hyperparameter Importance")

    plt.tight_layout()
    return fig