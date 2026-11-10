"""REALISMO-1 C6-B — conformidade da alteração exclusiva em obs4."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scripts.run_race_10_cars import NeuralRaceController  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent


def _controller(enabled=True, profile="composite"):
    ctrl = object.__new__(NeuralRaceController)
    ctrl.LAT_OFFSET_SLOTS_ENABLED = enabled
    ctrl.LAT_OFFSET_PROFILE = profile
    ctrl._half_width = 6.0
    ctrl._launch_grid_slots = {"A": 1, "B": 2}
    offsets = (ctrl.LAT_OFFSET_SLOTS_COMPOSITE if profile == "composite"
               else ctrl.LAT_OFFSET_SLOTS_BLIND)
    ctrl._lat_offset_slots = offsets if enabled else None
    return ctrl


def test_formula_changes_only_obs4_and_preserves_physical_inputs():
    ctrl = _controller(True, "composite")
    tels = np.zeros((2, 23), dtype=np.float32)
    tels[:, 0] = (0.25, 0.5)
    signed = np.array([3.0, -2.0], dtype=np.float64)
    signed_before = signed.copy()
    out = ctrl._apply_lat_offset_slots(tels, [SimpleNamespace(driver_id="A"),
                                               SimpleNamespace(driver_id="B")], signed)
    assert np.array_equal(signed, signed_before)
    assert np.allclose(out[0, 4], (3.0 - 0.273) / 6.0)
    assert np.allclose(out[1, 4], (-2.0 + 1.0) / 6.0)
    assert np.array_equal(out[:, :4], tels[:, :4])
    assert np.array_equal(out[:, 5:], tels[:, 5:])


def test_default_off_is_exact_noop():
    ctrl = _controller(False, "blind")
    tels = np.arange(46, dtype=np.float32).reshape(2, 23)
    signed = np.array([1.0, -1.0])
    out = ctrl._apply_lat_offset_slots(tels, [SimpleNamespace(driver_id="A"),
                                               SimpleNamespace(driver_id="B")], signed)
    assert out is tels
    assert np.array_equal(out, tels)


def test_frozen_vectors_are_bounded_and_have_ten_slots():
    for vector in (NeuralRaceController.LAT_OFFSET_SLOTS_COMPOSITE,
                   NeuralRaceController.LAT_OFFSET_SLOTS_BLIND):
        assert len(vector) == 10
        assert all(np.isfinite(vector))
        assert max(abs(float(x)) for x in vector) <= 1.0


def test_invalid_or_missing_slots_fail_loud():
    ctrl = _controller(True, "composite")
    ctrl._launch_grid_slots = None
    with pytest.raises(ValueError, match="tabela de slots ausente"):
        ctrl._apply_lat_offset_slots(np.zeros((2, 23), np.float32),
                                     [SimpleNamespace(driver_id="A"),
                                      SimpleNamespace(driver_id="B")],
                                     np.zeros(2))
    ctrl._launch_grid_slots = {"A": 0, "B": 2}
    with pytest.raises(ValueError, match="slot fora"):
        ctrl._apply_lat_offset_slots(np.zeros((2, 23), np.float32),
                                     [SimpleNamespace(driver_id="A"),
                                      SimpleNamespace(driver_id="B")],
                                     np.zeros(2))


def test_flag_is_wired_in_both_runners_and_parser_rejects_professor():
    diagnostic = (BACKEND / "model_train" / "race_diagnostic.py").read_text()
    visual = (BACKEND / "scripts" / "run_race_10_cars.py").read_text()
    assert "--lat-offset-slots" in diagnostic
    assert "--lat-offset-slots" in visual
    proc = subprocess.run(
        [sys.executable, "model_train/race_diagnostic.py",
         "--controller", "professor", "--lat-offset-slots", "--ticks", "1"],
        cwd=BACKEND, capture_output=True, text=True, timeout=60)
    assert proc.returncode != 0
    assert "--lat-offset-slots requer controller neural" in (proc.stdout + proc.stderr)
