# Real-Time Fraud Detection System

This repository contains a real-time fraud detection prototype with:

- a FastAPI backend
- a React/Vite frontend
- a transaction scoring pipeline
- rule-based and ML-based fraud detection
- WebSocket support for live updates

## What the system does

- Accepts transaction events through the API
- Enriches each transaction with user profile and recent activity context
- Scores transactions with the rule engine and model inference
- Persists transactions and alerts in the database
- Streams live events to the frontend through WebSockets

## Repository layout

- `backend/` API, services, models, data processing, and migrations
- `frontend/` React user interface
- `tests/` backend test suite
- `notebooks/` exploratory analysis and model development
- `docs/` project architecture, deployment, and model notes

## Local development

Backend:

```bash
cd backend
python -m uvicorn backend.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Quality checks

Recommended checks before release:

- `pytest -q`
- `npm run build`
- database migration verification
- backend startup verification with Redis and Postgres available

## Status

The codebase is functional, but docs and deployment verification are still part of the remaining completion work.
