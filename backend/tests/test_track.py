from __future__ import annotations

import math

import pytest

from domain.track import Track, build_interlagos_track


def test_from_waypoints_builds_closed_track():
    track = Track.from_waypoints(
        name="Box",
        waypoints=[(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0)],
        start_finish_waypoint=2,
        width_m=10.0,
    )

    assert track.name == "Box"
    assert len(track.waypoints) == 4
    assert track.start_finish_waypoint == 2
    assert track.source == "manual"
    assert track.waypoints[0] == (0.0, 0.0)
    assert math.isclose(track.length_m, 300.0, rel_tol=1e-6)
    assert track.waypoint(5) == track.waypoints[1]


def test_from_waypoints_rejects_too_few_points():
    with pytest.raises(ValueError, match="at least two points"):
        Track.from_waypoints(name="tiny", waypoints=[(0.0, 0.0)])


def test_from_waypoints_rejects_invalid_start_finish():
    with pytest.raises(ValueError, match="start_finish_waypoint"):
        Track.from_waypoints(
            name="line",
            waypoints=[(0.0, 0.0), (1.0, 0.0)],
            start_finish_waypoint=3,
        )


def test_interlagos_preset_is_closed_and_scaled():
    track = build_interlagos_track()
    assert track.name == "Interlagos"
    assert len(track.waypoints) >= 20
    assert track.start_finish_waypoint == 0
    assert math.isclose(track.length_m, 4309.0, rel_tol=1e-3)
    assert track.pit is not None
    assert len(track.sectors) == 3
    idx, dist = track.closest_waypoint(*track.waypoints[0])
    assert idx == 0
    assert dist == 0.0
    assert len(track.initial_positions) == 24
    pos0 = track.initial_position(0)
    pos1 = track.initial_position(1)
    assert len(pos0) == 2
    assert len(pos1) == 2
    assert pos0 != pos1


def test_track_custom_initial_positions():
    custom_slots = [(10.0, 5.0), (12.0, -5.0)]
    track = Track.from_waypoints(
        name="CustomGrid",
        waypoints=[(0.0, 0.0), (50.0, 0.0), (50.0, 50.0), (0.0, 50.0)],
        initial_positions=custom_slots,
    )
    assert track.initial_positions == custom_slots
    assert track.initial_position(0) == (10.0, 5.0)
    assert track.initial_position(1) == (12.0, -5.0)
    # Slot além do tamanho pré-calculado é computado dinamicamente
    pos_ext = track.initial_position(5)
    assert len(pos_ext) == 2
    d = track.to_dict()
    assert "initial_positions" in d
    assert d["initial_positions"] == [[10.0, 5.0], [12.0, -5.0]]
