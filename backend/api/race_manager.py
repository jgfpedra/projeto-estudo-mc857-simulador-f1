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
from engine.physics import CHASSIS_LENGTH_M, CHASSIS_WIDTH_M, CHASSIS_HEIGHT_M
from engine import InMemoryInputSource, Publisher, RuleBasedRaceController, SimulationEngine
from .providers.race_data import default_provider, driver_record
from .providers.f1db_layouts import load_layout_catalog, normalize

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
RACE_TTL = 24 * 60 * 60
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
        self.redis = client or redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        self.provider = provider or default_provider()
        try:
            self.catalog = catalog if catalog is not None else load_layout_catalog()
        except (OSError, ValueError) as exc:
            logger.warning('Catálogo F1DB indisponível: %s', exc)
            self.catalog = None
        self._threads = {}

    def create_race(self, laps, track, year, num_drivers=2, layout_id=None):
        if not 1 <= num_drivers <= 24:
            raise ValueError('A quantidade de corredores deve estar entre 1 e 24.')
        self.redis.ping()
        circuit = (track or 'interlagos').strip().lower() or 'interlagos'
        catalog_circuit = self.catalog.find_circuit(circuit) if self.catalog else None
        circuit_id = catalog_circuit['id'] if catalog_circuit else normalize(circuit).replace(' ', '-')
        season = year or (2024 if circuit_id == 'monza' else 2023)
        layout = self.catalog.find_layout(catalog_circuit, season) if catalog_circuit else None
        if layout_id is not None and (layout is None or layout['id'] != layout_id):
            raise ValueError(f"O layout '{layout_id}' não é confirmado para '{circuit_id}' em {season} pelo catálogo F1DB; confira a temporada e o catálogo.")
        track_obj, roster, sources = self.provider.load(circuit, season)
        if not roster:
            raise ValueError('Fonte não forneceu pilotos')
        roster = list(roster[:num_drivers])
        while len(roster) < num_drivers:
            i = len(roster)+1
            roster.append(driver_record(f'P{i:02d}', f'Piloto {i:02d}', None, None, '808080'))
        drivers = [replace(DEFAULT_DRIVERS[i % len(DEFAULT_DRIVERS)], driver_id=entry['driver_id'], name=entry['name'])
                   for i, entry in enumerate(roster)]
        race_id = f'race_{uuid.uuid4().hex}'
        gui = os.environ.get('F1_PYBULLET_GUI', '').lower() in ('1','true','yes','on')
        camera = os.environ.get('F1_GUI_CAMERA', 'follow') if gui else 'none'
        if camera not in ('follow', 'overview', 'none'):
            raise ValueError(f'Modo de câmera inválido: {camera}')
        config = replace(DEFAULT_INTERLAGOS_CONFIG, race_id=race_id, num_laps=laps, gui=gui,
                         camera_mode=camera, draw_track=gui, draw_track_details=False,
                         realtime=True, track_progress_laps=True)
        geometry = b''.join(struct.pack('<dd', float(x), float(y)) for x,y in track_obj.waypoints)
        digest = hashlib.sha256(geometry).hexdigest()[:16]
        driver_meta = [{**d, 'grid_position': i+1} for i,d in enumerate(roster)]
        meta = {'race_id':race_id, 'schema_version':SCHEMA_VERSION, 'season':season,
                'circuit_id':circuit_id, 'layout_id':layout['id'] if layout else None,
                'layout_reference':{'source':'F1DB','basis':'season', 'years':layout['years'],
                                    'catalog_generated_at':self.catalog.data.get('generated_at')} if layout else None,
                'num_laps':laps, 'num_drivers':num_drivers, 'sources':sources,
                'car_geometry':{'length_m':CHASSIS_LENGTH_M,'width_m':CHASSIS_WIDTH_M,'height_m':CHASSIS_HEIGHT_M},
                'track':{'name':track_obj.name, 'source':track_obj.source, 'geometry_sha256':digest,
                         'length_m':track_obj.length_m, 'width_m':track_obj.width_m,
                         'start_finish_waypoint':track_obj.start_finish_waypoint,
                         'waypoints':[[float(x),float(y)] for x,y in track_obj.waypoints]},
                'drivers':driver_meta}
        publisher = LivePublisher(self.redis, race_id, driver_meta)
        engine = SimulationEngine(config=config, track=track_obj, drivers=drivers, publisher=publisher,
                                  input_source=InMemoryInputSource(fallback_race_id=race_id))
        publisher.engine = engine
        engine.physics.contact_collector = []
        engine.physics.contact_collector_include_penetration = True
        controller = RuleBasedRaceController(track_obj, seed=config.random_seed)
        for driver in drivers:
            engine.set_controller(driver.driver_id, controller)
        self.redis.set(f'race:{race_id}:meta', json.dumps(meta, ensure_ascii=False), ex=RACE_TTL)
        self.redis.set(f'race:{race_id}:snapshot', json.dumps(publisher.snapshot), ex=RACE_TTL)
        thread = threading.Thread(target=self._run_engine, args=(engine,publisher), daemon=True)
        self._threads[race_id] = thread
        thread.start()
        return race_id, track_obj, config

    def _run_engine(self, engine, publisher):
        try:
            engine.run()
        except Exception as exc:
            logger.exception('Falha na corrida %s', engine.config.race_id)
            data = json.dumps({'type':'race_error','schema_version':SCHEMA_VERSION,'message':str(exc)})
            try:
                publisher.snapshot.update(status='failed', sim_ts=engine.sim_ts)
                pipe = self.redis.pipeline(transaction=True)
                pipe.set(f'race:{engine.config.race_id}:snapshot', json.dumps(publisher.snapshot), ex=RACE_TTL)
                pipe.set(f'race:{engine.config.race_id}:result', data, ex=RACE_TTL)
                pipe.publish(f'race:{engine.config.race_id}:events', data)
                pipe.execute()
            except redis.RedisError:
                pass
        finally:
            engine.teardown()
            self._threads.pop(engine.config.race_id, None)

    def metadata(self, race_id):
        value = self.redis.get(f'race:{race_id}:meta')
        return json.loads(value) if value else None

    def snapshot(self, race_id):
        value = self.redis.get(f'race:{race_id}:snapshot')
        return json.loads(value) if value else None


race_manager = RaceManager()
