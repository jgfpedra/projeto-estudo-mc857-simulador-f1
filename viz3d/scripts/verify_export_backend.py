"""Prove the exported frozen tracks' sha256 with the backend's own function.

Calls `backend.domain.track_resolution.load_track_frozen` unchanged, with
`strict=True` (a wrong hash raises). The only thing redirected is the
directory it reads from - its module-level `FROZEN_TRACKS_DIR` is pointed at
`viz3d/exports/` for the duration of the call - so nothing is copied into
`backend/`. Run from the repository root (the backend imports itself as the
`backend` package); needs numpy and pandas, not pybullet:

    viz3d/.venv/Scripts/python.exe viz3d/scripts/verify_export_backend.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "viz3d" / "exports"
sys.path.insert(0, str(ROOT))

import backend.domain.track_resolution as tr  # noqa: E402


def main() -> int:
    files = sorted(EXPORTS.glob("*_v1.json"))
    if not files:
        print(f"no exports in {EXPORTS}")
        return 1
    original = tr.FROZEN_TRACKS_DIR
    tr.FROZEN_TRACKS_DIR = EXPORTS
    ok = True
    try:
        for f in files:
            key = f.name[: -len("_v1.json")]
            doc = json.loads(f.read_text(encoding="ascii"))
            t = tr.load_track_frozen(key, strict=True)   # raises on a bad hash
            same = (t.frozen_sha256 == doc["sha256"]
                    and len(t.waypoints) == doc["n_wp"]
                    and t.start_finish_waypoint == doc["sf_idx"]
                    and float(t.width_m) == doc["width_m"])
            ok &= same
            print(f"  {'OK  ' if same else 'FAIL'} {f.name}: load_track_frozen('{key}', strict=True) "
                  f"-> {t.name!r}, {len(t.waypoints)} wp, sf {t.start_finish_waypoint}, "
                  f"width {t.width_m}, sha256 {t.frozen_sha256} "
                  f"(file sha256 {hashlib.sha256(f.read_bytes()).hexdigest()[:16]}...)")
    finally:
        tr.FROZEN_TRACKS_DIR = original
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
