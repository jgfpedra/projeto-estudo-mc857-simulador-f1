"""Engine frozen track -> our track JSON (docs/3d-design.md section 5).

Phase 0 of evaluating the simulation engine's frozen tracks as the single
geometry source (docs/phase0-geometry-report.md). The input is one of the
group repo's `backend/model_train/tracks_frozen/*.json`, read and never
written:

    python scripts/convert_frozen_track.py --circuit monza \\
        --frozen <group-repo>/backend/model_train/tracks_frozen/Monza_v1.json \\
        --corners-from public/tracks/monza.json \\
        --out public/tracks/monza_v1.json

    python scripts/convert_frozen_track.py --circuit interlagos \\
        --frozen <group-repo>/backend/model_train/tracks_frozen/interlagos_v2.json \\
        --corners-from-multiviewer --out public/tracks/interlagos_v2.json

What it does, and deliberately does not do
------------------------------------------
- **Rotate, never resample.** The loop is rolled so the frozen file's
  `sf_idx` becomes point 0, so `s = 0` is the engine's start/finish. The
  vertices are otherwise the engine's own, bit for bit up to the 6-decimal
  (micrometre) rounding of the output. `frame.ts` does not assume uniform
  spacing - `s` is cumulative chord length and segment lookup is a binary
  search - so the non-uniform 2-4 m spacing loads as is. Resampling would
  put our `s` off the engine's by the resampling's chord error; keeping the
  vertices makes the mapping exact:

      s_ours = (s_engine - s_engine[sf_idx]) mod L ,   d_ours = -d_engine

  (the engine's lateral is +left, ours +right; see the report).
- **Map to Three.js exactly as `extract_track.to_three` does**:
  `(X, Y) -> (X, 0, -Y)`. The frozen files are 2D, so `y = 0`.
- **Corners are projected, not invented.** Either from our own track JSON
  (each corner's point on *our* centreline, projected onto the frozen one with
  `centreline.project_global` - the refined projector, the same code
  `extract_track.py` and `extract_replay.py` use), or from MultiViewer's corner
  markers, which are FastF1's `circuit_info` source.
- **No geometric gate.** Unlike `extract_track.py`, this writes the JSON even
  when the reference checks would fail: the whole point is to measure how far
  the frozen geometry is from the references. It refuses only on *structural*
  problems - a hash that does not verify, an out-of-range `sf_idx`, a
  duplicated closing vertex, non-finite coordinates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from centreline import (  # noqa: E402
    _foot_f, brackets, frame_from_three, load_centre_frame, project_global,
    to_world,
)
from extract_track import CIRCUITS, signed_area  # noqa: E402

#: Output precision. Micrometres, not extract_track's millimetres: the claim
#: this file exists to support is that its vertices *are* the engine's.
DECIMALS = 6


class StructuralError(ValueError):
    """The frozen file is not what it claims to be."""


def engine_hash(doc: dict) -> str:
    """The engine's integrity hash, exactly as `load_track_frozen` computes it
    (`backend/model_train/f1_env.py`): the first 16 hex digits of the sha256
    of the document *minus* its own `sha256` field, dumped with sorted keys.

    Not a hash of the file. Recorded alongside the file's real sha256 so the
    two are never confused.
    """
    body = {k: v for k, v in doc.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]


def git_provenance(path: Path) -> dict:
    """Branch, commit and blob id of the frozen file in its own repository.

    Read-only git plumbing. A file with uncommitted changes is flagged rather
    than refused - the hash check already guarantees the content is the one the
    engine would accept.
    """
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(path.parent), *args],
                              check=True, capture_output=True,
                              text=True).stdout.strip()
    try:
        top = Path(git("rev-parse", "--show-toplevel"))
        rel = path.resolve().relative_to(top.resolve()).as_posix()
        return {
            "repo": top.name,
            "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "commit": git("rev-parse", "HEAD"),
            "path": rel,
            "gitBlob": git("hash-object", str(path)),
            "dirty": bool(git("status", "--porcelain", "--", str(path))),
        }
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return {"repo": None, "path": path.name}


def read_frozen(path: Path) -> tuple[dict, np.ndarray]:
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    for key in ("waypoints", "sf_idx", "sha256"):
        if key not in doc:
            raise StructuralError(f"{path.name}: missing '{key}'")
    got = engine_hash(doc)
    if got != doc["sha256"]:
        raise StructuralError(
            f"{path.name}: engine hash {got} does not match its sha256 field "
            f"{doc['sha256']} - the engine would refuse this file too")
    wps = np.asarray(doc["waypoints"], dtype=float)
    if wps.ndim != 2 or wps.shape[1] != 2 or len(wps) < 3:
        raise StructuralError(f"{path.name}: waypoints are not an (N, 2) list")
    if not np.isfinite(wps).all():
        raise StructuralError(f"{path.name}: non-finite waypoint")
    if "n_wp" in doc and int(doc["n_wp"]) != len(wps):
        raise StructuralError(
            f"{path.name}: n_wp {doc['n_wp']} != {len(wps)} waypoints")
    if np.linalg.norm(wps[0] - wps[-1]) < 1e-6:
        raise StructuralError(
            f"{path.name}: closing vertex duplicates waypoint 0; the engine "
            "treats the loop as implicitly closed, so this would be a "
            "zero-length segment")
    sf = int(doc["sf_idx"])
    if not 0 <= sf < len(wps):
        raise StructuralError(f"{path.name}: sf_idx {sf} out of range")
    doc["_fileSha256"] = hashlib.sha256(raw).hexdigest()
    return doc, wps


def to_three(xy: np.ndarray) -> np.ndarray:
    """FastF1 plan (X, Y) -> Three.js (x, y, z) = (X, 0, -Y).

    The 2D special case of `extract_track.to_three`, which owns the mapping;
    asserted equal to it in `main` rather than trusted.
    """
    return np.c_[xy[:, 0], np.zeros(len(xy)), -xy[:, 1]]


def projector_margin(frame, i: int, t: float) -> float:
    """cos(alpha) at a foot point: the cosine between segment `i`'s chord and
    the interpolated tangent there. `brackets` needs `cos alpha > |d kappa|`
    for `f` to be monotone on the segment (centreline.py); this is the left
    side of that, measured where it is used."""
    j = (i + 1) % len(frame.points)
    chord = frame.points[j] - frame.points[i]
    chord = chord / np.linalg.norm(chord)
    _, _, that, _ = _foot_f(frame, i, t, frame.points[i])
    return float(chord @ that)


def frame_alpha_stats(frame, half_width: float) -> dict:
    """Projector preconditions over the whole frozen loop.

    `centreline.brackets` assumes `f` is strictly monotone on every segment,
    which needs `cos alpha > |d kappa|` there. Those two numbers were measured
    on our uniform 5 m Monza (cos alpha >= 0.990, |d kappa| <= 0.041); the
    frozen loops have non-uniform spacing, so they are re-measured here, with
    `alpha` at both ends of every segment and `kappa` at the half-width.
    """
    n = len(frame.points)
    cos_min = 1.0
    for i in range(n):
        j = (i + 1) % n
        chord = frame.points[j] - frame.points[i]
        chord = chord / np.linalg.norm(chord)
        for k in (i, j):
            cos_min = min(cos_min, float(chord @ frame.tangent[k]))
    dk = float(np.max(np.abs(frame.curvature)) * half_width)
    seg = frame.seg_len
    ratio = np.maximum(seg, np.roll(seg, 1)) / np.minimum(seg, np.roll(seg, 1))
    return {"cosAlphaMin": round(cos_min, 5),
            "maxAbsDKappaAtHalfWidth": round(dk, 4),
            "monotone": bool(cos_min > dk),
            # Central-difference tangents are first-order biased where the two
            # neighbouring segments differ in length; this is how much they do.
            "maxNeighbourSegmentRatio": round(float(ratio.max()), 3)}


def project_corners(frame, sources: list[tuple[int, str, np.ndarray]]
                    ) -> list[dict]:
    """Each `(number, name, plan point)` -> `s` on the frozen centreline.

    Records, per corner, how far the point sits from the frozen line (`d`),
    whether a segment actually bracketed the foot point (if not,
    `project_global` falls back to the nearest vertex's segment and the `s` is
    an approximation), and the local `cos alpha`.
    """
    out = []
    for number, name, p in sources:
        s, d, res = project_global(frame, p)
        i = int(np.clip(np.searchsorted(frame.s, s, side="right") - 1,
                        0, len(frame.s) - 1))
        j = (i + 1) % len(frame.points)
        seg = (frame.s[j] - frame.s[i]) % frame.length_m
        t = (s - frame.s[i]) / seg if seg > 0 else 0.0
        out.append({
            "number": number, "name": name, "s": round(s, 1),
            "_dM": round(d, 2),
            "_bracketed": bool(brackets(frame, i, p)),
            "_cosAlpha": round(projector_margin(frame, i, t), 5),
            "_residual": float(res),
        })
    out.sort(key=lambda c: c["s"])
    return out


def corners_from_track(path: str) -> list[tuple[int, str, np.ndarray]]:
    """Our corners: their point *on our centreline* (`d = 0`).

    Our JSON stores corner `s` only; FastF1's markers sat within 0.7 m of the
    centreline when it was written (3d-design section 4, step 10), so dropping
    that offset moves each by under a metre - small against what is measured.
    """
    ours = load_centre_frame(path)
    return [(int(c["number"]), str(c["name"]), to_world(ours, float(c["s"])))
            for c in ours.corners]


def corners_from_multiviewer(circuit: str) -> list[tuple[int, str, np.ndarray]]:
    from multiviewer import fetch
    mv = fetch(circuit)
    names = CIRCUITS[circuit].corner_names or {}
    plan = to_three(mv.corners_xy)[:, [0, 2]]
    out = []
    for label, p in zip(mv.corner_numbers, plan):
        number = int("".join(ch for ch in label if ch.isdigit()))
        out.append((number, names.get(number, f"T{label}"), p))
    return out


def convert(args) -> dict:
    frozen_path = Path(args.frozen)
    doc, wps = read_frozen(frozen_path)
    sf = int(doc["sf_idx"])
    ref = CIRCUITS[args.circuit]

    # Engine arc length at sf_idx, from waypoint 0, chord sum - the engine's
    # own `_seg_cum` construction.
    seg_engine = np.linalg.norm(np.roll(wps, -1, axis=0) - wps, axis=1)
    s_engine_sf = float(np.concatenate([[0.0], np.cumsum(seg_engine)])[sf])

    rolled = np.roll(wps, -sf, axis=0)
    three = to_three(rolled)
    from extract_track import to_three as to_three_3d
    assert np.array_equal(three, to_three_3d(np.c_[rolled, np.zeros(len(rolled))])), \
        "2D mapping disagrees with extract_track.to_three"
    three = np.round(three, DECIMALS) + 0.0   # + 0.0: no "-0.0" in the JSON

    frame = frame_from_three(three, width_m=float(doc.get("width_m", 12.0)))
    width = float(doc.get("width_m", 12.0))
    stats = frame_alpha_stats(frame, width / 2.0)

    if args.corners_from:
        sources = corners_from_track(args.corners_from)
        corner_source = f"projected from {Path(args.corners_from).as_posix()}"
    elif args.corners_from_multiviewer:
        sources = corners_from_multiviewer(args.circuit)
        corner_source = "MultiViewer corner markers (FastF1 circuit_info source)"
    else:
        sources, corner_source = [], "none"
    corners = project_corners(frame, sources)

    seg = frame.seg_len
    n = len(three)
    out = {
        "circuit": args.circuit,
        "name": ref.name,
        "variant": frozen_path.stem,
        "year": None,
        "lengthM": round(frame.length_m, 1),
        "spacingM": round(frame.length_m / n, 4),
        "spacingMinM": round(float(seg.min()), 4),
        "spacingMaxM": round(float(seg.max()), 4),
        "uniformSpacing": False,
        "widthM": width,
        "rotationDeg": 0.0,
        "centerline": three.tolist(),
        "corners": [{"number": c["number"], "name": c["name"], "s": c["s"]}
                    for c in corners],
        "startFinishS": 0.0,
        "source": {
            **git_provenance(frozen_path),
            "frozenName": doc.get("name"),
            "sha256Field": doc["sha256"],
            "sha256FieldVerified": True,
            "fileSha256": doc["_fileSha256"],
            "sfIdx": sf,
            "nWaypoints": len(wps),
            "engineSAtSfM": round(s_engine_sf, 4),
            "lateral": "engine d is +left of travel; ours is +right: "
                       "d_ours = -d_engine",
            "arcLength": "s_ours = (s_engine - engineSAtSfM) mod lengthM; "
                         "vertices kept, not resampled",
            "corners": corner_source,
            "projector": stats,
        },
    }
    report(out, corners, signed_area(three[:, [0, 2]]))
    return out


def report(doc: dict, corners: list[dict], area: float) -> None:
    src = doc["source"]
    pr = src["projector"]
    print(f"\n  convert_frozen_track  {doc['variant']} -> circuit '{doc['circuit']}'")
    print("  " + "=" * 74)
    print(f"  source     {src.get('repo')}@{src.get('branch')} "
          f"{(src.get('commit') or '')[:10]} {src.get('path')}"
          f"{'  (DIRTY)' if src.get('dirty') else ''}")
    print(f"  hash       engine field {src['sha256Field']} verified; "
          f"file sha256 {src['fileSha256'][:16]}...")
    print(f"  loop       {src['nWaypoints']} vertices, {doc['lengthM']} m, "
          f"spacing {doc['spacingMinM']}-{doc['spacingMaxM']} m (mean "
          f"{doc['spacingM']}), {'clockwise' if area > 0 else 'anticlockwise'}")
    print(f"  s = 0      sf_idx {src['sfIdx']}, engine s {src['engineSAtSfM']} m")
    print(f"  projector  cos(alpha) min {pr['cosAlphaMin']}, |d kappa| max "
          f"{pr['maxAbsDKappaAtHalfWidth']} at half-width -> "
          f"{'monotone' if pr['monotone'] else 'NOT MONOTONE'}; neighbour "
          f"segment ratio up to {pr['maxNeighbourSegmentRatio']}")
    print(f"  corners    {len(corners)} ({src['corners']})")
    for c in corners:
        flag = "" if c["_bracketed"] else "  (no bracket: nearest-vertex fallback)"
        print(f"    T{c['number']:<3} s {c['s']:8.1f}  d {c['_dM']:+7.2f} m  "
              f"cos(alpha) {c['_cosAlpha']:.4f}  {c['name']}{flag}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--circuit", required=True, choices=sorted(CIRCUITS))
    p.add_argument("--frozen", required=True, help="engine frozen track JSON")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--corners-from", help="our track JSON to project corners from")
    g.add_argument("--corners-from-multiviewer", action="store_true")
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    try:
        doc = convert(args)
    except StructuralError as exc:
        print(f"\n  refusing: {exc}\n", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"  wrote      {out} ({len(doc['centerline'])} points)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
