# Model Performance

## Current model workflow

The repository contains multiple ML artifacts under `backend/models/`, including:

- `xgboost_model.pkl`
- `isolation_forest_model.pkl`
- `random_forest_model.pkl`

The training pipeline saves the model and preprocessor artifacts and logs them for experiment tracking.

The codebase evaluates models with precision, recall, F1, ROC-AUC, PR-AUC, MCC, accuracy, specificity, and confusion-matrix counts.

## What still needs to be documented

- Which model is the canonical inference artifact
- How preprocessing artifacts are versioned with the model
- What metrics define acceptable performance
- Which threshold is used for fraud classification in production

## Latest run

I could not find a persisted training report or notebook cell output in this repository with the latest numeric metrics, so I am not inventing values here.

If you have the latest training output elsewhere, add:

- train/test split date
- model type
- threshold
- precision
- recall
- F1
- ROC-AUC
- PR-AUC
- false positive rate
- confusion matrix

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
