"""C4 Task 11 — testes sintéticos antes de abrir qualquer pickle real."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scripts.c4_geometry_analysis import (  # noqa: E402
    C08_FOCAL,
    CORRIDOR_M,
    DS_BIN_M,
    MIN_CONTIGUOUS_M,
    focal_runs,
    project_points,
    rigid_fit,
    summarize_bins,
    synthetic_demo,
)


def circle(n=256, radius=20.0):
    a = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    return np.column_stack([radius * np.cos(a), radius * np.sin(a)])


def test_rigid_procrustes_recovers_known_rotation_translation():
    base = circle()
    theta = 0.37
    rotation = np.array([[math.cos(theta), -math.sin(theta)],
                         [math.sin(theta), math.cos(theta)]])
    source = base @ rotation.T + np.array([31.0, -17.0])
    fit = rigid_fit(source, base)
    assert fit["det"] == pytest.approx(1.0, abs=1e-12)
    assert fit["rms_m"] < 1e-10
    recovered = source @ np.asarray(fit["rotation"]).T + fit["translation"]
    assert np.max(np.abs(recovered - base)) < 1e-9


def test_projection_returns_known_s_and_signed_lateral_offset():
    wps = circle(n=1024)
    points = np.array([[20.5, 0.0], [0.0, -20.5]])
    s, lateral, segments = project_points(points, wps)
    assert len(s) == 2
    assert np.allclose(np.abs(lateral), [0.5, 0.5], atol=0.08)
    assert segments.dtype.kind in "iu"
    assert np.all((s >= 0.0) & (s < 2.0 * math.pi * 20.0))


def test_bins_are_equal_lap_weighted_and_preserve_iqr():
    laps = [
        {0: -7.0, 1: -7.0, 2: 0.0, 3: 0.0, 4: 7.0},
        {0: -5.0, 1: -5.0, 2: 0.0, 3: 0.0, 4: 5.0},
    ]
    summary = summarize_bins(laps)
    assert summary[0]["s_start_m"] == 0.0
    assert summary[0]["s_end_m"] == DS_BIN_M
    assert summary[0]["median_m"] == pytest.approx(-6.0)
    assert summary[0]["iqr_m"] == pytest.approx(1.0)
    assert summary[0]["n_laps"] == 2


def test_decision_requires_strict_threshold_and_five_contiguous_bins():
    rows = []
    first_bin = math.ceil(C08_FOCAL[0] / DS_BIN_M)
    for b in range(first_bin, first_bin + 5):
        rows.append({"bin": b, "s_start_m": b * DS_BIN_M,
                     "s_end_m": (b + 1) * DS_BIN_M,
                     "median_m": 6.0001, "iqr_m": 0.0, "n_laps": 15})
    runs = focal_runs(rows)
    assert len(runs) == 1
    assert runs[0]["length_m"] == pytest.approx(MIN_CONTIGUOUS_M)

    rows[2]["median_m"] = CORRIDOR_M
    assert focal_runs(rows) == []


def test_decision_ignores_qualifying_run_outside_c08():
    rows = [{"bin": b, "s_start_m": b * DS_BIN_M,
             "s_end_m": (b + 1) * DS_BIN_M,
             "median_m": 7.0, "iqr_m": 0.0, "n_laps": 15}
            for b in range(100, 105)]
    assert focal_runs(rows) == []


def test_synthetic_demo_is_self_contained():
    result = synthetic_demo()
    assert result["status"] == "PASS"
    assert result["rigid_rms_m"] < 1e-8
    assert result["bin_size_m"] == 2.0


def test_extended_timing_schema_and_lap_filters():
    from backend.scripts.c4_geometry_analysis import (
        _valid_laps_for_year, inspect_session_schema,
    )
    times = pd.to_timedelta(np.arange(0.0, 40.0, 0.5), unit="s")
    position = {"63": pd.DataFrame({
        "Time": times, "X": np.arange(len(times)) * 10.0,
        "Y": np.zeros(len(times)),
    })}
    status = {"Time": pd.to_timedelta([0.0], unit="s"), "Status": [1]}
    weather = {"Time": pd.to_timedelta([0.0, 40.0], unit="s"),
               "Rainfall": [False, False]}
    lap_count = {"Time": pd.to_timedelta([0.0], unit="s"),
                 "CurrentLap": [1]}
    timing = pd.DataFrame([
        {"Time": pd.Timedelta(seconds=2), "Driver": "63",
         "LapTime": pd.NaT, "NumberOfLaps": 1,
         "PitInTime": pd.NaT, "PitOutTime": pd.NaT},
        {"Time": pd.Timedelta(seconds=17), "Driver": "63",
         "LapTime": pd.Timedelta(seconds=10), "NumberOfLaps": 2,
         "PitInTime": pd.NaT, "PitOutTime": pd.NaT},
        {"Time": pd.Timedelta(seconds=27), "Driver": "63",
         "LapTime": pd.Timedelta(seconds=10), "NumberOfLaps": 3,
         "PitInTime": pd.Timedelta(seconds=18), "PitOutTime": pd.NaT},
    ])
    schema = inspect_session_schema(position, status, weather, lap_count,
                                    timing, year=2099)
    assert schema["timing_rows"] == 3
    laps, rejected = _valid_laps_for_year(2099, position, pd.DataFrame(status),
                                           pd.DataFrame(weather), timing)
    assert len(laps) == 1
    assert laps[0]["lap"] == 2
    assert rejected["lap1"] == 1
    assert rejected["pit"] == 1
