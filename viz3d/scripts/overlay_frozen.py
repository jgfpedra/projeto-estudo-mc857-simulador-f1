"""Phase 0 overlay: our centrelines against the engine's frozen tracks.

Produces every number and plot in docs/phase0-geometry-report.md:

    python scripts/overlay_frozen.py --frozen-dir <group-repo>/backend/model_train/tracks_frozen

writes `docs/phase0/metrics.json` and `docs/phase0/*.png`. Reads
`public/tracks/{monza,monza_v1,interlagos_v2}.json`, the original frozen files
(for their pre-rotation waypoints) and MultiViewer's circuit data
(`scripts/multiviewer.py`, cached under `.cache/`).

What is measured, and how
-------------------------
- **Distances are point-to-polyline, both ways**, from each line densified to
  1 m (vertices included) to the other line's segments. Not the projector's
  `d`: `project_global` assumes the foot point is nearby and well-conditioned,
  which a curve 100 m away is not. The larger of the two maxima is the
  (discrete) Hausdorff distance.
- **The corner-marker hypothesis**: (1) are MultiViewer's corner markers -
  FastF1's `circuit_info` source - vertices of the frozen loop; (2) which
  interpolant through those markers reproduces it; (3) does its curvature peak
  *at* the markers, and is it non-zero on the straights. A spline through
  apex markers should do both; a centreline fitted to driven laps should not.
- **Interlagos has no telemetry centreline of ours**: F1's live-timing archive
  answers 401, so `extract_track.py` cannot fetch São Paulo. MultiViewer's
  single recorded lap outline stands in, and its error is measured first on
  Monza, against our real centreline, so the Interlagos numbers carry error
  bars.

Everything is in Three.js plan space `(x, z)`; FastF1 `(X, Y)` inputs go
through `convert_frozen_track.to_three`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from centreline import (  # noqa: E402
    frame_from_three, load_centre_frame, project_global, to_world,
)
from convert_frozen_track import to_three  # noqa: E402
from multiviewer import fetch  # noqa: E402

OUT = Path("docs") / "phase0"

# Light-mode reference palette (dataviz skill, references/palette.md), slots
# 1-3, validated all-pairs. Aqua is below 3:1 on the surface, so the stand-in
# line is also dashed and direct-labelled.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3de"
C_OURS = "#2a78d6"
C_FROZEN = "#eb6834"
C_MV = "#1baf7a"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "font.size": 9, "axes.titlesize": 10,
    "axes.titleweight": "bold", "legend.frameon": False,
})


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def plan_of(xy_ff1: np.ndarray) -> np.ndarray:
    return to_three(xy_ff1)[:, [0, 2]]


def frame_of_plan(plan: np.ndarray, corners=None):
    # MultiViewer's Monza outline repeats its first point at the end; our
    # frames are open loops (closing segment implicit), so drop it.
    if np.linalg.norm(plan[0] - plan[-1]) < 1e-6:
        plan = plan[:-1]
    xyz = np.c_[plan[:, 0], np.zeros(len(plan)), plan[:, 1]]
    return frame_from_three(xyz, corners=corners or [])


def densify(frame, step: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Points every `step` metres along the closed polyline, vertices kept."""
    pts, ss = [], []
    n = len(frame.points)
    for i in range(n):
        a, b = frame.points[i], frame.points[(i + 1) % n]
        k = max(1, int(np.ceil(frame.seg_len[i] / step)))
        t = np.arange(k) / k
        pts.append(a + t[:, None] * (b - a))
        ss.append(frame.s[i] + t * frame.seg_len[i])
    return np.vstack(pts), np.concatenate(ss)


