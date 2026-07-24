# Deployment

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis

## Backend deployment steps

1. Install Python dependencies.
2. Apply database migrations.
3. Ensure the ML model artifact exists at the configured model path.
4. Set environment variables for database, Redis, CORS, and model configuration.
5. Start the FastAPI app with Uvicorn or your production ASGI server.

Example:

```bash
cd backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Frontend deployment steps

1. Install frontend dependencies.
2. Set the frontend API base path to the deployed backend origin or reverse proxy path.
3. Build the app.
4. Serve the generated static assets.

Example:

```bash
cd frontend
npm install
npm run build
```

## Operational checks

- Confirm `/api/v1/health` returns healthy.
- Confirm the frontend can reach the backend API and WebSocket endpoints.
- Confirm Redis and Postgres are reachable at startup.
- Confirm transaction submission creates a persisted record and optional alert.

## Production checklist

- Database migrations applied successfully in the target environment.
- `DATABASE_URL` points to the production Postgres instance.
- `REDIS_URL` points to the production Redis instance.
- `MODEL_PATH` resolves to the deployed inference artifact.
- `CORS_ORIGINS` contains only the production frontend origins.
- Reverse proxy forwards `/api/v1/*` and WebSocket routes to the backend.
- Static frontend assets are built and served from the production host or CDN.
- Health checks are configured for the API and, if applicable, the container orchestrator.
- Log aggregation and alerting are enabled.
- Backups and restore procedures are verified for Postgres.
- Redis eviction and memory policy are set for expected traffic.
- Model rollback procedure is documented and tested.
- A smoke test against the deployed API returns healthy before traffic is shifted.
- A smoke test against Redis succeeds in the production network segment.
- A rollback plan exists for failed deploys and failed model swaps.
- Alert routing is verified in the production environment.

## CI pipeline

The repository now includes a GitHub Actions workflow at [`.github/workflows/ci.yml`](/Users/amin/Documents/MyProjects/real_time_fraud_detection_system/.github/workflows/ci.yml) that:

- runs backend tests against SQLite and a Redis service container
- builds the frontend
- executes on pushes and pull requests to `main`

## Open deployment work

- Verify the deployment image or server has the correct model files.
- Verify environment-specific CORS settings.
- Verify WebSocket routing behind the production proxy.
- Verify database migrations run cleanly in the deployment target.
