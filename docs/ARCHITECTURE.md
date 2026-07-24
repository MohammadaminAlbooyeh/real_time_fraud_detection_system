# Architecture

## High-level flow

1. A transaction is submitted through the API.
2. The backend validates and enriches the request.
3. Recent transaction history and user profile data are loaded from the database.
4. The rule engine and ML detector score the transaction.
5. The transaction is persisted and alerts are emitted when risk is high.
6. The frontend receives live updates over WebSockets.

## Main backend components

- `backend/main.py` initializes FastAPI, middleware, and application lifespan hooks.
- `backend/api/routes.py` exposes health, transaction, alert, metrics, and WebSocket routes.
- `backend/services/transaction_processor.py` handles scoring and persistence.
- `backend/services/fraud_detector.py` loads and runs the model.
- `backend/services/rule_engine.py` evaluates deterministic fraud rules.
- `backend/services/feature_extractor.py` builds model features from transaction context.
- `backend/services/alert_service.py` creates and manages alert records.
- `backend/services/websocket_manager.py` broadcasts live events.

## Data stores

- PostgreSQL stores transactions, alerts, and user profiles.
- Redis is used for connection/state support and runtime coordination.
- ML artifacts are stored under `backend/models/`.

## Frontend

The frontend is a Vite/React application that consumes the API and subscribes to live events for dashboard, transaction, alert, and analytics pages.

## Notes

- The system is designed as a monolith with clearly separated service layers.
- The current implementation is close to production shape, but runtime validation and deployment wiring still need to be verified in the target environment.
