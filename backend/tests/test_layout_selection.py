"""A temporada dos pilotos e o traçado explicitamente escolhido são independentes."""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api import main
from api.providers.f1db_layouts import load_layout_catalog
from api.providers.historical_f1results import HistoricalResultsProvider
from api.providers.track_reference import candidate_reference_years
from api.race_manager import RaceManager
from database.f1results_database import F1ResultsDriverDatabase, race_driver_record


class Store:
    def __init__(self): self.values = {}
    def ping(self): return True
    def set(self, key, value, ex=None): self.values[key] = value
    def get(self, key): return self.values.get(key)


class Engine:
    def __init__(self, **kwargs): self.physics = SimpleNamespace(contact_collector=None)
    def set_controller(self, *_): pass


class Thread:
    def __init__(self, **_): pass
    def start(self): pass


@pytest.fixture
def ctx(monkeypatch):
    import api.race_manager as module
    monkeypatch.setattr(module, 'SimulationEngine', Engine)
    monkeypatch.setattr(module, 'RuleBasedRaceController', lambda *_a, **_k: object())
    monkeypatch.setattr(module.threading, 'Thread', Thread)
    store = Store()
    manager = RaceManager(store, provider=HistoricalResultsProvider())
    monkeypatch.setattr(main, 'race_manager', manager)
    database = F1ResultsDriverDatabase()
    monkeypatch.setattr(main.driver_service, 'list_drivers',
                        lambda year=None, **_kw: database.load_season_drivers(year))
    with TestClient(main.app) as client:
        yield SimpleNamespace(manager=manager, store=store, database=database, http=client)


def test_catalog_shows_real_layouts_and_recorded_years(ctx):
    circuits = ctx.http.get('/circuits').json()['circuits']
    austin = next(c for c in circuits if c['id'] == 'austin')
    assert len(austin['layouts']) == 1
    assert austin['layouts'][0]['years'] == ['2012-2019', '2021-2026']
    assert austin['layouts'][0]['is_current']
    interlagos = next(c for c in circuits if c['id'] == 'interlagos')
    assert [v['id'] for v in interlagos['layouts']] == ['interlagos-1', 'interlagos-2']
    assert all(v['simulable'] for v in interlagos['layouts'])
    monza = next(c for c in circuits if c['id'] == 'monza')
    assert len(monza['layouts']) == 7
    assert len([v for v in monza['layouts'] if v['simulable']]) == 6
    assert not next(v for v in monza['layouts'] if v['id'] == 'monza-2')['simulable']


