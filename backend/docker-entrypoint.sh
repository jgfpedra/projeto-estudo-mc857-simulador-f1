#!/bin/sh
set -eu
if [ -n "${DATABASE_URL:-}" ]; then
    python -m storage.postgres
fi
# Configure logging for backend modules
export PYTHONUNBUFFERED=1
exec "$@"
