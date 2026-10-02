from __future__ import annotations

import pytest

from config import INTERLAGOS_TRACK, load_track
from domain.track_loader import CircuitLoadError, FastF1TrackLoader


class _FakeCache:
    enabled_dir = None

    @staticmethod
    def enable_cache(path: str) -> None:
        _FakeCache.enabled_dir = path


class _FakeCorners:
    columns = ["X", "Y", "Number"]

    def __init__(self, points):
        self._xs = [p[0] for p in points]
        self._ys = [p[1] for p in points]

    def __getitem__(self, column: str):
        if column == "X":
            return self._xs
        if column == "Y":
            return self._ys
        raise KeyError(column)


def _square_corners():
    return _FakeCorners(
        [
            (0.0, 0.0),
            (100.0, 0.0),
            (100.0, 80.0),
            (0.0, 80.0),
        ]
    )


class _FakeCircuitInfo:
    def __init__(self, corners=None, length=None):
        self.corners = corners if corners is not None else _square_corners()
        self.rotation = 12.0
        if length is not None:
            self.Length = length


_DEFAULT = object()


class _FakeSession:
    def __init__(self, info=_DEFAULT, event=None, fail_load=False):
        self._info = _FakeCircuitInfo() if info is _DEFAULT else info
        self.event = event or {
            "EventName": "São Paulo Grand Prix",
            "Location": "São Paulo",
            "Country": "Brazil",
        }
        self.fail_load = fail_load
        self.loaded = False

    def load(self, **kwargs):
        if self.fail_load:
            raise RuntimeError("network down")
        self.loaded = True

    def get_circuit_info(self):
        return self._info


class _FakeFastF1:
    Cache = _FakeCache

    def __init__(self, session=None, error=None):
        self.session = session if session is not None else _FakeSession()
        self.error = error
        self.calls = []

    def get_session(self, year, event, session):
        self.calls.append((year, event, session))
        if self.error is not None:
            raise self.error
        return self.session


def test_loader_builds_closed_track_from_fastf1_dataframe(tmp_path):
    fake = _FakeFastF1(session=_FakeSession(info=_FakeCircuitInfo(length=400.0)))
    loader = FastF1TrackLoader(cache_dir=tmp_path / "fastf1", fastf1_module=fake)

    track = loader.load(year=2025, event="São Paulo", session="R", samples_per_segment=4)

    assert fake.calls == [(2025, "São Paulo", "R")]
    assert fake.session.loaded is True
    assert _FakeCache.enabled_dir == str(tmp_path / "fastf1")
    assert track.source == "fastf1"
    assert track.name == "São Paulo Grand Prix"
    assert len(track.waypoints) >= 12
    assert track.start_finish_waypoint == 0
    assert len(track.sectors) == 3
    assert track.pit is not None
    assert abs(track.length_m - 400.0) < 1e-6
    first, last = track.waypoints[0], track.waypoints[-1]
    assert first != last
    assert track.metadata["year"] == 2025
    assert track.metadata["corner_count"] == 4
    assert len(track.initial_positions) == 24
    assert len(track.initial_position(0)) == 2


def test_loader_errors_when_session_is_missing():
    fake = _FakeFastF1(error=KeyError("unknown event"))
    loader = FastF1TrackLoader(fastf1_module=fake)
    with pytest.raises(CircuitLoadError, match="could not find session"):
        loader.load(year=2025, event="Unknown GP", session="R")


def test_loader_errors_when_circuit_info_is_missing():
    fake = _FakeFastF1(session=_FakeSession(info=None))
    loader = FastF1TrackLoader(fastf1_module=fake)
    with pytest.raises(CircuitLoadError, match="no circuit info"):
        loader.load(year=2025, event="São Paulo", session="R")


def test_loader_errors_when_not_enough_corners():
    fake = _FakeFastF1(
        session=_FakeSession(info=_FakeCircuitInfo(corners=_FakeCorners([(0.0, 0.0), (1.0, 0.0)])))
    )
    loader = FastF1TrackLoader(fastf1_module=fake)
    with pytest.raises(CircuitLoadError, match="enough circuit corners"):
        loader.load(year=2025, event="São Paulo", session="R")


def test_load_track_defaults_to_interlagos_without_name():
    track = load_track()
    assert track is INTERLAGOS_TRACK


def test_load_track_local_interlagos_without_year():
    track = load_track("interlagos")
    assert track is INTERLAGOS_TRACK


def test_load_track_requires_year_for_unknown_name():
    with pytest.raises(ValueError, match="was not found locally"):
        load_track("Monaco")


def test_load_track_parses_round_number(monkeypatch):
    captured = {}

    class _CapturingLoader:
        def __init__(self, cache_dir=None):
            captured["cache_dir"] = cache_dir

        def load(self, year, event, session):
            captured["args"] = (year, event, session)
            return INTERLAGOS_TRACK

    monkeypatch.setattr("config.FastF1TrackLoader", _CapturingLoader)
    track = load_track("21", year=2025, session="Q", cache_dir="/tmp/cache")
    assert track is INTERLAGOS_TRACK
    assert captured["args"] == (2025, 21, "Q")
    assert captured["cache_dir"] == "/tmp/cache"
