"""Fontes intercambiáveis para metadados de pilotos e geometria de corrida.

OpenF1 é consultada primeiro. A geometria é aceita somente a partir de uma
volta cronometrada completa; quando não há dados válidos usamos o traçado
congelado local, com a proveniência divulgada na resposta.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import math
import re
from typing import Protocol
from integrations.openf1 import OpenF1Client
from .f1db_layouts import normalize

from config.live_tracks import load_live_track
from domain import Track

logger = logging.getLogger(__name__)
# Dados locais para funcionamento sem rede. Não substituem uma lista oficial
# da temporada solicitada; a origem é informada em driver_source.
FALLBACK = [
    ('VER','Max Verstappen',1,'Red Bull Racing','3671C6'),
    ('NOR','Lando Norris',4,'McLaren','FF8000'),
    ('LEC','Charles Leclerc',16,'Ferrari','E80020'),
    ('HAM','Lewis Hamilton',44,'Mercedes','27F4D2'),
    ('PIA','Oscar Piastri',81,'McLaren','FF8000'),
    ('SAI','Carlos Sainz',55,'Ferrari','E80020'),
    ('RUS','George Russell',63,'Mercedes','27F4D2'),
    ('PER','Sergio Perez',11,'Red Bull Racing','3671C6'),
    ('ALO','Fernando Alonso',14,'Aston Martin','229971'),
    ('GAS','Pierre Gasly',10,'Alpine','0093CC'),
    ('STR','Lance Stroll',18,'Aston Martin','229971'),
    ('OCO','Esteban Ocon',31,'Alpine','0093CC'),
    ('TSU','Yuki Tsunoda',22,'AlphaTauri','6692FF'),
    ('BOT','Valtteri Bottas',77,'Alfa Romeo','C92D4B'),
    ('ZHO','Zhou Guanyu',24,'Alfa Romeo','C92D4B'),
    ('ALB','Alexander Albon',23,'Williams','64C4FF'),
    ('SAR','Logan Sargeant',2,'Williams','64C4FF'),
    ('HUL','Nico Hulkenberg',27,'Haas','B6BABD'),
    ('MAG','Kevin Magnussen',20,'Haas','B6BABD'),
    ('RIC','Daniel Ricciardo',3,'AlphaTauri','6692FF'),
]


def driver_record(abbr, name, number, team, color):
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    color = str(color or '').lstrip('#')
    if not re.fullmatch(r'[0-9a-fA-F]{6}', color):
        color = '808080'
    return {'driver_id': slug, 'abbreviation': abbr, 'name': name,
            'number': number, 'team': team, 'team_color': '#'+color.upper()}


class RaceDataProvider(Protocol):
    def load(self, circuit: str, season: int) -> tuple[Track | None, list[dict], dict]: ...


class AmbiguousCircuitError(ValueError):
    """A temporada contém mais de uma sessão compatível com a seleção."""


def select_session(circuit, sessions):
    """Resolve pelo circuito/local; um país com múltiplas pistas é ambíguo."""
    aliases = {'sao paulo':'interlagos', 'brazil':'interlagos'}
    wanted = normalize(circuit)
    wanted = aliases.get(wanted, wanted)
    exact = [s for s in sessions if wanted and wanted in {
        normalize(s.get('circuit_short_name')), normalize(s.get('location')),
        normalize(s.get('country_name'))}]
    candidates = exact or [s for s in sessions if len(wanted) >= 3 and any(
        wanted in normalize(s.get(key)) for key in ('circuit_short_name','location'))]
    if len(candidates) > 1:
        raise AmbiguousCircuitError(f"Circuito '{circuit}' corresponde a várias corridas nessa temporada; informe uma pista sem ambiguidade.")
    if not candidates:
        raise ValueError(f"Sessão OpenF1 não encontrada para '{circuit}' nessa temporada")
    return candidates[0]


class OpenF1Provider:
    """OpenF1 histórico (2023+) com tempo de rede limitado e cache em memória."""
    def __init__(self, timeout=3.0, fetch=None):
        self.timeout = timeout
        self.fetch = fetch or OpenF1Client(timeout=timeout).get
        self._cache = {}

    def telemetry(self, session_key: int, driver_number: int, **filters):
        """Telemetria histórica bruta; não interfere nos estados da simulação."""
        return self.fetch('car_data', session_key=session_key, driver_number=driver_number, **filters)

    def load(self, circuit: str, season: int):
        cache_key = (circuit, season)
        if cache_key in self._cache:
            return self._cache[cache_key]
        if season < 2023:
            raise ValueError('OpenF1 oferece telemetria histórica a partir de 2023')
        sessions = self.fetch('sessions', year=season, session_name='Race')
        session = select_session(circuit, sessions)
        key = session['session_key']
        rows = self.fetch('drivers', session_key=key)
        drivers = [driver_record(row.get('name_acronym', ''), row['full_name'],
                                 row.get('driver_number'), row.get('team_name'), row.get('team_colour'))
                   for row in rows if row.get('full_name')]
        if not drivers:
            raise ValueError('Pilotos OpenF1 indisponíveis')
        try:
            # Seleciona a volta válida mais rápida, excluindo volta 1 e saída dos boxes.
            number = next((row['driver_number'] for row in rows if row.get('driver_number')), None)
            laps = self.fetch('laps', session_key=key, driver_number=number)
            valid = [lap for lap in laps if lap.get('date_start') and lap.get('lap_duration')
                     and 45 <= float(lap['lap_duration']) <= 180 and (lap.get('lap_number') or 0) > 1
                     and not lap.get('is_pit_out_lap')]
            if not valid:
                raise ValueError('Volta completa OpenF1 indisponível')
            lap = min(valid, key=lambda row: row['lap_duration'])
            start = datetime.fromisoformat(lap['date_start'].replace('Z', '+00:00'))
            end = start + timedelta(seconds=float(lap['lap_duration']))
            samples = self.fetch('location', session_key=key, driver_number=number,
                                 **{'date>': start.isoformat(), 'date<': end.isoformat()})
            points = [(float(p['x']) * 0.1, float(p['y']) * 0.1)
                      for p in sorted(samples, key=lambda p: p.get('date', '')) if p.get('x') is not None and p.get('y') is not None]
            filtered = []
            for point in points:
                if not filtered or math.dist(filtered[-1], point) >= 0.2:
                    filtered.append(point)
            points = filtered
            if len(points) > 1 and math.dist(points[0], points[-1]) < 0.2:
                points.pop()
            if len(points) < 100:
                raise ValueError('Amostras insuficientes para geometria OpenF1')
            steps = [math.dist(a,b) for a,b in zip(points, points[1:])]
            closure = math.dist(points[-1], points[0])
            length = sum(steps) + closure
            if not 2500 <= length <= 8000 or closure > 80 or max(steps, default=0) > 100:
                raise ValueError('Geometria OpenF1 não passou na validação')
            track = Track.from_waypoints(name=session.get('circuit_short_name') or circuit,
                                         waypoints=points, width_m=12.0, start_finish_waypoint=0,
                                         source='openf1', metadata={'session_key':key, 'driver_number':number,
                                         'lap_number':lap.get('lap_number'), 'timing_line':'lap_start_approximate'})
            if any(track.distance_to_centerline(*track.initial_position(i)) > track.width_m / 2 - 0.9
                   for i in range(10)):
                raise ValueError('Linha de cronometragem não comporta o grid de dez carros')
            result = track, drivers, {'track_source':'openf1', 'driver_source':'openf1', 'session_key':key}
            self._cache[cache_key] = result
            return result
        except Exception as exc:
            logger.warning("Geometria OpenF1 indisponível: %s", exc)
            return None, drivers, {"driver_source":"openf1", "session_key":key}



class FallbackProvider:
    def load(self, circuit: str, season: int):
        if season < 2018:
            raise ValueError('Sem geometria histórica verificada para esta pista e temporada: OpenF1 cobre 2023+ e FastF1 geralmente 2018+; F1DB informa layouts, não waypoints de simulação.')
        track = load_live_track(track_name=circuit, year=season)
        drivers = [driver_record(*item) for item in FALLBACK]
        return track, drivers, {'track_source':track.source, 'driver_source':'local_2023'}


class ProviderChain:
    def __init__(self, providers: list[RaceDataProvider]):
        self.providers = providers

    def load(self, circuit: str, season: int):
        errors = []
        track, drivers, sources = None, None, {}
        for provider in self.providers:
            try:
                candidate_track, candidate_drivers, candidate_sources = provider.load(circuit, season)
                if track is None and candidate_track is not None:
                    track = candidate_track
                    sources['track_source'] = candidate_sources.get('track_source')
                if drivers is None and candidate_drivers:
                    drivers = candidate_drivers
                    sources['driver_source'] = candidate_sources.get('driver_source')
                    if 'session_key' in candidate_sources:
                        sources['session_key'] = candidate_sources['session_key']
                if track is not None and drivers:
                    return track, drivers, sources
            except AmbiguousCircuitError:
                raise
            except Exception as exc:
                errors.append(f'{type(provider).__name__}: {exc}')
                logger.warning('Fonte de corrida indisponível: %s', errors[-1])
        raise ValueError('Nenhuma fonte de corrida disponível: ' + '; '.join(errors))



def default_provider():
    return ProviderChain([OpenF1Provider(), FallbackProvider()])
