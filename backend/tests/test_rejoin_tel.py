"""Synthetic and fixture checks for the opt-in REJOIN-TEL-1 writer."""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "model_train"))
import race_diagnostic as diag  # noqa: E402


FIXTURE = BACKEND / "experiments/proj-fix-1/1_replay_composite_monaco_s0_v34.csv"


def test_writer_v35_flag_is_opt_in_default_off():
    parser = argparse.ArgumentParser()
    diag._add_writer_v35_argument(parser)
    assert parser.parse_args([]).writer_v35 is False
    assert parser.parse_args(["--writer-v35"]).writer_v35 is True


def test_rejoin_window_ids_age_anchor_and_transitions():
    tel = diag.RejoinWindowTelemetry()
    on0 = tel.observe("CAR", 0, False, 1.0, 2.0, 3.0)
    assert on0 == dict(off_window_id=0, off_age_ticks=0,
                       anchor_x=1.0, anchor_y=2.0, anchor_s=3.0)
    assert tel.sample_reentry("CAR", on0) is False

    off1 = tel.observe("CAR", 1, True, 4.0, 5.0, 6.0)
    off2 = tel.observe("CAR", 2, True, 7.0, 8.0, 9.0)
    assert (off1["off_window_id"], off1["off_age_ticks"]) == (1, 0)
    assert (off2["off_window_id"], off2["off_age_ticks"]) == (1, 1)
    assert (off2["anchor_x"], off2["anchor_y"], off2["anchor_s"]) == (1.0, 2.0, 3.0)
    assert tel.sample_reentry("CAR", off2) is False

    on3 = tel.observe("CAR", 3, False, 10.0, 11.0, 12.0)
    assert on3["off_window_id"] == on3["off_age_ticks"] == 0
    assert (on3["anchor_x"], on3["anchor_y"], on3["anchor_s"]) == (10.0, 11.0, 12.0)
    assert tel.sample_reentry("CAR", on3) is True
    assert tel.sample_reentry("CAR", on3) is False

    off4 = tel.observe("CAR", 4, True, 13.0, 14.0, 15.0)
    assert (off4["off_window_id"], off4["off_age_ticks"]) == (2, 0)


def test_heading_error_uses_course_minus_frozen_tangent():
    tangent = lambda _s: math.pi / 2.0
    err = diag._rejoin_tel_heading_error((0.0, 0.0), (1.0, 0.0), 42.0, tangent)
    assert err == -90.0
    assert diag._rejoin_tel_heading_error((1.0, 1.0), (1.0, 1.0), 42.0,
                                          tangent) == 0.0


def test_target_capture_is_exact_pass_through():
    class FakeController:
        def _rejoin_target_point(self, driver_id, s_live, projection_x,
                                 projection_y, ahead_m):
            return projection_x + ahead_m, projection_y - ahead_m

        @staticmethod
        def _kappa_signed(s):
            return s / 1000.0

    ctrl = FakeController()
    captured = diag._install_rejoin_tel_target_capture(ctrl)
    result = ctrl._rejoin_target_point("CAR", 12.0, 3.0, 8.0, 5.0)
    assert result == (8.0, 3.0)
    assert captured == {"CAR": dict(target_x=8.0, target_y=3.0,
                                    target_kappa=0.017)}


def test_writer_appends_nine_fields_and_preserves_fixture_prefix(tmp_path):
    with FIXTURE.open(newline="") as source:
        source_reader = csv.reader(source)
        next(source_reader)  # v3.4 metadata
        fixture_header = next(source_reader)
        fixture_row = next(source_reader)
    assert len(fixture_header) == 71

    sample = pd.read_csv(FIXTURE, comment="#", nrows=1)
    output_v34 = tmp_path / "sample_v34.csv"
    diag._write_race_diag_csv(sample.copy(), output_v34, " | synthetic=1",
                              include_xy=True, writer_v35=False)
    for name, value in zip(diag._REJOIN_TEL_COLUMNS,
                           (1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)):
        sample[name] = value
    output = tmp_path / "sample_v35.csv"
    diag._write_race_diag_csv(sample, output, " | synthetic=1",
                              include_xy=True, writer_v35=True)
    with output.open(newline="") as written:
        result = list(csv.reader(written))
    assert len(result[1]) == 80
    assert result[1][:71] == fixture_header
    assert tuple(result[1][71:]) == diag._REJOIN_TEL_COLUMNS
    with output_v34.open(newline="") as written:
        baseline_rows = list(csv.reader(written))
    assert result[1][:71] == baseline_rows[1]
    assert result[2][:71] == baseline_rows[2]
    assert baseline_rows[1][:71] == fixture_header
    assert len(fixture_row) == 71

