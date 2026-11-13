"""The centreline frame and its exact inverse: `(s, d) <-> world`, plan view.

The one projection implementation in `scripts/`. Both extractors use it:
`extract_track.py` to put corner markers on the lap (step 10), and
`extract_replay.py` to recover `(s, d)` from every telemetry sample (section 6B).
Same rule as the viewer's single `toWorld`: one forward mapping, one inverse,
so a corner marker and a car at the same point cannot disagree about where it is.

The forward half is a port of `src/track/frame.ts` (`buildFrame`, `sampleAt`,
`toWorld`). The inverse solves

    f(t) = (p - c(t)) . that(t) = 0 ,   then   d = (p - c(t)) . rhat(t)

on the containing segment, where `that` is the *interpolated* tangent - not the
nearest point of the polyline. Nearest-segment projection measures `d` against
the segment normal, which differs from `rhat` by up to 7.93 deg on Monza, and
round-trips with up to 0.891 m of error; this one round-trips to float noise
(check N in `extract_replay.py`). See docs/3d-design.md, section 6B.

Everything here is in **Three.js plan space**, columns `(x, z)`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


#: Half-width of the constrained foot-point search, in centreline segments.
#: 8 segments is ~40 m. Measured: with the window centred on a velocity
#: prediction, 0.07% of samples escape it and need a global search, and over
#: 3,990 probes the windowed answer is identical to an unconstrained one - so
#: on Monza the window changes nothing and is insurance for the next circuit.
#: Check L measures both.
SEARCH_HALF_SEGMENTS = 8

#: Newton steps on the foot-point equation. `f` is strictly monotone on a
#: segment, so this converges quadratically; the residual is at float noise
#: after three. Check N asserts it.
NEWTON_STEPS = 4

#: Three.js plan columns. Spelled out rather than imported so the one gotcha
#: this module could hit is visible in it (CLAUDE.md: `(0, 1)` is elevation).
PLAN = (0, 2)


# --------------------------------------------------------------------------
# The centreline frame - a port of src/track/frame.ts `buildFrame`
# --------------------------------------------------------------------------

@dataclass
class CentreFrame:
    """Everything `sample_at` needs. Mirrors `TrackFrame` in `frame.ts`.

    Deliberately a port rather than an independent derivation: every formula
    here has a counterpart in `buildFrame`, and check N exists to prove the two
    agree. `points` is the plan view only - the committed `y` is identically 0,
    and carrying it would invite a 3-D residual that measures sea level.
    """

    points: np.ndarray        # (N, 2) plan (x, z), metres, loop not duplicated
    s: np.ndarray             # (N,) cumulative arc length, s[0] = 0
    length_m: float           # measured lap length, closing segment included
    tangent: np.ndarray       # (N, 2) unit, direction of travel
    right: np.ndarray         # (N, 2) unit, to the RIGHT of travel
    curvature: np.ndarray     # (N,) signed, 1/m, positive = turning right
    seg_len: np.ndarray       # (N,) length of segment i -> (i+1) % N
    corners: list[dict]       # from the JSON, for the `d` report's regions;
                              # empty when built before the JSON exists
    width_m: float


def _perp(v: np.ndarray) -> np.ndarray:
    """`cross(t, UP)` reduced to the plan.

    In three-space `(tx, 0, tz) x (0, 1, 0) = (-tz, 0, tx)`, so with the plan
    stored as `(x, z)` the right vector is `(-tz, tx)`. Writing the reduction
    out is cheaper than carrying a dead `y` column through every operation, and
    this is the one place the handedness of `frame.ts` is reproduced.
    """
    out = np.empty_like(v)
    out[..., 0] = -v[..., 1]
    out[..., 1] = v[..., 0]
    return out


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-300)


def load_centre_frame(path: str) -> CentreFrame:
    """Read the committed track JSON and rebuild `buildFrame`'s derived arrays.
    """
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    xyz = np.asarray(doc["centerline"], dtype=float)
    return frame_from_three(xyz, corners=list(doc["corners"]),
                            width_m=float(doc["widthM"]))


def frame_from_three(xyz: np.ndarray, *, corners: list[dict] | None = None,
                     width_m: float = 0.0) -> CentreFrame:
    """Build the frame from an (N, 3) Three.js-space centreline.

    `load_centre_frame` is this plus a file read. `extract_track.py` calls it
    directly, on the centreline it is about to write, because the corners it
    needs to project are part of that same document.
    """
    pts = np.asarray(xyz, dtype=float)[:, list(PLAN)]

    # Cumulative chord length, with the closing segment in the total but not in
    # `s`, so `length_m > s[-1]`. Exactly `buildFrame`'s loop.
    seg_len = np.linalg.norm(np.roll(pts, -1, axis=0) - pts, axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg_len)[:-1]])
    length_m = float(seg_len.sum())

    # Central difference, as in `buildFrame`: less sensitive to sample noise.
    tangent = _unit(np.roll(pts, -1, axis=0) - np.roll(pts, 1, axis=0))
    right = _perp(tangent)

    ds = (np.roll(s, -1) - np.roll(s, 1)) % length_m
    dt = np.roll(tangent, -1, axis=0) - np.roll(tangent, 1, axis=0)
    curvature = np.where(ds > 0, np.einsum("ij,ij->i", dt, right) / ds, 0.0)

    return CentreFrame(points=pts, s=s, length_m=length_m, tangent=tangent,
                       right=right, curvature=curvature, seg_len=seg_len,
                       corners=list(corners or []), width_m=float(width_m))


def wrap_s(frame: CentreFrame, s):
    """Wrap an arc length into [0, length_m). The only wrapping primitive."""
    return np.mod(s, frame.length_m)


def unwrap_near(s_wrapped: float, reference: float, length: float) -> float:
    """Lift a wrapped arc length onto the branch nearest `reference`.

    The whole of the seam handling, used once per sample. Valid because a
    per-sample advance is far below `length / 2`; nothing else in this script
    ever subtracts two wrapped values, which is the same discipline
    `src/cameras/rig.ts` documents at its head.
    """
    half = length / 2.0
    return reference + ((s_wrapped - reference + half) % length) - half


def segment_index(frame: CentreFrame, s_wrapped):
    """Index of the sample at or before an already-wrapped `s`.

    `searchsorted(..., "right") - 1` is the vectorised form of `frame.ts`'s
    binary search, including its behaviour past `s[-1]`, where it returns
    `N - 1` and so selects the closing segment.
    """
    return np.clip(np.searchsorted(frame.s, s_wrapped, side="right") - 1,
                   0, len(frame.s) - 1)


def sample_at(frame: CentreFrame, s: float):
    """Evaluate the centreline at `s` -> (position, tangent, right).

    Linear interpolation of position and tangent, with `right` re-derived from
    the interpolated tangent rather than interpolated itself. That last detail
    is the one that matters for the inverse: see the module docstring.
    """
    sw = float(wrap_s(frame, s))
    i = int(segment_index(frame, sw))
    j = (i + 1) % len(frame.points)
    seg = (frame.s[j] - frame.s[i] + frame.length_m) % frame.length_m
    t = (sw - frame.s[i]) / seg if seg > 0 else 0.0

    pos = frame.points[i] * (1.0 - t) + frame.points[j] * t
    tan = _unit(frame.tangent[i] * (1.0 - t) + frame.tangent[j] * t)
    return pos, tan, _perp(tan)


def to_world(frame: CentreFrame, s: float, d: float = 0.0) -> np.ndarray:
    """`(s, d) -> world`, plan view. The Python counterpart of `toWorld`."""
    pos, _, right = sample_at(frame, s)
    return pos + d * right


def curvature_at(frame: CentreFrame, s: float) -> float:
    """Signed curvature at `s`. Positive = the track turns right here."""
    sw = float(wrap_s(frame, s))
    i = int(segment_index(frame, sw))
    j = (i + 1) % len(frame.points)
    seg = (frame.s[j] - frame.s[i] + frame.length_m) % frame.length_m
    t = (sw - frame.s[i]) / seg if seg > 0 else 0.0
    return float(frame.curvature[i] * (1.0 - t) + frame.curvature[j] * t)


# --------------------------------------------------------------------------
# The inverse: world -> (s, d)
# --------------------------------------------------------------------------

def _foot_f(frame: CentreFrame, i: int, t: float, p: np.ndarray):
    """`f(t) = (p - c(t)) . that(t)`, its derivative, `that` and `p - c(t)`.

    Analytic rather than finite-differenced: the derivative is two terms and a
    sign error in either is exactly the kind of mistake a difference quotient
    hides by still roughly working.
    """
    j = (i + 1) % len(frame.points)
    a = frame.points[i]
    chord = frame.points[j] - a
    ti, tj = frame.tangent[i], frame.tangent[j]

    tu = ti * (1.0 - t) + tj * t          # unnormalised interpolated tangent
    tu_d = tj - ti                        # d/dt of the above
    norm = float(np.linalg.norm(tu))
    that = tu / norm
    # d/dt of a normalised vector: the part of `tu_d` orthogonal to `that`.
    that_d = (tu_d - that * float(that @ tu_d)) / norm

    rel = p - (a + t * chord)
    f = float(rel @ that)
    fd = float(-(chord @ that) + rel @ that_d)
    return f, fd, that, rel


def brackets(frame: CentreFrame, i: int, p: np.ndarray) -> bool:
    """Does the foot of `p` lie on segment `i`?

    `f` is strictly decreasing on a segment - `f' = -segLen * (cos alpha -
    d * kappa)`, with `cos alpha >= 0.990` and `|d * kappa| < 0.05` measured on
    Monza - so a sign change across the ends is necessary and sufficient.
    Inclusive at both ends: at a shared vertex both neighbouring segments
    bracket and both give the same `(s, d)` to float precision, so a double
    accept is harmless, while a strict test would reject a foot sitting exactly
    on a sample.
    """
    f0, _, _, _ = _foot_f(frame, i, 0.0, p)
    f1, _, _, _ = _foot_f(frame, i, 1.0, p)
    return f0 >= 0.0 >= f1


def foot_on_segment(frame: CentreFrame, i: int, p: np.ndarray,
                    steps: int = NEWTON_STEPS) -> tuple[float, float, float]:
    """Solve `f(t) = 0` on segment `i` -> (s, d, |residual|).

    Newton from the midpoint, clamped to [0, 1]. The clamp only keeps `c(t)` on
    the polyline while iterating; whether the foot is on this segment at all is
    decided by `brackets`, never by the clamp coming to rest at an end.
    """
    t = 0.5
    for _ in range(max(1, steps)):
        f, fd, _, _ = _foot_f(frame, i, t, p)
        if fd == 0.0:
            break
        t = min(1.0, max(0.0, t - f / fd))
    f, _, that, rel = _foot_f(frame, i, t, p)

    j = (i + 1) % len(frame.points)
    seg = (frame.s[j] - frame.s[i] + frame.length_m) % frame.length_m
    return float(frame.s[i] + t * seg), float(rel @ _perp(that)), abs(f)


def project_global(frame: CentreFrame,
                   p: np.ndarray) -> tuple[float, float, float]:
    """Unconstrained projection: find the bracketing segment by brute force.

    Seeds a car's first sample, and backs up `project_windowed` when a gap in
    the position stream outruns the window. Candidate segments are visited in
    nearest-vertex order, so the bracket test almost always succeeds on the
    first pair.
    """
    order = np.argsort(np.linalg.norm(frame.points - p[None, :], axis=1))
    n = len(frame.points)
    for v in order[:16]:
        for i in ((int(v) - 1) % n, int(v)):
            if brackets(frame, i, p):
                return foot_on_segment(frame, i, p)
    # No bracket near the point at all, which a position inside a curvature
    # centre can produce. The nearest vertex's own segment is the best answer.
    return foot_on_segment(frame, int(order[0]), p)


def project_windowed(frame: CentreFrame, p: np.ndarray, s_predict: float,
                     half: int = SEARCH_HALF_SEGMENTS):
    """Projection constrained to +/- `half` segments around a predicted `s`.

    Returns `(s_wrapped, d, residual, fell_back)`. The window is centred on a
    *velocity prediction*, not on the previous sample: measured over the race,
    the per-sample advance has a p99.9 of 75.7 m and a max of 314.7 m, so
    anchoring on the previous `s` would need an absurd half-width (2.18% of
    samples escape +/-40 m) while predicting first drops that to 0.005%.
    """
    n = len(frame.points)
    centre = int(segment_index(frame, float(wrap_s(frame, s_predict))))
    for k in range(half + 1):
        cands = (centre,) if k == 0 else ((centre + k) % n, (centre - k) % n)
        for i in cands:
            if brackets(frame, i, p):
                s, d, res = foot_on_segment(frame, i, p)
                return s, d, res, False
    s, d, res = project_global(frame, p)
    return s, d, res, True