def dist_to_polyline(P: np.ndarray, Q: np.ndarray, chunk: int = 2000):
    """Distance from each point of P to the closed polyline Q, and the arc
    length on Q of the closest point."""
    A = Q
    AB = np.roll(Q, -1, axis=0) - Q
    l2 = np.maximum(np.einsum("ij,ij->i", AB, AB), 1e-18)
    cum = np.concatenate([[0.0], np.cumsum(np.sqrt(l2))[:-1]])
    out_d = np.empty(len(P))
    out_s = np.empty(len(P))
    for lo in range(0, len(P), chunk):
        p = P[lo:lo + chunk]
        ap = p[:, None, :] - A[None, :, :]
        t = np.clip(np.einsum("pij,ij->pi", ap, AB) / l2, 0.0, 1.0)
        foot = A[None] + t[..., None] * AB[None]
        d = np.linalg.norm(foot - p[:, None, :], axis=2)
        j = np.argmin(d, axis=1)
        r = np.arange(len(p))
        out_d[lo:lo + chunk] = d[r, j]
        out_s[lo:lo + chunk] = cum[j] + t[r, j] * np.sqrt(l2[j])
    return out_d, out_s


def nearest_corner(s: float, corners: list[dict], length: float) -> str:
    if not corners:
        return "no corners"
    ds = [((s - c["s"] + length / 2) % length) - length / 2 for c in corners]
    k = int(np.argmin(np.abs(ds)))
    name = corners[k]["name"]
    label = f"T{corners[k]['number']}" + ("" if name.startswith("T") else f" {name}")
    return f"{label} ({ds[k]:+.0f} m)"


def both_ways(fa, fb, name_a: str, name_b: str) -> dict:
    """Densified point-to-polyline distances a->b and b->a."""
    out = {}
    for src, dst, key in ((fa, fb, f"{name_a}->{name_b}"),
                          (fb, fa, f"{name_b}->{name_a}")):
        P, s = densify(src)
        d, _ = dist_to_polyline(P, dst.points)
        i = int(np.argmax(d))
        out[key] = {
            "n": int(len(P)),
            "max": round(float(d.max()), 2),
            "p50": round(float(np.median(d)), 2),
            "p90": round(float(np.percentile(d, 90)), 2),
            "maxAtS": round(float(s[i]), 1),
            "maxNear": nearest_corner(float(s[i]), src.corners, src.length_m),
            "_s": s, "_d": d,
        }
    a, b = out.values()
    out["hausdorff"] = max(a["max"], b["max"])
    return out


def signed_s(s: float, length: float) -> float:
    return ((s + length / 2) % length) - length / 2


def sf_offset(fa, fb, pa=None, pb=None) -> dict:
    """Start/finish points against each other: straight-line distance and each
    projected onto the other line, `s` wrapped to +/- half a lap."""
    pa = fa.points[0] if pa is None else pa
    pb = fb.points[0] if pb is None else pb
    sa, da, _ = project_global(fb, pa)
    sb, db, _ = project_global(fa, pb)
    return {"distanceM": round(float(np.linalg.norm(pa - pb)), 1),
            "aOnB": {"s": round(signed_s(sa, fb.length_m), 1), "d": round(da, 1)},
            "bOnA": {"s": round(signed_s(sb, fa.length_m), 1), "d": round(db, 1)}}


# --------------------------------------------------------------------------
# the corner-marker hypothesis
# --------------------------------------------------------------------------

def markers_are_vertices(wps: np.ndarray, markers: np.ndarray) -> dict:
    d = np.array([np.linalg.norm(wps - m, axis=1).min() for m in markers])
    idx = [int(np.linalg.norm(wps - m, axis=1).argmin()) for m in markers]
    return {"count": int(len(markers)), "maxDistanceM": float(d.max()),
            "waypointIndices": idx}


def catmull_rom(P: np.ndarray, alpha: float, ns: int) -> np.ndarray:
    """Closed Catmull-Rom through P, parameterised by chord**alpha: 0 is the
    uniform variant (`backend/domain/track.py::_catmull_rom_spline`), 0.5
    centripetal, 1 chordal."""
    n = len(P)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        t1 = np.linalg.norm(p1 - p0) ** alpha
        t2 = t1 + np.linalg.norm(p2 - p1) ** alpha
        t3 = t2 + np.linalg.norm(p3 - p2) ** alpha
        t = np.linspace(t1, t2, ns, endpoint=False)[:, None]
        a1 = (t1 - t) / t1 * p0 + t / t1 * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / t2 * a1 + t / t2 * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    return np.vstack(out)


