#!/bin/bash
set -e

echo "=========================================="
echo "Running Alembic Migrations..."
echo "=========================================="
python -m alembic upgrade head

echo ""
echo "=========================================="
echo "Starting FastAPI Application..."
echo "=========================================="
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
