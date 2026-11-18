"""LOC-XY-1: contrato aditivo do CSV e identidade do kill-switch."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
for path in (BACKEND, REPO):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from model_train.race_diagnostic import _XY_DIAG_COLUMNS, _write_race_diag_csv  # noqa: E402
from model_train.f1_env import load_track_frozen  # noqa: E402

FIXTURE = BACKEND / "experiments/fail-forensics-1/1_blind_interlagos_s0.csv"
SAMPLE_FIXTURE = BACKEND / "tests/fixtures/loc_xy_interlagos_s377.csv"
_BASELINE_BYTES = FIXTURE.read_bytes()
_BASELINE_HEADER = _BASELINE_BYTES.splitlines(keepends=True)[0].decode("utf-8")
_BASELINE_PREFIX = "# race_diag_v3_3_res16d"


def _baseline_frame() -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(_BASELINE_BYTES), comment="#", dtype=str,
                       keep_default_na=False)


def _header_metadata() -> str:
    assert _BASELINE_HEADER.startswith(_BASELINE_PREFIX)
    return _BASELINE_HEADER[len(_BASELINE_PREFIX):].rstrip("\r\n")


def test_v34_header_appends_xyraw_columns_in_declared_order(tmp_path):
    df = _baseline_frame().head(1).copy()
    df["body_x"] = "1.25"
    df["body_y"] = "-2.5"
    df["ns_raw"] = "377"
    out_path = tmp_path / "v34.csv"

    _write_race_diag_csv(df, out_path, _header_metadata(), include_xy=True)

    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# race_diag_v3_4_xyraw | ")
    old_columns = _BASELINE_BYTES.splitlines()[1].decode("utf-8").split(",")
    assert lines[1].split(",") == old_columns + list(_XY_DIAG_COLUMNS)


def test_ns_raw_fixture_roundtrips_against_independent_global_argmin():
    sample = pd.read_csv(SAMPLE_FIXTURE, comment="#").iloc[0]
    track = load_track_frozen("interlagos", strict=True)
    assert track.frozen_sha256 == "164876196eb12174"

    # Re-derivação auxiliar vetorizada, separada do loop de Track.nearest_segment.
    points = np.asarray(track.waypoints, dtype=np.float64)
    starts = points
    vectors = np.roll(points, -1, axis=0) - starts
    lengths2 = np.einsum("ij,ij->i", vectors, vectors)
    valid = lengths2 >= 1e-9
    q = np.array([sample.body_x, sample.body_y], dtype=np.float64)
    t = np.zeros(len(points), dtype=np.float64)
    t[valid] = np.clip(np.einsum("ij,ij->i", q - starts[valid], vectors[valid])
                       / lengths2[valid], 0.0, 1.0)
    projected = starts + t[:, None] * vectors
    dist2 = np.einsum("ij,ij->i", q - projected, q - projected)
    dist2[~valid] = np.inf
    auxiliary_ns_raw = int(np.argmin(dist2))

    method_ns_raw = int(track.nearest_segment(float(sample.body_x),
                                               float(sample.body_y))[1])
    assert method_ns_raw == auxiliary_ns_raw == int(sample.ns_raw)


def test_kill_switch_serialization_is_byte_identical_to_v33_fixture(
        tmp_path, monkeypatch):
    df = _baseline_frame()
    df["body_x"] = "0.0"
    df["body_y"] = "0.0"
    df["ns_raw"] = "0"
    out_path = tmp_path / "v33-kill-switch.csv"
    monkeypatch.setenv("RACE_DIAG_NO_XY", "1")

    _write_race_diag_csv(df, out_path, _header_metadata())

    assert out_path.read_bytes() == _BASELINE_BYTES
