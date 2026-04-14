#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI application..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT
