"""Corridas locais e publicação dos estados autoritativos no Redis."""
from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass, replace
import hashlib
import json
import logging
import math
import os
import struct
import socket
import urllib.error
import urllib.parse
import urllib.request
import sys
import threading
import time
import uuid

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import redis
from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from engine.physics import CHASSIS_LENGTH_M, CHASSIS_WIDTH_M, CHASSIS_HEIGHT_M
from domain.pit_lane import ensure_pit_lane
from domain import TyreCompound, WeatherKind, WeatherModel, WeatherTransitionConfig, BASE_CONDITIONS
from .catalog import get_catalog
from engine import InMemoryInputSource, Publisher, RuleBasedRaceController, SimulationEngine
from engine.coach_controller import CoachController, CommandBus
from engine.ai_engineer import AiEngineer
from .redis_client import sync_client
from .providers.race_data import default_provider, driver_record
from .providers.f1db_layouts import load_layout_catalog, normalize
from .providers.track_reference import candidate_reference_years

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
RACE_TTL = 24 * 60 * 60
RACE_VIEWER_GRACE_S = 30.0
SCHEMA_VERSION = 1
logger = logging.getLogger(__name__)


class TimingTracker:
    """Gap temporal pela passagem anterior do líder na posição do seguidor.

    Sem passagem observada, após mudança de líder, ou com volta de atraso,
    o gap em segundos é desconhecido e representado por None.
    """
    def __init__(self):
        self.leader_id = None
        self.distances = []
        self.times = []

    def update(self, positions, sim_ts, length):
        if not positions:
            return
        leader = positions[0]
        leader_id = leader['driver_id']
        if leader_id != self.leader_id:
            self.leader_id = leader_id
            self.distances.clear()
            self.times.clear()
        lead = leader['progress_m']
        if self.distances and lead < self.distances[-1] - 0.1:
            self.distances.clear()
            self.times.clear()
        if not self.distances or lead > self.distances[-1]:
            self.distances.append(lead)
            self.times.append(sim_ts)
        leader['gap_to_leader_s'] = 0.0
        leader['laps_behind'] = 0
        for pos in positions[1:]:
            if leader.get('finished') and pos.get('finished'):
                pos['laps_behind'] = max(0, leader['lap'] - pos['lap'])
                leader_time, finish_time = leader.get('finish_time_s'), pos.get('finish_time_s')
                pos['gap_to_leader_s'] = (
                    round(max(0.0, finish_time - leader_time), 3)
                    if not pos['laps_behind'] and leader_time is not None and finish_time is not None
                    else None
                )
                continue
            distance = pos['progress_m']
            behind = max(0.0, lead - distance)
            pos['laps_behind'] = int(behind // length) if length > 0 else 0
            pos['gap_to_leader_s'] = None
            if pos['laps_behind'] or not self.distances:
                continue
            i = bisect_left(self.distances, distance)
            if i == 0 or i >= len(self.distances):
                continue
            a, b = self.distances[i-1], self.distances[i]
            fraction = (distance-a)/(b-a)
            crossing = self.times[i-1] + fraction*(self.times[i]-self.times[i-1])
            pos['gap_to_leader_s'] = round(max(0.0, sim_ts-crossing), 3)
        # Only the last two circuit lengths can be useful for same-lap gaps.
        if length > 0 and self.distances:
            cutoff = bisect_left(self.distances, lead - 2 * length)
            if cutoff > 1:
                del self.distances[:cutoff-1]
                del self.times[:cutoff-1]


class CollisionAggregator:
    """Um aviso por contato contínuo, baseado nos subpassos reais do solver."""
    def __init__(self, release_after_s=0.5):
        self.last_seen = {}
        self.release_after_s = release_after_s

    def update(self, raw, sim_ts, names):
        pairs = defaultdict(list)
        for contact in raw:
            a, b = contact.get('drv_a'), contact.get('drv_b')
            force = float(contact.get('f_n', 0.0))
            depth = float(contact.get('penetration_m', 0.0))
            if a and b and a != b and (force >= 1.0 or depth >= 0.001):
                pairs[tuple(sorted((a, b)))].append(contact)
        events = []
        for pair, contacts in pairs.items():
            if pair not in self.last_seen:
                per_substep = defaultdict(float)
                for c in contacts:
                    per_substep[c.get('sub', 0)] += float(c.get('f_n', 0.0))
                strongest = max(contacts, key=lambda c: float(c.get('f_n', 0.0)))
                a, b = pair
                events.append({'type': 'collision', 'schema_version': SCHEMA_VERSION,
                               'sim_ts': sim_ts, 'driver_a_id': a, 'driver_b_id': b,
                               'driver_a_name': names.get(a, a), 'driver_b_name': names.get(b, b),
                               'position_xy': [strongest.get('cx', 0.0), strongest.get('cy', 0.0)],
                               'impact_force_n': max(per_substep.values(), default=0.0),
                               'penetration_m': max(float(c.get('penetration_m', 0.0)) for c in contacts),
                               'drv_a': a, 'drv_b': b})
            self.last_seen[pair] = sim_ts
        for pair in list(self.last_seen):
            if pair not in pairs and sim_ts-self.last_seen[pair] > self.release_after_s:
                del self.last_seen[pair]
        return events



class LostRaceLease(RuntimeError):
    """A different process owns the race or the lease expired."""


LEASE_SECONDS = 12
CHECKPOINT_INTERVAL_S = 1.0


class LivePublisher(Publisher):
    def __init__(self, client, race_id, driver_meta=None):
        self.client, self.race_id = client, race_id
        self.engine = None
        self.lease_token = None
        self.owner_address = None
        self.last_checkpoint_ts = 0.0
        self.driver_meta = {d['driver_id']: d for d in (driver_meta or [])}
        self.timing = TimingTracker()
        self.collisions = CollisionAggregator()
        self.snapshot = {'race_id': race_id, 'status': 'starting', 'sim_ts': 0.0,
                         'last_tick': None, 'classification': None}

    def publish(self, event):
        payload = event.to_dict()
        payload['schema_version'] = SCHEMA_VERSION
        payload['race_id'] = self.race_id
        collision_events = []
        if event.type == 'race_start':
            self.snapshot['status'] = 'running'
        if event.type == 'tick' and self.engine is not None:
            engine = self.engine
            length = float(engine.track.length_m)
            for rank, position in enumerate(payload['positions'], 1):
                driver_id = position['driver_id']
                state = engine.states[driver_id]
                progress = float(engine.race_progress_m.get(driver_id, 0.0))
                position.update(position=rank, position_xy=[state.position_x, state.position_y],
                                heading_deg=math.degrees(state.heading_rad), velocity_mps=state.velocity_mps,
                                speed_kmh=state.velocity_mps*3.6, progress_m=progress,
                                s_m=engine.race_s_m.get(driver_id),
                                d_m=engine.race_lateral_m.get(driver_id),
                                team_color=self.driver_meta.get(driver_id, {}).get('team_color'))
            self.timing.update(payload['positions'], float(event.sim_ts), length)
            payload['leader_lap'] = payload['positions'][0]['lap'] if payload['positions'] else 0
            raw = engine.physics.contact_collector
            names = {d.driver_id: d.name for d in engine.drivers}
            collision_events = self.collisions.update(raw or [], float(event.sim_ts), names)
            for item in collision_events:
                item['lap'] = max(engine.states[item['driver_a_id']].lap, engine.states[item['driver_b_id']].lap)
                item['ts'] = event.ts
                item['race_id'] = self.race_id
            payload['collisions'] = collision_events
            if raw is not None:
                raw.clear()
            self.snapshot.update(status='running', sim_ts=payload['sim_ts'], last_tick=payload)
        elif event.type == 'race_end':
            self.snapshot.update(status='finished', sim_ts=payload['sim_ts'],
                                 classification=payload.get('final_classification'))
        data = json.dumps(payload, ensure_ascii=False, default=str)
        checkpoint = None
        # Checkpoint periódico: sempre cria, mas só renova lease no modo distribuído
        # Verifica se engine tem os atributos necessários (pode ser mock em testes)
        if (event.type == 'tick' and self.engine is not None
                and hasattr(self.engine, 'sim_ts')
                and self.engine.sim_ts - self.last_checkpoint_ts >= CHECKPOINT_INTERVAL_S):
            try:
                from engine.checkpoint import capture
                checkpoint = capture(self.engine, self)
            except Exception:
                # Se falhar (ex.: engine mock em testes), apenas não cria checkpoint
                checkpoint = None
        deadline = time.monotonic() + 90.0
        while True:
            try:
                pipe = self.client.pipeline(transaction=True)
                if self.lease_token:
                    # Modo distribuído: renova lease e verifica ownership
                    lease_key = f'race:{self.race_id}:lease'
                    pipe.watch(lease_key)
                    if pipe.get(lease_key) != self.lease_token:
                        pipe.reset()
                        raise LostRaceLease(self.race_id)
                    pipe.multi()
                    pipe.set(lease_key, self.lease_token, ex=LEASE_SECONDS)
                    pipe.set(f'race:{self.race_id}:owner', self.owner_address, ex=LEASE_SECONDS)
                    if event.type == 'race_end':
                        pipe.srem('ha:active_races', self.race_id)
                        pipe.delete(lease_key, f'race:{self.race_id}:owner', f'race:{self.race_id}:viewers')
                # Checkpoint salvo em ambos os modos
                if checkpoint is not None:
                    pipe.set(f'race:{self.race_id}:checkpoint', checkpoint, ex=RACE_TTL)
                if event.type == 'race_start':
                    pipe.set(f'race:{self.race_id}:start', data, ex=RACE_TTL)
                if event.type == 'tick':
                    pipe.set(f'race:{self.race_id}:state', data, ex=RACE_TTL)
                if event.type == 'race_end':
                    pipe.set(f'race:{self.race_id}:result', data, ex=RACE_TTL)
                pipe.set(f'race:{self.race_id}:snapshot', json.dumps(self.snapshot, ensure_ascii=False), ex=RACE_TTL)
                pipe.publish(f'race:{self.race_id}:events', data)
                for collision in collision_events:
                    pipe.publish(f'race:{self.race_id}:events', json.dumps(collision, ensure_ascii=False))
                pipe.execute()
                if checkpoint is not None:
                    self.last_checkpoint_ts = self.engine.sim_ts
                break
            except redis.WatchError:
                continue
            except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as exc:
                temporary_response = isinstance(exc, redis.ResponseError) and (
                    isinstance(exc, redis.exceptions.ReadOnlyError) or str(exc).startswith('NOREPLICAS'))
                if isinstance(exc, redis.ResponseError) and not temporary_response:
                    raise
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)


