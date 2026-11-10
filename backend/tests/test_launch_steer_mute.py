"""REALISMO-1 C1-B — contratos da flag --launch-steer-mute.

Sem corrida formal: testa a máquina D_L, a composição dos dois canais, os
motivos de término, o uso único, o SHA conhecido e a superfície CLI/CSV.
"""
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.model_train.f1_env import load_track_frozen
from backend.scripts.run_race_10_cars import (
    DEFAULT_MAPPINGS_PATH,
    MODEL_DIR,
    NeuralRaceController,
)

BACKEND = Path(__file__).resolve().parents[1]


def _controller(enabled=True, track_name="interlagos"):
    track = load_track_frozen(track_name, strict=True)
    return NeuralRaceController(
        weights_path=MODEL_DIR / "v10_dagger" / "dagger_actor_best_weights.npz",
        mappings_path=DEFAULT_MAPPINGS_PATH,
        track=track,
        obs_mode="edge",
        launch_steer_mute=enabled,
    )


def test_mute_changes_only_steer_axis_and_off_is_exact_noop():
    ctrl = _controller(True)
    action = np.array([0.7, -0.25], dtype=np.float64)
    solo = np.array([0.1, 0.8], dtype=np.float64)
    muted = ctrl._apply_launch_steer_mute(action, solo, True)
    assert muted[0] == pytest.approx(np.tanh(0.1))
    assert muted[1] == action[1]
    assert np.array_equal(ctrl._apply_launch_steer_mute(action, solo, False), action)


def test_d_l_crossed_reason_and_single_use():
    ctrl = _controller(True)
    assert ctrl._launch_steer_mute_step("VER", 2600.0, 0.0, 0.0) is True
    assert ctrl._launch_steer_mute_active["VER"] == 1
    assert ctrl._launch_steer_mute_step("VER", 2720.0, 0.0, 0.1) is False
    assert ctrl._launch_steer_mute_end_reason["VER"] == "crossed"
    # Não reativa se o carro voltar para a coordenada anterior.
    assert ctrl._launch_steer_mute_step("VER", 2600.0, 0.0, 0.2) is False
    assert ctrl._launch_steer_mute_end_reason["VER"] == "crossed"


def test_d_l_offtrack_and_deadline_reasons():
    off = _controller(True)
    assert off._launch_steer_mute_step("VER", 2600.0, 7.0, 0.0) is False
    assert off._launch_steer_mute_end_reason["VER"] == "offtrack"

    deadline = _controller(True)
    assert deadline._launch_steer_mute_step("VER", 2600.0, 0.0, 10.1) is False
    assert deadline._launch_steer_mute_end_reason["VER"] == "deadline"


def test_known_sha_is_required():
    track = load_track_frozen("interlagos", strict=True)
    track.frozen_sha256 = "unknown-sha"
    with pytest.raises(ValueError, match="sha256"):
        NeuralRaceController(
            weights_path=MODEL_DIR / "v10_dagger" / "dagger_actor_best_weights.npz",
            mappings_path=DEFAULT_MAPPINGS_PATH,
            track=track,
            obs_mode="edge",
            launch_steer_mute=True,
        )


def test_default_off_has_no_d_l_state():
    ctrl = _controller(False)
    assert ctrl.LAUNCH_STEER_MUTE_ENABLED is False
    assert ctrl._launch_steer_mute_step("VER", 2600.0, 0.0, 0.0) is False
    assert ctrl._launch_steer_mute_state == {}


def test_csv_launch_columns_are_conditional(tmp_path):
    from backend.model_train.race_diagnostic import _write_race_diag_csv

    off_path = tmp_path / "off.csv"
    _write_race_diag_csv(pd.DataFrame([{"tick": 0, "drv": "VER"}]),
                         str(off_path), " | track_frozen_sha256=x", include_xy=False)
    off_header = off_path.read_text(encoding="utf-8").splitlines()[1]
    assert "launch_steer_mute" not in off_header

    on_path = tmp_path / "on.csv"
    _write_race_diag_csv(pd.DataFrame([{
        "tick": 0, "drv": "VER", "launch_steer_mute": 1,
        "launch_steer_mute_end_reason": "",
    }]), str(on_path), " | track_frozen_sha256=x", include_xy=False)
    on_header = on_path.read_text(encoding="utf-8").splitlines()[1]
    assert "launch_steer_mute" in on_header
    assert "launch_steer_mute_end_reason" in on_header


@pytest.mark.parametrize("conflict", ["--pguard", "--launch-cap", "--launch-stagger"])
def test_launch_steer_mute_is_exclusive(conflict):
    proc = subprocess.run(
        [sys.executable, "model_train/race_diagnostic.py",
         "--profile", "composite", "--launch-steer-mute", conflict,
         "--ticks", "1", "--track", "interlagos"],
        cwd=str(BACKEND), capture_output=True, text=True, timeout=60)
    text = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "mutuamente exclusivo" in text


def test_composite_branch_assigns_action_before_mute():
    src = inspect.getsource(NeuralRaceController.predict_batch)
    i_assign = src.index("a = np.tanh(m_solo + gates[:, None] * r)")
    i_mute = src.index("if self.LAUNCH_STEER_MUTE_ENABLED")
    assert i_assign < i_mute


def test_race_runner_exposes_flag_in_help():
    source = (BACKEND / "scripts" / "run_race_10_cars.py").read_text(
        encoding="utf-8")
    assert 'parser.add_argument("--launch-steer-mute"' in source
