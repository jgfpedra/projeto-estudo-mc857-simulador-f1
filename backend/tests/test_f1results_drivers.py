"""Catálogo offline, grids históricos reais e exposição pela API."""
import pytest
from fastapi.testclient import TestClient

from database.f1results_database import AmbiguousHistoricalEvent, F1ResultsDriverDatabase
from database.openf1_driver_db import OpenF1DriverDatabase
from api.providers.race_data import AmbiguousCircuitError, HistoricalRosterProvider, default_provider


def test_real_grids_and_offline_seasons():
    db = F1ResultsDriverDatabase()
    event, roster = db.race_roster('interlagos', 1973)
    assert event['grand_prix'] == '1973 Brazilian Grand Prix'
    assert len(roster) == 20
    assert [(r['name'], r['number'], r['historical_grid_position']) for r in roster[:2]] == [
        ('Ronnie Peterson', 2, 1), ('Emerson Fittipaldi', 1, 2)]
    assert roster[0]['team_name'] == 'John Player Team Lotus'
    assert roster[0]['abbreviation_source'] == 'generated_from_name'
    assert roster[0]['team_color_source'] == 'generated_for_team'
    assert roster[0]['team_color'] == roster[1]['team_color'] != '#808080'
    assert all(r['historical_grid_position'] > 0 for r in roster)
    assert len(db.race_roster('interlagos', 1979)[1]) == 24
    assert {'Ronnie Peterson', 'Emerson Fittipaldi'} <= {r['name'] for r in db.load_season_drivers(1973)}
    assert 1950 in db.get_available_seasons() and 2026 in db.get_available_seasons()
    assert len({r['id'] for r in db.load_season_drivers(1973)}) == len(db.load_season_drivers(1973))
    modern = {r['name']: r for r in db.race_roster('monza', 2025)[1]}
    assert modern['Max Verstappen']['team_color'] == '#3671C6'
    assert modern['Lando Norris']['team_color'] == '#FF8000'


def test_ambiguous_event_requires_selection():
    db = F1ResultsDriverDatabase()
    with pytest.raises(AmbiguousHistoricalEvent):
        db.race_roster('spielberg', 2020)
    with pytest.raises(AmbiguousCircuitError):
        HistoricalRosterProvider().load('spielberg', 2020)
    event = db.events(2020, 'spielberg')[0]
    selected, drivers = db.race_roster('spielberg', 2020, event['grand_prix'])
    assert selected['id'] == event['id'] and drivers


def test_default_provider_combines_historical_geometry_and_roster():
    track, drivers, source = default_provider().load('interlagos', 1973)
    assert track.length_m == pytest.approx(7960, abs=.01)
    assert [d['name'] for d in drivers[:2]] == ['Ronnie Peterson', 'Emerson Fittipaldi']
    assert isinstance(drivers[0]['team'], str)
    assert source['driver_source'] == 'f1results_database'
    assert source['driver_provenance']['grand_prix'] == source['track_provenance']['grand_prix']


def test_legacy_season_never_requests_openf1():
    class Client:
        def get(self, *a, **k):
            raise AssertionError('unexpected network request')
    db = OpenF1DriverDatabase(client=Client())
    assert any(d['name'] == 'Emerson Fittipaldi' for d in db.load_season_drivers(1973))
    assert db.load_season_drivers(1900) == []


def test_api_historical_catalog_and_grid():
    from api.main import app
    with TestClient(app) as client:
        assert 1950 in client.get('/seasons').json()
        drivers = client.get('/seasons/1973/drivers').json()
        assert any(d['name'] == 'Emerson Fittipaldi' and d['source'] == 'f1results_database' for d in drivers)
        circuits = client.get('/circuits?season=1973').json()
        interlagos = next(c for c in circuits['circuits'] if c['id'] == 'interlagos')
        assert interlagos['events'][0]['geometry_available'] is True
        grid = client.get('/seasons/1973/circuits/interlagos/drivers').json()
        assert [d['name'] for d in grid['drivers'][:2]] == ['Ronnie Peterson', 'Emerson Fittipaldi']
        assert client.get('/seasons/2020/circuits/spielberg/drivers').status_code == 409
        events = client.get('/seasons/2020/events').json()['events']
        event = next(e for e in events if e['circuit_id'] == 'spielberg')
        assert client.get('/seasons/2020/circuits/spielberg/drivers',
                          params={'grand_prix': event['grand_prix']}).status_code == 200
        assert any(e['circuit_id'] is None for e in events)
        assert 'catalog' in client.get('/circuits').json()


def test_combination_keeps_primary_drivers_and_rejects_different_gp():
    from types import SimpleNamespace
    from api.providers.race_data import ProviderChain
    track = object()
    first = SimpleNamespace(load=lambda *_: (None, [{'driver_id': 'primary'}], {'driver_source': 'openf1'}))
    second = SimpleNamespace(load=lambda *_: (track, [{'driver_id': 'other'}], {'track_source': 'local'}))
    _, drivers, source = ProviderChain([first, second]).load('interlagos', 2023)
    assert drivers[0]['driver_id'] == 'primary' and source['driver_source'] == 'openf1'
    a = SimpleNamespace(load=lambda *_: (None, [{'driver_id': 'a'}],
             {'driver_source': 'f1results_database', 'driver_provenance': {'grand_prix': 'A'}}))
    b = SimpleNamespace(load=lambda *_: (track, [],
             {'track_source': 'f1results_svg', 'track_provenance': {'grand_prix': 'B'}}))
    with pytest.raises(AmbiguousCircuitError):
        ProviderChain([a, b]).load('interlagos', 2020)
