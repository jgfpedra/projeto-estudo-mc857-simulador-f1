"""The simulated road edge must match where the 3D kerb is drawn."""
import math

import pytest

from config import DEFAULT_DRIVERS
from config.live_tracks import load_live_track
from domain import BASE_CONDITIONS, WeatherKind
from engine import RuleBasedRaceController
from engine.controllers import EnvironmentState


def command_at(offset, heading_delta=0.0, s=800.0):
    track = load_live_track('interlagos', 2023)
    controller = RuleBasedRaceController(track, seed=42)
    state = DEFAULT_DRIVERS[0].initial_state()
    state.position_x, state.position_y = controller._point_at(s, offset, centerline=True)
    state.heading_rad = float(controller._heading[controller._segment_at(s)]) + heading_delta
    state.velocity_mps = 35.0
    env = EnvironmentState(50.0, 0, BASE_CONDITIONS[WeatherKind.DRY], track, {state.driver_id: state})
    command = controller.compute_input(env, state)
    return track, controller, state, command


@pytest.mark.parametrize('side', (-1, 1))
@pytest.mark.parametrize('s', (800.0, 1400.0))
def test_driving_on_inside_edge_does_not_trigger_grass_recovery(side, s):
    _, before, state_before, command_before = command_at(side * 5.3, s=s)
    track, on_kerb, state_on_kerb, command_on_kerb = command_at(side * 5.8, s=s)
    assert track.surface_grip_factor_from_distance(5.8) == 1.0
    assert before.last_authority[state_before.driver_id] == 'apex-rules'
    assert on_kerb.last_authority[state_on_kerb.driver_id] == 'apex-rules'
    assert command_on_kerb.brake == pytest.approx(command_before.brake)
    assert abs(command_on_kerb.steering_yaw_rad - command_before.steering_yaw_rad) < 0.1


@pytest.mark.parametrize('side', (-1, 1))
def test_outside_edge_and_wrong_way_still_trigger_recovery(side):
    _, outside, state_outside, _ = command_at(side * 6.1)
    assert outside.last_authority[state_outside.driver_id] == 'rejoin'
    _, backwards, state_backwards, _ = command_at(side * 5.0, math.pi)
    assert backwards.last_authority[state_backwards.driver_id] == 'rejoin'
