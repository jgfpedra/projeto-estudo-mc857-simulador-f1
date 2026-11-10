import inspect
import math

import numpy as np

from backend.scripts.run_race_10_cars import (
    NeuralRaceController,
    ProjectionAnchorGate,
)


def _controller(enabled):
    ctrl = object.__new__(NeuralRaceController)
    ctrl.PROJ_GATE_ENABLED = enabled
    ctrl._projection_anchor_gate = ProjectionAnchorGate() if enabled else None
    ctrl._heading_at = lambda s: float(s) % (2.0 * math.pi)
    return ctrl


def test_anchor_target_freezes_on_on_to_off_transition():
    gate = ProjectionAnchorGate()
    gate.remember_on_track("A", (4.0, 3.0), 12.0, 2, (5.0, 6.0))
    calls = []

    def build(anchor):
        calls.append(anchor["s"])
        return anchor["projection_xy"][0] + 10.0, anchor["projection_xy"][1]

    first = gate.target_for("A", build)
    second = gate.target_for("A", lambda anchor: (999.0, 999.0))
    assert first == second == (15.0, 6.0)
    assert calls == [12.0]
    assert gate._anchors["A"]["pose_xy"] == (4.0, 3.0)
    assert gate._anchors["A"]["ns"] == 2


def test_off_to_on_reacquisition_replaces_anchor_and_target():
    ctrl = _controller(True)
    gate = ctrl._projection_anchor_gate
    gate.remember_on_track("A", (4.0, 0.0), 4.0, 0, (4.0, 0.0))
    old_target = ctrl._rejoin_target_point("A", 18.0, 18.0, 2.0, 10.0)
    expected_old = (4.0 + 10.0 * math.cos(4.0),
                    10.0 * math.sin(4.0))
    assert old_target == expected_old
    # Later off-track live projections do not move the frozen target.
    assert ctrl._rejoin_target_point("A", 19.0, 19.0, 3.0, 10.0) == old_target

    # The on-track observation carries the fresh nearest-global projection.
    gate.remember_on_track("A", (0.0, 5.0), 35.0, 3, (0.0, 5.0))
    new_target = ctrl._rejoin_target_point("A", 35.0, 0.0, 5.0, 10.0)
    assert gate._anchors["A"]["ns"] == 3
    assert gate._anchors["A"]["s"] == 35.0
    heading = 35.0 % (2.0 * math.pi)
    assert new_target == (10.0 * math.cos(heading),
                          5.0 + 10.0 * math.sin(heading))
    assert new_target != old_target


def test_reacquisition_uses_global_nearest_on_adjacent_wrap_section():
    # Previous anchor is segment 0. The live point is on segment 3 at the
    # neighboring wrap section; global argmin must replace the stale segment.
    waypoints = np.asarray([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float)
    a = waypoints
    ab = np.roll(a, -1, axis=0) - a
    lengths = np.hypot(ab[:, 0], ab[:, 1])
    t = np.clip(((0.0 - a[:, 0]) * ab[:, 0] + (5.0 - a[:, 1]) * ab[:, 1])
                / (lengths * lengths + 1e-9), 0.0, 1.0)
    px, py = a[:, 0] + t * ab[:, 0], a[:, 1] + t * ab[:, 1]
    idx = int(np.argmin(np.hypot(px - 0.0, py - 5.0)))
    assert idx == 3

    gate = ProjectionAnchorGate()
    gate.remember_on_track("A", (5.0, 0.0), 5.0, 0, (5.0, 0.0))
    gate.target_for("A", lambda anchor: (anchor["s"], anchor["ns"]))
    gate.remember_on_track("A", (0.0, 5.0), 35.0, idx, (0.0, 5.0))
    assert gate._anchors["A"]["ns"] == idx
    assert gate._anchors["A"]["ns"] != 0


def test_s_zero_wrap_is_a_valid_reacquisition():
    ctrl = _controller(True)
    gate = ctrl._projection_anchor_gate
    gate.remember_on_track("A", (0.0, 0.0), 0.0, 0, (0.0, 0.0))
    target = ctrl._rejoin_target_point("A", 39.0, 0.0, 1.0, 10.0)
    assert target == (10.0, 0.0)
    assert all(math.isfinite(x) for x in target)
    assert gate._anchors["A"]["s"] == 0.0


def test_first_offtrack_acquisition_without_anchor_uses_legacy_target():
    ctrl = _controller(True)
    target = ctrl._rejoin_target_point("A", 3.0, 2.0, 4.0, 10.0)
    assert target == (2.0 + 10.0 * math.cos(3.0),
                      4.0 + 10.0 * math.sin(3.0))
    assert ctrl._projection_anchor_gate._anchors == {}


def test_flag_default_off_preserves_legacy_target_calculation():
    assert inspect.signature(NeuralRaceController.__init__).parameters[
        "proj_gate"].default is False
    ctrl = _controller(False)
    live_s, live_x, live_y, ahead = 0.5, 2.0, 4.0, 10.0
    assert ctrl._rejoin_target_point("A", live_s, live_x, live_y, ahead) == (
        live_x + ahead * math.cos(live_s),
        live_y + ahead * math.sin(live_s),
    )
