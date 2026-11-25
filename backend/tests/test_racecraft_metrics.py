"""Checks that the offline racecraft metric ignores short or invalid swaps."""
from scripts.benchmarks.measure_bot_pace import RacecraftMetrics


def test_estimated_pass_requires_sustained_order_change():
    metrics = RacecraftMetrics()
    def sample(a, b):
        metrics.observe([('A', a, True), ('B', b, True)], 'A' if a > b else 'B')
    sample(10, 0)
    sample(0, 10)
    sample(10, 0)  # momentary crossing did not last
    assert metrics.passes == 0
    sample(0, 10)
    sample(0, 10)
    assert metrics.passes == 1
    sample(0, 10)
    assert metrics.passes == 1


def test_passes_through_pit_or_off_track_are_excluded():
    metrics = RacecraftMetrics()
    metrics.observe([('A', 10, True), ('B', 0, True)], 'A')
    metrics.observe([('A', 0, False), ('B', 10, True)], 'B')
    metrics.observe([('A', 0, True), ('B', 10, True)], 'B')
    metrics.observe([('A', 0, True), ('B', 10, True)], 'B')
    assert metrics.passes == 0


def test_attack_bonus_is_only_applied_when_chasing_on_a_clear_straight():
    import pytest
    from config import DEFAULT_DRIVERS
    from config.live_tracks import load_live_track
    from domain import BASE_CONDITIONS, WeatherKind
    from engine import RuleBasedRaceController
    from engine.controllers import EnvironmentState

    track = load_live_track('interlagos', 2023)
    def target_speed(with_opponent, planned_fraction=0.95):
        controller = RuleBasedRaceController(track, seed=42)
        follower = DEFAULT_DRIVERS[0].initial_state()
        opponent = DEFAULT_DRIVERS[1].initial_state()
        for state, s in ((follower, 500.0), (opponent, 520.0)):
            state.position_x, state.position_y = controller._point_at(s, centerline=True)
            state.heading_rad = float(controller._heading[controller._segment_at(s)])
            state.velocity_mps = 60.0
        states = {follower.driver_id: follower}
        if with_opponent:
            states[opponent.driver_id] = opponent
        captured = []
        controller._planned_speed = lambda s, top, *args: top * planned_fraction
        controller._longitudinal_commands = lambda state, speed, target, *args, **kwargs: (captured.append(target) or (0.0, 0.0))
        controller.compute_input(EnvironmentState(10.0, 0, BASE_CONDITIONS[WeatherKind.DRY], track, states), follower)
        return captured[0]
    assert target_speed(True) / target_speed(False) == pytest.approx(1.006 * 1.045)
    # Braking/curvature speed below the threshold keeps the original envelope.
    assert target_speed(True, 0.7) / target_speed(False, 0.7) == pytest.approx(1.006)


def test_attack_bonus_requires_validated_geometry_and_width():
    from dataclasses import replace
    from config.live_tracks import load_live_track
    from engine import RuleBasedRaceController

    interlagos = load_live_track('interlagos', 2023)
    assert RuleBasedRaceController(interlagos, seed=42)._attack_bonus_enabled
    assert not RuleBasedRaceController(replace(interlagos, width_m=14.0), seed=42)._attack_bonus_enabled
    assert not RuleBasedRaceController(load_live_track('monza', 2024), seed=42)._attack_bonus_enabled
