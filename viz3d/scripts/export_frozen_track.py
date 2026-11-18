"""Our track JSON -> the simulation engine's frozen-track format (phase 0b).

The inverse direction of `convert_frozen_track.py`. Writes one file the
engine's `load_track_frozen` (`backend/domain/track_resolution.py`) accepts,
into `exports/` - never into `backend/`:

    python scripts/export_frozen_track.py --track public/tracks/interlagos.json \\
        --name "São Paulo Grand Prix (viz3d 2023 race)" \\
        --out exports/interlagos_2023_v1.json

    python scripts/verify_export_backend.py   # the backend's own hash check

Format, field by field
----------------------
- `waypoints`: `[[x, y], ...]` in metres, FastF1 plan frame - the frame the
  existing frozen files use. Our JSON is Three.js `(x, 0, z)` with
  `z = -ff1.Y` (CLAUDE.md), so `x = three.x`, `y = -three.z`. Loop not
  duplicated, in the direction of travel (check E keeps it that way).
- **Spacing at most `--max-spacing` (4 m)**, like the existing frozen files
  (2-4 m). Our centreline is 5 m, so it is resampled *uniformly* along its own
  polyline at `L / ceil(L / 4)` (~3.998 m): every waypoint lies on the
  viewer's polyline, and only vertex corners are cut, by the amount printed as
  `vertexCutMaxM`. Spacing matters to the engine beyond the 4 m limit: the
  rule-based controller smooths over 9 *waypoints*, so a finer grid would
  shorten that window. ~4 m keeps it close to interlagos_v2's 3.7 m mean.
- `sf_idx`: 0. Our s = 0 is the timing line (`extract_track.py
  --start-finish timing-line`), and resampling starts there, so waypoint 0 is
  it. `sf_method` says so.
- `width_m`: 12.0, as asked and as every existing frozen file.
- `n_wp`: number of waypoints.
- `sha256`: computed exactly as `load_track_frozen` checks it - first 16 hex
  digits of sha256 over `json.dumps(doc minus 'sha256', sort_keys=True)` -
  via `convert_frozen_track.engine_hash`, the same function Phase 0 verified
  the existing files with. `scripts/verify_export_backend.py` then proves it
  with the backend's own function.
- Written with `ensure_ascii=True`: `load_track_frozen` reads with
  `Path.read_text()`, i.e. the platform's default encoding (cp1252 on
  Windows). Escaped non-ASCII parses identically everywhere; raw UTF-8 "ã"
  would be mis-decoded there and change the hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from convert_frozen_track import engine_hash  # noqa: E402

DECIMALS = 6


def plan_ff1(doc: dict) -> np.ndarray:
    """Our committed centreline -> (N, 2) FastF1 plan (X, Y), metres."""
    c = np.asarray(doc["centerline"], dtype=float)
    return np.column_stack([c[:, 0], -c[:, 2]])


def resample_uniform(loop: np.ndarray, max_spacing: float) -> np.ndarray:
    """Points at `k * L / K` along the closed polyline, `K = ceil(L / max)`,
    starting at point 0. Linear along the polyline: no new shape."""
    seg = np.linalg.norm(np.roll(loop, -1, axis=0) - loop, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(cum[-1])
    k = int(math.ceil(total / max_spacing))
    targets = np.arange(k) * (total / k)
    closed = np.vstack([loop, loop[:1]])
    return np.column_stack([np.interp(targets, cum, closed[:, i]) for i in range(2)])


def dist_to_polyline(pts: np.ndarray, poly: np.ndarray) -> np.ndarray:
    a = poly
    ab = np.roll(poly, -1, axis=0) - poly
    l2 = np.maximum((ab * ab).sum(1), 1e-18)
    out = np.empty(len(pts))
    for lo in range(0, len(pts), 2000):
        p = pts[lo:lo + 2000][:, None, :]
        t = np.clip(((p - a) * ab).sum(2) / l2, 0.0, 1.0)
        out[lo:lo + 2000] = np.linalg.norm(a + t[..., None] * ab - p, axis=2).min(1)
    return out


def build(track_path: Path, name: str, width: float, max_spacing: float) -> tuple[dict, dict]:
    raw = track_path.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    sf = doc.get("startFinish", {})
    if sf.get("method") != "timing-line":
        raise SystemExit(f"{track_path}: s = 0 is not the timing line "
                         "(extract with --start-finish timing-line)")
    src = plan_ff1(doc)
    wps = np.round(resample_uniform(src, max_spacing), DECIMALS)
    seg = np.linalg.norm(np.roll(wps, -1, axis=0) - wps, axis=1)
    if seg.max() > max_spacing:
        raise SystemExit(f"spacing {seg.max():.4f} m exceeds {max_spacing} m")
    out = {
        "name": name,
        "waypoints": [[float(x), float(y)] for x, y in wps],
        "width_m": float(width),
        "sf_idx": 0,
        "n_wp": int(len(wps)),
        "sf_method": (
            "timing line: median of every clean timed lap's position "
            "interpolated at LapStartTime, projected onto the centreline "
            f"({sf.get('laps')} laps, MAD {sf.get('sMadM')} m); waypoint 0 is "
            "that point (viz3d extract_track.py --start-finish timing-line)"),
        "source": {
            "track": track_path.as_posix(),
            "trackSha256": hashlib.sha256(raw).hexdigest(),
            "circuit": doc["circuit"], "year": doc["year"],
            "pipeline": "viz3d scripts/extract_track.py (FastF1 3.8.3, offline cache)",
            "resample": f"uniform along the committed polyline, max {max_spacing} m",
        },
    }
    out["sha256"] = engine_hash(out)
    cut = dist_to_polyline(src, wps)
    stats = {"lengthSourceM": round(float(np.linalg.norm(np.roll(src, -1, 0) - src, axis=1).sum()), 3),
             "lengthExportM": round(float(seg.sum()), 3),
             "spacingMinM": round(float(seg.min()), 4), "spacingMaxM": round(float(seg.max()), 4),
             "vertexCutMaxM": round(float(cut.max()), 3),
             "vertexCutP99M": round(float(np.percentile(cut, 99)), 3)}
    return out, stats


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--track", required=True, type=Path)
    p.add_argument("--name", required=True)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--width", type=float, default=12.0)
    p.add_argument("--max-spacing", type=float, default=4.0)
    a = p.parse_args(argv)
    out, stats = build(a.track, a.name, a.width, a.max_spacing)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, ensure_ascii=True), encoding="ascii")
    print(f"  wrote {a.out}  n_wp {out['n_wp']}  sha256 {out['sha256']}")
    print("  " + "  ".join(f"{k} {v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
