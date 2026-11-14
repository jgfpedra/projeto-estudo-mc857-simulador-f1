"""Contrato live: gaps, colisões, fontes e ciclo de vida da corrida."""
import math
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.race_manager import CollisionAggregator, TimingTracker
from api.providers.race_data import OpenF1Provider, ProviderChain
from domain import Track


def test_gap_uses_leader_crossing_time_and_handles_laps_and_leader_change():
    tracker = TimingTracker()
    positions = [{'driver_id':'a','progress_m':0.0}, {'driver_id':'b','progress_m':-10.0}]
    tracker.update(positions, 0.0, 100.0)
    assert positions[1]['gap_to_leader_s'] is None
    positions[0]['progress_m'], positions[1]['progress_m'] = 20.0, 10.0
    tracker.update(positions, 2.0, 100.0)
    assert positions[1]['gap_to_leader_s'] == pytest.approx(1.0)
    positions[0]['progress_m'], positions[1]['progress_m'] = 150.0, 40.0
    tracker.update(positions, 15.0, 100.0)
    assert positions[1]['laps_behind'] == 1 and positions[1]['gap_to_leader_s'] is None
    positions[0]['progress_m'] = 100.0  # o líder voltou; histórico antigo fica inválido
    tracker.update(positions, 16.0, 100.0)
    assert positions[1]['gap_to_leader_s'] is None
    positions.reverse()
    tracker.update(positions, 17.0, 100.0)
    assert positions[1]['gap_to_leader_s'] is None


def test_collision_aggregates_substeps_and_releases_contact():
    aggregator = CollisionAggregator()
    raw = [{'drv_a':'b','drv_b':'a','sub':1,'f_n':100,'cx':1,'cy':2},
           {'drv_a':'a','drv_b':'b','sub':1,'f_n':60,'cx':1,'cy':2},
           {'drv_a':'a','drv_b':'b','sub':2,'f_n':30,'cx':1,'cy':2}]
    first = aggregator.update(raw, 1.0, {'a':'A','b':'B'})
    assert len(first) == 1 and first[0]['impact_force_n'] == 160
    assert not aggregator.update(raw, 1.1, {})
    aggregator.update([], 1.7, {})
    assert len(aggregator.update(raw, 1.8, {})) == 1
    penetrated = [{'drv_a':'c','drv_b':'d','f_n':0.0,'penetration_m':0.002}]
    assert aggregator.update(penetrated, 2.0, {})[0]['penetration_m'] == 0.002


def test_openf1_primary_geometry_and_drivers():
    # Perímetro fechado de 4000 m com linha de chegada numa reta longa.
    def point(i):
        d = i * 20
        if d < 600: return (600+d, 0)
        if d < 1400: return (1200, d-600)
        if d < 2600: return (1200-(d-1400), 800)
        if d < 3400: return (0, 800-(d-2600))
        return (d-3400, 0)
    def fetch(resource, **params):
        if resource == 'sessions': return [{'session_key':9,'circuit_short_name':'Interlagos'}]
        if resource == 'drivers': return [{'driver_number':1,'name_acronym':'VER','full_name':'Max Verstappen','team_name':'Red Bull Racing','team_colour':'3671C6'}]
        if resource == 'laps': return [{'date_start':'2023-11-05T12:00:00+00:00','lap_duration':80.0,'lap_number':2,'is_pit_out_lap':False}]
        return [{'date':f'{i:03}', 'x':10*point(i)[0], 'y':10*point(i)[1]} for i in range(200)]
    track, drivers, source = OpenF1Provider(fetch=fetch).load('interlagos',2023)
    assert track.source == 'openf1' and track.start_finish_waypoint == 0
    assert track.length_m == pytest.approx(4000, rel=.001)
    assert drivers[0]['driver_id'] == 'max-verstappen'
    assert drivers[0]['team_color'] == '#3671C6' and source['driver_source'] == 'openf1'


def test_provider_chain_keeps_primary_drivers_if_geometry_falls_back():
    track = Track.from_waypoints('fallback', [(0,0),(1,0),(1,1),(0,1)])
    primary = SimpleNamespace(load=lambda *_: (None,[{'driver_id':'a'}],{'driver_source':'openf1'}))
    fallback = SimpleNamespace(load=lambda *_: (track,[{'driver_id':'b'}],{'track_source':'local','driver_source':'local'}))
    result, drivers, source = ProviderChain([primary,fallback]).load('x',2023)
    assert result is track and drivers[0]['driver_id'] == 'a'
    assert source == {'track_source':'local','driver_source':'openf1'}


