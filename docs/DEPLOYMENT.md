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

## Open deployment work

- Verify the deployment image or server has the correct model files.
- Verify environment-specific CORS settings.
- Verify WebSocket routing behind the production proxy.
- Verify database migrations run cleanly in the deployment target.
