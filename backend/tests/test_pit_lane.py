"""A passagem pelos boxes deve ser simulada, visível e sem penalidade contábil."""
import math
from dataclasses import replace

import pytest
import pybullet as pb

from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from domain import TyreCompound
from domain.pit_lane import ensure_pit_lane
from engine import RuleBasedRaceController, SimulationEngine
from engine.publisher import Publisher


class Events(Publisher):
    def __init__(self): self.events = []
    def publish(self, event): self.events.append(event.to_dict())


@pytest.mark.parametrize('circuit,year', [('interlagos', 2023), ('monza', 2024)])
def test_physical_passage_changes_tyres_and_crosses_line(circuit, year):
    track = load_live_track(track_name=circuit, year=year)
    driver = DEFAULT_DRIVERS[0]
    events = Events()
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False,
                                     track_progress_laps=True, num_laps=3), track, [driver], publisher=events)
    engine.setup()
    engine.set_controller(driver.driver_id, RuleBasedRaceController(track, seed=42))
    try:
        a, b = track.pit.waypoints[:2]
        heading = math.atan2(b[1]-a[1], b[0]-a[0])
        cid, car = engine.physics._client_id, engine.handles[driver.driver_id].chassis_id
        pb.resetBasePositionAndOrientation(car, (a[0], a[1], .5),
            pb.getQuaternionFromEuler((0, 0, heading)), physicsClientId=cid)
        pb.resetBaseVelocity(car, (20*math.cos(heading), 20*math.sin(heading), 0), physicsClientId=cid)
        state = engine.states[driver.driver_id]
        state.tyre.tyre_life = 10
        engine.prev_waypoint_idx[driver.driver_id] = track.pit.entry_waypoint
        engine.last_pos[driver.driver_id] = a
        engine._update_race_progress(.1)
        # Já percorreu a maior parte da primeira volta antes de chegar à entrada.
        engine.race_progress_m[driver.driver_id] = track.length_m - 500
        engine._pit_requests[driver.driver_id] = {'compound': TyreCompound.MEDIUM, 'fuel': 0, 'serviced': False}
        assert state.pit_stop_done == 0
        seen_pit = False
        max_lane_error = 0.0
        observed_speeds = []
        for tick in range(550):
            engine._step_tick(.1, 24)
            if state.pitting:
                seen_pit = True
                max_lane_error = max(max_lane_error, engine.pit_controller.distance_to_lane(state.position_x, state.position_y))
                if tick > 50: observed_speeds.append(state.velocity_mps)
            if driver.driver_id not in engine._pit_requests:
                break
        else:
            pytest.fail('O carro não saiu dos boxes')
        assert seen_pit and not state.pitting
        assert max_lane_error < 3.5
        assert max(observed_speeds) <= track.pit.speed_limit_kmh/3.6 + 1
        assert state.pit_stop_done == 1 and state.tyre.tyre_life > 90
        assert state.pit_penalty_pending_s == 0
        assert state.lap == 1
        assert engine.race_progress_m[driver.driver_id] > track.length_m
        pit_events = [e for e in events.events if e['type'] == 'pit_stop']
        assert len(pit_events) == 1 and pit_events[0]['pit_time_s'] == 0
        assert any(e['type'] == 'tick' and e['positions'][0]['pitting'] for e in events.events)
        lap = next(e for e in events.events if e['type'] == 'lap_completed')
        assert lap['lap_time_s'] <= engine.sim_ts
    finally:
        engine.teardown()


def test_estimated_and_explicit_pit_paths():
    from domain import PitLane
    track = load_live_track(track_name='interlagos', year=2023)
    lane = ensure_pit_lane(track)
    assert lane.source == 'estimated' and len(lane.waypoints) > 20
    assert track.distance_to_centerline(*lane.waypoints[0]) < 1
    assert track.distance_to_centerline(*lane.waypoints[-1]) < 1
    explicit = PitLane(0, 2, waypoints=[(0, 0), (1, 1), (2, 0)], source='measured')
    track.pit = explicit
    assert ensure_pit_lane(track) is explicit


def test_pit_request_does_not_change_tyres_until_the_car_reaches_boxes():
    track = load_live_track(track_name='interlagos', year=2023)
    driver = DEFAULT_DRIVERS[0]
    events = Events()
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False, num_laps=3),
                              track, [driver], publisher=events)
    engine.setup()
    try:
        state = engine.states[driver.driver_id]
        state.tyre.tyre_life = 1.0
        old = state.tyre
        engine.sim_ts = 70.0
        engine._complete_lap(driver)
        assert driver.driver_id in engine._pit_requests
        assert not state.pitting and state.pit_stop_done == 0
        assert state.tyre is old and state.pit_penalty_pending_s == 0
        assert not any(e['type'] == 'pit_stop' for e in events.events)
    finally:
        engine.teardown()


def test_measured_lane_loader_scales_and_rejects_disconnected_geometry():
    from domain.track_loader import _pit_lane_from_info
    points = [(0, 0), (100, 0), (100, 100), (0, 100)]
    data = {'PitLane': [{'X': 0, 'Y': 0}, {'X': 25, 'Y': -2}, {'X': 50, 'Y': 0}]}
    pit = _pit_lane_from_info(data, points, scale=2)
    assert pit.source == 'track_data' and pit.waypoints[1] == (50, -4)
    data['PitLane'] = [{'X': 10000, 'Y': 10000}, {'X': 10001, 'Y': 10000}, {'X': 10002, 'Y': 10000}]
    assert _pit_lane_from_info(data, points).waypoints == []


def test_pitting_car_loses_position_to_a_car_on_the_track():
    track = load_live_track(track_name='interlagos', year=2023)
    first, second = DEFAULT_DRIVERS[:2]
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False,
                                     track_progress_laps=True, num_laps=3), track, [first, second])
    engine.setup()
    controller = RuleBasedRaceController(track, seed=42)
    for driver in (first, second):
        engine.set_controller(driver.driver_id, controller)
    try:
        entry = track.pit.entry_waypoint
        behind, distance = entry, 0.0
        while distance < 40:
            prior = (behind - 1) % len(track.waypoints)
            distance += math.dist(track.waypoints[behind], track.waypoints[prior])
            behind = prior
        for driver, index in ((first, entry), (second, behind)):
            a = track.waypoints[index]
            b = track.waypoints[(index + 1) % len(track.waypoints)]
            heading = math.atan2(b[1]-a[1], b[0]-a[0])
            cid, car = engine.physics._client_id, engine.handles[driver.driver_id].chassis_id
            pb.resetBasePositionAndOrientation(car, (a[0], a[1], .5),
                pb.getQuaternionFromEuler((0, 0, heading)), physicsClientId=cid)
            pb.resetBaseVelocity(car, (25*math.cos(heading), 25*math.sin(heading), 0), physicsClientId=cid)
            engine.prev_waypoint_idx[driver.driver_id] = index
            engine.last_pos[driver.driver_id] = a
        engine._update_race_progress(.1)
        assert engine.ranked_drivers()[0] == first
        engine._pit_requests[first.driver_id] = {'compound': TyreCompound.MEDIUM, 'fuel': 0, 'serviced': False}
        for _ in range(150):
            engine._step_tick(.1, 24)
            if engine.ranked_drivers()[0] == second:
                break
        else:
            pytest.fail('O carro que permaneceu na pista não ganhou a posição')
        assert engine.states[first.driver_id].pitting
        assert engine.race_progress_m[second.driver_id] > engine.race_progress_m[first.driver_id]
    finally:
        engine.teardown()