@dataclass
class RaceViewers:
    idle_since: float
    count: int = 0
    expired: bool = False
    next_poll: float = 0.0


class RaceManager:
    def __init__(self, client=None, provider=None, catalog=None, viewer_grace_s=RACE_VIEWER_GRACE_S):
        self.catalog = catalog
        self.redis = client or sync_client(REDIS_URL)
        self.provider = provider or default_provider()
        try:
            self.catalog = catalog if catalog is not None else load_layout_catalog()
        except (OSError, ValueError) as exc:
            logger.warning('Catálogo F1DB indisponível: %s', exc)
            self.catalog = None
        self._threads = {}
        self._engines = {}
        self._viewers = {}
        self._ai_engineers = {}  # race_id -> AiEngineer
        self._viewer_grace_s = viewer_grace_s
        self._engines_lock = threading.RLock()
        self._distributed = os.environ.get('F1_DISTRIBUTED_COMMANDS') == '1'
        self._owner_address = socket.gethostbyname(socket.gethostname()) if self._distributed else None
        self._recovery_stop = threading.Event()
        self._recovery_thread = None

    def create_race(self, laps, track, year, num_drivers=2, layout_id=None, selected_roster=None,
                    weather=None, weather_change=None, initial_tyre=None, user_driver_id=None, random_seed=None):
        print(f"=== create_race DIRECT PRINT: laps={laps}, track={track}, year={year}, num_drivers={num_drivers} ===", flush=True)
        logger.info('=== create_race INICIADO: laps=%s, track=%s, year=%s, num_drivers=%s ===', 
                    laps, track, year, num_drivers)
        if not 1 <= num_drivers <= 24:
            raise ValueError('A quantidade de corredores deve estar entre 1 e 24.')
        self.redis.ping()
        print(f"=== After redis.ping ===", flush=True)
        circuit = (track or 'interlagos').strip().lower() or 'interlagos'
        
        # Validação do catálogo: circuito deve existir
        if self.catalog:
            catalog_circuit = self.catalog.find_circuit(circuit)
            if catalog_circuit is None:
                raise ValueError(f"Circuito '{track}' não encontrado no catálogo")
            circuit_id = catalog_circuit['id']
            season = year or (2024 if circuit_id == 'monza' else 2023)
            season_layout = self.catalog.find_layout(catalog_circuit, season)
            if season_layout is None:
                available = []
                for l in catalog_circuit.get("layouts", []):
                    fy = l.get("first_year") or (l.get("years", [0])[0] if l.get("years") else 0)
                    ly = l.get("last_year") or (l.get("years", [-1])[-1] if l.get("years") else 0)
                    available.append(f"{fy}-{ly}")
                raise ValueError(
                    f"Circuito '{track}' não tem layout para o ano {year}. "
                    f"Anos disponíveis: {', '.join(available)}"
                )
        else:
            circuit_id = normalize(circuit).replace(' ', '-')
            season = year or (2024 if circuit_id == 'monza' else 2023)
            season_layout = None
        layout = season_layout
        if layout_id is not None:
            layout = next((item for item in (catalog_circuit or {}).get('layouts', [])
                           if item['id'] == layout_id), None)
            if layout is None:
                raise ValueError(f"O layout '{layout_id}' não pertence ao circuito '{circuit_id}'.")
        same_season_layout = layout is None or (season_layout is not None and layout['id'] == season_layout['id'])
        if layout_id is not None and not same_season_layout and selected_roster is None:
            raise ValueError(f"O layout '{layout_id}' não é confirmado para '{circuit_id}' em {season} pelo catálogo F1DB; informe o grid para usar pilotos de outra temporada.")

        # Com grid explícito a temporada identifica os pilotos, e o layout
        # selecionado identifica a pista. A referência nunca troca de layout.
        track_year = season
        track_obj = roster = sources = None
        original_error = None
        if same_season_layout:
            try:
                print(f"=== Calling provider.load for circuit={circuit}, season={season} ===", flush=True)
                track_obj, roster, sources = self.provider.load(circuit, season)
                print(f"=== provider.load returned ===", flush=True)
            except ValueError as exc:
                if layout_id is None or selected_roster is None:
                    raise
                original_error = exc
        if track_obj is None:
            candidates = candidate_reference_years(self.catalog, catalog_circuit, layout, excluded=(season,))
            errors = []
            for reference_year in candidates:
                try:
                    track_obj, roster, sources = self.provider.load(circuit, reference_year)
                except ValueError as exc:
                    # O snapshot identifica um GP específico mesmo quando há
                    # múltiplas sessões no mesmo circuito e ano.
                    try:
                        from .providers.historical_f1results import HistoricalResultsProvider
                        track_obj, roster, sources = HistoricalResultsProvider().load(circuit, reference_year)
                    except ValueError as fallback_exc:
                        errors.append(f'{reference_year}: {exc}; {fallback_exc}')
                        continue
                track_year = reference_year
                break
            if track_obj is None:
                detail = '; '.join(errors) or str(original_error or 'nenhum ano de referência disponível')
                raise ValueError(f"Geometria indisponível para o layout '{layout_id}' em qualquer referência conhecida: {detail}")
        reference = {'driver_season': season, 'track_year': track_year,
                     'basis': 'season' if track_year == season else 'selected_layout_reference'}
        if track_year != season:
            sources['track_reference'] = reference
            track_obj.metadata = {**track_obj.metadata, 'track_reference': reference}
        safe_grid = track_obj.metadata.get('max_safe_grid_cars')
        if safe_grid is not None and num_drivers > safe_grid:
            raise ValueError(f'A geometria histórica aproximada comporta apenas {safe_grid} carros no grid; solicite menos carros.')
        if not roster:
            raise ValueError('Fonte não forneceu pilotos')
        if selected_roster is not None:
            roster = selected_roster
            sources['driver_source'] = 'season_selection'
            sources.pop('driver_provenance', None)
        elif sources.get('driver_source') == 'f1results_database' and num_drivers > len(roster):
            raise ValueError(f'O GP histórico possui apenas {len(roster)} carros no grid; solicite menos carros.')
        roster = list(roster[:num_drivers])
        while len(roster) < num_drivers:
            i = len(roster)+1
            roster.append(driver_record(f'P{i:02d}', f'Piloto {i:02d}', None, None, None))
        if user_driver_id is not None and user_driver_id not in {entry['driver_id'] for entry in roster}:
            raise ValueError('O piloto do usuário deve pertencer ao grid da corrida.')
        drivers = [replace(DEFAULT_DRIVERS[i % len(DEFAULT_DRIVERS)], driver_id=entry['driver_id'], name=entry['name'],
                           **({'starting_tyre_compound': TyreCompound(initial_tyre.upper())} if initial_tyre else {}))
                   for i, entry in enumerate(roster)]
        race_id = f'race_{uuid.uuid4().hex}'
        # A separate seed per race avoids replaying the exact same bot rhythm
        # while preserving deterministic experiments when a seed is supplied.
        bot_seed = int(race_id[5:13], 16) if random_seed is None else int(random_seed)
        gui = os.environ.get('F1_PYBULLET_GUI', '').lower() in ('1','true','yes','on')
        camera = os.environ.get('F1_GUI_CAMERA', 'follow') if gui else 'none'
        if camera not in ('follow', 'overview', 'none'):
            raise ValueError(f'Modo de câmera inválido: {camera}')
        config = replace(DEFAULT_INTERLAGOS_CONFIG, race_id=race_id, num_laps=laps, gui=gui,
                         camera_mode=camera, draw_track=gui, draw_track_details=False,
                         realtime=True, track_progress_laps=True, random_seed=bot_seed)
        pit = ensure_pit_lane(track_obj)
        geometry = b''.join(struct.pack('<dd', float(x), float(y)) for x,y in track_obj.waypoints)
        digest = hashlib.sha256(geometry).hexdigest()[:16]
        driver_meta = [{**d, 'grid_position': i+1} for i,d in enumerate(roster)]
        meta = {'race_id':race_id, 'schema_version':SCHEMA_VERSION, 'season':season,
                'circuit_id':circuit_id, 'layout_id':layout['id'] if layout else None,
                'layout_reference':{'source':'F1DB','basis':reference['basis'], 'years':layout['years'],
                                    'track_year':track_year,
                                    'catalog_generated_at':self.catalog.data.get('generated_at')} if layout else None,
                'num_laps':laps, 'num_drivers':num_drivers, 'user_driver_id':user_driver_id,
                # No fluxo atual o piloto controlado pelo jogador é também o
                # piloto que o engenheiro de IA acompanha. Exposto explicitamente
                # para o viz3d/HUD e para o listener da IA.
                'followed_driver_id':user_driver_id,
                'random_seed':bot_seed, 'sources':sources,
                'car_geometry':{'length_m':CHASSIS_LENGTH_M,'width_m':CHASSIS_WIDTH_M,'height_m':CHASSIS_HEIGHT_M},
                'track':{'name':track_obj.name, 'source':track_obj.source, 'geometry_sha256':digest,
                         'length_m':track_obj.length_m, 'width_m':track_obj.width_m,
                         'start_finish_waypoint':track_obj.start_finish_waypoint,
                         'waypoints':[[float(x),float(y)] for x,y in track_obj.waypoints],
                         'pit_lane': {'waypoints': [[float(x), float(y)] for x, y in pit.waypoints],
                                      'width_m': pit.width_m, 'speed_limit_kmh': pit.speed_limit_kmh,
                                      'source': pit.source}},
                'drivers':driver_meta}
        publisher = LivePublisher(self.redis, race_id, driver_meta)
        weather_model = None
        if weather is not None:
            weather_map = {'dry': WeatherKind.DRY, 'cloudy': WeatherKind.CLOUDY,
                           'light_rain': WeatherKind.WET, 'rain': WeatherKind.WET,
                           'heavy_rain': WeatherKind.WET}
            initial = BASE_CONDITIONS[weather_map[weather]]
            if weather in ('light_rain', 'heavy_rain'):
                initial = replace(initial, rainfall=0.5 if weather == 'light_rain' else 7.0)
            transition = WeatherTransitionConfig.default(transition_prob_per_lap=0.0)
            if weather_change:
                kinds = list(dict.fromkeys(weather_map[x.value if hasattr(x, 'value') else x]
                                           for x in weather_change['possible']))
                transition = WeatherTransitionConfig(
                    transition_matrix={kind: {target: 1.0 / len(kinds) for target in kinds} for kind in WeatherKind},
                    transition_prob_per_lap=weather_change['probability_per_lap'])
            weather_model = WeatherModel(initial=initial, config=transition)
        engine_kwargs = dict(config=config, track=track_obj, drivers=drivers, publisher=publisher,
                             input_source=InMemoryInputSource(fallback_race_id=race_id))
        if weather_model is not None:
            engine_kwargs['weather_model'] = weather_model
        print(f"=== Creating SimulationEngine ===", flush=True)
        engine = SimulationEngine(**engine_kwargs)
        print(f"=== SimulationEngine created ===", flush=True)
        engine.user_driver_id = user_driver_id
        publisher.engine = engine
        engine.physics.contact_collector = []
        engine.physics.contact_collector_include_penetration = True

        # Bus de comandos do engenheiro (IA/usuário) — Redis para persistência e HA
        command_bus = CommandBus(self.redis, race_id, ttl=RACE_TTL)
        base_controller = RuleBasedRaceController(track_obj, seed=config.random_seed)
        for driver in drivers:
            coach = CoachController(
                base_controller,
                driver.driver_id,
                publisher=publisher,
                bus=command_bus,
            )
            engine.set_controller(driver.driver_id, coach)

        # Sempre inicializa engine e cria checkpoint inicial (para permitir recovery futuro)
        from engine.checkpoint import capture
        # Engine real tem setup(); mocks de teste podem não ter
        if hasattr(engine, 'setup'):
            engine.setup()
        initial_checkpoint = None
        try:
            initial_checkpoint = capture(engine, publisher)
        except Exception:
            # Se falhar (ex.: engine mock em testes), continua sem checkpoint inicial
            pass

        if self._distributed:
            publisher.lease_token = uuid.uuid4().hex
            publisher.owner_address = self._owner_address
            pipe = self.redis.pipeline(transaction=True)
            pipe.set(f'race:{race_id}:meta', json.dumps(meta, ensure_ascii=False), ex=RACE_TTL)
            pipe.set(f'race:{race_id}:snapshot', json.dumps(publisher.snapshot), ex=RACE_TTL)
            pipe.set(f'race:{race_id}:checkpoint', initial_checkpoint, ex=RACE_TTL)
            pipe.set(f'race:{race_id}:lease', publisher.lease_token, ex=LEASE_SECONDS)
            pipe.set(f'race:{race_id}:owner', self._owner_address, ex=LEASE_SECONDS)
            pipe.sadd('ha:active_races', race_id)
            try:
                pipe.execute()
            except Exception:
                engine.teardown()
                raise
        else:
            # Single-instance: salva checkpoint mas sem lease/HA
            # Tenta pipeline; se não existir (mocks de teste), usa set direto
            try:
                pipe = self.redis.pipeline(transaction=True)
                pipe.set(f'race:{race_id}:meta', json.dumps(meta, ensure_ascii=False), ex=RACE_TTL)
                pipe.set(f'race:{race_id}:snapshot', json.dumps(publisher.snapshot), ex=RACE_TTL)
                if initial_checkpoint is not None:
                    pipe.set(f'race:{race_id}:checkpoint', initial_checkpoint, ex=RACE_TTL)
                pipe.execute()
            except AttributeError:
                # Fallback para Redis simples (mocks de teste)
                self.redis.set(f'race:{race_id}:meta', json.dumps(meta, ensure_ascii=False), ex=RACE_TTL)
                self.redis.set(f'race:{race_id}:snapshot', json.dumps(publisher.snapshot), ex=RACE_TTL)
                if initial_checkpoint is not None:
                    self.redis.set(f'race:{race_id}:checkpoint', initial_checkpoint, ex=RACE_TTL)
        print(f"=== Calling _start_engine_thread ===", flush=True)
        self._start_engine_thread(engine, publisher)
        print(f"=== _start_engine_thread returned ===", flush=True)

        # Inicia Engenheiro de IA autônomo
        driver_meta = [
            {"driver_id": d.driver_id, "name": d.name, "team": getattr(d, "team", None)}
            for d in drivers
        ]
        ai_engineer = AiEngineer(
            race_id=race_id,
            redis_client=self.redis,
            command_bus=command_bus,
            publisher=publisher,
            engine=engine,
            total_laps=config.num_laps,
            drivers_meta=driver_meta,
            user_driver_id=user_driver_id,
        )
        ai_engineer.start()
        with self._engines_lock:
            self._ai_engineers[race_id] = ai_engineer

        logger.info('create_race: corrida %s criada com engine e AI engineer', race_id)
        return race_id, track_obj, config

    def _start_engine_thread(self, engine, publisher):
        race_id = publisher.race_id
        print(f"=== _start_engine_thread: iniciando thread para corrida {race_id} ===", flush=True)
        logger.info('_start_engine_thread: iniciando thread para corrida %s', race_id)
        thread = threading.Thread(target=self._run_engine, args=(engine, publisher), daemon=True)
        with self._engines_lock:
            self._threads[race_id] = thread
            self._engines[race_id] = engine
            self._viewers[race_id] = RaceViewers(idle_since=time.monotonic())
        thread.start()
        logger.info('_start_engine_thread: thread iniciada para %s (threads=%d, engines=%d)', 
                    race_id, len(self._threads), len(self._engines))

    def start_recovery(self):
        if not self._distributed or self._recovery_thread:
            return
        self._recovery_stop.clear()
        self._recovery_thread = threading.Thread(target=self._recover_loop, daemon=True)
        self._recovery_thread.start()

    def stop_recovery(self):
        self._recovery_stop.set()
        if self._recovery_thread:
            self._recovery_thread.join(timeout=3)
            self._recovery_thread = None

    def _recover_loop(self):
        while not self._recovery_stop.wait(2):
            try:
                for race_id in self.redis.smembers('ha:active_races'):
                    with self._engines_lock:
                        if race_id in self._engines:
                            continue
                    logger.info('Tentando recuperar corrida %s', race_id)
                    self._recover_race(race_id)
            except redis.RedisError:
                logger.warning('Redis indisponível durante busca de corridas', exc_info=True)
            except Exception:
                logger.exception('Falha ao procurar corridas para recuperação')

    def _recover_race(self, race_id):
        from engine.checkpoint import restore
        # Verifica se a corrida já está rodando localmente ANTES de tentar lease
        with self._engines_lock:
            if race_id in self._engines:
                logger.debug('Corrida %s já rodando localmente, pulando recovery', race_id)
                return
        token = uuid.uuid4().hex
        lease_key = f'race:{race_id}:lease'
        if not self.redis.set(lease_key, token, nx=True, ex=LEASE_SECONDS):
            logger.debug('Não conseguiu lease para recuperar %s (outro processo?)', race_id)
            return
        logger.info('Lease adquirido para recuperar corrida %s', race_id)
        # Verifica novamente após adquirir lease (outro thread pode ter iniciado)
        with self._engines_lock:
            if race_id in self._engines:
                logger.info('Corrida %s já iniciada por outro thread, liberando lease', race_id)
                self.redis.eval("if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end", 1, lease_key, token)
                return
        engine = None
        try:
            encoded = self.redis.get(f'race:{race_id}:checkpoint')
            meta = self.metadata(race_id)
            if not encoded and not meta:
                # Both keys expire after RACE_TTL; remove the orphan registry.
                self.redis.srem('ha:active_races', race_id)
                self.redis.eval("if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end", 1, lease_key, token)
                return
            if not encoded or not meta:
                raise ValueError('Checkpoint ou metadados ausentes')
            logger.info('Checkpoint e metadados encontrados para %s, restaurando...', race_id)
            publisher = LivePublisher(self.redis, race_id, meta.get('drivers'))
            publisher.lease_token, publisher.owner_address = token, self._owner_address
            engine = restore(encoded, publisher)
            publisher.last_checkpoint_ts = engine.sim_ts
            logger.info('Corrida %s restaurada em sim_ts=%.1fs', race_id, engine.sim_ts)
            # Refresh and verify lease after potentially slow restore.
            pipe = self.redis.pipeline(transaction=True)
            pipe.watch(lease_key)
            if pipe.get(lease_key) != token:
                pipe.reset()
                raise LostRaceLease(race_id)
            pipe.multi()
            pipe.set(lease_key, token, ex=LEASE_SECONDS)
            pipe.set(f'race:{race_id}:owner', self._owner_address, ex=LEASE_SECONDS)
            if publisher.snapshot.get('last_tick'):
                pipe.set(f'race:{race_id}:state', json.dumps(publisher.snapshot['last_tick']), ex=RACE_TTL)
            pipe.set(f'race:{race_id}:snapshot', json.dumps(publisher.snapshot), ex=RACE_TTL)
            pipe.publish(f'race:{race_id}:events', json.dumps({'type': 'race_recovered', 'race_id': race_id, 'sim_ts': engine.sim_ts}))
            pipe.execute()
            self._start_engine_thread(engine, publisher)
            logger.info('Engine thread reiniciada para corrida %s', race_id)

            # Reinicia o engenheiro junto com a engine recuperada. Reutiliza o
            # bus dos coaches restaurados para não reiniciar a sequência em zero.
            try:
                command_bus = next(
                    (
                        controller.bus
                        for controller in engine.controllers.values()
                        if isinstance(controller, CoachController) and controller.bus is not None
                    ),
                    None,
                )
                if command_bus is None:
                    command_bus = CommandBus(self.redis, race_id, ttl=RACE_TTL)
                ai_engineer = AiEngineer(
                    race_id=race_id,
                    redis_client=self.redis,
                    command_bus=command_bus,
                    publisher=publisher,
                    engine=engine,
                    total_laps=meta.get('num_laps', 10),
                    drivers_meta=meta.get('drivers', []),
                    user_driver_id=meta.get('user_driver_id'),
                )
                ai_engineer.start()
                with self._engines_lock:
                    self._ai_engineers[race_id] = ai_engineer
                logger.info(
                    'AiEngineer iniciado para corrida recuperada %s (bus seq=%d)',
                    race_id,
                    command_bus._seq,
                )
            except Exception as exc:
                logger.warning('Não foi possível iniciar AiEngineer para corrida recuperada %s: %s', race_id, exc)
            logger.info('Corrida %s retomada em %.1fs', race_id, engine.sim_ts)
        except Exception:
            if engine is not None:
                engine.teardown()
            # Release only if we still own this lease.
            self.redis.eval("if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end", 1, lease_key, token)
            raise

    def _run_engine(self, engine, publisher):
        race_id = engine.config.race_id
        try:
            completed = engine.run(should_cancel=lambda: self._viewer_timeout(race_id))
            if completed is False:
                self._publish_terminal(
                    race_id, publisher, 'cancelled', engine.sim_ts, 'race_cancelled',
                    'Corrida encerrada por falta de espectadores.',
                )
        except LostRaceLease:
            logger.info('Corrida %s mudou de proprietário', race_id)
        except redis.RedisError:
            if not self._distributed:
                self._publish_terminal(race_id, publisher, 'failed', engine.sim_ts, 'race_error',
                                       'Redis indisponível durante a simulação.')
        except Exception as exc:
            logger.exception('Falha na corrida %s', race_id)
            self._publish_terminal(race_id, publisher, 'failed', engine.sim_ts, 'race_error', str(exc))
        finally:
            try:
                engine.close_pit_requests()
            finally:
                try:
                    engine.teardown()
                finally:
                    # Para o Engenheiro de IA
                    ai_engineer = None
                    with self._engines_lock:
                        ai_engineer = self._ai_engineers.pop(race_id, None)
                    if ai_engineer:
                        ai_engineer.stop()
                    with self._engines_lock:
                        self._threads.pop(race_id, None)
                        self._engines.pop(race_id, None)
                        self._viewers.pop(race_id, None)

    def _publish_terminal(self, race_id, publisher, status, sim_ts, event_type, message):
        publisher.snapshot.update(status=status, sim_ts=sim_ts, message=message)
        payload = {'type': event_type, 'race_id': race_id, 'schema_version': SCHEMA_VERSION,
                   'sim_ts': sim_ts, 'message': message}
        try:
            with self.redis.pipeline(transaction=True) as pipe:
                if publisher.lease_token:
                    lease_key = f'race:{race_id}:lease'
                    pipe.watch(lease_key)
                    if pipe.get(lease_key) != publisher.lease_token:
                        return
                    pipe.multi()
                    pipe.srem('ha:active_races', race_id)
                    pipe.delete(lease_key, f'race:{race_id}:owner', f'race:{race_id}:viewers')
                pipe.set(f'race:{race_id}:snapshot', json.dumps(publisher.snapshot), ex=RACE_TTL)
                pipe.set(f'race:{race_id}:result', json.dumps(payload), ex=RACE_TTL)
                pipe.publish(f'race:{race_id}:events', json.dumps(payload))
                pipe.execute()
        except redis.RedisError:
            logger.warning('Não foi possível publicar o encerramento da corrida %s', race_id)

    def attach_viewer(self, race_id):
        with self._engines_lock:
            viewers = self._viewers.get(race_id)
            if viewers is None or viewers.expired:
                return False
            viewers.count += 1
            return True

    def detach_viewer(self, race_id):
        with self._engines_lock:
            viewers = self._viewers.get(race_id)
            if viewers is not None and viewers.count:
                viewers.count -= 1
                if viewers.count == 0:
                    viewers.idle_since = time.monotonic()

    def _viewer_timeout(self, race_id):
        if self._distributed:
            viewers = self._viewers[race_id]
            now = time.monotonic()
            if now < viewers.next_poll:
                return False
            viewers.next_poll = now + 1.0
            try:
                watching = self.redis.zcount(f'race:{race_id}:viewers', time.time(), '+inf')
            except redis.RedisError:
                # Redis failover is not evidence that all viewers have left.
                viewers.idle_since = now
                return False
            if watching:
                viewers.idle_since = now
            return now - viewers.idle_since >= self._viewer_grace_s
        with self._engines_lock:
            viewers = self._viewers.get(race_id)
            if viewers is not None and viewers.count == 0:
                if time.monotonic() - viewers.idle_since >= self._viewer_grace_s:
                    viewers.expired = True
                return viewers.expired
            return False


    def _forward_pit(self, race_id, driver_id, method, compound=None):
        owner = self.redis.get(f'race:{race_id}:owner')
        if not owner or owner == self._owner_address:
            raise RuntimeError('Corrida não está ativa neste processo')
        # O endereço é registrado pelo processo criador no Redis interno.
        import ipaddress
        try:
            address = ipaddress.ip_address(owner)
            if not address.is_private or address.version != 4:
                raise ValueError('invalid owner')
        except ValueError as exc:
            raise RuntimeError('Proprietário da corrida inválido') from exc
        path = '/races/{}/drivers/{}/pit-stop'.format(urllib.parse.quote(race_id, safe=''), urllib.parse.quote(driver_id, safe=''))
        body = json.dumps({'tyre_compound': compound.value}).encode() if compound else None
        request = urllib.request.Request(f'http://{address}:8000{path}', data=body, method=method,
                                         headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                response.read()
        except urllib.error.HTTPError as exc:
            try: detail = json.loads(exc.read()).get('detail', 'Comando recusado')
            except (ValueError, UnicodeDecodeError): detail = 'Comando recusado'
            if exc.code == 404: raise LookupError(detail) from exc
            raise RuntimeError(detail) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError('O processo proprietário da corrida está indisponível') from exc

    def request_pit_stop(self, race_id, driver_id, compound):
        """Valida a corrida e encaminha o comando à thread proprietária da engine."""
        meta = self.metadata(race_id)
        if meta is None:
            raise LookupError('Corrida não encontrada')
        if driver_id not in {driver['driver_id'] for driver in meta.get('drivers', [])}:
            raise LookupError('Piloto não encontrado nessa corrida')
        with self._engines_lock:
            engine = self._engines.get(race_id)
            if engine is None:
                if self._distributed:
                    return self._forward_pit(race_id, driver_id, 'POST', compound)
                raise RuntimeError('Corrida não está ativa neste processo')
            if self._distributed and self.redis.get(f'race:{race_id}:lease') != engine.publisher.lease_token:
                raise RuntimeError('Corrida está em recuperação; tente novamente')
            engine.request_pit_stop(driver_id, compound)

    def cancel_pit_stop(self, race_id, driver_id):
        meta = self.metadata(race_id)
        if meta is None:
            raise LookupError('Corrida não encontrada')
        if driver_id not in {driver['driver_id'] for driver in meta.get('drivers', [])}:
            raise LookupError('Piloto não encontrado nessa corrida')
        with self._engines_lock:
            engine = self._engines.get(race_id)
            if engine is None:
                if self._distributed:
                    return self._forward_pit(race_id, driver_id, 'DELETE')
                raise RuntimeError('Corrida não está ativa neste processo')
            if self._distributed and self.redis.get(f'race:{race_id}:lease') != engine.publisher.lease_token:
                raise RuntimeError('Corrida está em recuperação; tente novamente')
            engine.cancel_pit_stop(driver_id)

    def metadata(self, race_id):
        value = self.redis.get(f'race:{race_id}:meta')
        return json.loads(value) if value else None

    def snapshot(self, race_id):
        value = self.redis.get(f'race:{race_id}:snapshot')
        return json.loads(value) if value else None


race_manager = RaceManager(catalog=get_catalog(), viewer_grace_s=3600.0)  # 1h para testes
