"""HTTP requests are handed to the simulation thread and affect physical pit stops."""
import json
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace

import pytest
import pybullet as pb
from fastapi.testclient import TestClient

from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from domain import TyreCompound
from engine import RuleBasedRaceController, SimulationEngine
from engine.publisher import Publisher
from api.race_manager import RaceManager


class Events(Publisher):
    def __init__(self): self.events = []
    def publish(self, event): self.events.append(event.to_dict())


class Store:
    def __init__(self, values): self.values = values
    def get(self, key): return self.values.get(key)


@pytest.fixture
def context(monkeypatch):
    from api import main
    track = load_live_track(track_name='interlagos', year=2023)
    driver = DEFAULT_DRIVERS[0]
    events = Events()
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False,
                                     track_progress_laps=True, num_laps=3), track, [driver], publisher=events)
    engine.setup()
    engine.set_controller(driver.driver_id, RuleBasedRaceController(track, seed=42))
    meta = json.dumps({'drivers': [{'driver_id': driver.driver_id}]})
    store = Store({'race:race_test:meta': meta, 'race:race_finished:meta': meta})
    manager = RaceManager(client=store)
    manager._engines['race_test'] = engine
    monkeypatch.setattr(main, 'race_manager', manager)
    with TestClient(main.app) as http:
        yield SimpleNamespace(http=http, engine=engine, driver=driver, events=events, manager=manager)
    engine.teardown()


def test_http_rejects_invalid_or_unavailable_requests(context):
    c, driver_id = context.http, context.driver.driver_id
    endpoint = f'/races/race_test/drivers/{driver_id}/pit-stop'
    assert c.post(endpoint, json={'tyre_compound': 'banana'}).status_code == 422
    assert c.post(endpoint, json={}).status_code == 422
    assert c.post('/races/missing/drivers/x/pit-stop', json={'tyre_compound': 'soft'}).status_code == 404
    assert c.post('/races/race_test/drivers/missing/pit-stop', json={'tyre_compound': 'soft'}).status_code == 404
    assert c.post(f'/races/race_finished/drivers/{driver_id}/pit-stop', json={'tyre_compound': 'soft'}).status_code == 409
    response = c.post(endpoint, json={'tyre_compound': 'SOFT'})
    assert response.status_code == 202
    assert response.json() == {'race_id': 'race_test', 'driver_id': driver_id,
                               'tyre_compound': 'soft', 'status': 'queued'}
    assert c.post(endpoint, json={'tyre_compound': 'wet'}).status_code == 409
    assert driver_id not in context.engine._pit_requests
    assert context.engine.states[driver_id].pit_stop_done == 0


def test_manual_request_overrides_automatic_and_drives_to_pit(context):
    engine, driver, events = context.engine, context.driver, context.events
    driver_id = driver.driver_id
    track, state = engine.track, engine.states[driver_id]
    a, b = track.pit.waypoints[:2]
    heading = math.atan2(b[1]-a[1], b[0]-a[0])
    cid, car = engine.physics._client_id, engine.handles[driver_id].chassis_id
    pb.resetBasePositionAndOrientation(car, (a[0], a[1], .5),
        pb.getQuaternionFromEuler((0, 0, heading)), physicsClientId=cid)
    pb.resetBaseVelocity(car, (20*math.cos(heading), 20*math.sin(heading), 0), physicsClientId=cid)
    engine.prev_waypoint_idx[driver_id] = track.pit.entry_waypoint
    engine.last_pos[driver_id] = a
    engine._update_race_progress(.1)
    engine._pit_requests[driver_id] = {'compound': TyreCompound.MEDIUM, 'fuel': 0, 'serviced': False}
    old_tyre = state.tyre
    response = context.http.post(f'/races/race_test/drivers/{driver_id}/pit-stop',
                                 json={'tyre_compound': 'wet'})
    assert response.status_code == 202
    assert state.tyre is old_tyre and engine._pit_requests[driver_id]['compound'] == TyreCompound.MEDIUM
    engine._step_tick(.1, 24)
    assert engine._pit_requests[driver_id]['compound'] == TyreCompound.WET
    assert state.tyre is old_tyre and state.pitting
    requested = [event for event in events.events if event['type'] == 'pit_requested']
    assert len(requested) == 1 and requested[0]['tyre_compound'] == 'WET'
    assert context.http.post(f'/races/race_test/drivers/{driver_id}/pit-stop',
                             json={'tyre_compound': 'soft'}).status_code == 409
    for _ in range(550):
        engine._step_tick(.1, 24)
        if driver_id not in engine._pit_requests:
            break
    else:
        pytest.fail('Carro não completou a passagem pelos boxes')
    assert state.tyre.model.compound == TyreCompound.WET
    pit_events = [event for event in events.events if event['type'] == 'pit_stop']
    assert len(pit_events) == 1 and pit_events[0]['new_compound'] == 'WET'
    assert state.pit_penalty_pending_s == 0
    assert context.http.post(f'/races/race_test/drivers/{driver_id}/pit-stop',
                             json={'tyre_compound': 'hard'}).status_code == 202


