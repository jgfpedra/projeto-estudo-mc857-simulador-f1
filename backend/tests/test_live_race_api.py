"""Contract checks for authoritative live snapshots and the Redis bridge."""
import hashlib
import json
import struct
import os
from types import SimpleNamespace

import pytest

from api.race_manager import LivePublisher
from engine.events import TickEvent


class Pipeline:
    def __init__(self):
        self.values = {}
        self.messages = []
    def set(self, key, value, ex=None):
        self.values[key] = value
        return self
    def publish(self, channel, value):
        self.messages.append((channel, value))
        return self
    def execute(self):
        return []


class Client:
    def __init__(self):
        self.pipe = Pipeline()
    def pipeline(self, transaction):
        assert transaction
        return self.pipe


def test_tick_preserves_solver_pose_rank_and_contacts():
    from domain import Track
    client = Client()
    publisher = LivePublisher(client, 'abc', [{'driver_id':'a','team_color':'#123456'}])
    track = Track.from_waypoints('test', [(0,0),(100,0),(100,100),(0,100)])
    state_a = SimpleNamespace(position_x=4.25, position_y=-8.0, heading_rad=2.0, velocity_mps=9.0, lap=0)
    state_b = SimpleNamespace(position_x=1.0, position_y=0.0, heading_rad=0.0, velocity_mps=8.0, lap=0)
    contacts = [{'drv_a':'a','drv_b':'b','f_n':100.0,'sub':1,'cx':2.0,'cy':3.0},
                {'drv_a':'b','drv_b':'a','f_n':50.0,'sub':1,'cx':2.0,'cy':3.0}]
    publisher.engine = SimpleNamespace(track=track, prev_waypoint_idx={'a':0,'b':0},
        race_progress_m={'a':12.5,'b':1.0}, race_s_m={'a':12.5,'b':1.0},
        race_lateral_m={'a':8.0,'b':0.0}, states={'a':state_a,'b':state_b},
        drivers=[SimpleNamespace(driver_id='a',name='A'),SimpleNamespace(driver_id='b',name='B')],
        physics=SimpleNamespace(contact_collector=contacts))
    positions=[{'driver_id':'a','lap':0},{'driver_id':'b','lap':0}]
    publisher.publish(TickEvent(sim_ts=1.2, positions=positions))
    tick = json.loads(client.pipe.values['race:abc:state'])
    assert tick['schema_version'] == 1 and tick['leader_lap'] == 0
    assert tick['positions'][0]['heading_deg'] == pytest.approx(114.59, abs=0.01)
    assert tick['positions'][0]['team_color'] == '#123456'
    assert tick['positions'][0]['gap_to_leader_s'] == 0.0
    assert tick['positions'][0]['d_m'] == pytest.approx(8.0)
    assert tick['positions'][1]['gap_to_leader_s'] is None
    assert len(tick['collisions']) == 1
    assert tick['collisions'][0]['impact_force_n'] == 150.0
    assert contacts == []
    assert json.loads(client.pipe.messages[0][1]) == tick
    assert json.loads(client.pipe.messages[1][1])['type'] == 'collision'
    assert json.loads(client.pipe.values['race:abc:snapshot'])['last_tick'] == tick



