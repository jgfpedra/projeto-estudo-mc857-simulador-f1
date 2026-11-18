"""FastF1 session -> (s, d) replay JSON.

Implements section 6B of docs/3d-design.md: project real position samples onto
the committed centreline to recover `(s, d)` per car per timestamp, so the
viewer can replay a real session through the same `(s, d) -> world` path the
synthetic field uses.

A sibling of `extract_track.py`, not an extension of it. Track geometry and
session replay are different artifacts with different lifetimes: the centreline
is extracted once and committed forever, a replay is one session's worth of
motion. Shared helpers are imported.

The inverse of `toWorld`
------------------------
This script's one interesting function is `foot_on_segment`, which lives in
`centreline.py` so that `extract_track.py` places corner markers with the same
code. The renderer
places a car at

    toWorld(s, d) = c(s) + d * rhat(s)

where `c` is the linearly-interpolated centreline and `rhat` is built from the
*interpolated* tangent (see `src/track/frame.ts`, `sampleAt`). Recovering
`(s, d)` from a world point therefore means solving

    f(t) = (p - c(t)) . that(t) = 0 ,   then   d = (p - c(t)) . rhat(t)

on the containing segment. Note what this is *not*: it is not the distance to
the nearest point of the polyline. `project_naive` below computes that - it is
what corner markers used to be placed with - and it is wrong here, because the
segment normal and `rhat` differ by up to 7.93 deg on Monza: 0.891 m of
round-trip error at the 6.5 m track half-width. Check N measures both.

Because `y` is identically 0 on the centreline, `rhat` and `that` span the
plane and the solution above reproduces `p` *exactly* rather than
approximately. The round trip is an identity to float64 precision, not an
approximation with a tolerance to argue about.

Coordinate frames
-----------------
Everything here runs in **Three.js plan space**: columns `(x, z)` of the
committed JSON, which is `PLAN_COLS["three"] = (0, 2)`. Not `(0, 1)` - that is
the elevation axis and on a flat circuit it silently halves every length
(CLAUDE.md). The geometry is read from `public/tracks/monza.json` rather than
re-derived from FastF1, because the viewer reads that file and a round trip
against a differently-derived centreline would measure the difference between
two centrelines instead of the projection.

The vertical channel is dropped at projection and reported, never asserted on:
telemetry `Z` at Monza sits ~188 m above sea level while the committed
centreline's `y` is 0 by construction (`--elevation zero`), so a 3-D residual
would measure that datum and nothing about the projection.

Porting to another circuit
--------------------------
The one thing that will not transfer is the search window. If a circuit's
centreline comes close to itself within the window - a street circuit, or Spa's
Bus Stop - the answer is *not* a wider window, because width is what buys the
ambiguity the window exists to prevent. It is a better predictor: the measured
gain from anchoring on the previous sample to a velocity prediction is a factor
of 436, and a constant-acceleration predictor is the next step. Keep the global
fallback under a monotonicity veto.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_track import (            # noqa: E402
    CheckFailure,
    StageWriter,
    enable_cache,
    load_session,
    run_checks,
)
# The frame and its inverse live in `centreline.py`, shared with
# `extract_track.py`'s corner markers. Re-exported here under their old names.
from centreline import (               # noqa: E402,F401
    NEWTON_STEPS,
    PLAN,
    SEARCH_HALF_SEGMENTS,
    CentreFrame,
    _foot_f,
    _perp,
    _unit,
    brackets,
    curvature_at,
    foot_on_segment,
    load_centre_frame,
    project_global,
    project_windowed,
    sample_at,
    segment_index,
    to_world,
    unwrap_near,
    wrap_s,
)

# --------------------------------------------------------------------------
# Reference constants
# --------------------------------------------------------------------------

#: Physical bound on along-track speed, m/s. Monza's real peak is ~98; anything
#: above this is a position-stream glitch, not a car. See `repair_jumps`.
MAX_SPEED_MPS = 105.0

#: Timestamp jitter in the position stream, seconds.
#:
#: **The single most important measured fact about this data.** The positions are
#: good; their timestamps are not. Consecutive samples routinely imply 130-150
#: m/s against a real Monza peak near 98, and always in pairs - a fast step
#: followed by a slow one - because the pair's *timestamps* are off, not its
#: coordinates. Measured over one driver's race: per-step implied speed exceeds
#: 105 m/s for 5.75% of steps, but over a 1 s baseline **0.00%** do, with a
#: maximum of 106.5 m/s. Timestamps arrive quantised to 20 ms with roughly this
#: much scatter about the true sampling instant.
#:
#: Two consequences run through the whole script. Nothing should be rejected on
#: a per-step speed test - that discards good positions for having an imprecise
#: clock, and an earlier cut of this script threw away 6.5% of the race that
#: way. And `s` has to be *estimated* rather than interpolated, because linear
#: interpolation through jittery timestamps propagates the jitter into the
#: output as +/- 7 m of along-track position at racing speed.
JITTER_S = 0.12

#: Position-noise allowance on the outlier guard, metres. Added to the physical
#: bound rather than folded into it, so the bound stays a statement about cars
#: and this stays a statement about measurement.
JUMP_SLACK_M = 2.0

#: Smoothing weight for the spline that turns jittery samples into `s` on the
#: output grid.
#:
#: The penalty in `scipy.interpolate.make_smoothing_spline`, which minimises
#: `sum (s - f)^2 + lam * integral f''^2`. **Not dimensionless** - it is tied
#: to seconds and metres, so it would need re-tuning if either unit changed.
#:
#: Chosen as the *least* smoothing for which no grid step is physically
#: impossible. Measured over the committed window, 19 cars x 2243 samples,
#: against the `MAX_SPEED_MPS` bound and FastF1's independent `Speed` channel:
#:
#:     lam    steps over 105 m/s   speed sd   departure from raw
#:     0.25        0.049%            2.47 m/s      20.7 m
#:     0.40        0.021%            2.35          21.3
#:     0.60        0.012%            2.30          21.8
#:     0.80        0.009%            2.30          22.1
#:     1.20        0.000%            2.37          23.0
#:     2.00        0.000%            2.57          24.2
#:
#: 1.2 costs almost nothing against the best agreement available (2.37 against
#: 2.30 m/s) and for the noisiest car it is actually better, because that car's
#: scatter is what the looser settings were following. Braking survives: the
#: minimum speed through the Rettifilo lands within 1 m/s of the reference
#: channel on every car checked. |acceleration| p99 comes out 20% below the
#: reference's, which costs nothing here - no part of the viewer consumes
#: longitudinal acceleration, and the camera's roll is driven by curvature and
#: speed squared.
#:
#: A *spline* rather than a window filter or a local fit, and the reason is
#: specific: a fit evaluated independently at each grid point has no reason to
#: agree with its neighbour, so the fitted series carries fit-to-fit wiggle
#: that differentiates into noise. Local quadratics over +/-1.1 s left
#: 0.14-0.88% of grid steps implying over 105 m/s - a car gaining a couple of
#: metres in one frame and losing them in the next - and tricube weighting made
#: it worse rather than better. One spline over the whole series has no such
#: seam. It also made the speed channel's extra smoothing unnecessary: a plain
#: central difference of the committed `s` now matches the independent channel
#: as well as any boxcar did (sd 1.99 against 2.02), so the viewer does no
#: smoothing at all and `speed` is
#: *exactly* `d(committed s)/dt`.
SMOOTH_LAMBDA = 1.2


#: Lateral offset above which a sample is in the pit lane rather than on the
#: track, metres. Monza's pit lane runs parallel to the start of the main
#: straight at d ~ +18 m, so anything past this is a different regime and is
#: reported separately from the `d` distribution.
PIT_ABS_D_M = 8.0

#: Where corner regions end, metres of arc either side of the corner's own `s`.
#: Samples outside every window are "straight". Chicane corners are 25-100 m
#: apart, so regions are assigned by *nearest* corner and split at the midpoint
#: rather than overlapping.
CORNER_SPAN_M = 100.0


# --------------------------------------------------------------------------
# The naive inverse, kept as check N's baseline
# --------------------------------------------------------------------------

def project_naive(frame: CentreFrame, p: np.ndarray) -> tuple[float, float]:
    """The nearest-point projection, for comparison only. Not used for output.

    This is what `extract_track.py`'s corner markers used before they moved to
    `centreline.project_global`, kept so check N can measure what it costs: `d` perpendicular to
    the *segment* rather than along `rhat`, and `s` from the fractional index
    times a nominal spacing. Both are wrong for an inverse of `toWorld`, and
    the point of keeping it is to print the size of the error next to zero.
    """
    a = frame.points
    b = np.roll(a, -1, axis=0)
    ab = b - a
    ap = p[None, :] - a
    denom = np.einsum("ij,ij->i", ab, ab)
    denom[denom == 0] = 1e-12
    t = np.clip(np.einsum("ij,ij->i", ap, ab) / denom, 0.0, 1.0)
    proj = a + t[:, None] * ab
    dist = np.linalg.norm(p[None, :] - proj, axis=1)
    i = int(np.argmin(dist))
    spacing = frame.length_m / len(a)
    sign = np.sign(np.cross(ab[i], p - proj[i]))
    signed = dist[i] * (sign if sign else 1.0)
    return float((i + t[i]) * spacing), float(signed)


# --------------------------------------------------------------------------
# Session -> per-car position series
# --------------------------------------------------------------------------

def car_positions(session, drv: str):
    """One driver's position stream -> (t seconds, plan (M, 2) metres, z metres).

    The same filtering as `lap_positions` in `extract_track.py` - `OnTrack`
    only, finite rows, exact `(0, 0)` samples dropped (CLAUDE.md gotcha), the
    one `/ 10` conversion - but masking the DataFrame rather than the array, so
    the time column survives. That is the whole reason this is a sibling script
    and not a reuse: a replay is parameterised by time and the extractor throws
    time away.

    `to_three` is applied here: `three.x = ff1.X`, `three.z = -ff1.Y`, and the
    minus is not optional. The elevation channel `ff1.Z` is returned separately
    and never projected - see the module docstring.
    """
    pos = session.pos_data[drv]
    if "Status" in pos.columns:
        pos = pos[pos["Status"] == "OnTrack"]

    t = pos["SessionTime"].dt.total_seconds().to_numpy(dtype=float)
    xyz = pos[["X", "Y", "Z"]].to_numpy(dtype=float)

    ok = np.isfinite(xyz).all(axis=1) & np.isfinite(t)
    ok &= ~((xyz[:, 0] == 0.0) & (xyz[:, 1] == 0.0))
    t, xyz = t[ok], xyz[ok] / 10.0

    order = np.argsort(t, kind="stable")
    t, xyz = t[order], xyz[order]
    keep = np.concatenate([[True], np.diff(t) > 0])
    t, xyz = t[keep], xyz[keep]

    plan = np.column_stack([xyz[:, 0], -xyz[:, 1]])
    return t, plan, xyz[:, 2]


# --------------------------------------------------------------------------
# Projection of a whole path, with the predicted window
# --------------------------------------------------------------------------

@dataclass
class TrackPath:
    """One car's motion in `(s, d)`. `s` is unwrapped and never wrapped again.
    """

    t: np.ndarray             # seconds, session time
    s: np.ndarray             # unwrapped arc length, metres
    d: np.ndarray             # lateral offset, metres, + = right of travel
    residual: np.ndarray      # |f| at the solved foot point, metres
    good: np.ndarray          # bool: False where the sample was repaired
    fallbacks: int            # samples the window missed, taken globally
    z: np.ndarray             # discarded elevation, carried only to report it


def project_path(t: np.ndarray, plan: np.ndarray, z: np.ndarray,
                 frame: CentreFrame, *, half: int = SEARCH_HALF_SEGMENTS,
                 max_speed_mps: float = MAX_SPEED_MPS,
                 max_reverse_mps: float = 2.0,
                 slack_m: float = JUMP_SLACK_M) -> TrackPath:
    """Project a whole position stream, predict-then-correct.

    Two things happen per sample. The window is centred on `s_anchor + v * dt`,
    a velocity prediction rather than the previous sample, which is what keeps
    the half-width at 40 m instead of 300 (see `project_windowed`). And the
    result is sanity-checked against a physical speed bound before it is
    allowed to become the next anchor - so a glitched position cannot poison
    the prediction for the samples after it, which is the failure that turns
    one bad sample into a bad second.

    The guard allows for `JITTER_S` of timestamp scatter, which is what makes
    it a guard rather than a shredder. Measured over the race window of all
    twenty cars it rejects **0 of 356,040 samples**: this session has no
    position outliers at all, only a jittery clock. It stays because a session
    with a genuine dropout should not be allowed through silently, and because
    its firing count is the cheapest possible statement that the data was
    clean.
    """
    n = len(t)
    s = np.zeros(n)
    d = np.zeros(n)
    res = np.zeros(n)
    good = np.zeros(n, dtype=bool)
    fallbacks = 0

    s[0], d[0], res[0] = project_global(frame, plan[0])
    good[0] = True
    s_anchor, t_anchor, v = s[0], t[0], 0.0

    for k in range(1, n):
        dt = t[k] - t_anchor
        predict = s_anchor + v * dt
        sw, dk, rk, fb = project_windowed(frame, plan[k], predict, half)
        fallbacks += int(fb)
        su = unwrap_near(sw, predict, frame.length_m)

        # On *displacement* over a jitter-widened interval, never on a speed
        # ratio. A ratio test rejects honest samples for arriving close
        # together: `dt` has a p1 of 0.06 s, and a timestamp 0.12 s early turns
        # an ordinary 16 m step into 137 m/s. Widening the interval by the
        # jitter asks the only question worth asking - could a car have covered
        # this ground at all - and leaves the jitter itself to `fit_to_grid`.
        step = su - s_anchor
        reach = dt + JITTER_S
        lo = -(max_reverse_mps * reach + slack_m)
        hi = max_speed_mps * reach + slack_m
        if lo <= step <= hi:
            v_inst = step / dt if dt > 0 else 0.0
            s[k], d[k], res[k], good[k] = su, dk, rk, True
            # Mild low-pass on the predictor: a single noisy step should not
            # swing the next window, and the window is wide enough not to need
            # the prediction to be sharp.
            v = 0.5 * v + 0.5 * v_inst
            s_anchor, t_anchor = su, t[k]
        else:
            # Kept for reporting; `np.interp` overwrites it below.
            s[k], d[k], res[k] = su, dk, rk

    # Repair: interpolate the rejected samples from the accepted ones. Done on
    # `s` and `d` rather than on the raw position, so a repaired sample is a
    # point *on the track* at the right arc length rather than a smoothed
    # coordinate that would then have to be projected again.
    if good.sum() >= 2:
        s = np.interp(t, t[good], s[good])
        d = np.interp(t, t[good], d[good])

    return TrackPath(t=t, s=s, d=d, residual=res, good=good,
                     fallbacks=fallbacks, z=z)


def clip_path(path: TrackPath, t0: float, t1: float) -> TrackPath:
    """Restrict a path to a time window, keeping everything index-aligned."""
    m = (path.t >= t0) & (path.t <= t1)
    return TrackPath(t=path.t[m], s=path.s[m], d=path.d[m],
                     residual=path.residual[m], good=path.good[m],
                     fallbacks=path.fallbacks, z=path.z[m])


def fit_to_grid(path: TrackPath, hz: float, t0: float, samples: int,
                lam: float = SMOOTH_LAMBDA) -> TrackPath:
    """Estimate `(s, d)` on a uniform `hz` grid. Not an interpolation.

    Uniform because the viewer then needs no search at all - `index =
    floor((t - t0) * hz)` - and `hz` divides a second exactly, so a timeline
    tick is an integer number of samples.

    **`s` and `d` are resampled against different variables, and that is the
    point.** `s` is smoothed against *time*, because the error being removed is
    timestamp jitter and jitter lives in the time domain. `d` is interpolated
    against *arc length*, because `d` is a function of where the car is on the
    track rather than of when: the systematic part of `d` swings 1.7 m across
    the 25 m of the Rettifilo, and the smoothing scale is over 100 m of track
    at racing speed, so smoothing `d` in time would flatten exactly the feature
    the lateral report exists to measure. Measured: the systematic profile
    spans
    -0.93 to +0.80 m resampled against arc length, against -0.77 to +0.67
    smoothed in time - 13% of the signal, thrown away for nothing.

    Monotonicity is enforced on the `s` axis before interpolating `d`, because
    a stationary car makes `s` flat and `np.interp` needs its `xp` increasing.
    """
    from scipy.interpolate import make_smoothing_spline

    grid = t0 + np.arange(samples) / hz

    t_src, s_src = path.t, path.s
    uniq = np.concatenate([[True], np.diff(t_src) > 1e-9])
    t_src, s_src = t_src[uniq], s_src[uniq]
    if len(t_src) >= 8:
        s_fit = make_smoothing_spline(t_src, s_src, lam=lam)(grid)
    else:
        s_fit = np.interp(grid, t_src, s_src)

    mono = np.maximum.accumulate(path.s)
    keep = np.concatenate([[True], np.diff(mono) > 1e-9])
    d_fit = (np.interp(s_fit, mono[keep], path.d[keep]) if keep.sum() >= 2
             else np.full(samples, float(path.d[0])))

    return TrackPath(t=grid, s=s_fit, d=d_fit,
                     residual=np.interp(grid, path.t, path.residual),
                     good=np.interp(grid, path.t,
                                    path.good.astype(float)) > 0.999,
                     fallbacks=path.fallbacks,
                     z=np.interp(grid, path.t, path.z))


# --------------------------------------------------------------------------
# Derived channels
# --------------------------------------------------------------------------

def derive_speed(s: np.ndarray, hz: float) -> np.ndarray:
    """Along-track speed from the committed `s`, m/s. Mirrored in `load.ts`.

    A central difference and nothing else. The speed channel is NOT committed -
    the viewer derives it - so `speed` is *exactly* the rate the committed `s`
    advances, which is what `rig.ts` feeds forward into the chase camera's
    anchor. A smoothed speed would be a second opinion about the same motion,
    and the two would disagree.

    No smoothing is needed because `s` arrives from a smoothing spline already.
    Measured against FastF1's independent `Speed` channel, adding a boxcar
    changed the agreement from sd 1.99 to 2.02 m/s - i.e. not at all - so the
    constant that would have had to be kept identical in two languages is
    simply absent.
    """
    return np.gradient(s) * hz


def lap_boundaries(lapinfo: Sequence[tuple], path: TrackPath, t0: float):
    """Official lap boundaries inside the window -> (numbers, s, t).

    `s` rather than a sample index, deliberately. An index silently changes
    meaning if `--hz` changes; `s` is the unit everything else is in, so the
    viewer recovers the lap at any sample with one `searchSorted` and no index
    arithmetic. It also makes the disagreement between the official timing
    boundary and the geometric `s = 0` crossing directly readable as
    `s[k] - k * L`, which is what check Q reports - `startFinishS` is point 0
    of the median lap, not the surveyed painted line (design doc section 5).
    """
    nums: list[int] = []
    ss: list[float] = []
    ts: list[float] = []
    for num, start, _ in lapinfo:
        if start < path.t[0] or start > path.t[-1]:
            continue
        nums.append(int(num))
        ss.append(float(np.interp(start, path.t, path.s)))
        ts.append(float(start - t0))
    return nums, ss, ts


def assign_regions(frame: CentreFrame, s: np.ndarray,
                   span_m: float = CORNER_SPAN_M) -> np.ndarray:
    """Label every sample with the nearest corner's number, or 0 for a straight.

    By *nearest* corner rather than by overlapping windows, so the Rettifilo's
    two corners 55 m apart and Ascari's three 95 m apart split at their
    midpoints instead of double-counting the samples between them.
    """
    sw = np.asarray(wrap_s(frame, s))
    cs = np.array([c["s"] for c in frame.corners], dtype=float)
    nums = np.array([c["number"] for c in frame.corners], dtype=int)
    gap = np.abs(sw[:, None] - cs[None, :])
    gap = np.minimum(gap, frame.length_m - gap)
    near = np.argmin(gap, axis=1)
    out = nums[near]
    out[gap[np.arange(len(sw)), near] > span_m] = 0
    return out


def region_name(frame: CentreFrame, number: int) -> str:
    if number == 0:
        return "straight"
    for c in frame.corners:
        if c["number"] == number:
            return "T%d %s" % (number, c["name"])
    return "T%d" % number


# --------------------------------------------------------------------------
# Encoding - integer channels
# --------------------------------------------------------------------------

def encode_car(path: TrackPath) -> tuple[float, list[int], list[int]]:
    """`(s, d)` -> `(s0M, dsMm, dCm)`, the committed integer channels.

    `s` goes out as millimetre *deltas* from a float origin, `d` as absolute
    centimetres. Deltas because at 5 Hz a step is 0-20 m, i.e. five digits in
    millimetres against the seven or eight an absolute arc length needs after
    five laps - which is most of the difference between a 375 KB file and a
    591 KB one.

    Millimetres rather than centimetres because the deltas accumulate: a
    centimetre quantisation random-walks about 0.33 m of absolute `s` over five
    laps, and a millimetre one about 0.02 m, for one extra digit. Check U
    measures the realised drift rather than trusting the estimate.
    """
    s0 = round(float(path.s[0]), 2)
    ds_mm = np.round(np.diff(path.s) * 1000.0).astype(np.int64)
    d_cm = np.round(path.d * 100.0).astype(np.int64)
    return s0, [int(v) for v in ds_mm], [int(v) for v in d_cm]


def decode_s(s0: float, ds_mm: Sequence[int]) -> np.ndarray:
    """The viewer's own decode, so the checks measure what will actually load.
    """
    steps = np.asarray(ds_mm, dtype=float) / 1000.0
    return s0 + np.concatenate([[0.0], np.cumsum(steps)])


# --------------------------------------------------------------------------
# The lateral-offset report - section 6B's "is the median good enough"
# --------------------------------------------------------------------------

def self_approach(frame: CentreFrame,
                  window_m: float) -> tuple[float, float, float]:
    """Closest the centreline comes to itself, for pairs separated by > `window_m`.

    The upper bound on a safe search window, and the thing that decides whether
    a *global* search could ever pick the wrong stretch: a sample at offset `d`
    can only be mis-assigned to a stretch that is within `2 * |d|` of its own,
    so this number halved is the largest offset the geometry tolerates.
    """
    p = frame.points
    dist = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=2)
    gap = np.abs(frame.s[:, None] - frame.s[None, :])
    gap = np.minimum(gap, frame.length_m - gap)
    mask = gap > window_m
    if not mask.any():
        return float("inf"), 0.0, 0.0
    k = int(np.argmin(np.where(mask, dist, np.inf)))
    i, j = np.unravel_index(k, dist.shape)
    return float(dist[mask].min()), float(frame.s[i]), float(frame.s[j])


def lateral_report(frame: CentreFrame, cars: list[dict],
                   pit_abs_d: float = PIT_ABS_D_M) -> dict:
    """Everything the `d` distribution report prints, as plain numbers.

    The point of the split is that the centreline is a median of racing lines
    rather than a survey, so `d` is expected to carry a *systematic* component
    - a bias as a function of `s` that every car shares - on top of per-car
    spread. Reporting one number for both would hide which it is, and they have
    different consequences: a shared bias is a centreline that could be
    improved, per-car spread is cars actually racing.
    """
    s = np.concatenate([c["raw"].s for c in cars])
    d = np.concatenate([c["raw"].d for c in cars])
    pit = np.abs(d) > pit_abs_d
    on, d_on, s_on = ~pit, d[~pit], s[~pit]

    # The systematic part: mean d per centreline sample, shared by the field.
    idx = np.asarray(segment_index(frame, np.asarray(wrap_s(frame, s_on))))
    prof = np.full(len(frame.points), np.nan)
    counts = np.bincount(idx, minlength=len(frame.points))
    sums = np.bincount(idx, weights=d_on, minlength=len(frame.points))
    live = counts > 0
    prof[live] = sums[live] / counts[live]
    resid = d_on - prof[idx]

    worst_lo = int(np.nanargmin(prof))
    worst_hi = int(np.nanargmax(prof))
    explained = (1.0 - float(np.var(resid)) / float(np.var(d_on))
                 if len(d_on) else 0.0)

    reg = assign_regions(frame, s_on)
    regions = []
    for number in [c["number"] for c in frame.corners] + [0]:
        sel = reg == number
        if not sel.any():
            continue
        v = d_on[sel]
        regions.append({
            "number": number, "name": region_name(frame, number),
            "n": int(sel.sum()),
            "mean": float(v.mean()), "sd": float(v.std()),
            "p95abs": float(np.percentile(np.abs(v), 95)),
            "max_abs": float(np.abs(v).max()),
        })

    per_driver = []
    for c in cars:
        dv = c["raw"].d
        sel = np.abs(dv) <= pit_abs_d
        if not sel.any():
            continue
        per_driver.append({"code": c["code"], "mean": float(dv[sel].mean()),
                           "sd": float(dv[sel].std()),
                           "p99abs": float(np.percentile(np.abs(dv[sel]),
                                                         99))})

    return {
        "n_total": int(len(d)), "n_on": int(on.sum()), "n_pit": int(pit.sum()),
        "pit_frac": float(pit.mean()) if len(d) else 0.0,
        "pit_d_p50": float(np.median(d[pit])) if pit.any() else float("nan"),
        "pit_s_lo": (float(np.percentile(wrap_s(frame, s[pit]), 1))
                    if pit.any() else float("nan")),
        "pit_s_hi": (float(np.percentile(wrap_s(frame, s[pit]), 99))
                    if pit.any() else float("nan")),
        "mean": float(d_on.mean()), "sd": float(d_on.std()),
        "pct": [float(x) for x in
                np.percentile(d_on, [0.1, 1, 5, 25, 50, 75, 95, 99, 99.9])],
        "max_abs": float(np.abs(d_on).max()),
        "profile_sd": float(np.nanstd(prof)),
        "profile_lo": float(prof[worst_lo]),
        "profile_lo_s": float(frame.s[worst_lo]),
        "profile_hi": float(prof[worst_hi]),
        "profile_hi_s": float(frame.s[worst_hi]),
        "profile_max_abs": float(np.nanmax(np.abs(prof))),
        "profile_p90_abs": float(np.nanpercentile(np.abs(prof), 90)),
        "explained": explained,
        "resid_sd": float(resid.std()),
        "resid_p99": float(np.percentile(np.abs(resid), 99)),
        "regions": regions, "per_driver": per_driver,
    }


def print_lateral_report(rep: dict) -> None:
    print("\n  Lateral offset `d` across the field")
    print("  " + "-" * 74)
    print("  samples    %d on track, %d in the pit lane (%.2f%%)"
          % (rep["n_on"], rep["n_pit"], rep["pit_frac"] * 100))
    if rep["n_pit"]:
        print("  pit lane   d p50 %+.2f m over s %.0f..%.0f m - reported "
              "separately, never folded into the mean below"
              % (rep["pit_d_p50"], rep["pit_s_lo"], rep["pit_s_hi"]))
    p = rep["pct"]
    print("  on track   mean %+.4f m   sd %.4f m   max |d| %.3f m"
          % (rep["mean"], rep["sd"], rep["max_abs"]))
    print("             p0.1 %+.3f  p1 %+.3f  p5 %+.3f  p25 %+.3f  p50 %+.3f"
          % tuple(p[:5]))
    print("             p75 %+.3f  p95 %+.3f  p99 %+.3f  p99.9 %+.3f"
          % tuple(p[5:]))
    print("  systematic mean d per centreline sample: sd %.4f m, range %+.3f m at "
          "s=%.0f to %+.3f m at s=%.0f"
          % (rep["profile_sd"], rep["profile_lo"], rep["profile_lo_s"],
             rep["profile_hi"], rep["profile_hi_s"]))
    print("             |profile| p90 %.3f m, max %.3f m - explains %.1f%% of the "
          "variance of d" % (rep["profile_p90_abs"], rep["profile_max_abs"],
                             rep["explained"] * 100))
    print("  residual   after removing the shared profile: sd %.4f m, p99 %.3f m"
          % (rep["resid_sd"], rep["resid_p99"]))
    print("\n  %-34s %7s %8s %7s %8s" % ("region", "n", "mean", "sd", "max|d|"))
    for r in sorted(rep["regions"], key=lambda r: -abs(r["mean"])):
        print("  %-34s %7d %+8.3f %7.3f %8.3f"
              % (r["name"][:34], r["n"], r["mean"], r["sd"], r["max_abs"]))
    drivers = rep["per_driver"]
    if drivers:
        means = [x["mean"] for x in drivers]
        sds = [x["sd"] for x in drivers]
        print("  per driver mean d spans %+.4f .. %+.4f m, sd spans %.4f .. %.4f m "
              "across %d cars" % (min(means), max(means), min(sds), max(sds),
                                  len(drivers)))


# --------------------------------------------------------------------------
# The committed documents
# --------------------------------------------------------------------------

def build_doc(frame: CentreFrame, cars: list[dict], *, name: str, year: int,
              session: str, hz: float, t0: float, samples: int,
              from_lap: int, to_lap: int, pit_abs_d: float) -> dict:
    """The replay artifact. Schema per section 6B of docs/3d-design.md.

    Columnar per car rather than the row-oriented draft in the design doc: at
    twenty cars and five laps that draft is 42,500 repeated key sets, which is
    several times the size of the numbers it carries.

    Two things are deliberately absent. There is no speed channel - `load.ts`
    derives it, so it cannot disagree with the rate `s` advances. And there is
    no colour: the viewer assigns `PALETTE[floor(i / 2) % 10]` by car index
    exactly as `buildField` does, so the palette stays in one place and
    CLAUDE.md's rule about liveries stays in the file that renders.

    Cars are ordered by classified position at the window start, so the swatch
    row reads as a running order and the colour a driver gets is deterministic.
    """
    return {
        "name": name,
        "year": year,
        "session": session,
        # Echoed so `parseReplay` can refuse a replay projected against a
        # different centreline - it would wrap wrongly and look almost right.
        "trackLengthM": round(frame.length_m, 4),
        "hz": hz,
        "t0S": round(t0, 3),
        "samples": samples,
        "fromLap": from_lap,
        "toLap": to_lap,
        "pitAbsDM": pit_abs_d,
        "cars": [
            {
                "code": c["code"],
                "name": c["name"],
                "s0M": c["s0"],
                "dsMm": c["ds_mm"],
                "dCm": c["d_cm"],
                "lapNumber": c["lap_numbers"],
                "lapStartS": [round(v, 2) for v in c["lap_start_s"]],
                "lapStartT": [round(v, 3) for v in c["lap_start_t"]],
            }
            for c in cars
        ],
    }


#: Lateral strata the round-trip fixture is sampled from, metres.
#:
#: Stratified rather than uniform in time, because on-track |d| has a median
#: near 0.04 m: a fixture drawn uniformly would be almost entirely samples
#: where the lateral offset is too small to exercise the sign of `right`. The
#: bands here reach the largest offset the committed window contains, 1.03 m.
#:
#: The margin against a sign error comes from the tolerance rather than from
#: the strata, and that is worth being explicit about. A flipped `right` moves
#: the
#: world point by `2 * |d|`, so even the smallest band moves it ~0.07 m against
#: a test tolerance of 1e-4 m. The pit lane, where `|d| ~ 18 m`, would give a
#: far larger margin but cannot appear here: the window picker excludes any car
#: that visits it, which is the whole point of a clean green-flag window.
FIXTURE_STRATA = ((0.0, 0.1), (0.1, 0.5), (0.5, 1.3))


def build_fixture(frame: CentreFrame, cars: list[dict], *, per_stratum: int = 40,
                  seam_rows: int = 20, seam_span_m: float = 30.0) -> dict:
    """Committed input for `src/replay/roundtrip.test.ts`.

    Rows of `{w, s, d}` where `w` is the *plan* pair only. Storing two columns
    rather than three makes the dropped vertical channel structural instead of
    a remark in a docstring: there is no third number for a reader to wonder
    about.

    Values keep six decimals, not the integer quantisation of the committed
    replay. The test is an identity assertion - the projection is the exact
    inverse of `toWorld` - so the fixture must not be the thing that limits it.
    """
    rng = np.random.default_rng(20240901)       # the race date; deterministic
    s_all = np.concatenate([c["raw"].s for c in cars])
    d_all = np.concatenate([c["raw"].d for c in cars])
    w_all = np.array([to_world(frame, s, d) for s, d in zip(s_all, d_all)]) \
        if False else None                       # never: built per pick below

    rows: list[dict] = []

    def take(idx: np.ndarray, count: int, label: str) -> None:
        if len(idx) == 0:
            return
        pick = rng.choice(idx, size=min(count, len(idx)), replace=False)
        for k in pick:
            s, d = float(s_all[k]), float(d_all[k])
            w = to_world(frame, s, d)
            rows.append({
                "w": [round(float(w[0]), 6), round(float(w[1]), 6)],
                "s": round(s, 6), "d": round(d, 6),
                "region": region_name(
                    frame, int(assign_regions(frame, np.array([s]))[0])),
                "stratum": label,
            })

    absd = np.abs(d_all)
    for lo, hi in FIXTURE_STRATA:
        take(np.flatnonzero((absd >= lo) & (absd < hi)), per_stratum,
             "d %g-%g" % (lo, hi))

    sw = np.asarray(wrap_s(frame, s_all))
    near_seam = (sw <= seam_span_m) | (sw >= frame.length_m - seam_span_m)
    take(np.flatnonzero(near_seam), seam_rows, "seam")

    return {
        "source": "2024 Italian Grand Prix, race, FastF1 position samples",
        "note": ("Plan view only: `w` is Three.js (x, z) in metres. The vertical "
                 "channel is dropped at projection because the committed "
                 "centreline's y is 0 by construction while telemetry Z sits "
                 "~188 m above sea level."),
        "trackLengthM": round(frame.length_m, 4),
        "rows": rows,
    }


def write_min(doc: dict, path: str) -> str:
    """Write minified. 42,500 integers is not a file anyone reads by eye."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    return str(out)


