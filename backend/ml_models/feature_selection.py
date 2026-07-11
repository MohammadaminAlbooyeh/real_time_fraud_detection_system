import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel, mutual_info_classif
from sklearn.inspection import permutation_importance
from sklearn.model_selection import StratifiedKFold

warnings.filterwarnings("ignore")


def select_features_rf(
    X: pd.DataFrame,
    y: pd.Series,
    threshold: str = "median",
    max_features: int | None = None,
) -> list[str]:
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    rf.fit(X, y)

    selector = SelectFromModel(rf, threshold=threshold, max_features=max_features)
    selector.fit(X, y)

    mask = selector.get_support()
    selected_features = list(X.columns[mask])

    importances = pd.DataFrame({
        "feature": X.columns,
        "importance": rf.feature_importances_,
    }).sort_values("importance", ascending=False)

    return selected_features


def select_features_mutual_info(
    X: pd.DataFrame,
    y: pd.Series,
    n_features: int = 20,
    random_state: int = 42,
) -> list[str]:
    mi_scores = mutual_info_classif(X, y, random_state=random_state)
    mi_series = pd.Series(mi_scores, index=X.columns).sort_values(ascending=False)
    return mi_series.head(n_features).index.tolist()


def compute_shap_values(
    model,
    X: pd.DataFrame,
    n_samples: int = 100,
) -> tuple[np.ndarray, list[str]]:
    if n_samples < len(X):
        X_sample = X.sample(n_samples, random_state=42)
    else:
        X_sample = X

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    return shap_values, list(X_sample.columns)


def compute_permutation_importance(
    model,
    X: pd.DataFrame,
    y: pd.Series,
    n_repeats: int = 10,
    random_state: int = 42,
) -> pd.DataFrame:
    result = permutation_importance(
        model, X, y,
        n_repeats=n_repeats,
        random_state=random_state,
        n_jobs=-1,
    )

    importance_df = pd.DataFrame({
        "feature": X.columns,
        "importance_mean": result.importances_mean,
        "importance_std": result.importances_std,
    }).sort_values("importance_mean", ascending=False)

    return importance_df


def plot_feature_importance(
    importance_df: pd.DataFrame,
    top_n: int = 20,
    title: str = "Feature Importance",
    figsize: tuple[int, int] = (10, 8),
) -> plt.Figure:
    top_features = importance_df.head(top_n)
    fig, ax = plt.subplots(figsize=figsize)

    bars = ax.barh(range(len(top_features)), top_features["importance_mean"].values)
    ax.set_yticks(range(len(top_features)))
    ax.set_yticklabels(top_features["feature"].values)
    ax.set_xlabel("Importance")
    ax.set_title(title)
    ax.invert_yaxis()

    return fig


def get_top_features(
    X: pd.DataFrame,
    y: pd.Series,
    n_features: int = 20,
    methods: list[str] | None = None,
) -> list[str]:
    methods = methods or ["rf", "mutual_info"]

    all_selected = set()

    for method in methods:
        if method == "rf":
            selected = select_features_rf(X, y, max_features=n_features * 2)
        elif method == "mutual_info":
            selected = select_features_mutual_info(X, y, n_features=n_features)
        else:
            continue
        all_selected.update(selected)

    return list(all_selected)[:n_features]


def compute_feature_correlation(
    X: pd.DataFrame,
    y: pd.Series,
) -> pd.DataFrame:
    correlations = []
    for col in X.columns:
        corr = X[col].corr(y)
        correlations.append({"feature": col, "correlation": corr})

    return pd.DataFrame(correlations).sort_values("correlation", key=abs, ascending=False)