"""REALISMO-1 C2-B — conformidade da flag --rejoin-handoff align.

Testes de camada בלבד: nenhum teste executa uma corrida de produto.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.model_train.f1_env import load_track_frozen  # noqa: E402
from backend.scripts.run_race_10_cars import (  # noqa: E402
    DEFAULT_MAPPINGS_PATH,
    MODEL_DIR,
    NeuralRaceController,
)

BACKEND = Path(__file__).resolve().parents[1]


def _build(mode="align", track_name="interlagos"):
    track = load_track_frozen(track_name, strict=True)
    ctrl = NeuralRaceController(
        weights_path=MODEL_DIR / "v10_dagger" / "dagger_actor_best_weights.npz",
        mappings_path=DEFAULT_MAPPINGS_PATH,
        track=track,
        obs_mode="edge",
        rejoin_handoff=mode,
    )
    s = 1000.0
    px, py = ctrl._A[0]
    heading = ctrl._heading_at(s)
    return ctrl, track, s, px, py, heading


def _step(ctrl, s, px, py, heading, *, driver="VER", was_off=True,
          off=False, speed=20.0, lat=5.0, t=0.0):
    return ctrl._rejoin_handoff_step(
        driver,
        was_offtrack=was_off,
        offtrack=off,
        s_live=s,
        signed_lat=lat,
        speed=speed,
        heading_rad=heading,
        live_x=px,
        live_y=py,
        projection_x=px,
        projection_y=py,
        sim_ts=t,
    )


def test_flag_off_is_noop_and_default_off():
    ctrl, _track, s, px, py, heading = _build(mode="off")
    assert ctrl.REJOIN_HANDOFF_ENABLED is False
    active, steer, reason = _step(ctrl, s, px, py, heading + 1.0)
    assert (active, steer, reason) == (False, None, None)
    assert ctrl._rejoin_handoff_state == {}


def test_activation_requires_offtrack_transition():
    ctrl, _track, s, px, py, heading = _build()
    assert _step(ctrl, s, px, py, heading + 1.0,
                 was_off=False)[0] is False
    assert _step(ctrl, s, px, py, heading + 1.0,
                 was_off=True, off=True)[0] is False
    assert _step(ctrl, s, px, py, heading + 1.0,
                 was_off=True, off=False)[0] is True


def test_steer_is_limited_by_speed_dependent_steer_limit():
    ctrl, _track, s, px, py, heading = _build()
    active, steer, _ = _step(ctrl, s, px, py, heading + 2.0, speed=60.0)
    assert active is True
    assert abs(steer) <= ctrl.steer_limit_rad(60.0) + 1e-12


def test_longitudinal_is_not_touched_by_handoff_helper():
    src = inspect.getsource(NeuralRaceController._rejoin_handoff_step)
    assert "th =" not in src and "brk =" not in src
    assert "policy + governor" in src


def test_aligned_timeout_and_offtrack_termination_reasons():
    ctrl, _track, s, px, py, heading = _build()
    assert _step(ctrl, s, px, py, heading + 1.0)[0] is True
    active, steer, reason = _step(ctrl, s, px, py, heading,
                                  was_off=False, lat=5.0, t=0.1)
    assert (active, steer, reason) == (False, None, "aligned")

    ctrl, _track, s, px, py, heading = _build()
    assert _step(ctrl, s, px, py, heading + 1.0)[0] is True
    assert _step(ctrl, s, px, py, heading + 1.0,
                 was_off=False, lat=5.0, t=24.1)[2] == "timeout"

    ctrl, _track, s, px, py, heading = _build()
    assert _step(ctrl, s, px, py, heading + 1.0)[0] is True
    assert _step(ctrl, s, px, py, heading + 1.0,
                 was_off=False, off=True, lat=7.0, t=0.1)[2] == "offtrack"


def test_state_isolated_by_driver_and_episode():
    ctrl, _track, s, px, py, heading = _build()
    assert _step(ctrl, s, px, py, heading + 1.0, driver="VER")[0] is True
    assert _step(ctrl, s, px, py, heading + 1.0,
                 driver="HAM", was_off=False)[0] is False
    assert _step(ctrl, s, px, py, heading,
                 driver="VER", was_off=False, lat=5.0, t=0.1)[2] == "aligned"
    # Nova off->on inicia um novo episódio para VER.
    assert _step(ctrl, s, px, py, heading + 1.0,
                 driver="VER", was_off=True, lat=5.0, t=1.0)[0] is True
    assert ctrl._rejoin_handoff_state["VER"]["t0"] == pytest.approx(1.0)
    assert "HAM" not in ctrl._rejoin_handoff_state


def test_handoff_precedes_gap_and_authority_has_no_persistence():
    src = inspect.getsource(NeuralRaceController.predict_batch)
    assert "and not handoff_active" in src
    assert src.index("elif handoff_active:") < src.index("elif gap_hold:")
    ctrl, _track, s, px, py, heading = _build()
    assert _step(ctrl, s, px, py, heading + 1.0)[0] is True
    assert _step(ctrl, s, px, py, heading,
                 was_off=False, lat=5.0, t=0.1)[2] == "aligned"
    assert ctrl._rejoin_handoff_active["VER"] == 0
    assert ctrl._rejoin_handoff_end_reason["VER"] == "aligned"


def test_unknown_track_sha_fails_loud():
    track = load_track_frozen("interlagos", strict=True)
    track.frozen_sha256 = "unknown-sha"
    with pytest.raises(ValueError, match="rejoin_handoff inválido|sha"):
        NeuralRaceController(
            weights_path=MODEL_DIR / "v10_dagger" / "dagger_actor_best_weights.npz",
            mappings_path=DEFAULT_MAPPINGS_PATH,
            track=track,
            obs_mode="edge",
            rejoin_handoff="align",
        )


def test_constants_are_frozen():
    assert NeuralRaceController.REJOIN_HANDOFF_THETA_RAD == pytest.approx(
        0.3490658503988659)
    assert NeuralRaceController.REJOIN_HANDOFF_MARGIN_M == pytest.approx(0.5)
    assert NeuralRaceController.REJOIN_HANDOFF_TMAX_S == pytest.approx(24.0)