@pytest.mark.skipif(not os.getenv('TEST_REDIS_URL'), reason='requires an isolated Redis server')
def test_real_engine_redis_websocket_roundtrip(monkeypatch):
    from fastapi.testclient import TestClient
    from api.main import app, race_manager
    import redis

    client = redis.Redis.from_url(os.environ['TEST_REDIS_URL'], decode_responses=True)
    import api.main as api_main
    from api.providers.race_data import FallbackProvider
    monkeypatch.setattr(api_main, 'REDIS_URL', os.environ['TEST_REDIS_URL'])
    monkeypatch.setattr(race_manager, 'redis', client)
    monkeypatch.setattr(race_manager, 'provider', FallbackProvider())
    with TestClient(app) as http:
        response = http.post('/races', json={'laps': 1, 'track': 'interlagos', 'num_drivers': 10})
        assert response.status_code == 200, response.text
        race_id = response.json()['race_id']
        metadata = http.get(f'/races/{race_id}').json()
        assert len(metadata['track']['waypoints']) > 3
        assert len(metadata['drivers']) == 10
        assert metadata['drivers'][0]['abbreviation'] == 'VER'
        assert metadata['season'] == 2023 and metadata['circuit_id'] == 'interlagos'
        assert metadata['track']['width_m'] == 12.0
        assert all(d['team_color'].startswith('#') for d in metadata['drivers'])
        assert metadata['car_geometry'] == {'length_m': 5.0, 'width_m': 1.8, 'height_m': 0.7}
        assert metadata['track']['source'] == 'telemetry'
        encoded = b''.join(struct.pack('<dd', *point) for point in metadata['track']['waypoints'])
        assert metadata['track']['geometry_sha256'] == hashlib.sha256(encoded).hexdigest()[:16]
        assert metadata['track']['start_finish_waypoint'] == 0
        with http.websocket_connect(f'/ws/races/{race_id}') as ws:
            got_start = False
            for _ in range(30):
                tick = ws.receive_json()
                if tick['type'] == 'race_start':
                    got_start = True
                if tick['type'] == 'tick':
                    break
            assert got_start and tick['type'] == 'tick', tick
            assert len(tick['positions']) == 10
            assert tick['schema_version'] == 1 and 'leader_lap' in tick
            assert all('gap_to_leader_s' in p and 'd_m' in p and 's_m' in p for p in tick['positions'])
            saved = http.get(f'/races/{race_id}/snapshot').json()
            assert saved['status'] == 'running' and saved['last_tick']['type'] == 'tick'
            assert all(len(p['position_xy']) == 2 and 'heading_deg' in p and 'progress_m' in p for p in tick['positions'])
            assert 'collisions' in tick
            assert client.get(f'race:{race_id}:state') is not None
        with http.websocket_connect(f'/ws/races/{race_id}') as reconnected:
            restored = reconnected.receive_json()
            if restored['type'] == 'race_start':
                restored = reconnected.receive_json()
            assert restored['type'] == 'tick'
            assert restored['sim_ts'] >= tick['sim_ts']


@pytest.mark.parametrize('enabled,camera,expected_gui,expected_camera', [
    ('1', 'overview', True, 'overview'),
    ('0', 'follow', False, 'none'),
])
def test_gui_is_enabled_only_when_requested(monkeypatch, enabled, camera, expected_gui, expected_camera):
    import api.race_manager as module

    class RedisStub:
        def ping(self):
            return True
        def set(self, *args, **kwargs):
            return True

    class EngineStub:
        def __init__(self, **kwargs):
            self.config = kwargs['config']
            self.physics = SimpleNamespace(contact_collector=None)
        def set_controller(self, *_args):
            pass

    class ThreadStub:
        def __init__(self, **_kwargs):
            pass
        def start(self):
            pass

    engines = []
    def make_engine(**kwargs):
        engine = EngineStub(**kwargs)
        engines.append(engine)
        return engine

    monkeypatch.setenv('F1_PYBULLET_GUI', enabled)
    monkeypatch.setenv('F1_GUI_CAMERA', camera)
    monkeypatch.setattr(module, 'SimulationEngine', make_engine)
    monkeypatch.setattr(module, 'RuleBasedRaceController', lambda *_args, **_kwargs: object())
    monkeypatch.setattr(module.threading, 'Thread', ThreadStub)
    from api.providers.race_data import FallbackProvider
    manager = module.RaceManager(RedisStub(), provider=FallbackProvider())
    manager.create_race(1, 'interlagos', None)
    assert engines[0].config.gui is expected_gui
    assert engines[0].config.camera_mode == expected_camera
    assert engines[0].config.draw_track is expected_gui
