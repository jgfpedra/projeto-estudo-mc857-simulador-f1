from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.model_train.f1_env import load_track_frozen
from backend.scripts.run_race_10_cars import (
    DEFAULT_MAPPINGS_PATH,
    MODEL_DIR,
    NeuralRaceController,
)


def _controller(*, c8_rejoin: bool = False):
    track = load_track_frozen("interlagos", strict=True)
    return NeuralRaceController(
        weights_path=MODEL_DIR / "v10_dagger" / "dagger_actor_best_weights.npz",
        mappings_path=DEFAULT_MAPPINGS_PATH,
        track=track,
        obs_mode="edge",
        c8_rejoin=c8_rejoin,
    )


def test_c8_flag_off_is_inert_and_default_is_off():
    default = _controller()
    explicit = _controller(c8_rejoin=False)
    assert default.C8_REJOIN_ENABLED is False
    assert explicit.C8_REJOIN_ENABLED is False
    assert default.c8_gap_blocked(100.0, (130.0,), 1000.0, 20.0) is False


def test_c8_gap_check_activation_and_longitudinal_direction():
    ctrl = _controller(c8_rejoin=True)
    assert ctrl.C8_REJOIN_ENABLED is True
    assert ctrl.c8_gap_blocked(100.0, (115.0,), 1000.0, ctrl.C8_GAP_M)
    assert not ctrl.c8_gap_blocked(100.0, (130.0,), 1000.0, ctrl.C8_GAP_M)
    assert ctrl.c8_gap_blocked(990.0, (5.0,), 1000.0, ctrl.C8_GAP_M)


def test_c8_precedes_handoff_and_ramp_and_tracks_transition():
    source = inspect.getsource(NeuralRaceController.predict_batch)
    assert "if c8_gap_hold:" in source
    assert "handoff_active, handoff_steer = False, None" in source
    assert source.index("handoff_active, handoff_steer = False, None") < source.index(
        "if c8_gap_hold:\n                ramp_active")
    assert "self._was_offtrack.get(drv_id, False)" in source


def test_c8_constants_are_frozen():
    assert NeuralRaceController.C8_GRASS_V_CAP_MPS == pytest.approx(6.0)
    assert NeuralRaceController.C8_GAP_M == pytest.approx(20.0)
    assert NeuralRaceController.C8_GAP_WINDOW_TICKS == 100
