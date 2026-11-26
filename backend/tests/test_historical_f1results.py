"""Geometria histórica aproximada, procedência e grid da corrida."""
import copy
import json
import math
from dataclasses import replace
from types import SimpleNamespace

import pytest
import pybullet as pb

from api.providers.historical_f1results import HistoricalResultsProvider, load_historical_snapshot
from api.providers.race_data import OpenF1Provider, ProviderChain, default_provider
from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from engine import RuleBasedRaceController, SimulationEngine


@pytest.mark.parametrize('circuit,year,expected,direction', [
    ('interlagos', 1973, 7960, 'Anticlockwise'),
    ('interlagos', 1979, 7874, 'Anticlockwise'),
    ('monza', 1950, 6300, 'Clockwise'),
    ('spa-francorchamps', 1966, 14100, 'Clockwise'),
])
def test_historical_provider_matches_year_length_direction_and_grid(circuit, year, expected, direction):
    track, drivers, sources = HistoricalResultsProvider().load(circuit, year)
    assert track.length_m == pytest.approx(expected, abs=.01)
    assert track.start_finish_waypoint == 0 and len(track.waypoints) >= 100
    assert len(drivers) >= 2 and sources['driver_source'] == 'f1results_database'
    assert sources['track_provenance']['geometry'] == 'approximate_svg'
    assert sources['track_provenance']['direction'] == direction
    assert sources['track_provenance']['season'] == year
    assert sources['track_provenance']['max_safe_grid_cars'] == 24
    points = track.waypoints
    area = sum(a[0]*b[1] - b[0]*a[1] for a, b in zip(points, points[1:] + points[:1]))
    assert (area < 0) == (direction == 'Clockwise')
    assert all(track.distance_to_centerline(*pos) < track.width_m / 2 - .9 for pos in track.initial_positions)
    assert all(math.dist(a, b) >= 6 for i, a in enumerate(track.initial_positions) for b in track.initial_positions[:i])


def test_historical_provider_rejects_unavailable_year_and_corrupt_points():
    provider = HistoricalResultsProvider()
    with pytest.raises(ValueError, match='indisponível'):
        provider.load('interlagos', 1978)
    source = load_historical_snapshot()
    event = copy.deepcopy(source['races']['interlagos:1973'])
    geometry = copy.deepcopy(source['geometries'][str(event['source_layout_id'])])
    geometry['points'][1] = [float('nan'), 0]
    broken = {'races': {'interlagos:1973': event},
              'geometries': {str(event['source_layout_id']): geometry}}
    with pytest.raises(ValueError, match='não finito'):
        HistoricalResultsProvider(snapshot=broken).load('interlagos', 1973)


def test_historical_provider_chain_exposes_provenance():
    class Missing:
        def load(self, *_args):
            raise ValueError('sem telemetria')
    track, _, source = ProviderChain([Missing(), HistoricalResultsProvider()]).load('interlagos', 1973)
    assert source['track_source'] == 'f1results_svg'
    assert source['track_provenance']['reference_length_m'] == 7960
    assert source['track_provenance']['source_layout_id'] == 50
    assert track.source == 'f1results_svg'


@pytest.mark.parametrize('circuit,year,length_m,source_layout_id', [
    ('interlagos', 2023, 4309.0, 51),
    ('monza', 2024, 5793.0, 107),
])
def test_default_provider_prefers_the_local_svg_snapshot(monkeypatch, circuit, year, length_m, source_layout_id):
    monkeypatch.setattr(OpenF1Provider, 'load', lambda *_: pytest.fail('SVG disponível deve evitar a consulta OpenF1'))

    track, drivers, sources = default_provider().load(circuit, year)

    assert track.source == sources['track_source'] == 'f1results_svg'
    assert track.length_m == pytest.approx(length_m)
    assert sources['track_provenance']['source_layout_id'] == source_layout_id
    assert sources['driver_source'] == 'f1results_database'
    assert len(drivers) == 20


def test_default_provider_uses_openf1_if_catalog_has_no_svg(monkeypatch):
    monkeypatch.setattr(
        'api.providers.historical_f1results.load_historical_snapshot',
        lambda: {'geometries': {}, 'races': {}},
    )
    track = SimpleNamespace(source='openf1')
    drivers = [{'driver_id': 'test-driver'}]
    monkeypatch.setattr(OpenF1Provider, 'load', lambda *_: (
        track, drivers, {'track_source': 'openf1', 'driver_source': 'openf1'},
    ))

    assert default_provider().load('interlagos', 2023) == (
        track, drivers, {'track_source': 'openf1', 'driver_source': 'openf1'},
    )


def test_race_catalog_excludes_circuits_and_layouts_without_local_geometry():
    from api.main import list_circuits

    available = {c['id']: c for c in list_circuits()['circuits']}
    full = {c['id']: c for c in list_circuits(include_unavailable=True)['circuits']}
    for circuit_id in ('caesars-palace', 'brands-hatch', 'avus'):
        assert circuit_id not in available
        assert not full[circuit_id]['simulable']
    assert all(c['simulable'] and c['layouts'] and all(l['simulable'] for l in c['layouts'])
               for c in available.values())
    assert 'monza-2' not in {layout['id'] for layout in available['monza']['layouts']}
    # Having a recent season is not enough to claim the geometry is available.
    assert 'las-vegas' not in available and not full['las-vegas']['simulable']
    assert 'ain-diab' in available


