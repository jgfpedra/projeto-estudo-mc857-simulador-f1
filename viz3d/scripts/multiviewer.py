"""MultiViewer circuit data: corner markers and a reference lap outline.

This is the service FastF1's `Session.get_circuit_info()` reads from
(`fastf1/mvapi`), queried directly by circuit key. Phase 0 needs it for two
reasons, both written up in docs/phase0-geometry-report.md:

- **The corner markers are the frozen tracks' control points.** Every marker
  is an exact waypoint of `Monza_v1` and `interlagos_v2` (to ~1e-13 m), which
  is the evidence that those tracks are splines through the markers.
- **F1's live-timing archive now answers 401** to unauthenticated requests,
  for every session including ones FastF1 used to serve, so
  `extract_track.py` cannot fetch São Paulo telemetry. MultiViewer still
  serves one recorded lap outline per circuit (`x`, `y`), which is the only
  telemetry-derived Interlagos reference reachable, and is used as a
  *labelled stand-in* only.

Responses are cached under `.cache/multiviewer/` (gitignored: raw third-party
data, same rule as `.fastf1-cache/`). Coordinates are FastF1's 1/10 m and are
converted to metres here, once.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HOST = "https://api.multiviewer.app"
CACHE_DIR = Path(".cache") / "multiviewer"

#: F1 live-timing circuit keys, as FastF1 uses them.
CIRCUIT_KEYS = {"monza": 39, "interlagos": 14}


@dataclass
class CircuitData:
    key: int
    #: The dataset year MultiViewer actually returned - it serves the nearest
    #: layout it has, which is not necessarily the year asked for.
    year: int
    name: str
    rotation_deg: float
    #: (K, 2) FastF1 plan (X, Y), metres.
    corners_xy: np.ndarray
    corner_numbers: list[str]
    #: (M, 2) FastF1 plan, metres: one recorded lap, as drawn on track maps.
    outline_xy: np.ndarray
    #: Which lap the outline is (driver, session, lap number, date).
    outline_lap: dict
    url: str


def fetch(circuit: str, year: int = 2024,
          cache_dir: Path = CACHE_DIR) -> CircuitData:
    key = CIRCUIT_KEYS[circuit]
    url = f"{HOST}/api/v1/circuits/{key}/{year}"
    path = Path(cache_dir) / f"{key}_{year}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            url, headers={"User-Agent": "f1-3d-experimental (MC857 spike)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            path.write_bytes(resp.read())
    d = json.loads(path.read_text(encoding="utf-8"))
    corners = d["corners"]
    return CircuitData(
        key=key,
        year=int(d["year"]),
        name=str(d["circuitName"]),
        rotation_deg=float(d["rotation"]),
        corners_xy=np.array([[c["trackPosition"]["x"], c["trackPosition"]["y"]]
                             for c in corners], dtype=float) / 10.0,
        corner_numbers=[f"{c['number']}{c.get('letter') or ''}"
                        for c in corners],
        outline_xy=np.c_[d["x"], d["y"]].astype(float) / 10.0,
        outline_lap=dict(d["candidateLap"]),
        url=url,
    )
