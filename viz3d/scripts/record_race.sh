#!/usr/bin/env bash
# Phase 3: record the engine race in WSL. PowerShell mangles nested quoting
# into `wsl -- bash -lc "..."`, so the command lives here instead:
#
#   wsl -d Ubuntu-22.04 -- bash /mnt/c/<...>/viz3d/scripts/record_race.sh [args]
#
# Needs the venv from docs/phase0-geometry-report.md section 11:
# backend/requirements.txt + joblib + gymnasium in ~/venvs/sim.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/../.."
PY="${SIM_PYTHON:-$HOME/venvs/sim/bin/python}"
exec "$PY" viz3d/scripts/record_race.py "$@"
