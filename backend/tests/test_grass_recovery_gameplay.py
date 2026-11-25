"""Less punitive grass must still respect tyres, weather and recovery safety."""
from dataclasses import replace
import math

import pybullet as pb
import pytest

from api.providers.historical_f1results import HistoricalResultsProvider
from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from domain import BASE_CONDITIONS, Track, WeatherKind, WeatherModel, WeatherTransitionConfig
from engine import RuleBasedRaceController, SimulationEngine
from engine.controllers import CarInput, EnvironmentState


def test_grass_has_gradual_surface_penalty_without_changing_asphalt():
    track = Track.from_waypoints('square', [(0, 0), (200, 0), (200, 200), (0, 200)], width_m=12)
    assert track.surface_grip_factor_from_distance(0) == 1.0
    assert track.surface_grip_factor_from_distance(6) == 1.0
    assert track.surface_grip_factor_from_distance(7.5) == pytest.approx(0.8)
    assert track.surface_grip_factor_from_distance(9) == pytest.approx(0.6)
    assert track.surface_grip_factor_from_distance(30) == pytest.approx(0.6)


def test_grass_surface_still_multiplies_tyre_and_weather_grip():
    track = Track.from_waypoints('square', [(0, 0), (200, 0), (200, 200), (0, 200)], width_m=12)
    driver = DEFAULT_DRIVERS[0]
    engine = SimulationEngine(DEFAULT_INTERLAGOS_CONFIG, track, [driver])
    state = driver.initial_state()
    state.position_x, state.position_y = 100.0, -12.0
    for weather in (WeatherKind.DRY, WeatherKind.WET):
        base = state.tyre.grip_multiplier(weather, 35.0)
        expected = max(0.3, min(1.2, base)) * 0.6
        assert engine._compute_grip(driver.driver_id, CarInput(), state, weather, 35.0) == pytest.approx(expected)
        controller = RuleBasedRaceController(track, seed=42)
        env = EnvironmentState(10.0, 0, BASE_CONDITIONS[weather], track, {driver.driver_id: state})
        result = controller.compute_input(env, state)
        bot_grip = state.tyre.grip_multiplier(weather, env.weather.track_temp)
        assert result.grip_override == pytest.approx(max(0.3, min(1.2, bot_grip)) * 0.6)


def test_backwards_car_recovers_without_crossing_back_to_grass():
    track, _, _ = HistoricalResultsProvider().load('ain-diab', 1958)
    driver = replace(DEFAULT_DRIVERS[0], driver_id='recovery-test')
    config = replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False, track_progress_laps=True)
    weather = WeatherModel(BASE_CONDITIONS[WeatherKind.DRY], WeatherTransitionConfig.default(0.0))
    engine = SimulationEngine(config, track, [driver], weather_model=weather)
    engine.setup()
    controller = RuleBasedRaceController(track, seed=42)
    engine.set_controller(driver.driver_id, controller)
    s = 900.0
    x, y = controller._point_at(s, 12.0, centerline=True)
    idx = controller._segment_at(s)
    yaw = float(controller._heading[idx]) + math.pi
    cid = engine.physics._client_id
    body = engine.handles[driver.driver_id].chassis_id
    pb.resetBasePositionAndOrientation(body, (x, y, 0.5), pb.getQuaternionFromEuler((0, 0, yaw)), physicsClientId=cid)
    pb.resetBaseVelocity(body, (0, 0, 0), (0, 0, 0), physicsClientId=cid)
    engine.prev_waypoint_idx[driver.driver_id] = idx
    engine.last_pos[driver.driver_id] = (x, y)
    engine._update_race_progress(0.1)
    stable, recovered = 0, False
    try:
        for _ in range(155):
            engine._step_tick(0.1, 24)
            state = engine.states[driver.driver_id]
            projected_s, _ = controller._project_in_frame(driver.driver_id, state.position_x, state.position_y)
            heading = float(controller._heading[controller._segment_at(projected_s)])
            aligned = abs(controller._wrap(heading - state.heading_rad)) < math.radians(35)
            inside = abs(engine.race_lateral_m[driver.driver_id]) <= track.width_m / 2 - 1.5
            stable = stable + 1 if inside and aligned else 0
            if stable >= 10:
                recovered = True
                break
        assert recovered, 'O carro deve recuperar direção e posição em até 15,5 segundos'
        for _ in range(50):
            engine._step_tick(0.1, 24)
            assert abs(engine.race_lateral_m[driver.driver_id]) <= track.width_m / 2
    finally:
        engine.teardown()
