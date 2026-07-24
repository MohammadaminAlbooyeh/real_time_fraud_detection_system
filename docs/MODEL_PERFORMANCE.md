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

I used the saved `backend/models/xgboost_model.pkl` artifact as the latest concrete training output available in the repository. Its recorded metrics are:

- precision: 1.0
- recall: 0.98
- f1_score: 0.9899
- mcc: 0.9898
- roc_auc: 0.99999
- pr_auc: 0.99952
- log_loss: 0.00069
- accuracy: 0.9998
- specificity: 1.0
- false_positive_rate: 0.0
- false_discovery_rate: 0.0
- true_negatives: 9900
- false_positives: 0
- false_negatives: 2
- true_positives: 98
- negative_predictive_value: 0.9998

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