def test_snapshot_endpoint_returns_snapshot_and_404(monkeypatch):
    from api.main import app, race_manager
    monkeypatch.setattr(race_manager, 'snapshot', lambda race_id: {'race_id':race_id,'status':'running','sim_ts':1,'last_tick':None,'classification':None} if race_id=='ok' else None)
    with TestClient(app) as client:
        assert client.get('/races/ok/snapshot').json()['status'] == 'running'
        assert client.get('/races/missing/snapshot').status_code == 404


def test_driver_catalog_prefers_openf1_and_uses_fallback():
    from database.openf1_driver_db import OpenF1DriverDatabase
    class Client:
        def get(self, resource, **params):
            if resource == 'sessions':
                return [{'session_key': 42, 'date_start':'2024-11-01'}]
            return [{'full_name':'Max Verstappen', 'name_acronym':'VER', 'driver_number':1,
                     'team_name':'Red Bull Racing', 'team_colour':'3671c6'}]
    fallback = SimpleNamespace(load_season_drivers=lambda year: [{'id':'fallback','name':'Fallback','abbreviation':'FBK'}],
                               get_available_seasons=lambda all_historical=False: [2024, 2023])
    db = OpenF1DriverDatabase(client=Client(),fallback=fallback)
    assert db.get_driver_by_id('VER', year=2024)['team_color'] == '#3671C6'
    assert db.get_all_drivers(year=2024, query='max')[0]['permanent_number'] == 1
    assert db.get_all_drivers(year=2022)[0]['id'] == 'fallback'


def test_snapshot_preserves_classification_after_finish():
    import json
    from engine.events import RaceStartEvent, RaceEndEvent
    from api.race_manager import LivePublisher
    class Pipeline:
        def __init__(self): self.values = {}
        def set(self, key, value, ex=None): self.values[key] = value; return self
        def publish(self, channel, value): return self
        def execute(self): return []
    pipe = Pipeline()
    publisher = LivePublisher(SimpleNamespace(pipeline=lambda transaction: pipe), 'race-1')
    publisher.publish(RaceStartEvent(race_id='race-1'))
    assert json.loads(pipe.values['race:race-1:start'])['schema_version'] == 1
    publisher.publish(RaceEndEvent(race_id='race-1', sim_ts=99, final_classification=[{'driver_id':'a'}]))
    snapshot = json.loads(pipe.values['race:race-1:snapshot'])
    assert snapshot['status'] == 'finished' and snapshot['sim_ts'] == 99
    assert snapshot['classification'] == [{'driver_id':'a'}]


def test_create_race_accepts_season_and_rejects_conflicting_year(monkeypatch):
    from fastapi import HTTPException
    from api.main import create_race, race_manager
    from api.schemas import RaceSetupRequest
    calls = []
    def create(laps, track, year, num_drivers, layout_id=None):
        calls.append((laps,track,year,num_drivers,layout_id))
        return 'race-1', SimpleNamespace(name='Interlagos'), SimpleNamespace(num_laps=laps)
    monkeypatch.setattr(race_manager,'create_race',create)
    assert create_race(RaceSetupRequest(season=2025, num_drivers=10)).race_id == 'race-1'
    assert calls[0][2:] == (2025,10,None)
    with pytest.raises(HTTPException) as error:
        create_race(RaceSetupRequest(year=2024,season=2025))
    assert error.value.status_code == 400


