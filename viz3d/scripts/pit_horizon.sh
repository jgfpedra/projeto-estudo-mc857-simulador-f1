#!/usr/bin/env bash
# Phase 3b: first-pit horizon from the engine's own wear/fuel code (WSL).
#   wsl -d Ubuntu-22.04 -- bash /mnt/c/<...>/viz3d/scripts/pit_horizon.sh [--json out]
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/../.."
PY="${SIM_PYTHON:-$HOME/venvs/sim/bin/python}"
exec "$PY" viz3d/scripts/pit_horizon.py "$@"
