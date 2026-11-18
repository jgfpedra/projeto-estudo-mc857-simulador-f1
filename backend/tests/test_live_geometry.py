"""Verifica o traçado e o grid usados pela corrida ao vivo."""
import json
import math
from dataclasses import replace
from pathlib import Path

import pytest
import pybullet as p
from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from engine import SimulationEngine
from engine.physics import CHASSIS_LENGTH_M, CHASSIS_WIDTH_M, CHASSIS_HEIGHT_M

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('name,reference,length', [
    ('interlagos', 'interlagos.json', 4226.1),
    ('monza', 'monza.json', 5756.8),
])
def test_live_grid_uses_telemetry_timing_line_and_straight(name, reference, length):
    track = load_live_track(name)
    raw = json.loads((ROOT / 'viz3d/public/tracks' / reference).read_text())
    assert track.source == 'telemetry'
    assert track.start_finish_waypoint == 0
    assert track.length_m == pytest.approx(length, abs=2)
    x, _, z = raw['centerline'][0]
    assert track.waypoints[0] == pytest.approx((x, -z), abs=1e-5)
    # Every initial slot is behind the timing line and inside the same track.
    tx = track.waypoints[1][0] - track.waypoints[-1][0]
    ty = track.waypoints[1][1] - track.waypoints[-1][1]
    norm = math.hypot(tx, ty)
    tx, ty = tx / norm, ty / norm
    origin = track.waypoints[0]
    for i in range(2):
        pos = track.initial_position(i)
        behind = (pos[0] - origin[0]) * tx + (pos[1] - origin[1]) * ty
        assert behind == pytest.approx(-8 - i * 8, abs=0.01)
        assert track.distance_to_centerline(*pos) < track.width_m / 2 - CHASSIS_WIDTH_M / 2
    # The 80 m of track behind the timing line is locally straight.
    prev = track.waypoints[-20]
    tangent_delta = math.atan2(origin[1] - prev[1], origin[0] - prev[0]) - math.atan2(ty, tx)
    assert abs(math.atan2(math.sin(tangent_delta), math.cos(tangent_delta))) < 0.1


def test_physics_chassis_matches_published_geometry_and_spawn():
    track = load_live_track('interlagos')
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, track_progress_laps=True), track, list(DEFAULT_DRIVERS))
    engine.setup()
    try:
        for i, driver in enumerate(engine.drivers):
            handle = engine.handles[driver.driver_id]
            xyz, _ = p.getBasePositionAndOrientation(handle.chassis_id, physicsClientId=engine.physics._client_id)
            assert xyz[:2] == pytest.approx(track.initial_position(i))
            shape = p.getCollisionShapeData(handle.chassis_id, -1, physicsClientId=engine.physics._client_id)[0]
            assert shape[3] == pytest.approx((CHASSIS_LENGTH_M, CHASSIS_WIDTH_M, CHASSIS_HEIGHT_M))
    finally:
        engine.teardown()


@pytest.mark.parametrize('name', ['interlagos', 'monza'])
def test_first_ten_seconds_start_cleanly_on_the_straight(name):
    from engine import RuleBasedRaceController

    track = load_live_track(name)
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, track_progress_laps=True), track, list(DEFAULT_DRIVERS))
    controller = RuleBasedRaceController(track, seed=42)
    for driver in engine.drivers:
        engine.set_controller(driver.driver_id, controller)
    engine.setup()
    try:
        for _ in range(100):
            engine._step_tick(0.1, 24)
            for driver in engine.drivers:
                state = engine.states[driver.driver_id]
                assert track.distance_to_centerline(state.position_x, state.position_y) < track.width_m / 2 - CHASSIS_WIDTH_M / 2
        for driver in engine.drivers:
            assert engine.race_progress_m[driver.driver_id] > 150
            assert engine.states[driver.driver_id].lap == 0
    finally:
        engine.teardown()


def test_safety_limit_counts_seconds_at_logic_tick_rate(monkeypatch):
    """A 10 Hz, a race must not stop after 600 ticks (only 60 seconds)."""
    track = load_live_track('interlagos')
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False, num_laps=1), track, list(DEFAULT_DRIVERS))
    engine.states = {'test': object()}  # Skip physics setup; the loop is under test.
    monkeypatch.setattr(engine, '_publish_race_start', lambda: None)
    monkeypatch.setattr(engine, '_publish_weather_changed', lambda **_kwargs: None)
    monkeypatch.setattr(engine, '_publish_race_end', lambda: None)
    ticks = []
    def step(_dt, _sub_steps):
        ticks.append(1)
        if len(ticks) == 601:
            engine.race_finished = True
    monkeypatch.setattr(engine, '_step_tick', step)
    engine.run()
    assert len(ticks) == 601