def test_metadata_uses_exact_engine_geometry_and_unique_drivers(monkeypatch):
    import json
    import api.race_manager as module
    from api.providers.race_data import FallbackProvider
    class Store:
        def __init__(self): self.values = {}
        def ping(self): return True
        def set(self, key, value, ex=None): self.values[key] = value
    class Engine:
        def __init__(self, **kwargs):
            self.track = kwargs['track']
            self.drivers = kwargs['drivers']
            self.physics = SimpleNamespace(contact_collector=None)
        def set_controller(self, *args): pass
    class Thread:
        def __init__(self, **kwargs): pass
        def start(self): pass
    engines=[]
    def make_engine(**kwargs):
        engine=Engine(**kwargs); engines.append(engine); return engine
    monkeypatch.setattr(module,'SimulationEngine',make_engine)
    monkeypatch.setattr(module,'RuleBasedRaceController',lambda *a, **k: object())
    monkeypatch.setattr(module.threading,'Thread',Thread)
    store=Store()
    race_id, track, _=module.RaceManager(store, provider=FallbackProvider()).create_race(3,'interlagos',2023,10)
    meta=json.loads(store.values[f'race:{race_id}:meta'])
    assert engines[0].track is track
    assert meta['track']['waypoints'] == [list(p) for p in track.waypoints]
    assert meta['track']['width_m'] == track.width_m
    assert meta['layout_id'] == 'interlagos-2'
    assert meta['layout_reference']['basis'] == 'season'
    assert [d['driver_id'] for d in meta['drivers']] == [d.driver_id for d in engines[0].drivers]
    assert len({d['driver_id'] for d in meta['drivers']}) == 10
    assert all(d['team_color'].startswith('#') for d in meta['drivers'])


def test_engine_projection_has_right_positive_lateral():
    from dataclasses import replace
    from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
    from engine import SimulationEngine
    track = Track.from_waypoints('square', [(0,0),(100,0),(100,100),(0,100)])
    driver = DEFAULT_DRIVERS[0]
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False), track, [driver])
    engine.states = {driver.driver_id: driver.initial_state()}
    engine.handles = {driver.driver_id: object()}
    engine.prev_waypoint_idx = {driver.driver_id: 0}
    engine.physics = SimpleNamespace(get_state=lambda _: {'x':25.0,'y':-2.0,'speed_mps':10.0,'heading_rad':0.0})
    engine._update_race_progress(0.1)
    assert engine.race_s_m[driver.driver_id] == pytest.approx(25.0)
    assert engine.race_lateral_m[driver.driver_id] == pytest.approx(2.0)
    assert engine.race_progress_m[driver.driver_id] == pytest.approx(25.0)


def test_f1db_history_respects_exact_seasons_and_unknown_gaps():
    from api.providers.f1db_layouts import load_layout_catalog
    catalog = load_layout_catalog()
    circuit = catalog.find_circuit('São Paulo')
    assert circuit['id'] == 'interlagos'
    assert catalog.find_layout(circuit,1975)['id'] == 'interlagos-1'
    assert catalog.find_layout(circuit,2023)['id'] == 'interlagos-2'
    assert catalog.find_layout(circuit,2020) is None
    assert catalog.provenance['source'] == 'F1DB (Formula 1 Database)'


def test_old_telemetry_limit_is_explicit_and_no_incorrect_fallback(monkeypatch):
    from api.providers.race_data import FallbackProvider, OpenF1Provider, ProviderChain
    monkeypatch.setattr('api.providers.race_data.load_live_track', lambda **kwargs: pytest.fail('não deveria carregar uma pista antiga sem geometria'))
    def no_request(*args, **kwargs):
        pytest.fail('OpenF1 não deve ser consultada para antes de 2023')
    with pytest.raises(ValueError,match='Sem geometria histórica verificada'):
        ProviderChain([OpenF1Provider(fetch=no_request), FallbackProvider()]).load('interlagos',1975)


def test_openf1_refuses_ambiguous_country_and_selects_exact_circuit():
    from api.providers.race_data import AmbiguousCircuitError, select_session
    sessions = [{'circuit_short_name':'Imola','location':'Imola','country_name':'Italy','session_key':1},
                {'circuit_short_name':'Monza','location':'Monza','country_name':'Italy','session_key':2}]
    assert select_session('Monza',sessions)['session_key'] == 2
    with pytest.raises(AmbiguousCircuitError):
        select_session('Italy',sessions)


def test_layout_history_endpoint_and_conflicting_layout(monkeypatch):
    from api.main import app
    from api.race_manager import RaceManager
    from api.providers.race_data import FallbackProvider
    class Store:
        def ping(self): return True
    manager = RaceManager(Store(), provider=FallbackProvider())
    with pytest.raises(ValueError, match='não é confirmado'):
        manager.create_race(1,'interlagos',2023,layout_id='interlagos-1')
    with TestClient(app) as client:
        catalog = client.get('/circuits').json()
        assert any(entry['id'] == 'interlagos' for entry in catalog['circuits'])
        result = client.get('/circuits/interlagos/layouts')
        assert result.status_code == 200
        assert [entry['id'] for entry in result.json()['layouts']] == ['interlagos-1','interlagos-2']
        assert result.json()['catalog']['license'] == 'CC-BY-4.0'
        assert client.get('/circuits/no-such-circuit/layouts').status_code == 404


