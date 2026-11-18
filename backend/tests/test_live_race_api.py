"""Contract checks for live ticks and GET /races/{id} (in-memory, no Redis)."""
import hashlib
import struct
from types import SimpleNamespace

from api.race_manager import BroadcastPublisher
from engine.events import TickEvent


def test_tick_enriches_rank_progress_and_contacts():
    publisher = BroadcastPublisher("abc", manager=None, loop=None)
    contacts = [{"drv_a": "a", "drv_b": "b", "j_n": 12.0}]
    publisher.engine = SimpleNamespace(
        race_progress_m={"a": 12.5},
        states={
            "a": SimpleNamespace(
                position_x=4.25,
                position_y=-8.0,
                heading_rad=3.141592653589793 * 0.75,
                velocity_mps=9.0,
            )
        },
        physics=SimpleNamespace(contact_collector=contacts),
    )
    payload = TickEvent(
        sim_ts=1.2,
        positions=[{"driver_id": "a", "position_xy": [4.25, -8.0], "heading_deg": 135.0}],
    ).to_dict()
    publisher._enrich_tick(payload)
    assert payload["positions"][0] == {
        "driver_id": "a",
        "position_xy": [4.25, -8.0],
        "heading_deg": 135.0,
        "velocity_mps": 9.0,
        "position": 1,
        "progress_m": 12.5,
    }
    assert payload["collisions"] == [{"drv_a": "a", "drv_b": "b", "j_n": 12.0}]
    assert contacts == []


def test_get_race_metadata_format(monkeypatch):
    """GET /races/{id} devolve o contrato estático que o viz3d consome."""
    from fastapi.testclient import TestClient

    from api import main
    from api.race_manager import RaceManager, race_manager
    from api_fixtures import FakeLoader, make_catalog

    loader = FakeLoader()
    monkeypatch.setattr(RaceManager, "_run_engine", staticmethod(lambda engine: None))
    main.app.dependency_overrides[main.optional_catalog] = make_catalog
    main.app.dependency_overrides[main.get_track_loader] = lambda: loader
    race_manager._races.clear()
    with TestClient(main.app) as http:
        r = http.post("/races", json={"laps": 3})
        assert r.status_code == 200, r.text
        race_id = r.json()["race_id"]
        meta = http.get(f"/races/{race_id}")
        assert meta.status_code == 200
        data = meta.json()
        assert data["race_id"] == race_id
        assert data["num_laps"] == 3
        assert len(data["track"]["waypoints"]) > 3
        assert data["track"]["start_finish_waypoint"] == 0
        encoded = b"".join(
            struct.pack("<dd", *point) for point in data["track"]["waypoints"]
        )
        assert data["track"]["geometry_sha256"] == hashlib.sha256(encoded).hexdigest()[:16]
        assert data["car_geometry"] == {"length_m": 5.0, "width_m": 1.8, "height_m": 0.7}
        assert len(data["drivers"]) == 2
        assert data["drivers"][0]["grid_position"] == 1
        missing = http.get("/races/race_nope")
        assert missing.status_code == 404
    main.app.dependency_overrides.clear()
