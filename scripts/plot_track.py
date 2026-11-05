"""Matplotlib view of an extracted centreline, with corner numbers annotated.

Debugging geometry in a 2D plot is much easier than in a 3D scene, so this
runs before anything is loaded into Three.js (design doc, section 4).

It can plot either a pipeline stage dump or the final JSON:

    python scripts/plot_track.py --stage .cache/stages/09_centreline.npy \
        --corners .cache/stages/10_corners.json --out .cache/monza.png

    python scripts/plot_track.py --json public/tracks/monza.json \
        --out .cache/monza.png

`--zoom rettifilo` insets the chicane, and `--compare-smoothing` overlays
several Savitzky-Golay settings over it so the window can be chosen by eye
rather than taken on faith.

Stage dumps are in FastF1 plan space (X, Y, Z metres); the JSON is in Three.js
space (x, y up, z). Both are reduced to the same plan view here, so the two
render identically - which is itself a check on `to_three`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")           # write PNGs; no interactive window
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402

import sys                       # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_track import (      # noqa: E402
    MONZA_LENGTH_M,
    polyline_length,
    resample_arclength,
    signed_area,
    smooth_loop,
)

#: Approximate arc length of the Rettifilo chicane, metres, used to frame the
#: zoom. Only a viewport - nothing downstream depends on it.
RETTIFILO_S = 915.0

#: Half-width of the chicane viewport, metres. The chicane displaces the track
#: by ~50 m over ~110 m of arc, so with equal aspect a viewport much wider
#: than this squeezes it into an unreadable sliver.
ZOOM_HALF_SPAN = 170.0


def _window(plan: np.ndarray, spacing: float, lo: float, hi: float
            ) -> np.ndarray:
    """Points between two arc lengths, wrapping around the loop."""
    idx = np.arange(int(lo / spacing), int(hi / spacing)) % len(plan)
    return plan[idx]


def curvature(plan: np.ndarray, spacing: float) -> np.ndarray:
    """Unsigned curvature, 1/m, of a uniformly-spaced closed polyline.

    This is the quantity Savitzky-Golay smoothing actually destroys - two
    windows can look identical in plan view while differing by a third in
    peak curvature, so the comparison plot shows both.
    """
    x, y = plan[:, 0], plan[:, 1]
    dx = (np.roll(x, -1) - np.roll(x, 1)) / (2 * spacing)
    dy = (np.roll(y, -1) - np.roll(y, 1)) / (2 * spacing)
    ddx = (np.roll(x, -1) - 2 * x + np.roll(x, 1)) / spacing ** 2
    ddy = (np.roll(y, -1) - 2 * y + np.roll(y, 1)) / spacing ** 2
    denom = np.power(dx * dx + dy * dy, 1.5)
    denom[denom == 0] = 1e-12
    return np.abs(dx * ddy - dy * ddx) / denom


def load_plan(stage: str | None, json_path: str | None
              ) -> tuple[np.ndarray, list[dict], str]:
    """-> (plan-view (N, 2) in metres, corners, a label for the title).

    Stage arrays are FastF1 plan space, so the plan view is columns (X, Y).
    The JSON is Three.js space, so the plan view is (x, -z) - undoing
    `to_three`, which is why the two plots should be indistinguishable.
    """
    if json_path:
        doc = json.loads(Path(json_path).read_text(encoding="utf-8"))
        three = np.asarray(doc["centerline"], dtype=float)
        plan = np.column_stack([three[:, 0], -three[:, 2]])
        return plan, doc.get("corners", []), "%s %s" % (doc["name"], doc["year"])

    if not stage:
        raise SystemExit("Pass one of --stage or --json.")
    arr = np.load(stage)
    if arr.ndim == 3:            # 04_normalised is (laps, N, 3)
        arr = np.median(arr, axis=0)
    return arr[:, :2], [], Path(stage).stem


def draw_centreline(ax, plan: np.ndarray, corners: list[dict],
                    spacing: float, title: str) -> None:
    ax.plot(plan[:, 0], plan[:, 1], "-", lw=1.6, color="#1f2937", zorder=2)
    ax.plot([plan[-1, 0], plan[0, 0]], [plan[-1, 1], plan[0, 1]],
            "-", lw=1.6, color="#1f2937", zorder=2)

    # Start/finish and the direction of travel, so a reversed lap is obvious.
    ax.plot(plan[0, 0], plan[0, 1], "o", ms=9, color="#dc2626", zorder=5)
    ax.annotate("start/finish\n(s = 0)", plan[0], textcoords="offset points",
                xytext=(12, -28), fontsize=9, color="#dc2626", weight="bold")
    step = max(1, len(plan) // 60)
    tail, head = plan[0], plan[step]
    ax.annotate("", xy=head, xytext=tail,
                arrowprops=dict(arrowstyle="-|>", lw=3, color="#dc2626"),
                zorder=6)

    for c in corners:
        s = c["s"]
        i = int(round(s / spacing)) % len(plan)
        pt = plan[i]
        centroid = plan.mean(axis=0)
        out = pt - centroid
        out = out / max(float(np.linalg.norm(out)), 1e-9) * 60.0
        ax.annotate(str(c["number"]), pt, textcoords="data",
                    xytext=pt + out, ha="center", va="center", fontsize=9,
                    weight="bold", color="#1d4ed8",
                    arrowprops=dict(arrowstyle="-", lw=0.7, color="#93c5fd"))
        ax.plot(pt[0], pt[1], ".", ms=5, color="#1d4ed8", zorder=4)

    ax.set_aspect("equal")
    ax.set_title(title, fontsize=12, weight="bold")
    ax.set_xlabel("metres")
    ax.grid(alpha=0.25, lw=0.5)


def plot_overview(plan: np.ndarray, corners: list[dict], spacing: float,
                  label: str, out: str) -> str:
    length = polyline_length(plan, closed=True)
    area = signed_area(plan)
    sense = "counter-clockwise" if area > 0 else "clockwise"

    fig, ax = plt.subplots(figsize=(11, 8.5), dpi=130)
    draw_centreline(
        ax, plan, corners, spacing,
        "%s  -  %.1f m, %d points @ %.2f m  -  %s (plan view)"
        % (label, length, len(plan), spacing, sense))

    if corners:
        names = [c for c in corners if c.get("name")]
        txt = "\n".join("%2d  %-28s s = %6.1f m"
                        % (c["number"], c["name"], c["s"]) for c in names)
        # Outside the axes: inside, it sits on top of the Parabolica.
        ax.text(1.03, 0.0, txt, transform=ax.transAxes, fontsize=8,
                family="monospace", va="bottom", ha="left",
                bbox=dict(fc="white", ec="#d1d5db", alpha=0.95, pad=6))

    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_rettifilo(plan: np.ndarray, corners: list[dict], spacing: float,
                   label: str, out: str) -> str:
    """Zoom on the first chicane - the feature over-smoothing destroys first.

    Two panels: the plan view, and curvature against s. The chicane can look
    fine in plan view while its curvature peaks have been shaved off, so the
    second panel is the one that actually answers "is this over-smoothed".
    """
    chicane = [c for c in corners if c["number"] in (1, 2)]
    centre_s = (float(np.mean([c["s"] for c in chicane]))
                if chicane else RETTIFILO_S)
    lo, hi = centre_s - ZOOM_HALF_SPAN, centre_s + ZOOM_HALF_SPAN
    seg = _window(plan, spacing, lo, hi)

    fig, (ax, bx) = plt.subplots(
        1, 2, figsize=(13, 7), dpi=130,
        gridspec_kw={"width_ratios": [1.0, 1.25]})

    ax.plot(seg[:, 0], seg[:, 1], "-o", lw=1.8, ms=3.4, color="#1f2937")
    for c in corners:
        if lo <= c["s"] <= hi:
            pt = plan[int(round(c["s"] / spacing)) % len(plan)]
            ax.plot(pt[0], pt[1], "o", ms=8, color="#1d4ed8", zorder=5)
            ax.annotate("%d" % c["number"], pt, textcoords="offset points",
                        xytext=(11, 8), fontsize=11, weight="bold",
                        color="#1d4ed8")
    ax.set_aspect("equal")
    ax.grid(alpha=0.25, lw=0.5)
    ax.set_xlabel("metres")
    ax.set_title("plan view, s = %.0f to %.0f m\n(dots are %.1f m apart)"
                 % (lo, hi, spacing), fontsize=10, weight="bold")

    kappa = curvature(plan, spacing)
    s_axis = np.arange(int(lo / spacing), int(hi / spacing)) * spacing
    bx.plot(s_axis, _window(kappa.reshape(-1, 1), spacing, lo, hi)[:, 0],
            "-", lw=1.8, color="#1f2937")
    for c in corners:
        if lo <= c["s"] <= hi:
            bx.axvline(c["s"], color="#1d4ed8", lw=1.0, ls="--", alpha=0.8)
            bx.annotate("%d %s" % (c["number"], c.get("name") or ""),
                        (c["s"], bx.get_ylim()[1]), xytext=(4, -14),
                        textcoords="offset points", fontsize=8.5,
                        weight="bold", color="#1d4ed8", rotation=90,
                        va="top")
    for radius in (20.0, 50.0):
        bx.axhline(1.0 / radius, color="#9ca3af", lw=0.8, ls=":")
        bx.annotate("r = %.0f m" % radius, (s_axis[0], 1.0 / radius),
                    xytext=(3, 3), textcoords="offset points", fontsize=8,
                    color="#6b7280")
    bx.set_xlabel("s, metres")
    bx.set_ylabel("curvature, 1/m")
    bx.grid(alpha=0.25, lw=0.5)
    bx.set_title("curvature through the chicane\n"
                 "(over-smoothing shows up here first)",
                 fontsize=10, weight="bold")

    fig.suptitle("%s  -  Rettifilo chicane" % label,
                 fontsize=12, weight="bold")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def plot_smoothing_comparison(median_stage: str, spacing: float,
                              grid_m: float, out: str,
                              windows=(9, 15, 21, 31),
                              orders=(2, 3)) -> str:
    """Overlay Savitzky-Golay settings over the Rettifilo, so the window is
    chosen by eye against the chicane rather than asserted."""
    median = np.load(median_stage)
    lo, hi = RETTIFILO_S - ZOOM_HALF_SPAN, RETTIFILO_S + ZOOM_HALF_SPAN
    colours = ["#dc2626", "#16a34a", "#2563eb", "#9333ea"]

    fig, axes = plt.subplots(2, len(orders), figsize=(14, 11), dpi=130)
    axes = np.atleast_2d(axes)

    for col, order in enumerate(orders):
        ax, bx = axes[0, col], axes[1, col]
        raw = resample_arclength(median, spacing)
        seg = _window(raw[:, :2], spacing, lo, hi)
        ax.plot(seg[:, 0], seg[:, 1], "-", lw=4.0, color="#cbd5e1",
                label="unsmoothed median", zorder=1)
        s_axis = np.arange(int(lo / spacing), int(hi / spacing)) * spacing
        bx.plot(s_axis,
                _window(curvature(raw[:, :2], spacing).reshape(-1, 1),
                        spacing, lo, hi)[:, 0],
                "-", lw=3.0, color="#cbd5e1", label="unsmoothed median")

        for colour, w in zip(colours, windows):
            pts = resample_arclength(smooth_loop(median, w, order), spacing)
            tag = "window %d  (%.0f m)" % (w, w * grid_m)
            ax.plot(*_window(pts[:, :2], spacing, lo, hi).T, "-", lw=1.6,
                    color=colour, label=tag, zorder=2)
            k = curvature(pts[:, :2], spacing).reshape(-1, 1)
            bx.plot(s_axis, _window(k, spacing, lo, hi)[:, 0], "-", lw=1.6,
                    color=colour, label=tag)

        ax.set_aspect("equal")
        ax.grid(alpha=0.25, lw=0.5)
        ax.set_title("polyorder %d  -  plan view" % order,
                     fontsize=11, weight="bold")
        ax.legend(fontsize=8, loc="best")

        for radius in (20.0, 50.0):
            bx.axhline(1.0 / radius, color="#9ca3af", lw=0.8, ls=":")
            bx.annotate("r = %.0f m" % radius, (s_axis[0], 1.0 / radius),
                        xytext=(3, 3), textcoords="offset points",
                        fontsize=8, color="#6b7280")
        bx.grid(alpha=0.25, lw=0.5)
        bx.set_xlabel("s, metres")
        bx.set_ylabel("curvature, 1/m")
        bx.set_title("polyorder %d  -  curvature" % order,
                     fontsize=11, weight="bold")
        bx.legend(fontsize=8, loc="best")

    fig.suptitle("Savitzky-Golay window vs the Rettifilo chicane\n"
                 "The plan views barely differ; the curvature traces are "
                 "where over-smoothing shows.",
                 fontsize=12, weight="bold")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--stage", default=None, help="a .npy stage dump")
    p.add_argument("--json", default=None, help="an extracted track JSON")
    p.add_argument("--corners", default=None,
                   help="10_corners.json, when plotting a stage dump")
    p.add_argument("--out", default=".cache/monza_centreline.png")
    p.add_argument("--zoom", choices=["rettifilo"], default=None)
    p.add_argument("--compare-smoothing", action="store_true")
    p.add_argument("--median-stage", default=".cache/stages/05_median.npy")
    p.add_argument("--n-resample", type=int, default=2000)
    args = p.parse_args(argv)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    if args.compare_smoothing:
        out = plot_smoothing_comparison(
            args.median_stage, spacing=5.0,
            grid_m=MONZA_LENGTH_M / args.n_resample, out=args.out)
        print("wrote %s" % out)
        return 0

    plan, corners, label = load_plan(args.stage, args.json)
    if args.corners:
        corners = json.loads(Path(args.corners).read_text(encoding="utf-8"))
    spacing = polyline_length(plan, closed=True) / len(plan)

    if args.zoom == "rettifilo":
        out = plot_rettifilo(plan, corners, spacing, label, args.out)
    else:
        out = plot_overview(plan, corners, spacing, label, args.out)
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