def test_historical_grid_pose_and_first_ten_seconds():
    track, _, _ = HistoricalResultsProvider().load('interlagos', 1973)
    drivers = [replace(DEFAULT_DRIVERS[i % len(DEFAULT_DRIVERS)], driver_id=f'test-{i}') for i in range(2)]
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False,
                                      track_progress_laps=True), track, drivers)
    controller = RuleBasedRaceController(track, seed=42)
    for driver in drivers:
        engine.set_controller(driver.driver_id, controller)
    engine.setup()
    try:
        for i, driver in enumerate(drivers):
            pose, quaternion = pb.getBasePositionAndOrientation(engine.handles[driver.driver_id].chassis_id,
                                                               physicsClientId=engine.physics._client_id)
            assert pose[:2] == pytest.approx(track.initial_position(i))
            yaw = pb.getEulerFromQuaternion(quaternion)[2]
            assert yaw == pytest.approx(track.metadata['grid_yaws_rad'][i])
        for _ in range(100):
            engine._step_tick(.1, 24)
            assert all(track.distance_to_centerline(state.position_x, state.position_y) < track.width_m / 2
                       for state in engine.states.values())
        assert all(engine.race_progress_m[d.driver_id] > 100 for d in drivers)
    finally:
        engine.teardown()


def test_race_metadata_contains_authoritative_geometry_and_provenance(monkeypatch):
    import api.race_manager as module
    class Store:
        def __init__(self): self.values = {}
        def ping(self): return True
        def set(self, key, value, ex=None): self.values[key] = value
    class Engine:
        def __init__(self, **kwargs): self.physics = SimpleNamespace(contact_collector=None)
        def set_controller(self, *_): pass
    class Thread:
        def __init__(self, **_): pass
        def start(self): pass
    monkeypatch.setattr(module, 'SimulationEngine', Engine)
    monkeypatch.setattr(module, 'RuleBasedRaceController', lambda *_a, **_k: object())
    monkeypatch.setattr(module.threading, 'Thread', Thread)
    store = Store()
    manager = module.RaceManager(store, provider=HistoricalResultsProvider())
    race_id, track, _ = manager.create_race(3, 'interlagos', 1973, 20, layout_id='interlagos-1')
    meta = json.loads(store.values[f'race:{race_id}:meta'])
    assert meta['track']['length_m'] == pytest.approx(7960, abs=.01)
    assert meta['track']['waypoints'] == [list(point) for point in track.waypoints]
    assert meta['track']['pit_lane']['source'] == 'estimated'
    assert meta['track']['pit_lane']['waypoints'] == [list(point) for point in track.pit.waypoints]
    assert meta['sources']['track_provenance']['geometry'] == 'approximate_svg'
    assert meta['sources']['track_provenance']['grand_prix'] == '1973 Brazilian Grand Prix'
    assert [d['name'] for d in meta['drivers'][:2]] == ['Ronnie Peterson', 'Emerson Fittipaldi']
    with pytest.raises(ValueError, match='apenas 20 carros'):
        manager.create_race(3, 'interlagos', 1973, 21)


def test_historical_real_engine_redis_websocket(monkeypatch):
    import os
    import redis
    import api.main as api_main
    from fastapi.testclient import TestClient
    url = os.getenv('TEST_REDIS_URL')
    if not url:
        pytest.skip('requires an isolated Redis server')
    client = redis.Redis.from_url(url, decode_responses=True)
    monkeypatch.setattr(api_main, 'REDIS_URL', url)
    monkeypatch.setattr(api_main.race_manager, 'redis', client)
    monkeypatch.setattr(api_main.race_manager, 'provider', HistoricalResultsProvider())
    with TestClient(api_main.app) as http:
        response = http.post('/races', json={'track': 'interlagos', 'year': 1973,
                                           'num_drivers': 20, 'laps': 1, 'layout_id': 'interlagos-1'})
        assert response.status_code == 200, response.text
        race_id = response.json()['race_id']
        meta = http.get(f'/races/{race_id}').json()
        assert meta['track']['source'] == 'f1results_svg'
        assert meta['track']['length_m'] == pytest.approx(7960, abs=.01)
        assert meta['sources']['track_provenance']['geometry'] == 'approximate_svg'
        assert len(meta['drivers']) == 20
        with http.websocket_connect(f'/ws/races/{race_id}') as ws:
            for _ in range(10):
                event = ws.receive_json()
                if event['type'] == 'tick':
                    break
            assert event['type'] == 'tick'
            assert len(event['positions']) == 20
            assert all(len(pos['position_xy']) == 2 and 'heading_deg' in pos for pos in event['positions'])
        snapshot = http.get(f'/races/{race_id}/snapshot').json()
        assert snapshot['last_tick']['type'] == 'tick'


def test_twenty_car_grid_follows_local_historical_tangents():
    track, _, _ = HistoricalResultsProvider().load('interlagos', 1973)
    drivers = [replace(DEFAULT_DRIVERS[i % len(DEFAULT_DRIVERS)], driver_id=f'grid-{i}') for i in range(20)]
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False), track, drivers)
    engine.setup()
    try:
        for i, driver in enumerate(drivers):
            pose, quaternion = pb.getBasePositionAndOrientation(engine.handles[driver.driver_id].chassis_id,
                                                               physicsClientId=engine.physics._client_id)
            assert pose[:2] == pytest.approx(track.initial_position(i))
            assert pb.getEulerFromQuaternion(quaternion)[2] == pytest.approx(track.metadata['grid_yaws_rad'][i])
            assert track.distance_to_centerline(*pose[:2]) < track.width_m / 2 - .9
    finally:
        engine.teardown()