def reconstruct(markers: np.ndarray, samples_per_segment: int = 12,
                max_seg_m: float = 4.0) -> np.ndarray:
    """The frozen-track construction, as reverse-engineered in phase 0:
    centripetal Catmull-Rom through the corner markers, `samples_per_segment`
    knots per marker-to-marker span, then every knot-to-knot chord split into
    ceil(len / max_seg_m) equal pieces. Compared vertex-for-vertex with the
    frozen file in `reproduction`."""
    knots = catmull_rom(markers, 0.5, samples_per_segment)
    out = []
    for a, b in zip(knots, np.roll(knots, -1, axis=0)):
        k = int(np.ceil(np.linalg.norm(b - a) / max_seg_m - 1e-9))
        out.append(a + (np.arange(k) / k)[:, None] * (b - a))
    return np.vstack(out)


def reproduction(wps: np.ndarray, markers: np.ndarray) -> dict:
    rec = reconstruct(markers)
    same = len(rec) == len(wps)
    return {"vertices": [len(rec), len(wps)],
            "maxVertexErrorM": float(np.abs(rec - wps).max()) if same else None,
            "knots": len(markers) * 12}


def spline_sweep(wps: np.ndarray, markers: np.ndarray) -> list[dict]:
    rows = []
    for alpha in (0.0, 0.4, 0.5, 0.6, 1.0):
        curve = catmull_rom(markers, alpha, 400)
        d, _ = dist_to_polyline(wps, curve)
        L = float(np.linalg.norm(np.roll(curve, -1, 0) - curve, axis=1).sum())
        rows.append({"alpha": alpha, "p50": round(float(np.median(d)), 3),
                     "p90": round(float(np.percentile(d, 90)), 3),
                     "max": round(float(d.max()), 3), "lengthM": round(L, 1)})
    return rows


def vertex_turns_deg(frame) -> np.ndarray:
    """Heading change at each vertex, degrees, positive = right turn."""
    e = np.roll(frame.points, -1, axis=0) - frame.points
    h = np.arctan2(e[:, 1], e[:, 0])
    turn = np.angle(np.exp(1j * (h - np.roll(h, 1))))
    # (x, z) with z towards the viewer: a right turn decreases atan2(z, x)'s
    # complement... measured, not derived: sign chosen to agree with
    # frame.curvature, which is positive to the right.
    sign = np.sign(np.sum(turn * frame.curvature)) or 1.0
    return np.degrees(turn) * sign


def peaks_at_markers(frame, corners: list[dict], window_m: float = 50.0) -> list[dict]:
    """For each corner: |kappa| at the corner's own s, over the max |kappa|
    within +/- window. 1.0 means the curvature peak sits exactly on the
    corner position; a centreline fitted to driven laps peaks wherever the
    real apex is, which need not coincide with an annotation marker."""
    k = np.abs(frame.curvature)
    rows = []
    for c in corners:
        ds = ((frame.s - c["s"] + frame.length_m / 2) % frame.length_m) - frame.length_m / 2
        near = np.abs(ds) <= window_m
        at = int(np.argmin(np.abs(ds)))
        peak = int(np.flatnonzero(near)[np.argmax(k[near])])
        rows.append({"corner": c["number"], "s": c["s"],
                     "ratio": round(float(k[at] / k[peak]), 3),
                     "peakOffsetM": round(float(signed_s(frame.s[peak] - c["s"], frame.length_m)), 1),
                     "kappaPeak": round(float(k[peak]), 4)})
    return rows


