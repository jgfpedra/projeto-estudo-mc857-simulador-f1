#!/bin/sh
set -eu
if [ -n "${DATABASE_URL:-}" ]; then
    python -m storage.postgres
fi
exec "$@"
