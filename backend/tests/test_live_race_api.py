"""Contract checks for authoritative live snapshots and the Redis bridge."""
import json
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
    client = Client()
    publisher = LivePublisher(client, 'abc')
    contacts = [{'drv_a': 'a', 'drv_b': 'b', 'j_n': 12.0}]
    publisher.engine = SimpleNamespace(race_progress_m={'a': 12.5}, states={'a': SimpleNamespace(position_x=4.25, position_y=-8.0, heading_rad=3.141592653589793 * 0.75, velocity_mps=9.0)}, physics=SimpleNamespace(contact_collector=contacts))
    publisher.publish(TickEvent(sim_ts=1.2, positions=[{'driver_id': 'a', 'position_xy': [4.25, -8.0], 'heading_deg': 135.0}]))
    snapshot = json.loads(client.pipe.values['race:abc:state'])
    assert snapshot['positions'][0] == {'driver_id': 'a', 'position_xy': [4.25, -8.0], 'heading_deg': 135.0, 'velocity_mps': 9.0, 'position': 1, 'progress_m': 12.5}
    assert snapshot['collisions'] == [{'drv_a': 'a', 'drv_b': 'b', 'j_n': 12.0}]
    assert contacts == []
    assert json.loads(client.pipe.messages[0][1]) == snapshot


@pytest.mark.skipif(not os.getenv('TEST_REDIS_URL'), reason='requires an isolated Redis server')
def test_real_engine_redis_websocket_roundtrip():
    from fastapi.testclient import TestClient
    from api.main import app, race_manager
    import redis

    client = redis.Redis.from_url(os.environ['TEST_REDIS_URL'], decode_responses=True)
    race_manager.redis = client
    with TestClient(app) as http:
        response = http.post('/races', json={'laps': 1, 'track': 'interlagos'})
        assert response.status_code == 200, response.text
        race_id = response.json()['race_id']
        metadata = http.get(f'/races/{race_id}').json()
        assert len(metadata['track']['waypoints']) > 3
        assert len(metadata['drivers']) == 2
        with http.websocket_connect(f'/ws/races/{race_id}') as ws:
            for _ in range(30):
                tick = ws.receive_json()
                if tick['type'] == 'tick':
                    break
            assert tick['type'] == 'tick', tick
            assert len(tick['positions']) == 2
            assert all(len(p['position_xy']) == 2 and 'heading_deg' in p and 'progress_m' in p for p in tick['positions'])
            assert 'collisions' in tick
            assert client.get(f'race:{race_id}:state') is not None
        with http.websocket_connect(f'/ws/races/{race_id}') as reconnected:
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
    manager = module.RaceManager(RedisStub())
    manager.create_race(1, 'interlagos', None)
    assert engines[0].config.gui is expected_gui
    assert engines[0].config.camera_mode == expected_camera
    assert engines[0].config.draw_track is expected_gui