def write_indented(doc: dict, path: str) -> str:
    """Write readable, for the fixture - a human checks these rows by hand."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return str(out)


# --------------------------------------------------------------------------
# Picking the window
# --------------------------------------------------------------------------

@dataclass
class Window:
    """A run of laps every chosen car completes without visiting the pit lane.
    """

    from_lap: int
    to_lap: int
    t0: float
    t1: float
    codes: list[str]
    dropped: dict[str, str]


def pick_window(cars: dict, laps_wanted: int, pit_abs_d: float,
                from_lap: int | None = None) -> Window:
    """Choose a clean green-flag window, from the data rather than from memory.

    A car is in the window if it has a timed lap record for every lap of it and
    never leaves the ribbon during it. Pit visits are detected from `|d|`
    rather than from FastF1's pit columns: the projection already knows,
    because Monza's pit lane runs parallel to the main straight about 18 m to
    the right of the centreline, so a pit stop is a car with `|d|` far outside
    a 13 m ribbon. One fewer thing to look up, and it cross-checks the
    projection at the same time
    - if `d` were wrong, this would pick nonsense.

    Scored by how many cars survive, ties broken towards the earlier window:
    the field is still closed up early in a race and spread out later, and a
    closed-up field is the more useful thing to look at.
    """
    timed: dict[str, dict[int, tuple[float, float]]] = {}
    pitted: dict[str, set[int]] = {}
    for code, car in cars.items():
        timed[code] = {}
        pitted[code] = set()
        t, d = car["path"].t, car["path"].d
        for num, start, lap_time in car["lapinfo"]:
            if not np.isfinite(lap_time):
                continue
            sel = (t >= start) & (t <= start + lap_time)
            if sel.sum() < 10:
                continue
            timed[code][int(num)] = (start, start + lap_time)
            if np.abs(d[sel]).max() > pit_abs_d:
                pitted[code].add(int(num))

    all_laps = sorted({n for v in timed.values() for n in v})
    if not all_laps:
        raise RuntimeError(
            "No timed laps with position data; cannot pick a window.")

    def survivors(lo: int) -> list[str]:
        span = range(lo, lo + laps_wanted)
        return sorted(c for c in timed
                      if all(n in timed[c] for n in span)
                      and not any(n in pitted[c] for n in span))

    starts = [lo for lo in all_laps if lo + laps_wanted - 1 <= all_laps[-1]]
    if from_lap is not None:
        best = from_lap
    else:
        scored = [(len(survivors(lo)), -lo, lo) for lo in starts]
        scored.sort(reverse=True)
        print("  window     best candidates (cars kept, start lap):")
        for n, _, lo in scored[:4]:
            print("             %2d cars from lap %d" % (n, lo))
        best = scored[0][2]

    codes = survivors(best)
    if not codes:
        raise RuntimeError(
            "No car completes laps %d-%d without a pit visit. Try --laps fewer, "
            "or a different --from-lap." % (best, best + laps_wanted - 1))

    t0 = min(timed[c][best][0] for c in codes)
    t1 = max(timed[c][best + laps_wanted - 1][1] for c in codes)

    dropped = {}
    for code in sorted(timed):
        if code in codes:
            continue
        span = range(best, best + laps_wanted)
        if any(n in pitted[code] for n in span):
            which = sorted(n for n in span if n in pitted[code])
            dropped[code] = "pit lane on lap %s" % ",".join(str(n) for n in which)
        else:
            dropped[code] = "no timed lap data for the whole window"
    return Window(from_lap=best, to_lap=best + laps_wanted - 1, t0=t0, t1=t1,
                  codes=codes, dropped=dropped)


# --------------------------------------------------------------------------
# Sanity checks - letters continue from extract_track.py's A-K, so a terminal
# running both scripts never shows the same letter twice.
# --------------------------------------------------------------------------

def check_l_window(frame: CentreFrame, cars: list[dict], *, n_steps: int,
                   rejected: int, fallbacks: int, window_m: float,
                   tol_reject: float = 0.005, tol_fallback: float = 0.002,
                   tol_m: float = 1e-6, probes: int = 4000) -> str:
    """The window changes no answer, and the clock guard barely fires.

    The interesting assertion is the third one: for a subsample of real
    positions, the *windowed* projection is compared against an unconstrained
    *global* one. If they agree everywhere then the window demonstrably did not
    change a single answer on this data, which is a stronger statement than any
    bound on the geometry.

    An earlier cut asserted a geometric sufficient condition instead - that
    points more than a window apart along the lap never come within twice the
    largest observed |d|. That is conservative to the point of being
    misleading: it pairs the tightest self-approach on the lap, 23.6 m at the
    Rettifilo, with the largest offset seen anywhere, 19 m in the pit lane,
    although those are at opposite ends of the circuit and cannot occur
    together. The geometry is still reported below, because it is the reason
    the window is cheap insurance rather than load-bearing.
    """
    approach, s_i, s_j = self_approach(frame, window_m)
    reject_frac = rejected / max(n_steps, 1)
    fallback_frac = fallbacks / max(n_steps, 1)

    rng = np.random.default_rng(20240901)
    disagree = 0
    worst = (0.0, 0.0)
    checked = 0
    for car in cars:
        raw = car["raw"]
        if len(raw.t) == 0:
            continue
        take = rng.choice(len(raw.t), size=min(probes // max(len(cars), 1),
                                              len(raw.t)), replace=False)
        for k in take:
            p = to_world(frame, raw.s[k], raw.d[k])
            s_win, d_win, _, _ = project_windowed(frame, p, raw.s[k])
            s_glob, d_glob, _ = project_global(frame, p)
            gap = abs(unwrap_near(s_win, s_glob, frame.length_m) - s_glob)
            checked += 1
            if gap > tol_m or abs(d_win - d_glob) > tol_m:
                disagree += 1
                if gap > worst[0]:
                    worst = (gap, float(raw.s[k]))

    assert reject_frac <= tol_reject, (
        "[L] %d of %d steps (%.3f%%) failed the physical reach test, tolerance "
        "%.2f%%. Suspect the jitter allowance: a per-step speed test rejects "
        "honest samples for arriving close together."
        % (rejected, n_steps, reject_frac * 100, tol_reject * 100))
    assert fallback_frac <= tol_fallback, (
        "[L] %d of %d samples (%.3f%%) escaped the +/-%.0f m window and needed a "
        "global search, tolerance %.2f%%. Suspect the velocity prediction in "
        "`project_path`, not the window width - widening the window buys the "
        "ambiguity it exists to prevent."
        % (fallbacks, n_steps, fallback_frac * 100, window_m, tol_fallback * 100))
    assert disagree == 0, (
        "[L] The +/-%.0f m window disagrees with an unconstrained search on %d of "
        "%d probes, worst %.3f m of arc near s=%.0f. The window is picking a "
        "different stretch of track from the one the geometry says is nearest."
        % (window_m, disagree, checked, worst[0], worst[1]))
    return ("+/-%.0f m: %.3f%% rejected, %.3f%% global fallback, and agrees with "
            "an unconstrained search on all %d probes. Pairs that far apart along "
            "the lap never come within %.1f m (s=%.0f vs %.0f), so on this "
            "circuit a global search could not jump either"
            % (window_m, reject_frac * 100, fallback_frac * 100, checked,
               approach, s_i, s_j))


def check_m_domain(frame: CentreFrame, s: np.ndarray, d: np.ndarray,
                   tol: float = 0.5) -> str:
    """`(s, d)` stays far from the fold where the mapping stops being invertible.

    `toWorld` is singular at `d = 1 / kappa`, the centre of curvature. The
    Jacobian is `1 - d * kappa`, so this is the margin to a point where two
    `(s, d)` pairs would name one place and the inverse would have no answer.
    """
    kappa = np.array([curvature_at(frame, v) for v in s[::7]])
    defect = np.abs(d[::7] * kappa)
    k = int(np.argmax(defect))
    radius = 1.0 / max(abs(kappa[k]), 1e-12)
    assert defect.max() < tol, (
        "[M] |d * kappa| reaches %.4f at s=%.1f (d=%+.2f m, local radius %.1f m), "
        "tolerance %.2f. The (s, d) map folds at 1.0 and the inverse has no "
        "unique answer near it."
        % (defect.max(), s[::7][k], d[::7][k], radius, tol))
    return ("max |d * kappa| %.4f at s=%.1f (d=%+.2f m, radius %.1f m) - %.0fx "
            "margin to the fold"
            % (defect.max(), s[::7][k], d[::7][k], radius,
               1.0 / max(defect.max(), 1e-12)))


def check_n_identity(frame: CentreFrame, *, step_m: float = 1.3,
                     tol: float = 1e-9) -> str:
    """The projection is the exact inverse of `toWorld`, not an approximation.

    Swept on synthetic probes rather than on telemetry, because the property is
    about the two functions and not about the data. The naive nearest-segment
    projection is measured on the same probes and printed beside it: the
    contrast
    *is* the justification for `foot_on_segment` existing, and a tolerance alone
    would not show that the obvious implementation is eleven orders of
    magnitude worse.
    """
    probes = np.arange(0.0, frame.length_m, step_m)
    offsets = (-6.5, -3.0, 0.0, 3.0, 6.5)
    worst = 0.0
    worst_at = (0.0, 0.0)
    worst_naive = 0.0
    naive_at = (0.0, 0.0)
    for d0 in offsets:
        for s0 in probes:
            p = to_world(frame, s0, d0)
            sw, d1, _, _ = project_windowed(frame, p, s0)
            err = float(np.linalg.norm(
                to_world(frame, unwrap_near(sw, s0, frame.length_m), d1) - p))
            if err > worst:
                worst, worst_at = err, (s0, d0)
            s2, d2 = project_naive(frame, p)
            nerr = float(np.linalg.norm(to_world(frame, s2, d2) - p))
            if nerr > worst_naive:
                worst_naive, naive_at = nerr, (s0, d0)
    assert worst <= tol, (
        "[N] Round trip reaches %.3e m at s=%.1f d=%+.1f, tolerance %.0e. This is "
        "an identity in exact arithmetic, so anything above float noise is a bug "
        "in `foot_on_segment` or a disagreement with `sampleAt` in frame.ts - not "
        "geometry to be tolerated." % (worst, worst_at[0], worst_at[1], tol))
    return ("%d probes: refined max %.2e m (at s=%.0f d=%+.1f) against naive "
            "nearest-segment max %.4f m (at s=%.0f d=%+.1f) - %.0e x better"
            % (len(probes) * len(offsets), worst, worst_at[0], worst_at[1],
               worst_naive, naive_at[0], naive_at[1],
               worst_naive / max(worst, 1e-300)))


def check_o_roundtrip(frame: CentreFrame, cars: list[dict],
                      tol_m: float = 0.06) -> str:
    """The committed integer channels still round-trip, quantisation included.

    Check N proves the mathematics; this proves the file. It decodes `s` and
    `d`
    exactly as `load.ts` will and measures `|to_world(s, d) - p|` against the
    world point the encoder started from, so millimetre deltas, centimetre
    offsets and the accumulated delta sum are all inside the measurement.

    Plan view only, and the vertical residual is reported rather than asserted:
    the committed centreline's `y` is 0 by construction while telemetry Z sits
    ~188 m above sea level, so a 3-D figure would measure Monza's altitude.
    """
    errs = []
    worst = (0.0, 0.0, 0.0)
    for car in cars:
        s_dec = decode_s(car["s0"], car["ds_mm"])
        d_dec = np.asarray(car["d_cm"], dtype=float) / 100.0
        grid = car["grid"]
        for k in range(0, len(s_dec), 11):
            want = to_world(frame, grid.s[k], grid.d[k])
            got = to_world(frame, s_dec[k], d_dec[k])
            e = float(np.linalg.norm(got - want))
            errs.append(e)
            if e > worst[0]:
                worst = (e, grid.s[k], grid.d[k])
    arr = np.array(errs)
    vert = np.concatenate([c["raw"].z for c in cars])
    # Split the error: the millimetre deltas accumulate into a slow drift of
    # absolute `s`, while `d` and the per-step rounding do not. Reporting both
    # says which one any future tightening would have to attack.
    drift = max(float(np.abs(decode_s(c["s0"], c["ds_mm"]) - c["grid"].s).max())
                for c in cars)
    assert arr.max() <= tol_m, (
        "[O] Quantised round trip reaches %.4f m at s=%.1f d=%+.2f, tolerance "
        "%.3f m. Suspect `encode_car`'s precision, or delta accumulation in "
        "`decode_s`." % (arr.max(), worst[1], worst[2], tol_m))
    return ("p50 %.5f p90 %.5f p99 %.5f max %.5f m (worst at s=%.0f d=%+.2f), of "
            "which %.4f m is millimetre-delta drift and the rest is rounding; "
            "vertical channel dropped spans %.1f-%.1f m, reported not asserted"
            % (*np.percentile(arr, [50, 90, 99]), arr.max(), worst[1], worst[2],
               drift, vert.min(), vert.max()))


def check_p_continuity(cars: list[dict], hz: float,
                       max_speed_mps: float = MAX_SPEED_MPS,
                       tol_frac: float = 0.0) -> str:
    """No car teleports on the committed grid, and `s` never runs backwards far.

    Measured on the *output* grid rather than on the source, because the grid
    is what renders. A step beyond the physical bound here would be a car
    crossing part of a corner between two frames, which makes a replay unusable
    however good its statistics are.

    The tolerance is zero, which is only affordable because `s` comes from a
    smoothing spline. An earlier cut used local quadratic fits and 0.88% of
    grid steps exceeded the bound - small enough to look like noise in a
    summary, and quite visible as a car gaining two metres in one frame and
    losing them in the next.
    """
    worst_v = 0.0
    worst_at = ("", 0.0)
    worst_back = 0.0
    worst_smooth = 0.0
    over = total = 0
    for car in cars:
        s = decode_s(car["s0"], car["ds_mm"])
        step = np.diff(s) * hz
        total += len(step)
        over += int((step > max_speed_mps).sum())
        if step.max() > worst_v:
            worst_v = float(step.max())
            worst_at = (car["code"], float(s[int(np.argmax(step))]))
        worst_back = min(worst_back, float(step.min()))
        worst_smooth = max(worst_smooth, float(derive_speed(s, hz).max()))
    frac = over / max(total, 1)
    assert frac <= tol_frac, (
        "[P] %d of %d grid steps (%.3f%%) imply more than %.0f m/s, worst %.1f m/s "
        "for %s near s=%.0f. Tolerance %.2f%%. Suspect SMOOTH_LAMBDA being too "
        "small: the source clock jitters, and a grid that follows it too closely "
        "carries that straight through."
        % (over, total, frac * 100, max_speed_mps, worst_v, worst_at[0],
           worst_at[1], tol_frac * 100))
    return ("%d grid steps: fastest %.1f m/s (%s near s=%.0f) against a %.0f m/s "
            "bound, fastest derived speed %.1f m/s, most negative step %.2f m/s"
            % (total, worst_v, worst_at[0], worst_at[1], max_speed_mps,
               worst_smooth, worst_back))


def check_q_lap_number(frame: CentreFrame, cars: list[dict],
                       tol_m: float = 50.0) -> str:
    """Official lap boundaries sit close to the geometric `s = 0` crossing.

    `startFinishS` is point 0 of the median lap - the lap-timing boundary, not
    the surveyed painted line (design doc section 5). This measures how far
    apart the two actually are, which is the reason `lapStartS` is committed
    rather than left for the viewer to derive from `floor(s / L)`: both lap
    numbers are real and they are not the same number.
    """
    offs = []
    worst = (0.0, "", 0)
    for car in cars:
        for num, s in zip(car["lap_numbers"], car["lap_start_s"]):
            off = s - round(s / frame.length_m) * frame.length_m
            offs.append(off)
            if abs(off) > abs(worst[0]):
                worst = (off, car["code"], num)
    arr = np.array(offs)
    assert np.abs(arr).max() <= tol_m, (
        "[Q] Lap boundary for %s lap %d sits %+.1f m from the geometric start/"
        "finish crossing, tolerance %.0f m. Suspect `lap_boundaries` interpolating "
        "against the wrong path, or a lap record outside the window."
        % (worst[1], worst[2], worst[0], tol_m))
    return ("%d boundaries: mean %+.2f m, sd %.2f m, worst %+.1f m (%s lap %d) "
            "from the geometric crossing - %.2f%% of a lap"
            % (len(arr), arr.mean(), arr.std(), worst[0], worst[1], worst[2],
               abs(worst[0]) / frame.length_m * 100))


def check_r_speed(cars: list[dict], hz: float, tol_bias_frac: float = 0.02,
                  tol_corr: float = 0.97) -> str:
    """The derived speed agrees with FastF1's own, independently-derived channel.

    `Speed` comes from car telemetry, not from position, so it knows nothing
    about the centreline or the projection. Agreement is therefore a
    cross-check on both at once - the same move as the `Distance` column
    cross-check for corners in `extract_track.py`. The bias is the interesting
    number: it is the fractional error in lap length and projection together.
    """
    bias = []
    sd = []
    corr = []
    for car in cars:
        if len(car["speed_t"]) < 10:
            continue
        s = decode_s(car["s0"], car["ds_mm"])
        v = derive_speed(s, hz)
        ref = np.interp(car["grid"].t, car["speed_t"], car["speed_v"])
        moving = ref > 5.0
        if moving.sum() < 50:
            continue
        err = v[moving] - ref[moving]
        bias.append(float(err.mean()))
        sd.append(float(err.std()))
        corr.append(float(np.corrcoef(v[moving], ref[moving])[0, 1]))
    if not bias:
        return "skipped - no car telemetry Speed channel available"
    mean_ref = 5756.9 / 85.0
    worst_bias = max(bias, key=abs)
    assert abs(worst_bias) <= tol_bias_frac * mean_ref, (
        "[R] Derived speed is biased %+.3f m/s (%.2f%% of a %.1f m/s lap average) "
        "against FastF1's Speed channel, tolerance %.0f%%. Suspect the projection "
        "or the lap length, not the smoothing - a boxcar preserves the mean."
        % (worst_bias, worst_bias / mean_ref * 100, mean_ref, tol_bias_frac * 100))
    assert min(corr) >= tol_corr, (
        "[R] Derived speed correlates only %.4f with FastF1's Speed channel, "
        "tolerance %.2f. Suspect SMOOTH_LAMBDA, or jitter left in `s` by "
        "`fit_to_grid`." % (min(corr), tol_corr))
    return ("%d cars: bias %+.3f..%+.3f m/s (worst %.2f%% of lap average), sd "
            "%.2f..%.2f m/s, correlation %.4f..%.4f"
            % (len(bias), min(bias), max(bias), worst_bias / mean_ref * 100,
               min(sd), max(sd), min(corr), max(corr)))


def check_s_jitter(cars: list[dict], hz: float, jitter_s: float = JITTER_S,
                   tol_mult: float = 2.5) -> str:
    """The fitted grid stays close to the raw samples, allowing for their clock.

    Not a fidelity check in the usual sense, and the difference matters. The
    grid
    *should* differ from a linear interpolation of the source, because the source
    timestamps jitter and the fit is there to remove that. So the bound is the
    jitter itself: a sample whose timestamp is off by `jitter_s` sits
    `speed * jitter_s` away along the track, and a residual of that order is
    the fit doing its job. A residual much larger would mean the fit is
    fighting the data rather than cleaning it.
    """
    worst = 0.0
    worst_at = ("", 0.0)
    allowed = 0.0
    resid = []
    for car in cars:
        grid, raw = car["grid"], car["raw"]
        # Only where the grid covers the source. `raw` is clipped a little
        # wider than the window on purpose, so the fit has samples either side
        # of the first and last grid point; comparing outside the grid would
        # measure `np.interp` clamping at the ends rather than anything about
        # the fit.
        inside = (raw.t >= grid.t[0]) & (raw.t <= grid.t[-1])
        if inside.sum() < 2:
            continue
        err = np.abs(np.interp(raw.t[inside], grid.t, grid.s) - raw.s[inside])
        resid.append(err)
        v = np.abs(np.gradient(raw.s) / np.maximum(np.gradient(raw.t), 1e-9))
        allowed = max(allowed, float(np.percentile(v, 99) * jitter_s * tol_mult))
        if err.max() > worst:
            worst = float(err.max())
            worst_at = (car["code"], float(raw.s[inside][int(np.argmax(err))]))
    if not resid:
        return "skipped - no overlap between the grid and the source samples"
    arr = np.concatenate(resid)
    assert worst <= allowed, (
        "[S] The fitted grid departs from a raw sample by %.1f m (%s near s=%.0f), "
        "against %.1f m of expected clock jitter at this speed. Suspect "
        "SMOOTH_LAMBDA being too large, or a genuine gap in the stream."
        % (worst, worst_at[0], worst_at[1], allowed))
    return ("p50 %.2f p90 %.2f p99 %.2f max %.2f m against %.1f m of expected "
            "jitter displacement (worst %s near s=%.0f)"
            % (*np.percentile(arr, [50, 90, 99]), worst, allowed, worst_at[0],
               worst_at[1]))


def check_t_lateral(rep: dict, width_m: float, tol_profile_m: float = 1.5,
                    tol_p999_m: float = 2.0) -> str:
    """The systematic part of `d` is small enough that the median is good enough.

    The question this milestone exists to answer. `d` is measured against a
    centreline that is a median across racing lines rather than a survey, so a
    bias as a function of `s` is expected by construction; what was not known
    was its size.
    """
    assert rep["profile_max_abs"] <= tol_profile_m, (
        "[T] The systematic lateral profile reaches %.3f m (at s=%.0f or s=%.0f), "
        "tolerance %.1f m on a %.1f m ribbon. Suspect the centreline rather than "
        "the projection - a median of racing lines cuts apexes, and over-smoothing "
        "rounds a chicane off (design doc section 4 step 6)."
        % (rep["profile_max_abs"], rep["profile_lo_s"], rep["profile_hi_s"],
           tol_profile_m, width_m))
    assert abs(rep["pct"][-1]) <= tol_p999_m and abs(rep["pct"][0]) <= tol_p999_m, (
        "[T] On-track |d| reaches %.2f m at p99.9 against a %.1f m half-width, "
        "tolerance %.1f m. Suspect `pitAbsDM` failing to separate the pit lane, or "
        "cars genuinely running off the track."
        % (max(abs(rep["pct"][0]), abs(rep["pct"][-1])), width_m / 2, tol_p999_m))
    pit = ("%.2f%% in the pit lane at d p50 %+.1f m" %
           (rep["pit_frac"] * 100, rep["pit_d_p50"]) if rep["n_pit"]
           else "no sample off the ribbon at all")
    return ("on track mean %+.4f m sd %.4f m, systematic profile %+.3f..%+.3f m "
            "(%.0f%% of the variance), residual sd %.4f m; %s"
            % (rep["mean"], rep["sd"], rep["profile_lo"], rep["profile_hi"],
               rep["explained"] * 100, rep["resid_sd"], pit))


def check_u_well_formed(doc: dict, cars: list[dict], path_out: str,
                        tol_drift_m: float = 0.1,
                        tol_bytes: int = 450_000) -> str:
    """Channel lengths, delta drift and byte size.

    The drift is the one worth measuring rather than estimating: millimetre
    deltas random-walk, and the accumulated error in absolute `s` is what a
    later milestone measuring a gap between two cars would inherit.
    """
    samples = doc["samples"]
    worst_drift = 0.0
    worst_code = ""
    for car in cars:
        assert len(car["ds_mm"]) == samples - 1, (
            "[U] %s has %d delta samples, expected %d. Suspect `fit_to_grid` being "
            "handed a different sample count per car."
            % (car["code"], len(car["ds_mm"]), samples - 1))
        assert len(car["d_cm"]) == samples, (
            "[U] %s has %d lateral samples, expected %d."
            % (car["code"], len(car["d_cm"]), samples))
        decoded = decode_s(car["s0"], car["ds_mm"])
        drift = float(np.abs(decoded - car["grid"].s).max())
        if drift > worst_drift:
            worst_drift, worst_code = drift, car["code"]
        finite = (np.isfinite(car["grid"].s).all()
                  and np.isfinite(car["grid"].d).all())
        assert finite, (
            "[U] %s has a non-finite sample." % car["code"])
    size = len(json.dumps(doc, separators=(",", ":")).encode("utf-8"))
    assert worst_drift <= tol_drift_m, (
        "[U] Millimetre-delta accumulation drifts %.3f m for %s over %d samples, "
        "tolerance %.2f m. Suspect `encode_car` - centimetre deltas drift about "
        "ten times further." % (worst_drift, worst_code, samples, tol_drift_m))
    assert size <= tol_bytes, (
        "[U] %s would be %.0f KB, budget %.0f KB. The lever is --to-lap at roughly "
        "70 KB a lap, not the rate or the precision."
        % (path_out, size / 1024, tol_bytes / 1024))
    return ("%d cars x %d samples, worst delta drift %.3f m (%s), %.0f KB "
            "(%.0f KB per lap)"
            % (len(cars), samples, worst_drift, worst_code, size / 1024,
               size / 1024 / max(doc["toLap"] - doc["fromLap"] + 1, 1)))


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

def run_pipeline(args) -> tuple[dict, dict]:
    """Returns `(replay doc, fixture doc)`, both only after every check passes.
    """
    stages = StageWriter(args.stage_dir)

    frame = load_centre_frame(args.track)
    print("  step 1     %s: %d points, %.1f m, %.4f m spacing, %d corners"
          % (args.track, len(frame.points), frame.length_m,
             frame.length_m / len(frame.points), len(frame.corners)))

    enable_cache(args.cache)
    print("  cache      %s" % args.cache)
    print("  loading    %d %s %s (slow on a cache miss)..."
          % (args.year, args.event, args.session))
    session = load_session(args.year, args.event, args.session)

    # Track status, so safety-car handling is answered from data rather than
    # implemented speculatively.
    status = getattr(session, "track_status", None)
    if status is not None and len(status):
        labels = ", ".join(sorted(set(str(v) for v in status["Message"])))
        print("  step 2     track status: %d change(s) - %s"
              % (len(status), labels))

    series: dict[str, dict] = {}
    gaps = []
    for drv in session.drivers:
        info = session.get_driver(drv)
        code = str(info["Abbreviation"])
        t, plan, z = car_positions(session, drv)
        gaps.append(np.diff(t))
        path = project_path(t, plan, z, frame, half=args.search_half,
                            max_speed_mps=args.max_speed)
        lapinfo = []
        for _, lap in session.laps[session.laps["Driver"] == code].iterrows():
            start, lap_time = lap["LapStartTime"], lap["LapTime"]
            if start is None or not np.isfinite(start.total_seconds()):
                continue
            lapinfo.append((
                int(lap["LapNumber"]), float(start.total_seconds()),
                float(lap_time.total_seconds())
                if lap_time is not None and np.isfinite(lap_time.total_seconds())
                else float("nan")))
        series[code] = {
            "path": path, "lapinfo": lapinfo, "raw_t": t,
            "name": str(info["FullName"]), "number": int(info["DriverNumber"]),
            "speed": _speed_channel(session, drv),
        }
        stages.array("03_path_%s" % code, np.column_stack([path.t, path.s, path.d]))

    g = np.concatenate(gaps)
    print("  step 3     %d cars; source dt p50 %.3f s (%.2f Hz), p99 %.3f, max "
          "%.3f -> output %g Hz"
          % (len(series), np.median(g), 1 / np.median(g),
             np.percentile(g, 99), g.max(), args.hz))

    window = pick_window(series, args.laps, args.pit_abs_d, args.from_lap)
    print("  step 4     laps %d-%d, t %.1f-%.1f s (%.1f s), %d cars"
          % (window.from_lap, window.to_lap, window.t0, window.t1,
             window.t1 - window.t0, len(window.codes)))
    for code, why in sorted(window.dropped.items()):
        print("             dropped %-4s %s" % (code, why))

    samples = int(np.floor((window.t1 - window.t0) * args.hz))
    cars: list[dict] = []
    rejected = n_steps = fallbacks = 0
    for code in window.codes:
        src = series[code]
        raw = clip_path(src["path"], window.t0 - 2.0, window.t1 + 2.0)
        grid = fit_to_grid(raw, args.hz, window.t0, samples, args.smooth_lambda)
        s0, ds_mm, d_cm = encode_car(grid)
        nums, lap_s, lap_t = lap_boundaries(src["lapinfo"], grid, window.t0)
        rejected += int((~src["path"].good).sum())
        n_steps += len(src["path"].t)
        fallbacks += src["path"].fallbacks
        cars.append({
            "code": code, "name": src["name"], "raw": raw, "grid": grid,
            "s0": s0, "ds_mm": ds_mm, "d_cm": d_cm,
            "lap_numbers": nums, "lap_start_s": lap_s, "lap_start_t": lap_t,
            "speed_t": src["speed"][0], "speed_v": src["speed"][1],
        })
    print("  step 5     %d samples per car at %g Hz, %d cars, %.1f s of replay"
          % (samples, args.hz, len(cars), samples / args.hz))

    rep = lateral_report(frame, cars, args.pit_abs_d)
    print_lateral_report(rep)

    doc = build_doc(frame, cars, name=args.event, year=args.year,
                    session=args.session, hz=args.hz, t0=window.t0,
                    samples=samples, from_lap=window.from_lap,
                    to_lap=window.to_lap, pit_abs_d=args.pit_abs_d)
    fixture = build_fixture(frame, cars)
    stages.doc("05_window", {"from": window.from_lap, "to": window.to_lap,
                             "codes": window.codes, "dropped": window.dropped})

    s_all = np.concatenate([c["grid"].s for c in cars])
    d_all = np.concatenate([c["grid"].d for c in cars])
    window_m = args.search_half * frame.length_m / len(frame.points)

    run_checks([
        ("L window", lambda: check_l_window(
            frame, cars, n_steps=n_steps, rejected=rejected,
            fallbacks=fallbacks, window_m=window_m)),
        ("M domain", lambda: check_m_domain(frame, s_all, d_all)),
        ("N identity", lambda: check_n_identity(frame)),
        ("O round trip", lambda: check_o_roundtrip(frame, cars)),
        ("P continuity", lambda: check_p_continuity(cars, args.hz,
                                                    args.max_speed)),
        ("Q lap number", lambda: check_q_lap_number(frame, cars)),
        ("R speed", lambda: check_r_speed(cars, args.hz)),
        ("S jitter", lambda: check_s_jitter(cars, args.hz)),
        ("T lateral", lambda: check_t_lateral(rep, frame.width_m)),
        ("U well formed", lambda: check_u_well_formed(doc, cars, args.out)),
    ])
    return doc, fixture


def _speed_channel(session, drv: str) -> tuple[np.ndarray, np.ndarray]:
    """FastF1's own `Speed`, in m/s, for the cross-check in check R."""
    try:
        cd = session.car_data[drv]
        return (cd["SessionTime"].dt.total_seconds().to_numpy(dtype=float),
                cd["Speed"].to_numpy(dtype=float) / 3.6)
    except Exception:
        return np.array([]), np.array([])


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Project a FastF1 session onto a committed centreline.")
    p.add_argument("--year", type=int, default=2024)
    p.add_argument("--event", default="Monza")
    p.add_argument("--session", default="R")
    p.add_argument("--track", default="public/tracks/monza.json")
    p.add_argument("--out", default="public/replays/monza-2024-race.json")
    p.add_argument("--fixture",
                   default="scripts/fixtures/roundtrip-monza-2024.json")
    p.add_argument("--cache", default=".fastf1-cache")
    p.add_argument("--stage-dir", default=None,
                   help="dump every intermediate stage here for inspection")
    p.add_argument("--hz", type=float, default=5.0)
    p.add_argument("--laps", type=int, default=5)
    p.add_argument("--from-lap", type=int, default=None,
                   help="start lap; by default the cleanest window is chosen")
    p.add_argument("--search-half", type=int, default=SEARCH_HALF_SEGMENTS)
    p.add_argument("--smooth-lambda", type=float, default=SMOOTH_LAMBDA)
    p.add_argument("--max-speed", type=float, default=MAX_SPEED_MPS)
    p.add_argument("--pit-abs-d", type=float, default=PIT_ABS_D_M)
    p.add_argument("--dry-run", action="store_true",
                   help="run everything and report checks, but write no JSON")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    print("\n  extract_replay  %s %d (%s)" % (args.event, args.year, args.session))
    print("  " + "=" * 74)
    try:
        doc, fixture = run_pipeline(args)
    except CheckFailure as exc:
        print("\n  %s\n" % exc, file=sys.stderr)
        return 1

    if args.dry_run:
        print("  DRY RUN - not writing %s\n" % args.out)
    else:
        print("  wrote      %s (%d cars x %d samples)"
              % (write_min(doc, args.out), len(doc["cars"]), doc["samples"]))
        print("  wrote      %s (%d rows)\n"
              % (write_indented(fixture, args.fixture), len(fixture["rows"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