def test_f1db_refresh_detects_layout_changes_and_ignores_metadata():
    from scripts.tracks.refresh_f1db_layouts import find_changes
    old = {'circuits':[{'id':'interlagos','layouts':[{'id':'interlagos-2','years':['2021-2024'],'length_km':4.309,'turns':15}]}]}
    new = {'circuits':[{'id':'interlagos','layouts':[{'id':'interlagos-2','years':['2021-2025'],'length_km':4.309,'turns':15},
                                                    {'id':'interlagos-3','years':['2026'],'length_km':4.4,'turns':16}]}]}
    assert find_changes(old,new) == [
        {'circuit_id':'interlagos','layout_id':'interlagos-2','change':'alterado'},
        {'circuit_id':'interlagos','layout_id':'interlagos-3','change':'adicionado'}]
    assert find_changes(old,dict(old, generated_at='other')) == []


def test_race_creation_rejects_unknown_setup_fields():
    from api.main import app
    with TestClient(app) as client:
        response = client.post('/races', json={'laps': 1, 'unsupported_option': True})
    assert response.status_code == 422
    assert any(item['type'] == 'extra_forbidden' for item in response.json()['detail'])


def test_2d_setup_passes_selected_grid_and_options(monkeypatch):
    from api import main
    from api.schemas import RaceSetupRequest
    selected = [
        {'id': 'driver-b', 'name': 'Driver B', 'abbreviation': 'DRB', 'permanent_number': 7,
         'team_name': 'B', 'team_color': '#123456'},
        {'id': 'driver-a', 'name': 'Driver A', 'abbreviation': 'DRA', 'permanent_number': 8,
         'team_name': 'A', 'team_color': '#654321'},
    ]
    monkeypatch.setattr(main.driver_service, 'list_drivers', lambda **_: selected)
    calls = []
    def create(*args, **kwargs):
        calls.append((args, kwargs))
        return 'race-2d', SimpleNamespace(name='Interlagos'), SimpleNamespace(num_laps=args[0])
    monkeypatch.setattr(main.race_manager, 'create_race', create)
    req = RaceSetupRequest.model_validate({'laps': 4, 'circuit': {'id': 'interlagos', 'layout_id': 'interlagos-2'},
        'year': 2023, 'grid': ['driver-a', 'driver-b'], 'weather': 'rain', 'initial_tyre': 'wet',
        'stints': [{'compound': 'wet', 'laps': 4}]})
    result = main.create_race(req)
    assert calls[0][0] == (4, 'interlagos', 2023)
    assert [d['driver_id'] for d in calls[0][1]['selected_roster']] == ['driver-a', 'driver-b']
    assert calls[0][1]['weather'] == 'rain' and calls[0][1]['initial_tyre'] == 'wet'
    assert result.ws_path == '/ws/races/race-2d' and result.warnings


def test_2d_options_reach_engine_and_metadata(monkeypatch):
    import api.race_manager as module
    from api.providers.race_data import FallbackProvider, driver_record
    from domain import TyreCompound, WeatherKind
    class Store:
        def __init__(self): self.values = {}
        def ping(self): return True
        def set(self, key, value, ex=None): self.values[key] = value
    engines = []
    class Engine:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.physics = SimpleNamespace(contact_collector=None)
            engines.append(self)
        def set_controller(self, *_): pass
    class Thread:
        def __init__(self, **kwargs): pass
        def start(self): pass
    monkeypatch.setattr(module, 'SimulationEngine', Engine)
    monkeypatch.setattr(module, 'RuleBasedRaceController', lambda *a, **k: object())
    monkeypatch.setattr(module.threading, 'Thread', Thread)
    roster = [driver_record('TST', 'Test Driver', 77, 'Team', '123456')]
    store = Store()
    race_id, _, _ = module.RaceManager(store, provider=FallbackProvider()).create_race(
        1, 'interlagos', 2023, num_drivers=1, selected_roster=roster,
        weather='rain', initial_tyre='wet')
    assert engines[0].kwargs['drivers'][0].starting_tyre_compound == TyreCompound.WET
    assert engines[0].kwargs['weather_model'].current.kind == WeatherKind.WET
    import json
    assert json.loads(store.values[f'race:{race_id}:meta'])['drivers'][0]['driver_id'] == 'test-driver'
