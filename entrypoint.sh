#!/bin/sh
set -eu

echo "Running database migrations..."
if ! alembic upgrade head; then
  echo "ERROR: Database migration failed" >&2
  exit 1
fi

echo "Starting API server..."
exec uvicorn src.main:create_app --factory --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-1}"