def test_simultaneous_duplicate_requests_are_rejected(context):
    engine, driver_id = context.engine, context.driver.driver_id
    def request(_):
        try:
            engine.request_pit_stop(driver_id, TyreCompound.SOFT)
            return 'accepted'
        except RuntimeError:
            return 'duplicate'
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(request, range(20)))
    assert results.count('accepted') == 1
    assert results.count('duplicate') == 19
    engine.close_pit_requests()
    with pytest.raises(RuntimeError, match='ativa'):
        engine.request_pit_stop(driver_id, TyreCompound.WET)


def test_http_command_reaches_websocket_via_real_redis(monkeypatch):
    import os
    import redis
    import api.main as main
    from api.race_manager import LivePublisher
    url = os.getenv('TEST_REDIS_URL')
    if not url:
        pytest.skip('requires an isolated Redis server')
    client = redis.Redis.from_url(url, decode_responses=True)
    race_id = 'race_pit_websocket'
    driver = DEFAULT_DRIVERS[0]
    track = load_live_track(track_name='interlagos', year=2023)
    publisher = LivePublisher(client, race_id)
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False,
                                     track_progress_laps=True, num_laps=3, race_id=race_id),
                              track, [driver], publisher=publisher)
    engine.setup()
    engine.set_controller(driver.driver_id, RuleBasedRaceController(track, seed=42))
    engine.physics.contact_collector = []
    publisher.engine = engine
    manager = RaceManager(client=client)
    manager._engines[race_id] = engine
    client.set(f'race:{race_id}:meta', json.dumps({'drivers': [{'driver_id': driver.driver_id}]}))
    monkeypatch.setattr(main, 'REDIS_URL', url)
    monkeypatch.setattr(main, 'race_manager', manager)
    try:
        with TestClient(main.app) as http:
            with http.websocket_connect(f'/ws/races/{race_id}') as ws:
                result = http.post(f'/races/{race_id}/drivers/{driver.driver_id}/pit-stop',
                                   json={'tyre_compound': 'hard'})
                assert result.status_code == 202
                engine._step_tick(.1, 24)
                event = ws.receive_json()
                assert event['type'] == 'pit_requested'
                assert event['race_id'] == race_id
                assert event['driver_id'] == driver.driver_id and event['tyre_compound'] == 'HARD'
                tick = ws.receive_json()
                assert tick['type'] == 'tick'
                assert tick['positions'][0]['pit_request'] == {
                    'tyre_compound': 'HARD', 'source': 'user', 'status': 'scheduled'}
                cancelled = http.delete(f'/races/{race_id}/drivers/{driver.driver_id}/pit-stop')
                assert cancelled.status_code == 202
                engine._step_tick(.1, 24)
                event = ws.receive_json()
                assert event['type'] == 'pit_cancelled' and event['driver_id'] == driver.driver_id
                assert ws.receive_json()['positions'][0]['pit_request'] is None
                snapshot = http.get(f'/races/{race_id}/snapshot').json()
                assert snapshot['last_tick']['positions'][0]['pit_request'] is None
    finally:
        engine.teardown()
        for suffix in ('meta', 'snapshot', 'state', 'start', 'result'):
            client.delete(f'race:{race_id}:{suffix}')


