"""Pistas históricas aproximadas, derivadas dos mapas F1 Results Database."""
from __future__ import annotations

from bisect import bisect_right
import json
import math
import os
from functools import lru_cache
from pathlib import Path

from domain import Track
from .f1db_layouts import load_layout_catalog

DEFAULT_PATH = Path(__file__).resolve().parents[2] / 'config' / 'historical_tracks' / 'f1results_tracks.json'


@lru_cache(maxsize=4)
def load_historical_snapshot(path=None):
    selected = Path(path or os.environ.get('F1_RESULTS_TRACKS_PATH') or DEFAULT_PATH)
    data = json.loads(selected.read_text(encoding='utf-8'))
    if not isinstance(data.get('geometries'), dict) or not isinstance(data.get('races'), dict):
        raise ValueError('Catálogo de geometrias históricas inválido')
    return data


def grid_along_track(points, width_m, slots=24):
    """Posiciona cada slot no trecho anterior à linha, seguindo sua tangente."""
    reverse = [points[0], *reversed(points[1:]), points[0]]
    distances = [0.0]
    for a, b in zip(reverse, reverse[1:]):
        distances.append(distances[-1] + math.dist(a, b))
    positions, headings = [], []
    lateral = min(2.5, max(1.0, width_m * .22))
    for index in range(slots):
        distance = 8.0 + index * 8.0
        if distance >= distances[-1]:
            break
        segment = min(bisect_right(distances, distance) - 1, len(reverse) - 2)
        a, b = reverse[segment], reverse[segment + 1]
        length = distances[segment + 1] - distances[segment]
        if length <= 0:
            raise ValueError('Segmento inválido no grid histórico')
        fraction = (distance - distances[segment]) / length
        x, y = a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction
        fx, fy = (a[0] - b[0]) / length, (a[1] - b[1]) / length
        side = lateral if index % 2 == 0 else -lateral
        positions.append((x - fy * side, y + fx * side))
        headings.append(math.atan2(fy, fx))
    return positions, headings


class HistoricalResultsProvider:
    """Fonte local versionada, usada após telemetria e pistas congeladas."""
    def __init__(self, snapshot=None, catalog=None):
        self.snapshot = snapshot
        self.catalog = catalog

    def load(self, circuit: str, season: int):
        catalog = self.catalog if self.catalog is not None else load_layout_catalog()
        entry = catalog.find_circuit(circuit)
        if entry is None:
            raise ValueError(f'Circuito histórico desconhecido: {circuit}')
        snapshot = self.snapshot if self.snapshot is not None else load_historical_snapshot()
        race = snapshot['races'].get(f"{entry['id']}:{season}")
        if race is None:
            raise ValueError('Geometria histórica indisponível ou ambígua para essa temporada')
        geom = snapshot['geometries'].get(str(race['source_layout_id']))
        if not geom or geom.get('circuit_id') != entry['id']:
            raise ValueError('Geometria histórica não corresponde ao circuito')
        raw = geom.get('points')
        if not isinstance(raw, list) or not 100 <= len(raw) <= 10000:
            raise ValueError('Waypoints históricos insuficientes ou inválidos')
        points = []
        for point in raw:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError('Waypoint histórico inválido')
            x, y = float(point[0]), float(point[1])
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError('Waypoint histórico não finito')
            points.append((x, y))
        perimeter = sum(math.dist(a, b) for a, b in zip(points, points[1:] + points[:1]))
        expected = float(race['length_m'])
        if not math.isfinite(perimeter) or perimeter <= 0 or not 1000 <= expected <= 30000:
            raise ValueError('Comprimento histórico inválido')
        scale = expected / perimeter
        scaled = [(x * scale, y * scale) for x, y in points]
        steps = [math.dist(a, b) for a, b in zip(scaled, scaled[1:] + scaled[:1])]
        if min(steps) < .01 or max(steps) > 100:
            raise ValueError('Traçado histórico contém saltos ou pontos repetidos')
        provenance = {
            'source': snapshot['source'], 'source_url': snapshot['source_url'],
            'release': snapshot['release'], 'license': snapshot['license'],
            'source_db_sha256': snapshot['db_sha256'],
            'source_layout_id': race['source_layout_id'], 'grand_prix': race['grand_prix'],
            'season': season, 'reference_length_m': expected, 'geometry': 'approximate_svg',
            'start_finish': geom['start_finish'], 'direction': geom['direction'],
            'width_m': 12.0, 'width_source': 'assumed',
        }
        positions, headings = grid_along_track(scaled, 12.0)
        track = Track.from_waypoints(name=entry.get('full_name') or entry['id'],
                                     waypoints=scaled, width_m=12.0,
                                     start_finish_waypoint=0, source='f1results_svg',
                                     metadata={**provenance, 'grid_yaws_rad': headings},
                                     initial_positions=positions)
        safe_grid = 0
        for pos in positions:
            if track.distance_to_centerline(*pos) > track.width_m / 2 - .9:
                break
            if any(math.dist(pos, prior) < 6.0 for prior in positions[:safe_grid]):
                break
            safe_grid += 1
        if not safe_grid:
            raise ValueError('A geometria histórica não comporta o primeiro carro no grid')
        provenance['max_safe_grid_cars'] = safe_grid
        track.metadata = {**provenance, 'grid_yaws_rad': headings}
        from database.f1results_database import F1ResultsDriverDatabase, race_driver_record, roster_provenance
        database = F1ResultsDriverDatabase()
        event, roster = database.race_roster(entry['id'], season, grand_prix=race['grand_prix'])
        if not roster:
            raise ValueError('Grid histórico indisponível para este GP')
        drivers = [race_driver_record(driver) for driver in roster]
        return track, drivers, {'track_source': 'f1results_svg', 'driver_source': 'f1results_database',
                                'driver_provenance': roster_provenance(database, event),
                                'track_provenance': provenance}
