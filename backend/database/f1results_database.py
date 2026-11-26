"""Catálogo desacoplado de eventos e pilotos históricos do F1 Results Database."""
from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import re
import unicodedata

from .driver_db import DriverDatabase
from .team_colors import resolve_team_color

DEFAULT_PATH = Path(__file__).resolve().parents[1] / 'config' / 'historical_tracks' / 'f1results_rosters.json'


@lru_cache(maxsize=4)
def load_f1results_catalog(path=None):
    from storage import postgres
    if path is None and not os.environ.get('F1_RESULTS_ROSTERS_PATH') and postgres.configured():
        data = postgres.catalog('f1results_rosters')
    else:
        selected = Path(path or os.environ.get('F1_RESULTS_ROSTERS_PATH') or DEFAULT_PATH)
        data = json.loads(selected.read_text(encoding='utf-8'))
    if not isinstance(data.get('drivers'), dict) or not isinstance(data.get('events'), list):
        raise ValueError('Catálogo F1 Results de pilotos inválido')
    return data


class AmbiguousHistoricalEvent(ValueError):
    """Mais de um GP foi realizado no mesmo circuito e temporada."""


def _abbreviation(name):
    clean = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    words = re.findall(r'[A-Za-z]+', clean)
    return (words[-1][:3] if words else 'UNK').upper()


def _with_display_color(record):
    color, source = resolve_team_color(record['team_name'])
    return {**record, 'team_color': color, 'team_color_source': source,
            'team': {**record['team'], 'color': color}}


class F1ResultsDriverDatabase(DriverDatabase):
    """Metadados locais versionados com siglas e cores de exibição derivadas."""
    def __init__(self, data=None, default_year=2024):
        from storage import postgres
        self._postgres = data is None and not os.environ.get('F1_RESULTS_ROSTERS_PATH') and postgres.configured()
        self.data = data if data is not None else load_f1results_catalog()
        self.default_year = default_year
        self._seasons = {}

    @property
    def provenance(self):
        return {k: self.data.get(k) for k in ('source', 'source_url', 'license', 'release', 'db_sha256')}

    def events(self, season=None, circuit_id=None):
        return [e for e in self.data['events']
                if (season is None or e['season'] == season)
                and (circuit_id is None or e.get('circuit_id') == circuit_id)]

    def event_for_race(self, circuit_id, season, grand_prix=None):
        events = self.events(season, circuit_id)
        if grand_prix is not None:
            events = [e for e in events if e['grand_prix'] == grand_prix]
        if len(events) > 1:
            raise AmbiguousHistoricalEvent(f"Há mais de um GP em '{circuit_id}' na temporada {season}; selecione um evento específico.")
        return events[0] if events else None

    def _record(self, entry, event):
        driver_id, number, team, grid = entry
        raw = self.data['drivers'].get(str(driver_id))
        if not raw:
            raise ValueError(f'Piloto histórico {driver_id} ausente no catálogo')
        name = raw['name']
        return _with_display_color({'id': f'f1results-{driver_id}', 'driver_id': f'f1results-{driver_id}',
                'name': name, 'full_name': name, 'abbreviation': _abbreviation(name),
                'abbreviation_source': 'generated_from_name', 'number': number, 'permanent_number': None,
                'team_name': team,
                'country_name': raw.get('nationality'), 'country_code': None,
                'team': {'id': None, 'name': team},
                'source': 'f1results_database', 'source_grand_prix': event['grand_prix'],
                'historical_grid_position': grid})

    def race_roster(self, circuit_id, season, grand_prix=None):
        event = self.event_for_race(circuit_id, season, grand_prix)
        if event is None:
            return None, []
        starters = [e for e in event['entries'] if isinstance(e[3], int) and e[3] > 0]
        starters.sort(key=lambda entry: (entry[3], entry[0]))
        return event, [self._record(entry, event) for entry in starters]

    def load_season_drivers(self, year):
        if year not in self._seasons and self._postgres:
            from storage import postgres
            # Rows imported before the palette was added still contain gray.
            self._seasons[year] = [_with_display_color(record) for record in postgres.season_drivers(year)]
        if year not in self._seasons:
            # Um piloto pode mudar de equipe durante a temporada: devolvemos a última
            # inscrição registrada e informamos o GP de origem daquele registro.
            selected = {}
            for event in self.events(season=year):
                for entry in event['entries']:
                    record = self._record(entry, event)
                    selected[record['id']] = record
            self._seasons[year] = sorted(selected.values(), key=lambda d: (d['name'].casefold(), d['id']))
        return list(self._seasons[year])

    def get_all_drivers(self, year=None, query=None, nationality=None, limit=None, offset=None):
        drivers = self.load_season_drivers(year if isinstance(year, int) else self.default_year)
        if query:
            key = query.casefold().strip()
            drivers = [d for d in drivers if key in ' '.join(str(d.get(k) or '') for k in
                       ('id', 'name', 'abbreviation', 'team_name')).casefold()]
        if nationality:
            key = nationality.casefold().strip()
            drivers = [d for d in drivers if (d.get('country_name') or '').casefold() == key]
        start = offset if isinstance(offset, int) and offset > 0 else 0
        return drivers[start:start+limit] if isinstance(limit, int) else drivers[start:]

    def get_driver_by_id(self, driver_id, year=None):
        key = driver_id.casefold().strip()
        matches = [d for d in self.get_all_drivers(year=year)
                   if d['id'].casefold() == key or d['abbreviation'].casefold() == key]
        return matches[0] if len(matches) == 1 else None

    def get_available_seasons(self, all_historical=False):
        return sorted({e['season'] for e in self.data['events']}, reverse=True)


def race_driver_record(record):
    """Adaptar um registro do catálogo ao contrato dos pilotos da corrida."""
    return {key: record[key] for key in (
        'driver_id', 'name', 'abbreviation', 'number', 'team_color',
        'abbreviation_source', 'team_color_source', 'historical_grid_position', 'country_name', 'country_code'
    )} | {'team': record['team_name']}


def roster_provenance(database, event):
    return {**database.provenance, 'grand_prix': event['grand_prix'],
            'grid': 'starting_grid_position', 'abbreviation': 'generated_from_name',
            'team_color': 'display_palette'}
