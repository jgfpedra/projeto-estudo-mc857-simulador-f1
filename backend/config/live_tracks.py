"""Traçados para a corrida ao vivo, derivados de telemetria e verificáveis."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from domain import Track
from . import load_track

_TRACKS = Path(__file__).resolve().parent / 'tracks'
_INTERLAGOS = {'interlagos', 'sao-paulo', 'são-paulo', 'sao paulo', 'são paulo', 'brazil'}


def load_live_track(track_name: str | None = None, year: int | None = None) -> Track:
    """Usa telemetria local para Interlagos 2023 e Monza 2024, sem fallback silencioso."""
    name = (track_name or 'interlagos').strip().lower() or 'interlagos'
    if name in _INTERLAGOS and year in (None, 2023):
        path = _TRACKS / 'interlagos_2023_v1.json'
    elif name == 'monza' and year in (None, 2024):
        path = _TRACKS / 'monza_2024_v1.json'
    else:
        return load_track(track_name=track_name, year=year)

    data = json.loads(path.read_text(encoding='utf-8'))
    unsigned = {key: value for key, value in data.items() if key != 'sha256'}
    digest = hashlib.sha256(json.dumps(unsigned, sort_keys=True).encode()).hexdigest()[:16]
    if digest != data['sha256'] or len(data['waypoints']) != data['n_wp']:
        raise ValueError(f'Traçado de corrida corrompido: {path.name}')
    return Track.from_waypoints(
        name=data['name'], waypoints=data['waypoints'], width_m=data['width_m'],
        start_finish_waypoint=data['sf_idx'], source='telemetry',
        metadata={'geometry_file': path.name, 'geometry_sha256': digest,
                  'sf_method': data['sf_method'], **data['source']},
    )
