# Model Performance

## Current model workflow

The repository contains multiple ML artifacts under `backend/models/`, including:

- `xgboost_model.pkl`
- `isolation_forest_model.pkl`
- `random_forest_model.pkl`

The training pipeline saves the model and preprocessor artifacts and logs them for experiment tracking.

## What still needs to be documented

- Which model is the canonical inference artifact
- How preprocessing artifacts are versioned with the model
- What metrics define acceptable performance
- Which threshold is used for fraud classification in production

## Suggested performance sections

- training data summary
- feature set description
- class imbalance handling
- validation strategy
- precision, recall, F1, ROC-AUC
- alert volume and false-positive rate
- threshold tuning results

## Recommended next step

Populate this document from the latest training run so that model selection and deployment decisions are traceable.
