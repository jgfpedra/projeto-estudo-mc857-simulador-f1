"""Seeded exit mistakes change only acceleration, once per eligible corner."""
import pytest

from config.live_tracks import load_live_track
from engine import RuleBasedRaceController


class FixedRandom:
    def __init__(self, value=0.0):
        self.value = value
        self.draws = 0

    def random(self):
        self.draws += 1
        return self.value

    def uniform(self, a, b):
        return (a + b) / 2


def test_exit_mistake_waits_for_acceleration_and_occurs_once():
    controller = RuleBasedRaceController(load_live_track('interlagos', 2023), seed=42)
    style = controller._style_for('leader')
    style.corner_rng = FixedRandom()
    ordinary_rng_before = style.rng.getstate()
    factor = controller._corner_exit_factor
    assert factor(style, 0.02, 25, 0.8, 0, 0.1, False) == 1.0  # in bend
    assert factor(style, 0.002, 25, 0, 0.4, 0.1, False) == 1.0  # braking on exit
    assert style.corner_rng.draws == 0
    assert factor(style, 0.002, 25, 0.8, 0, 0.1, False) == pytest.approx(0.55)
    assert style.corner_error_count == 1 and style.corner_rng.draws == 1
    assert factor(style, 0.002, 25, 0.8, 0, 0.1, False) == pytest.approx(0.55)
    for _ in range(40):
        factor(style, 0.002, 25, 0.8, 0, 0.1, False)
    assert style.corner_error_count == 1 and style.corner_rng.draws == 1
    assert style.rng.getstate() == ordinary_rng_before


def test_errors_are_probabilistic_and_cancelled_on_rejoin_and_pit_exit():
    controller = RuleBasedRaceController(load_live_track('interlagos', 2023), seed=42)
    style = controller._style_for('follower')
    style.corner_rng = FixedRandom(value=0.99)
    factor = controller._corner_exit_factor
    factor(style, 0.02, 25, 0.8, 0, 0.1, False)
    assert factor(style, 0.002, 25, 0.8, 0, 0.1, False) == 1.0
    assert style.corner_error_count == 0
    style.corner_error_left_s = 1.0
    style.corner_exit_window_s = 1.0
    assert factor(style, 0.002, 25, 0.8, 0, 0.1, True) == 1.0
    assert style.corner_error_left_s == style.corner_exit_window_s == 0.0
    style.corner_armed, style.corner_error_left_s = True, 1.0
    controller.on_pit_exit('follower')
    assert not style.corner_armed and style.corner_error_left_s == 0.0


def test_corner_rng_repeats_per_driver_and_seed():
    track = load_live_track('interlagos', 2023)
    a, b, different = (RuleBasedRaceController(track, seed=seed) for seed in (42, 42, 43))
    a_rng = a._style_for('max-verstappen').corner_rng
    b_rng = b._style_for('max-verstappen').corner_rng
    other_rng = different._style_for('max-verstappen').corner_rng
    a_values = [a_rng.random() for _ in range(4)]
    b_values = [b_rng.random() for _ in range(4)]
    other_values = [other_rng.random() for _ in range(4)]
    assert a_values == b_values
    assert a_values != other_values


def test_mistake_reduces_acceleration_without_changing_steering_or_brakes():
    from config import DEFAULT_DRIVERS
    from domain import BASE_CONDITIONS, WeatherKind
    from engine.controllers import EnvironmentState

    track = load_live_track('interlagos', 2023)
    state = DEFAULT_DRIVERS[0].initial_state()
    def command(chance_draw):
        controller = RuleBasedRaceController(track, seed=42)
        state.position_x, state.position_y = controller._point_at(500, centerline=True)
        state.heading_rad = float(controller._heading[controller._segment_at(500)])
        state.velocity_mps = 30.0
        style = controller._style_for(state.driver_id)
        style.corner_armed = True
        style.corner_rng = FixedRandom(chance_draw)
        controller._curvature_at = lambda _: 0.0
        env = EnvironmentState(10.0, 0, BASE_CONDITIONS[WeatherKind.DRY], track, {state.driver_id: state})
        return controller.compute_input(env, state)
    normal = command(0.99)
    mistake = command(0.0)
    assert normal.throttle > 0.03
    assert mistake.throttle == pytest.approx(normal.throttle * 0.55)
    assert mistake.steering_yaw_rad == pytest.approx(normal.steering_yaw_rad)
    assert mistake.brake == normal.brake


def test_real_simulation_can_make_a_seeded_corner_exit_mistake():
    from dataclasses import replace
    from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
    from domain import BASE_CONDITIONS, WeatherKind, WeatherModel, WeatherTransitionConfig
    from engine import SimulationEngine

    track = load_live_track('interlagos', 2023)
    driver = replace(DEFAULT_DRIVERS[0], driver_id='d00')
    config = replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False, track_progress_laps=True)
    weather = WeatherModel(BASE_CONDITIONS[WeatherKind.DRY], WeatherTransitionConfig.default(0))
    engine = SimulationEngine(config, track, [driver], weather_model=weather)
    engine.setup()
    controller = RuleBasedRaceController(track, seed=42)
    engine.set_controller(driver.driver_id, controller)
    try:
        for _ in range(600):
            engine._step_tick(0.1, 24)
            style = controller._style_for(driver.driver_id)
            if style.corner_error_count:
                break
        assert style.corner_error_count == 1
        assert style.corner_error_left_s > 0 and not style.rejoining
        assert abs(engine.race_lateral_m[driver.driver_id]) < track.width_m / 2
    finally:
        engine.teardown()