def test_2d_grid_1968_uses_austin_layout_reference_and_warns(ctx):
    chosen = ctx.database.load_season_drivers(1968)[:20]
    ids = [d['id'] for d in chosen]
    response = ctx.http.post('/races', json={
        'circuit': {'id': 'austin', 'layout_id': 'austin-1'},
        'year': 1968, 'grid': ids, 'laps': 3,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['grid'] == ids
    assert any('1968' in warning and '2025' in warning for warning in body['warnings'])
    meta = ctx.manager.metadata(body['race_id'])
    assert meta['season'] == 1968 and meta['layout_id'] == 'austin-1'
    assert meta['layout_reference']['basis'] == 'selected_layout_reference'
    assert meta['layout_reference']['track_year'] == 2025
    assert meta['sources']['track_reference'] == {
        'driver_season': 1968, 'track_year': 2025, 'basis': 'selected_layout_reference'}
    assert meta['sources']['track_provenance']['season'] == 2025
    assert meta['track']['length_m'] == pytest.approx(5513, abs=.01)
    assert [d['driver_id'] for d in meta['drivers']] == ids
    assert [d['name'] for d in meta['drivers']] == [d['name'] for d in chosen]


def test_explicit_historical_variation_uses_that_layout_not_season_layout(ctx):
    chosen = [race_driver_record(d) for d in ctx.database.load_season_drivers(1968)[:2]]
    race_id, track, _ = ctx.manager.create_race(3, 'monza', 1968, 2, layout_id='monza-1',
                                                selected_roster=chosen)
    meta = ctx.manager.metadata(race_id)
    assert meta['layout_id'] == 'monza-1'
    assert meta['layout_reference']['track_year'] == 1954
    assert track.length_m == pytest.approx(6300, abs=.01)
    assert meta['sources']['track_provenance']['season'] == 1954


def test_matching_season_keeps_actual_layout_and_year(ctx):
    chosen = [race_driver_record(d) for d in ctx.database.load_season_drivers(1973)[:2]]
    race_id, track, _ = ctx.manager.create_race(3, 'interlagos', 1973, 2,
                                                layout_id='interlagos-1', selected_roster=chosen)
    meta = ctx.manager.metadata(race_id)
    assert meta['layout_reference']['basis'] == 'season'
    assert meta['layout_reference']['track_year'] == 1973
    assert 'track_reference' not in meta['sources']
    assert track.length_m == pytest.approx(7960, abs=.01)


def test_mismatched_layout_without_grid_or_unknown_layout_is_rejected(ctx):
    with pytest.raises(ValueError, match='informe o grid'):
        ctx.manager.create_race(1, 'austin', 1968, 2, layout_id='austin-1')
    chosen = [race_driver_record(d) for d in ctx.database.load_season_drivers(1968)[:2]]
    with pytest.raises(ValueError, match='não pertence'):
        ctx.manager.create_race(1, 'austin', 1968, 2, layout_id='monza-1', selected_roster=chosen)


def test_missing_reference_never_substitutes_a_different_layout(ctx):
    chosen = [race_driver_record(d) for d in ctx.database.load_season_drivers(1968)[:2]]
    with pytest.raises(ValueError, match='Geometria indisponível'):
        ctx.manager.create_race(1, 'monaco', 1968, 2, layout_id='monaco-1', selected_roster=chosen)


def test_valid_season_falls_back_to_same_layout_if_provider_unavailable(ctx):
    historical = HistoricalResultsProvider()
    class Provider:
        def load(self, circuit, year):
            if year == 1975:
                raise ValueError('Sem geometria para o ano solicitado')
            return historical.load(circuit, year)
    ctx.manager.provider = Provider()
    chosen = [race_driver_record(d) for d in ctx.database.load_season_drivers(1975)[:2]]
    race_id, track, _ = ctx.manager.create_race(3, 'interlagos', 1975, 2,
                                                layout_id='interlagos-1', selected_roster=chosen)
    meta = ctx.manager.metadata(race_id)
    assert meta['season'] == 1975 and meta['layout_id'] == 'interlagos-1'
    assert meta['layout_reference']['track_year'] != 1975
    assert meta['layout_reference']['track_year'] in (1973, 1974, 1976, 1977, 1979, 1980)
    assert track.source == 'f1results_svg'


def test_reference_candidates_never_cross_f1db_layouts():
    catalog = load_layout_catalog()
    circuit = catalog.find_circuit('monza')
    layout = next(item for item in circuit['layouts'] if item['id'] == 'monza-1')
    years = candidate_reference_years(catalog, circuit, layout)
    assert years and all(catalog.find_layout(circuit, year)['id'] == 'monza-1' for year in years)


def test_default_provider_preserves_selected_grid_without_network(ctx, monkeypatch):
    from api.providers import race_data
    monkeypatch.setattr(race_data.OpenF1Provider, 'load',
                        lambda *_: (_ for _ in ()).throw(ValueError('sem rede')))
    monkeypatch.setattr(race_data, 'load_live_track',
                        lambda **_kw: (_ for _ in ()).throw(ValueError('sem cache FastF1')))
    ctx.manager.provider = race_data.default_provider()
    chosen = ctx.database.load_season_drivers(1968)[:20]
    response = ctx.http.post('/races', json={
        'circuit': {'id': 'austin', 'layout_id': 'austin-1'}, 'year': 1968,
        'grid': [d['id'] for d in chosen], 'laps': 1,
    })
    assert response.status_code == 200, response.text
    meta = ctx.manager.metadata(response.json()['race_id'])
    assert meta['season'] == 1968 and meta['layout_reference']['track_year'] == 2025
    assert meta['sources']['track_source'] == 'f1results_svg'
    assert meta['sources']['driver_source'] == 'season_selection'
    assert [d['driver_id'] for d in meta['drivers']] == [d['id'] for d in chosen]


def test_warning_preserves_stint_warning_and_reports_track_reference(ctx):
    ids = [d['id'] for d in ctx.database.load_season_drivers(1968)[:2]]
    result = ctx.http.post('/races', json={
        'circuit': {'id': 'austin', 'layout_id': 'austin-1'}, 'year': 1968,
        'grid': ids, 'laps': 2, 'stints': [{'compound': 'soft', 'laps': 2}],
    })
    assert result.status_code == 200
    warnings = result.json()['warnings']
    assert any('stints' in warning for warning in warnings)
    assert any('1968' in warning and '2025' in warning for warning in warnings)


def test_2d_historical_grid_real_engine_redis_and_websocket(monkeypatch):
    import os
    import redis
    url = os.environ.get('TEST_REDIS_URL')
    if not url:
        pytest.skip('requires an isolated Redis server')
    client = redis.Redis.from_url(url, decode_responses=True)
    manager = RaceManager(client, provider=HistoricalResultsProvider())
    monkeypatch.setattr(main, 'race_manager', manager)
    monkeypatch.setattr(main, 'REDIS_URL', url)
    database = F1ResultsDriverDatabase()
    monkeypatch.setattr(main.driver_service, 'list_drivers',
                        lambda year=None, **_kw: database.load_season_drivers(year))
    ids = [d['id'] for d in database.load_season_drivers(1968)[:20]]
    race_id = None
    try:
        with TestClient(main.app) as http:
            response = http.post('/races', json={
                'circuit': {'id': 'austin', 'layout_id': 'austin-1'},
                'year': 1968, 'grid': ids, 'laps': 1,
            })
            assert response.status_code == 200, response.text
            race_id = response.json()['race_id']
            meta = http.get(f'/races/{race_id}').json()
            assert meta['season'] == 1968 and meta['layout_reference']['track_year'] == 2025
            assert [d['driver_id'] for d in meta['drivers']] == ids
            with http.websocket_connect(f'/ws/races/{race_id}') as ws:
                for _ in range(12):
                    event = ws.receive_json()
                    if event['type'] == 'tick':
                        break
                assert event['type'] == 'tick'
                assert {position['driver_id'] for position in event['positions']} == set(ids)
                assert all(len(position['position_xy']) == 2 for position in event['positions'])
    finally:
        if race_id:
            with manager._engines_lock:
                engine, thread = manager._engines.get(race_id), manager._threads.get(race_id)
            if engine:
                engine.race_finished = True
            if thread:
                thread.join(timeout=20)
                assert not thread.is_alive()
            for suffix in ('meta', 'snapshot', 'state', 'start', 'result'):
                client.delete(f'race:{race_id}:{suffix}')
