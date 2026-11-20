"""HTTP/WebSocket contract tests for the Redis-backed race manager."""
import json
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api import main
from api.providers.race_data import driver_record
from api.race_manager import RaceManager
from config.live_tracks import load_live_track


class MemoryStore:
    def __init__(self): self.values = {}
    def ping(self): return True
    def set(self, key, value, ex=None): self.values[key] = value
    def get(self, key): return self.values.get(key)


class FakeProvider:
    def load(self, circuit, season):
        if circuit != 'interlagos':
            raise ValueError('Circuito indisponível')
        track = load_live_track(track_name='interlagos', year=2023)
        return track, [driver_record('VER', 'Max Verstappen', 1, 'Red Bull', '3671C6'),
                       driver_record('NOR', 'Lando Norris', 4, 'McLaren', 'FF8000')], {
                           'track_source': 'test', 'driver_source': 'test'}


class FakeEngine:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.physics = SimpleNamespace(contact_collector=None)
    def set_controller(self, *_args): pass


class FakeThread:
    def __init__(self, **_kwargs): pass
    def start(self): pass


DRIVERS = [
    {'id': 'max-verstappen', 'name': 'Max Verstappen', 'abbreviation': 'VER',
     'permanent_number': 1, 'team_name': 'Red Bull', 'team_color': '#3671C6',
     'team': {'id': 'red-bull'}, 'country_name': 'Netherlands', 'country_code': 'NL'},
    {'id': 'lando-norris', 'name': 'Lando Norris', 'abbreviation': 'NOR',
     'permanent_number': 4, 'team_name': 'McLaren', 'team_color': '#FF8000',
     'team': {'id': 'mclaren'}, 'country_name': 'United Kingdom', 'country_code': 'GB'},
]


@pytest.fixture
def context(monkeypatch):
    import api.race_manager as module
    url = os.environ.get('TEST_REDIS_URL')
    if url:
        import redis
        store = redis.Redis.from_url(url, decode_responses=True)
        monkeypatch.setattr(main, 'REDIS_URL', url)
    else:
        store = MemoryStore()
    manager = RaceManager(client=store, provider=FakeProvider())
    monkeypatch.setattr(main, 'race_manager', manager)
    monkeypatch.setattr(module, 'SimulationEngine', FakeEngine)
    monkeypatch.setattr(module.threading, 'Thread', FakeThread)
    monkeypatch.setattr(main.driver_service, 'get_available_seasons', lambda: [2025, 2024, 1973])
    monkeypatch.setattr(main.driver_service, 'list_drivers',
                        lambda year=None, **_kwargs: DRIVERS if year in (2024, 2025) else [])
    with TestClient(main.app) as client:
        yield SimpleNamespace(client=client, manager=manager, store=store, redis_url=url)
    if url:
        for race_id in manager._engines:
            for suffix in ('meta', 'snapshot', 'state', 'start', 'result'):
                store.delete(f'race:{race_id}:{suffix}')


def test_circuit_catalog_matches_2d_client(context):
    result = context.client.get('/circuits')
    assert result.status_code == 200
    entry = next(c for c in result.json()['circuits'] if c['id'] == 'interlagos')
    assert entry['country']['code'] == 'BR' and entry['city']
    assert entry['simulable'] and len(entry['layouts']) >= 2
    assert all('simulable' in layout and 'is_current' in layout for layout in entry['layouts'])
    assert next(layout for layout in entry['layouts'] if layout['id'] == 'interlagos-1')['simulable']


def test_season_drivers_match_2d_client(context):
    assert context.client.get('/seasons').json() == [2025, 2024, 1973]
    drivers = context.client.get('/seasons/2024/drivers').json()
    assert drivers[0]['id'] == 'max-verstappen'
    assert drivers[0]['team'] == 'Red Bull' and drivers[0]['country']['code'] == 'NL'
    assert context.client.get('/seasons/1800/drivers').json() == []


def test_unavailable_circuit_catalog_returns_503(context):
    context.manager.catalog = None
    assert context.client.get('/circuits').status_code == 503


def test_create_2d_race_keeps_selected_grid_and_configuration(context):
    body = {'circuit': {'id': 'interlagos', 'layout_id': 'interlagos-2'},
            'year': 2023, 'laps': 6, 'grid': ['lando-norris', 'max-verstappen'],
            'weather': 'rain', 'initial_tyre': 'wet',
            'stints': [{'compound': 'wet', 'laps': 2}, {'compound': 'hard', 'laps': 4}]}
    # The season source is mocked, without relying on network access.
    from api import main
    original = main.driver_service.list_drivers
    main.driver_service.list_drivers = lambda **_kwargs: DRIVERS
    try:
        response = context.client.post('/races', json=body)
    finally:
        main.driver_service.list_drivers = original
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['grid'] == body['grid'] and result['initial_weather'] == 'rain'
    assert result['warnings'] and result['ws_path'] == f"/ws/races/{result['race_id']}"
    meta = context.manager.metadata(result['race_id'])
    assert [driver['driver_id'] for driver in meta['drivers']] == body['grid']
    assert meta['track']['pit_lane']['waypoints']
    engine = context.manager._engines[result['race_id']]
    assert engine.kwargs['drivers'][0].starting_tyre_compound.value == 'WET'
    assert engine.kwargs['weather_model'].current.kind.value == 'WET'


def test_minimal_race_returns_ws_path_and_snapshot(context):
    response = context.client.post('/races', json={'laps': 3})
    assert response.status_code == 200
    result = response.json()
    assert result['num_laps'] == 3 and result['ws_path'] == f"/ws/races/{result['race_id']}"
    assert context.client.get(f"/races/{result['race_id']}/snapshot").json()['status'] == 'starting'


@pytest.mark.parametrize('body', [
    {'laps': 0}, {'weather': 'snow'}, {'grid': ['a', 'a']},
    {'laps': 10, 'stints': [{'compound': 'soft', 'laps': 3}]},
    {'unexpected': True},
])
def test_invalid_setup_is_rejected(context, body):
    assert context.client.post('/races', json=body).status_code == 422


def test_unknown_grid_driver_returns_clear_error(context):
    response = context.client.post('/races', json={'year': 2024, 'grid': ['ghost']})
    assert response.status_code == 400 and 'ghost' in response.json()['detail']


def test_unavailable_track_returns_clear_error(context):
    response = context.client.post('/races', json={'track': 'narnia', 'year': 2024})
    assert response.status_code == 400 and 'indisponível' in response.json()['detail']


def test_websocket_unknown_race_closes_4404(context):
    if not context.redis_url:
        pytest.skip('requires isolated Redis')
    with pytest.raises(WebSocketDisconnect) as exc:
        with context.client.websocket_connect('/ws/races/race_nao_existe'):
            pass
    assert exc.value.code == 4404


def test_websocket_replays_start_and_latest_tick_and_forwards_end(context):
    if not context.redis_url:
        pytest.skip('requires isolated Redis')
    result = context.client.post('/races', json={'laps': 1}).json()
    race_id = result['race_id']
    start = {'type': 'race_start', 'race_id': race_id}
    tick = {'type': 'tick', 'sim_ts': 1.0, 'positions': []}
    context.store.set(f'race:{race_id}:start', json.dumps(start))
    context.store.set(f'race:{race_id}:state', json.dumps(tick))
    with context.client.websocket_connect(f'/ws/races/{race_id}') as ws:
        assert ws.receive_json() == start
        assert ws.receive_json() == tick
        end = {'type': 'race_end', 'race_id': race_id}
        context.store.publish(f'race:{race_id}:events', json.dumps(end))
        assert ws.receive_json() == end
