#!/usr/bin/env python3
"""Reproduz/verifica os traçados de telemetria usados pela corrida ao vivo."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'viz3d' / 'scripts'))
from export_frozen_track import plan_ff1, resample_uniform  # noqa: E402


def monza_export() -> bytes:
    source = ROOT / 'viz3d/public/tracks/monza.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    waypoints = np.round(resample_uniform(plan_ff1(data), 4.0), 6)
    result = {
        'name': 'Monza Grand Prix (viz3d 2024 race)',
        'waypoints': waypoints.tolist(), 'width_m': 12.0,
        'sf_idx': 0, 'n_wp': len(waypoints),
        'sf_method': 'Median lap start, approximately 1 m from timing line according to viz3d/docs/phase0-geometry-report.md section 4.',
        'source': {
            'track': 'public/tracks/monza.json',
            'trackSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'circuit': 'monza', 'year': 2024,
            'pipeline': 'viz3d FastF1 2024 telemetry centreline',
            'resample': 'uniform along the committed polyline, max 4.0 m',
        },
    }
    result['sha256'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:16]
    return (json.dumps(result, ensure_ascii=True) + '\n').encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='grava os arquivos em backend/config/tracks')
    args = parser.parse_args()
    output = ROOT / 'backend/config/tracks'
    exports = {
        'interlagos_2023_v1.json': (ROOT / 'viz3d/exports/interlagos_2023_v1.json').read_bytes(),
        'monza_2024_v1.json': monza_export(),
    }
    if args.write:
        output.mkdir(parents=True, exist_ok=True)
    valid = True
    for name, expected in exports.items():
        path = output / name
        if args.write:
            path.write_bytes(expected)
        matches = path.exists() and path.read_bytes() == expected
        valid &= matches
        print(f'{name}: {"OK" if matches else "DIVERGENTE"}')
    return 0 if valid else 1


if __name__ == '__main__':
    raise SystemExit(main())