def test_real_race_thread_consumes_command(monkeypatch):
    import os
    import time
    import redis
    import api.main as main
    from api.providers.race_data import driver_record
    url = os.getenv('TEST_REDIS_URL')
    if not url:
        pytest.skip('requires an isolated Redis server')
    store = redis.Redis.from_url(url, decode_responses=True)
    class Provider:
        def load(self, _circuit, _year):
            track = load_live_track(track_name='interlagos', year=2023)
            return track, [driver_record('AAA', 'Driver A', 1, 'Team', '112233')], {
                'track_source': 'test', 'driver_source': 'test'}
    manager = RaceManager(client=store, provider=Provider())
    monkeypatch.setattr(main, 'race_manager', manager)
    race_id = None
    pubsub = store.pubsub()
    try:
        with TestClient(main.app) as http:
            response = http.post('/races', json={'track': 'interlagos', 'year': 2023,
                                                  'laps': 2, 'num_drivers': 1})
            assert response.status_code == 200, response.text
            race_id = response.json()['race_id']
            driver_id = http.get(f'/races/{race_id}').json()['drivers'][0]['driver_id']
            pubsub.subscribe(f'race:{race_id}:events')
            assert pubsub.get_message(timeout=2)['type'] == 'subscribe'
            result = http.post(f'/races/{race_id}/drivers/{driver_id}/pit-stop',
                               json={'tyre_compound': 'intermediate'})
            assert result.status_code == 202, result.text
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                message = pubsub.get_message(timeout=0.2)
                if message and message['type'] == 'message':
                    event = json.loads(message['data'])
                    if event['type'] == 'pit_requested':
                        break
            else:
                pytest.fail('A thread da corrida não confirmou o pedido')
            assert event['driver_id'] == driver_id and event['tyre_compound'] == 'INTERMEDIATE'
    finally:
        pubsub.close()
        if race_id:
            with manager._engines_lock:
                engine = manager._engines.get(race_id)
                thread = manager._threads.get(race_id)
            if engine:
                engine.race_finished = True
            if thread:
                thread.join(timeout=10)
                assert not thread.is_alive()
            for suffix in ('meta', 'snapshot', 'state', 'start', 'result'):
                store.delete(f'race:{race_id}:{suffix}')


def test_cancel_queued_request_before_engine_tick(context):
    c, engine, driver = context.http, context.engine, context.driver
    endpoint = f'/races/race_test/drivers/{driver.driver_id}/pit-stop'
    old_tyre = engine.states[driver.driver_id].tyre
    assert c.post(endpoint, json={'tyre_compound': 'soft'}).status_code == 202
    response = c.delete(endpoint)
    assert response.status_code == 202
    assert response.json() == {'race_id': 'race_test', 'driver_id': driver.driver_id,
                               'status': 'cancellation_queued'}
    assert c.delete(endpoint).status_code == 409
    assert c.post(endpoint, json={'tyre_compound': 'wet'}).status_code == 409
    engine._step_tick(.1, 24)
    assert driver.driver_id not in engine._pit_commands
    assert driver.driver_id not in engine._pit_requests
    assert engine.states[driver.driver_id].tyre is old_tyre
    assert not engine.states[driver.driver_id].pitting
    types = [event['type'] for event in context.events.events]
    assert types.count('pit_cancelled') == 1
    assert 'pit_requested' not in types and 'pit_stop' not in types
    assert c.post(endpoint, json={'tyre_compound': 'hard'}).status_code == 202