def straights(ours, frozen, min_len: float = 250.0, k_max: float = 1e-3) -> list[dict]:
    """Our straights - runs with |kappa| (smoothed over +/-25 m) under 1/km for
    at least `min_len` - and how straight the frozen line is over the same
    stretch: max deviation from the chord between the stretch's ends, and the
    median |kappa|."""
    k = np.abs(ours.curvature)
    w = max(1, int(round(25.0 / np.median(ours.seg_len))))
    ks = np.convolve(np.r_[k[-w:], k, k[:w]], np.ones(2 * w + 1) / (2 * w + 1), "valid")
    flat = ks < k_max
    n = len(flat)
    start = int(np.argmin(flat)) if not flat.all() else 0   # begin on a non-flat sample
    runs, cur = [], None
    for m in range(1, n + 1):
        i = (start + m) % n
        if flat[i] and cur is None:
            cur = i
        if (not flat[i] or m == n) and cur is not None:
            runs.append((cur, (i - 1) % n))
            cur = None
    rows = []
    for a, b in runs:
        L = (ours.s[b] - ours.s[a]) % ours.length_m
        if L < min_len:
            continue
        idx = np.arange(a, a + ((b - a) % n) + 1) % n
        rows.append(_straightness(ours, frozen, idx, L))
    return rows


def _chord_dev(pts: np.ndarray) -> float:
    a, b = pts[0], pts[-1]
    u = (b - a) / np.linalg.norm(b - a)
    rel = pts - a
    return float(np.max(np.abs(rel[:, 0] * u[1] - rel[:, 1] * u[0])))


def _total_turn(pts: np.ndarray) -> float:
    """Sum of |heading change| along an open polyline, degrees."""
    e = np.diff(pts, axis=0)
    e = e[np.linalg.norm(e, axis=1) > 1e-9]
    h = np.arctan2(e[:, 1], e[:, 0])
    return float(np.degrees(np.abs(np.angle(np.exp(1j * np.diff(h)))).sum()))


def _straightness(ours, frozen, idx, L) -> dict:
    p0, p1 = ours.points[idx[0]], ours.points[idx[-1]]
    s0, _, _ = project_global(frozen, p0)
    s1, _, _ = project_global(frozen, p1)
    span = (s1 - s0) % frozen.length_m
    sel = ((frozen.s - s0) % frozen.length_m) <= span
    fpts = np.vstack([to_world(frozen, s0), frozen.points[sel][np.argsort(
        (frozen.s[sel] - s0) % frozen.length_m)], to_world(frozen, s1)])
    return {"oursS": [round(float(ours.s[idx[0]]), 0), round(float(ours.s[idx[-1]]), 0)],
            "lengthM": round(float(L), 0),
            "between": f"{nearest_corner(float(ours.s[idx[0]]), ours.corners, ours.length_m)}"
                       f" .. {nearest_corner(float(ours.s[idx[-1]]), ours.corners, ours.length_m)}",
            "oursChordDevM": round(_chord_dev(ours.points[idx]), 2),
            "frozenChordDevM": round(_chord_dev(fpts), 2),
            "oursTotalTurnDeg": round(_total_turn(ours.points[idx]), 1),
            "frozenTotalTurnDeg": round(_total_turn(fpts), 1),
            "oursMedianKappa": float(f"{np.median(np.abs(ours.curvature[idx])):.2e}"),
            "frozenMedianKappa": float(f"{np.median(np.abs(frozen.curvature[sel])):.2e}")}


# --------------------------------------------------------------------------
# plots
# --------------------------------------------------------------------------

def _loop(p):
    return np.vstack([p, p[:1]])


def _edges(frame, half: float):
    right = np.c_[-frame.tangent[:, 1], frame.tangent[:, 0]]
    return frame.points + half * right, frame.points - half * right


