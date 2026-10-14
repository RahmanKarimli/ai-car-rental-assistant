#!/bin/sh
set -eu

langsmith_key_file="${LANGSMITH_API_KEY_FILE:-/run/secrets/langsmith_api_key}"
if [ -r "$langsmith_key_file" ]; then
  LANGSMITH_API_KEY="$(cat "$langsmith_key_file")"
  export LANGSMITH_API_KEY
fi

alembic upgrade head
python scripts/initialize_checkpoints.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
