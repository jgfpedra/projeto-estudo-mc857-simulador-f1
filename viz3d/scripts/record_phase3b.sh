#!/usr/bin/env bash
# Phase 3b: the three 15-lap recordings, one after the other (so each wall time
# is a clean single-process measurement). Same seed, grid, profile and length:
#   a  interlagos_v2, tuning as the engine runs it
#   b  interlagos_v2, Interlagos tuning forced off (control)
#   c  viz3d/exports/interlagos_2023_v1.json (untuned by construction)
#   wsl -d Ubuntu-22.04 -- bash /mnt/c/<...>/viz3d/scripts/record_phase3b.sh [laps]
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
LAPS="${1:-15}"
bash "$HERE/record_race.sh" --laps "$LAPS" --label a_tuned
bash "$HERE/record_race.sh" --laps "$LAPS" --label b_untuned --interlagos-tuning off
bash "$HERE/record_race.sh" --laps "$LAPS" --label c_ours --track interlagos_2023 --tracks-dir viz3d/exports
