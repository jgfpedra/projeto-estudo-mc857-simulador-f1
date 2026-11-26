"""Corridas locais e publicação dos estados autoritativos no Redis."""
from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from dataclasses import replace
import hashlib
import json
import logging
import math
import os
import struct
import sys
import threading
import uuid

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import redis
from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from engine.physics import CHASSIS_LENGTH_M, CHASSIS_WIDTH_M, CHASSIS_HEIGHT_M
from domain.pit_lane import ensure_pit_lane
from domain import TyreCompound, WeatherKind, WeatherModel, WeatherTransitionConfig, BASE_CONDITIONS
from .catalog import get_catalog
from engine import (
    CoachController,
    CommandBus,
    InMemoryInputSource,
    Publisher,
    RuleBasedRaceController,
    SimulationEngine,
)

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
RACE_TTL = 24 * 60 * 60
CONTROL_CHANNEL = 'race:control'
SCHEMA_VERSION = 1
# A corrida nasce parada no grid e só larga quando o primeiro visualizador
# conecta no WebSocket. Assim quem abre o viz sempre vê a largada de verdade,
# em vez de entrar no meio da primeira volta. Se ninguém conectar, a corrida
# começa sozinha depois deste prazo para não ficar presa.
START_GATE_TIMEOUT_S = float(os.environ.get('F1_START_GATE_TIMEOUT_S', '120'))
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
                events.append({'type': 'collision', 'sim_ts': sim_ts, 'driver_a_id': a, 'driver_b_id': b,
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



class LivePublisher(Publisher):
    def __init__(self, client, race_id, driver_meta=None):
        self.client, self.race_id = client, race_id
        self.engine = None
        self.driver_meta = {d['driver_id']: d for d in (driver_meta or [])}
        self.timing = TimingTracker()
        self.collisions = CollisionAggregator()
        self.snapshot = {'race_id': race_id, 'status': 'starting', 'sim_ts': 0.0,
                         'last_tick': None, 'classification': None}

    def publish(self, event):
        payload = event.to_dict()
        payload['race_id'] = self.race_id
        payload['schema_version'] = SCHEMA_VERSION
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
                item['schema_version'] = SCHEMA_VERSION
            payload['collisions'] = collision_events
            if raw is not None:
                raw.clear()
            self.snapshot.update(status='running', sim_ts=payload['sim_ts'], last_tick=payload)
        elif event.type == 'race_end':
            self.snapshot.update(status='finished', sim_ts=payload['sim_ts'],
                                 classification=payload.get('final_classification'))
        data = json.dumps(payload, ensure_ascii=False, default=str)
        pipe = self.client.pipeline(transaction=True)
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


class RaceManager:
    def __init__(self, client=None, provider=None, catalog=None):
        # provider e catalog são mantidos para compatibilidade com testes,
        # mas não são usados na versão live_tracks.
        self.catalog = catalog
        self.redis = client or redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        self._threads = {}
        self._buses = {}
        # race_id -> Event liberado quando o primeiro viz conecta.
        self._start_gates = {}

    def create_race(self, laps, track, year, num_drivers=2, layout_id=None, selected_roster=None,
                    weather=None, weather_change=None, initial_tyre=None, user_driver_id=None,
                    followed_driver_id=None):
        if not 1 <= num_drivers <= 24:
            raise ValueError('A quantidade de corredores deve estar entre 1 e 24.')
        self.redis.ping()
        
        # Valida se o circuito existe no catálogo para o ano solicitado
        if self.catalog:
            circuit = self.catalog.circuit(track)
            if circuit is None:
                raise ValueError(f"Circuito '{track}' não encontrado no catálogo")
            # Verifica se há layout para o ano
            layout = self.catalog.find_layout(circuit, year)
            if layout is None:
                available_years = []
                for l in circuit.get("layouts", []):
                    fy = l.get("first_year") or (l.get("years", [0])[0] if l.get("years") else 0)
                    ly = l.get("last_year") or (l.get("years", [-1])[-1] if l.get("years") else 0)
                    available_years.append(f"{fy}-{ly}")
                raise ValueError(
                    f"Circuito '{track}' não tem layout para o ano {year}. "
                    f"Anos disponíveis: {', '.join(available_years)}"
                )
        
        track_obj = load_live_track(track_name=track, year=year)
        race_id = f'race_{uuid.uuid4().hex}'
        gui = os.environ.get('F1_PYBULLET_GUI', '').lower() in ('1', 'true', 'yes', 'on')
        camera_mode = os.environ.get('F1_GUI_CAMERA', 'follow') if gui else 'none'
        if camera_mode not in ('follow', 'overview', 'none'):
            raise ValueError(f'Modo de câmera inválido: {camera_mode}')
        config = replace(DEFAULT_INTERLAGOS_CONFIG, race_id=race_id, num_laps=laps,
                         gui=gui, camera_mode=camera_mode, draw_track=gui, draw_track_details=False,
                         realtime=True, track_progress_laps=True)
        drivers = [
            replace(
                DEFAULT_DRIVERS[index % len(DEFAULT_DRIVERS)],
                driver_id=f'drv_{index + 1:02d}',
                name=(DEFAULT_DRIVERS[index].name if index < len(DEFAULT_DRIVERS)
                      else f'Piloto {index + 1:02d}'),
            )
            for index in range(num_drivers)
        ]
        geometry_bytes = b''.join(struct.pack('<dd', float(x), float(y)) for x, y in track_obj.waypoints)
        geometry_sha256 = hashlib.sha256(geometry_bytes).hexdigest()[:16]
        followed_driver_id = followed_driver_id or drivers[0].driver_id
        if followed_driver_id not in {d.driver_id for d in drivers}:
            followed_driver_id = drivers[0].driver_id
        meta = {
            'race_id': race_id, 'num_laps': laps, 'num_drivers': num_drivers,
            'followed_driver_id': followed_driver_id,
            'dt_s': 1.0 / max(1.0, config.logic_step_hz),
            'car_geometry': {'length_m': CHASSIS_LENGTH_M, 'width_m': CHASSIS_WIDTH_M,
                             'height_m': CHASSIS_HEIGHT_M},
            'track': {'name': track_obj.name, 'source': track_obj.source,
                      'geometry_sha256': geometry_sha256,
                      'length_m': track_obj.length_m, 'width_m': track_obj.width_m,
                      'start_finish_waypoint': track_obj.start_finish_waypoint,
                      'waypoints': [[float(x), float(y)] for x, y in track_obj.waypoints]},
            'drivers': [{'driver_id': d.driver_id, 'name': d.name, 'grid_position': i + 1}
                        for i, d in enumerate(drivers)],
        }
        publisher = LivePublisher(self.redis, race_id)
        engine = SimulationEngine(config=config, track=track_obj, drivers=drivers,
                                  publisher=publisher, input_source=InMemoryInputSource(fallback_race_id=race_id))
        publisher.engine = engine
        engine.physics.contact_collector = []
        base_controller = RuleBasedRaceController(track_obj, seed=config.random_seed)
        publisher.projector = base_controller._project
        bus = CommandBus()
        for driver in drivers:
            engine.set_controller(
                driver.driver_id,
                CoachController(
                    base=base_controller,
                    driver_id=driver.driver_id,
                    publisher=publisher,
                    bus=bus,
                ),
            )
        self._buses[race_id] = bus
        self._start_gates[race_id] = threading.Event()
        self.redis.set(f'race:{race_id}:meta', json.dumps(meta), ex=RACE_TTL)
        # O serviço de IA (separado) escuta este canal para descobrir a corrida
        # que acabou de nascer e o piloto que deve acompanhar.
        try:
            self.redis.publish(CONTROL_CHANNEL, json.dumps({
                'type': 'race_created',
                'race_id': race_id,
                'followed_driver_id': followed_driver_id,
                'num_laps': laps,
            }))
        except redis.RedisError:
            logger.warning('Não foi possível publicar race_created em %s', CONTROL_CHANNEL)
        thread = threading.Thread(
            target=self._run_engine,
            args=(engine, publisher, self._start_gates[race_id]),
            daemon=True,
        )
        self._threads[race_id] = thread
        thread.start()
        return race_id, track_obj, config

    def signal_viewer_connected(self, race_id):
        """Libera a largada quando o visualizador conecta no WebSocket."""
        gate = self._start_gates.get(race_id)
        if gate is None:
            return False
        gate.set()
        return True

    def push_command(self, race_id, driver_id, command, value=0.0, reason='', issued_by='ai'):
        """Enfileira um comando de alto nível para o coach da corrida."""
        bus = self._buses.get(race_id)
        if bus is None:
            raise KeyError(f'race not found: {race_id!r}')
        return bus.push(driver_id, command, value=value, reason=reason, issued_by=issued_by)

    def followed_driver(self, race_id):
        meta = self.metadata(race_id)
        return meta.get('followed_driver_id') if meta else None

    def _run_engine(self, engine, publisher, start_gate=None):
        try:
            if start_gate is not None:
                # Espera o viz abrir. O timeout é só uma rede de segurança,
                # para uma corrida criada por script não ficar parada.
                if not start_gate.wait(timeout=START_GATE_TIMEOUT_S):
                    logger.info('Corrida %s largou sem visualizador (timeout de %.0fs)',
                                engine.config.race_id, START_GATE_TIMEOUT_S)
            engine.run()
        except Exception as exc:
            logger.exception('Falha na corrida %s', engine.config.race_id)
            data = json.dumps({'type': 'race_error', 'message': str(exc)})
            try:
                self.redis.set(f'race:{engine.config.race_id}:result', data, ex=RACE_TTL)
                self.redis.publish(f'race:{engine.config.race_id}:events', data)
            except redis.RedisError:
                pass
        finally:
            engine.teardown()
            self._threads.pop(engine.config.race_id, None)
            self._buses.pop(engine.config.race_id, None)
            self._start_gates.pop(engine.config.race_id, None)

    def metadata(self, race_id):
        value = self.redis.get(f'race:{race_id}:meta')
        return json.loads(value) if value else None


race_manager = RaceManager(catalog=get_catalog())