def test_cancel_during_approach_before_entry(context):
    engine, driver = context.engine, context.driver
    track, state = engine.track, engine.states[driver.driver_id]
    a, b = track.pit.waypoints[:2]
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    dx, dy = dx/length, dy/length
    x, y = a[0]-30*dx, a[1]-30*dy
    heading = math.atan2(dy, dx)
    cid, car = engine.physics._client_id, engine.handles[driver.driver_id].chassis_id
    pb.resetBasePositionAndOrientation(car, (x, y, .5),
        pb.getQuaternionFromEuler((0, 0, heading)), physicsClientId=cid)
    state.position_x, state.position_y, state.pitting = x, y, True
    engine._pit_requests[driver.driver_id] = {
        'compound': TyreCompound.WET, 'fuel': 0, 'serviced': False, 'source': 'user'}
    engine._manual_pit_active.add(driver.driver_id)
    assert not engine.pit_controller.has_entered(state)
    assert engine._snapshot_position(driver)['pit_request']['status'] == 'approaching'
    endpoint = f'/races/race_test/drivers/{driver.driver_id}/pit-stop'
    assert context.http.delete(endpoint).status_code == 202
    engine._step_tick(.1, 24)
    assert not state.pitting and driver.driver_id not in engine._pit_requests
    assert [event['type'] for event in context.events.events].count('pit_cancelled') == 1


def test_cancel_rejects_after_entering_pit_lane(context):
    engine, driver = context.engine, context.driver
    state = engine.states[driver.driver_id]
    state.pitting = True
    engine._pit_requests[driver.driver_id] = {'compound': TyreCompound.HARD, 'fuel': 0, 'serviced': False}
    engine.pit_controller.progress[driver.driver_id] = 5.0
    endpoint = f'/races/race_test/drivers/{driver.driver_id}/pit-stop'
    response = context.http.delete(endpoint)
    assert response.status_code == 409 and 'entrou' in response.json()['detail']
    assert driver.driver_id in engine._pit_requests
    assert engine._snapshot_position(driver)['pit_request']['status'] == 'in_pit_lane'


def test_cancel_rechecked_if_car_crosses_entry_before_tick(context):
    engine, driver = context.engine, context.driver
    state, track = engine.states[driver.driver_id], engine.track
    a, b = track.pit.waypoints[:2]
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    dx, dy = dx/length, dy/length
    state.position_x, state.position_y, state.pitting = a[0]-dx*3, a[1]-dy*3, True
    engine._pit_requests[driver.driver_id] = {'compound': TyreCompound.WET, 'fuel': 0, 'serviced': False}
    endpoint = f'/races/race_test/drivers/{driver.driver_id}/pit-stop'
    assert context.http.delete(endpoint).status_code == 202
    cid, car = engine.physics._client_id, engine.handles[driver.driver_id].chassis_id
    pb.resetBasePositionAndOrientation(car, (a[0]+dx*5, a[1]+dy*5, .5),
        pb.getQuaternionFromEuler((0, 0, math.atan2(dy, dx))), physicsClientId=cid)
    engine._step_tick(.1, 24)
    events = context.events.events
    assert any(event['type'] == 'pit_cancel_rejected' and
               event['reason'] == 'already_in_pit_lane' for event in events)
    assert not any(event['type'] == 'pit_cancelled' for event in events)
    assert driver.driver_id in engine._pit_requests and state.pitting


def test_cancel_auto_request_waits_one_decision_before_rescheduling(context):
    engine, driver = context.engine, context.driver
    state = engine.states[driver.driver_id]
    state.tyre.tyre_life = 1.0
    engine._pit_requests[driver.driver_id] = {'compound': TyreCompound.MEDIUM, 'fuel': 0, 'serviced': False}
    endpoint = f'/races/race_test/drivers/{driver.driver_id}/pit-stop'
    assert context.http.delete(endpoint).status_code == 202
    engine._step_tick(.1, 24)
    assert driver.driver_id not in engine._pit_requests
    engine._complete_lap(driver)
    assert driver.driver_id not in engine._pit_requests
    engine._complete_lap(driver)
    assert driver.driver_id in engine._pit_requests


def test_cancel_errors(context):
    c, driver_id = context.http, context.driver.driver_id
    assert c.delete('/races/missing/drivers/x/pit-stop').status_code == 404
    assert c.delete('/races/race_test/drivers/missing/pit-stop').status_code == 404
    assert c.delete(f'/races/race_finished/drivers/{driver_id}/pit-stop').status_code == 409
    assert c.delete(f'/races/race_test/drivers/{driver_id}/pit-stop').status_code == 409
