"""Corridas locais e publicação dos estados da engine no Redis."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import struct
import sys
import threading
import uuid
from dataclasses import replace

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import redis
from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from engine.physics import CHASSIS_LENGTH_M, CHASSIS_WIDTH_M, CHASSIS_HEIGHT_M
from engine import InMemoryInputSource, Publisher, RuleBasedRaceController, SimulationEngine

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
RACE_TTL = 24 * 60 * 60
logger = logging.getLogger(__name__)


class LivePublisher(Publisher):
    """Publica cada tick após o solver e guarda o último tick para reconexões."""
    def __init__(self, client, race_id):
        self.client, self.race_id = client, race_id
        self.engine = None

    def publish(self, event):
        payload = event.to_dict()
        if event.type == 'tick' and self.engine is not None:
            for rank, position in enumerate(payload['positions'], 1):
                state = self.engine.states[position['driver_id']]
                position['position'] = rank
                position['position_xy'] = [state.position_x, state.position_y]
                position['heading_deg'] = math.degrees(state.heading_rad)
                position['velocity_mps'] = state.velocity_mps
                position['progress_m'] = self.engine.race_progress_m.get(position['driver_id'], 0.0)
            # Estes contatos são medidos pelo solver em cada subpasso, não
            # inferidos a partir da proximidade entre meshes no navegador.
            contacts = self.engine.physics.contact_collector
            payload['collisions'] = list(contacts or [])
            if contacts is not None:
                contacts.clear()
        data = json.dumps(payload, ensure_ascii=False, default=str)
        pipe = self.client.pipeline(transaction=True)
        if event.type == 'tick':
            pipe.set(f'race:{self.race_id}:state', data, ex=RACE_TTL)
        if event.type == 'race_end':
            pipe.set(f'race:{self.race_id}:result', data, ex=RACE_TTL)
        pipe.publish(f'race:{self.race_id}:events', data)
        pipe.execute()


class RaceManager:
    def __init__(self, client=None):
        self.redis = client or redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        self._threads = {}

    def create_race(self, laps, track, year, num_drivers=2):
        if not 1 <= num_drivers <= 24:
            raise ValueError('A quantidade de corredores deve estar entre 1 e 24.')
        self.redis.ping()
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
        meta = {
            'race_id': race_id, 'num_laps': laps, 'num_drivers': num_drivers,
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
        controller = RuleBasedRaceController(track_obj, seed=config.random_seed)
        for driver in drivers:
            engine.set_controller(driver.driver_id, controller)
        self.redis.set(f'race:{race_id}:meta', json.dumps(meta), ex=RACE_TTL)
        thread = threading.Thread(target=self._run_engine, args=(engine, publisher), daemon=True)
        self._threads[race_id] = thread
        thread.start()
        return race_id, track_obj, config

    def _run_engine(self, engine, publisher):
        try:
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

    def metadata(self, race_id):
        value = self.redis.get(f'race:{race_id}:meta')
        return json.loads(value) if value else None


race_manager = RaceManager()
