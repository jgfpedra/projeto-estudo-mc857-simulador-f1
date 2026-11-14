"""Fonte de pilotos OpenF1, com fallback injetável para temporadas legadas."""
from __future__ import annotations

import logging
import re
from typing import Optional
from database.driver_db import DriverDatabase, FastF1DriverDatabase
from integrations.openf1 import OpenF1Client

logger = logging.getLogger(__name__)


class OpenF1DriverDatabase(DriverDatabase):
    def __init__(self, client=None, fallback=None, default_year=2024):
        self.client = client or OpenF1Client()
        self.fallback = fallback or FastF1DriverDatabase(default_year=default_year)
        self.default_year = default_year
        self._cache = {}

    def load_season_drivers(self, year):
        if year in self._cache:
            return self._cache[year]
        try:
            if year < 2023:
                raise ValueError('OpenF1 fornece dados históricos a partir de 2023')
            sessions = self.client.get('sessions', year=year, session_name='Race')
            sessions = sorted(sessions, key=lambda s: s.get('date_start', ''), reverse=True)
            if not sessions:
                raise ValueError('temporada sem sessões')
            rows = self.client.get('drivers', session_key=sessions[0]['session_key'])
            result = []
            for row in rows:
                name = row.get('full_name')
                if not name:
                    continue
                code = row.get('name_acronym') or ''
                country = row.get('country_code')
                team = row.get('team_name') or 'Unknown'
                color = str(row.get('team_colour') or '').lstrip('#')
                color = '#'+color.upper() if re.fullmatch('[0-9A-Fa-f]{6}', color) else None
                result.append({'id': re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-'),
                    'name': name, 'full_name': name, 'first_name': row.get('first_name'),
                    'last_name': row.get('last_name'), 'abbreviation':code,
                    'permanent_number':row.get('driver_number'), 'team_name':team,
                    'team_color':color, 'country_code':country, 'nationality_country_id':country,
                    'team':{'id':None, 'name':team, 'color':color}})
            if not result:
                raise ValueError('sessão sem pilotos')
            self._cache[year] = sorted(result, key=lambda d:(d['team_name'], d['name']))
        except Exception as exc:
            logger.warning('OpenF1 indisponível para pilotos de %s: %s', year, exc)
            return self.fallback.load_season_drivers(year)
        return self._cache[year]

    def get_all_drivers(self, year=None, query=None, nationality=None, limit=None, offset=None):
        drivers = list(self.load_season_drivers(year if isinstance(year,int) else self.default_year))
        if query:
            term = query.strip().lower()
            drivers = [d for d in drivers if any(term in str(d.get(k) or '').lower()
                       for k in ('id','name','first_name','last_name','full_name','abbreviation','team_name'))]
        if nationality:
            drivers = [d for d in drivers if str(d.get('country_code') or '').lower() == nationality.strip().lower()]
        start = offset if isinstance(offset,int) and offset > 0 else 0
        return drivers[start:start+limit] if isinstance(limit,int) else drivers[start:]

    def get_driver_by_id(self, driver_id, year=None):
        key = driver_id.strip().lower().replace('_','-')
        return next((d for d in self.get_all_drivers(year=year)
                     if d['id'] == key or d['abbreviation'].lower() == key), None)

    def get_available_seasons(self, all_historical=False):
        # Preserva as temporadas anteriores a 2023 suportadas pelo adaptador legado.
        return self.fallback.get_available_seasons(all_historical=all_historical)