def plot_overlay(path, ref, ref_label, ref_colour, frozen, frozen_label, markers,
                 title, sf_ref=None, ref_dashed=False, worst=None, zooms=()):
    """Full plan overlay; `zooms` adds one panel per (title, centre, half-span).
    The reference line's ribbon (+/-6 m) is shaded so deviations read against
    track width."""
    n = 1 + len(zooms)
    fig = plt.figure(figsize=(11, 7.2) if n > 1 else (7.5, 7.2))
    gs = fig.add_gridspec(len(zooms) or 1, 2 if zooms else 1,
                          width_ratios=[1.6, 1] if zooms else [1])
    axes = [fig.add_subplot(gs[:, 0])] + [fig.add_subplot(gs[i, 1]) for i in range(len(zooms))]
    ls = (0, (5, 3)) if ref_dashed else "-"
    for k, ax in enumerate(axes):
        if ref.width_m:
            lft, rgt = _edges(ref, ref.width_m / 2)
            ax.fill(np.r_[_loop(lft)[:, 0], _loop(rgt)[::-1, 0]],
                    -np.r_[_loop(lft)[:, 1], _loop(rgt)[::-1, 1]],
                    color=ref_colour, alpha=0.10, lw=0, zorder=1)
        ax.plot(_loop(ref.points)[:, 0], -_loop(ref.points)[:, 1], color=ref_colour,
                lw=1.4, ls=ls, label=ref_label, zorder=3)
        ax.plot(_loop(frozen.points)[:, 0], -_loop(frozen.points)[:, 1],
                color=C_FROZEN, lw=1.4, label=frozen_label, zorder=4)
        ax.scatter(markers[:, 0], -markers[:, 1], s=16, color=INK, zorder=5,
                   label="FastF1 / MultiViewer corner marker" if k == 0 else None)
        ax.set_aspect("equal")
        ax.tick_params(labelsize=7)
        if k == 0:
            p = frozen.points[0]
            ax.scatter([p[0]], [-p[1]], marker="s", s=30, color=C_FROZEN,
                       edgecolor=SURFACE, lw=1.5, zorder=6)
            ax.annotate("engine s = 0 (sf_idx)", (p[0], -p[1]), xytext=(10, 4),
                        textcoords="offset points", fontsize=8, color=INK_2, ha="left")
            q = ref.points[0] if sf_ref is None else sf_ref
            ax.scatter([q[0]], [-q[1]], marker="s", s=30, color=ref_colour,
                       edgecolor=SURFACE, lw=1.5, zorder=6)
            ax.annotate("reference s = 0 (timing line)", (q[0], -q[1]), xytext=(10, -12),
                        textcoords="offset points", fontsize=8, color=INK_2, ha="left")
            if worst is not None:
                w, val = worst
                ax.annotate(f"max {val:.0f} m", (w[0], -w[1]), xytext=(45, -10),
                            textcoords="offset points", fontsize=8, color=INK,
                            arrowprops=dict(arrowstyle="-", color=INK_2, lw=0.8))
            ax.set_title(title, loc="left")
            ax.set_xlabel("x (m)")
            ax.set_ylabel("-z = FastF1 Y (m)")
            ax.legend(loc="upper left", bbox_to_anchor=(0.0, -0.08), ncol=2, fontsize=8)
        else:
            ztitle, c, half = zooms[k - 1]
            ax.set_xlim(c[0] - half, c[0] + half)
            ax.set_ylim(-c[1] - half, -c[1] + half)
            ax.set_title(ztitle, loc="left", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_profiles(path, rows, title):
    """Stacked panels sharing nothing but the layout: each row is
    (label, s, values, colour, corners, ylabel, ylim, note)."""
    fig, axes = plt.subplots(len(rows), 1, figsize=(11, 2.4 * len(rows)))
    for ax, (label, s, v, colour, corners, ylabel, ylim, note) in zip(np.atleast_1d(axes), rows):
        ax.plot(s, v, color=colour, lw=1.0)
        ax.axhline(0, color=INK_2, lw=0.6)
        for c in corners:
            ax.axvline(c["s"], color=INK_2, lw=0.6, ls=(0, (2, 3)))
            ax.text(c["s"], 1.0, f"T{c['number']}", transform=ax.get_xaxis_transform(),
                    ha="center", va="bottom", fontsize=7, color=INK_2)
        if ylim:
            ax.set_ylim(*ylim)
        ax.set_xlim(0, s.max())
        ax.set_ylabel(ylabel, fontsize=8)
        ax.set_title(label + (f"   |   {note}" if note else ""), loc="left", fontsize=9, pad=12)
        ax.tick_params(labelsize=7)
    np.atleast_1d(axes)[-1].set_xlabel("s along that line (m)")
    fig.suptitle(title, x=0.01, ha="left", fontsize=10, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def clipped(k, lim):
    """Clip for display and say what was clipped, so an off-scale spike is
    labelled rather than silently flattened."""
    i = int(np.argmax(np.abs(k)))
    note = ""
    if abs(k[i]) > lim:
        note = f"off scale: {k[i]:+.3f} /m (R {1 / abs(k[i]):.1f} m) at s {{s:.0f}}"
    return np.clip(k, -lim, lim), note, i


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def strip(d):
    """Drop the private arrays before writing JSON."""
    if isinstance(d, dict):
        return {k: strip(v) for k, v in d.items() if not k.startswith("_")}
    if isinstance(d, list):
        return [strip(v) for v in d]
    return d


def monza(frozen_dir: Path) -> dict:
    ours = load_centre_frame("public/tracks/monza.json")
    ours.width_m = 13.0
    v1 = load_centre_frame("public/tracks/monza_v1.json")
    raw = np.asarray(json.loads((frozen_dir / "Monza_v1.json").read_text())["waypoints"])
    mv = fetch("monza")
    markers = plan_of(mv.corners_xy)
    outline = frame_of_plan(plan_of(mv.outline_xy))

    m = {"lengthM": {"ours": round(ours.length_m, 1), "frozen": round(v1.length_m, 1),
                     "published": 5793.0, "diff": round(v1.length_m - ours.length_m, 1)}}
    m["overlay"] = both_ways(ours, v1, "ours", "frozen")
    m["startFinish"] = sf_offset(ours, v1)
    m["corners"] = [{"number": a["number"], "name": a["name"], "oursS": a["s"], "frozenS": b["s"],
                     "deltaS": round(b["s"] - a["s"], 1)}
                    for a, b in zip(ours.corners, v1.corners)]
    m["markersAreVertices"] = markers_are_vertices(raw, mv.corners_xy)
    m["splineFit"] = spline_sweep(raw, mv.corners_xy)
    m["reproduction"] = reproduction(raw, mv.corners_xy)
    turns = vertex_turns_deg(v1)
    m["vertexTurnDeg"] = {"frozenMaxAbs": round(float(np.abs(turns).max()), 1),
                          "frozenAtS": round(float(v1.s[np.argmax(np.abs(turns))]), 1),
                          "oursMaxAbs": round(float(np.abs(vertex_turns_deg(ours)).max()), 1)}
    m["peaksAtMarkers"] = {"frozen": peaks_at_markers(v1, v1.corners),
                           "ours": peaks_at_markers(ours, ours.corners)}
    m["straights"] = straights(ours, v1)
    m["multiviewerStandIn"] = {"lap": mv.outline_lap, "points": len(mv.outline_xy),
                               "vsOurs": strip(both_ways(ours, outline, "ours", "mv")),
                               "vsFrozen": strip(both_ways(v1, outline, "frozen", "mv")),
                               "lapStartOnOurs": sf_offset(ours, outline, pb=outline.points[0])["bOnA"]}

    ov = m["overlay"]["ours->frozen"]
    worst = (ours.points[np.argmin(np.abs(ours.s - ov["maxAtS"]))], ov["max"])
    zoom = lambda a, b, half: (np.mean([to_world(ours, c["s"]) for c in ours.corners
                                         if a <= c["number"] <= b], axis=0), half)
    plot_overlay(OUT / "monza-overlay.png", ours, "ours (telemetry)", C_OURS, v1,
                 "Monza_v1 (engine)", markers,
                 "Monza: our telemetry centreline vs the engine's Monza_v1", worst=worst,
                 zooms=[("Rettifilo, T1-T2", *zoom(1, 2, 140)),
                        ("Roggia, T4-T5", *zoom(4, 5, 120)),
                        ("Ascari, T8-T10", *zoom(8, 10, 200))])

    k_o, note_o, _ = clipped(ours.curvature, 0.08)
    k_f, note_f, i_f = clipped(v1.curvature, 0.08)
    d_of = m["overlay"]["ours->frozen"]
    plot_profiles(OUT / "monza-curvature.png", [
        ("ours: signed curvature (positive = right)", ours.s, k_o, C_OURS, ours.corners,
         "kappa (1/m)", (-0.085, 0.085), note_o),
        ("Monza_v1: signed curvature - dashed lines are the corner markers' s", v1.s, k_f,
         C_FROZEN, v1.corners, "kappa (1/m)", (-0.085, 0.085),
         note_f.format(s=v1.s[i_f])),
        ("distance from our centreline to Monza_v1 (point-to-polyline)", d_of["_s"], d_of["_d"],
         INK_2, ours.corners, "metres", None, f"p50 {d_of['p50']} m, p90 {d_of['p90']} m, "
                                              f"max {d_of['max']} m"),
    ], "Monza: Monza_v1's curvature is spikes at 132 spline knots, zero between them, largest at the markers")
    return m


def interlagos(frozen_dir: Path) -> dict:
    v2 = load_centre_frame("public/tracks/interlagos_v2.json")
    raw = np.asarray(json.loads((frozen_dir / "interlagos_v2.json").read_text())["waypoints"])
    mv = fetch("interlagos")
    markers = plan_of(mv.corners_xy)
    outline = frame_of_plan(plan_of(mv.outline_xy))
    outline.width_m = 0.0
    steps = np.linalg.norm(np.diff(outline.points, axis=0), axis=1)

    m = {"lengthM": {"frozen": round(v2.length_m, 1), "published": 4309.0,
                     "mvOutline": round(outline.length_m, 1)},
         "multiviewer": {"lap": mv.outline_lap, "points": len(mv.outline_xy),
                         "medianStepM": round(float(np.median(steps)), 1),
                         "maxStepM": round(float(steps.max()), 1),
                         "openingGapM": round(float(np.linalg.norm(outline.points[0] - outline.points[-1])), 1),
                         "datasetYear": mv.year}}
    m["overlay"] = both_ways(outline, v2, "mv", "frozen")
    # The stand-in's first sample is the start of a timed lap - the timing
    # line, to within a sample (validated on Monza: lapStartOnOurs).
    m["timingLine"] = sf_offset(outline, v2, pa=outline.points[0])["aOnB"]
    m["markersAreVertices"] = markers_are_vertices(raw, mv.corners_xy)
    m["splineFit"] = spline_sweep(raw, mv.corners_xy)
    m["reproduction"] = reproduction(raw, mv.corners_xy)
    turns = vertex_turns_deg(v2)
    m["vertexTurnDeg"] = {"frozenMaxAbs": round(float(np.abs(turns).max()), 1),
                          "frozenAtS": round(float(v2.s[np.argmax(np.abs(turns))]), 1)}
    m["peaksAtMarkers"] = {"frozen": peaks_at_markers(v2, v2.corners)}

    ov = m["overlay"]["frozen->mv"]
    worst = (v2.points[np.argmin(np.abs(v2.s - ov["maxAtS"]))], ov["max"])
    plot_overlay(OUT / "interlagos-overlay.png", outline,
                 "MultiViewer lap outline (stand-in)", C_MV, v2, "interlagos_v2 (engine)",
                 markers, "Interlagos: engine interlagos_v2 vs a recorded lap (stand-in reference)",
                 sf_ref=outline.points[0], ref_dashed=True, worst=worst)
    k_f, note_f, i_f = clipped(v2.curvature, 0.08)
    d = m["overlay"]["frozen->mv"]
    plot_profiles(OUT / "interlagos-curvature.png", [
        ("interlagos_v2: signed curvature (positive = right) - dashed lines are the markers' s",
         v2.s, k_f, C_FROZEN, v2.corners, "kappa (1/m)", (-0.085, 0.085),
         note_f.format(s=v2.s[i_f])),
        ("distance from interlagos_v2 to the MultiViewer outline (point-to-polyline)",
         d["_s"], d["_d"], INK_2, v2.corners, "metres", None,
         f"p50 {d['p50']} m, p90 {d['p90']} m, max {d['max']} m"),
    ], "Interlagos: interlagos_v2's curvature is spikes at 180 spline knots, largest at the markers")
    return m


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--frozen-dir", required=True, type=Path)
    args = p.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    metrics = {"monza": monza(args.frozen_dir), "interlagos": interlagos(args.frozen_dir)}
    (OUT / "metrics.json").write_text(json.dumps(strip(metrics), indent=1, ensure_ascii=False),
                                      encoding="utf-8")
    print(json.dumps(strip(metrics), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
