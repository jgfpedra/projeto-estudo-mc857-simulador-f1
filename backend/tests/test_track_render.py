from __future__ import annotations

from types import SimpleNamespace

from config import INTERLAGOS_TRACK
from engine.physics import PyBulletPhysics


def test_draw_track_lines_uses_start_finish_index(monkeypatch):
    physics = PyBulletPhysics(gui=True)
    physics._client_id = 1
    calls = []

    def fake_line(**kwargs):
        calls.append(kwargs)
        return len(calls)

    monkeypatch.setattr("engine.physics.p.addUserDebugLine", fake_line)

    waypoints = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    physics.draw_track_lines(
        waypoints,
        start_finish_waypoint=2,
        track_width_m=4.0,
    )

    finish_lines = [
        call
        for call in calls
        if call["lineColorRGB"] == (1.0, 0.1, 0.1)
    ]
    assert len(finish_lines) == 1
    start = finish_lines[0]["lineFromXYZ"]
    end = finish_lines[0]["lineToXYZ"]
    mid_x = (start[0] + end[0]) / 2.0
    mid_y = (start[1] + end[1]) / 2.0
    assert abs(mid_x - 10.0) < 1e-6
    assert abs(mid_y - 10.0) < 1e-6
    assert any(call["lineColorRGB"] == (0.2, 0.8, 0.2) for call in calls)
    assert any(call["lineColorRGB"] == (0.85, 0.85, 0.9) for call in calls)


def test_interlagos_track_still_injectable():
    assert len(INTERLAGOS_TRACK.waypoints[0]) == 2
    handle = SimpleNamespace(waypoints=INTERLAGOS_TRACK.waypoints)
    assert handle.waypoints is INTERLAGOS_TRACK.waypoints
