"""FastF1 -> track centreline JSON.

Implements section 4 of docs/3d-design.md. Each numbered step there is one
function here, taking and returning plain numpy arrays so it can be driven
from a REPL:

    >>> import numpy as np
    >>> from scripts.extract_track import smooth_loop, resample_arclength
    >>> med = np.load('.cache/stages/05_median.npy')
    >>> resample_arclength(smooth_loop(med, 21, 3), 5.0).shape

There are no module-level side effects, so importing this is safe and cheap.

Coordinate frames
-----------------
The pipeline runs end to end in FastF1 plan space: ``X``, ``Y`` on the ground
plane and ``Z`` for elevation, in **metres** (converted from FastF1's 1/10 m
exactly once, in `lap_positions`). The Three.js mapping is applied exactly
once, in `to_three`, at document-build time. That keeps every intermediate
stage in a natural plan view for plotting and keeps the mapping in one place,
as CLAUDE.md requires.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
from scipy.signal import savgol_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))

# The one projection implementation, shared with `extract_replay.py`.
from centreline import frame_from_three, project_global  # noqa: E402

# --------------------------------------------------------------------------
# Reference constants
# --------------------------------------------------------------------------

#: Published Monza lap length, metres. Check A compares against this.
MONZA_LENGTH_M = 5793.0

#: Corner names are annotation only - FastF1's circuit_info supplies corner
#: numbers and positions but no names. Keyed by event name -> corner number.
CORNER_NAMES: dict[str, dict[int, str]] = {
    "Monza": {
        1: "Variante del Rettifilo (1)",
        2: "Variante del Rettifilo (2)",
        3: "Curva Grande",
        4: "Variante della Roggia (1)",
        5: "Variante della Roggia (2)",
        6: "Curva di Lesmo 1",
        7: "Curva di Lesmo 2",
        8: "Variante Ascari (1)",
        9: "Variante Ascari (2)",
        10: "Variante Ascari (3)",
        11: "Curva Parabolica",
    }
}

#: Expected sign of the signed area of the (x, z) loop in Three.js space.
#: Monza runs clockwise; viewed down the +y axis with x right and z toward the
#: viewer, a clockwise loop has positive shoelace area. See check E - this is
#: confirmed against the matplotlib plot rather than trusted from reasoning
#: alone, because a sign convention derived on paper can quietly invert itself.
EXPECTED_AREA_SIGN = 1.0


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

#: Which columns are the ground plane, per coordinate frame. In FastF1 space
#: the plan view is (X, Y) and Z is elevation; in Three.js space Y is up, so
#: the plan view is (x, z). Measuring lengths with the wrong pair silently
#: projects the track onto the elevation axis, which on a flat circuit halves
#: the apparent lap length rather than erroring.
PLAN_COLS = {"ff1": (0, 1), "three": (0, 2)}


def ground(pts: np.ndarray, frame: str = "ff1") -> np.ndarray:
    """Ground-plane (N, 2) view of an (N, 3) array in the named frame.
    Passing an (N, 2) array through is a no-op, so callers can chain."""
    if pts.shape[1] == 2:
        return pts
    return pts[:, list(PLAN_COLS[frame])]


def _chord_lengths(pts: np.ndarray, closed: bool = False) -> np.ndarray:
    """Per-segment straight-line lengths of a polyline (N, >=2).

    Uses the first two columns, i.e. assumes FastF1 plan space. For a
    Three.js-space array, pass `ground(pts, "three")` first.
    """
    if closed:
        pts = np.vstack([pts, pts[:1]])
    return np.linalg.norm(np.diff(pts[:, :2], axis=0), axis=1)


def _cumulative(pts: np.ndarray, closed: bool = False) -> np.ndarray:
    """Cumulative chord distance, starting at 0. Length N (+1 if closed)."""
    return np.concatenate([[0.0], np.cumsum(_chord_lengths(pts, closed=closed))])


def polyline_length(pts: np.ndarray, closed: bool = True) -> float:
    """Total polyline length in metres, including the wrap segment if closed."""
    return float(_chord_lengths(pts, closed=closed).sum())


def tangents(pts: np.ndarray) -> np.ndarray:
    """Unit tangents of a closed polyline, central-differenced with wraparound."""
    d = np.roll(pts, -1, axis=0) - np.roll(pts, 1, axis=0)
    n = np.linalg.norm(d[:, :2], axis=1, keepdims=True)
    n[n == 0] = 1.0
    return d[:, :2] / n


def signed_area(xy: np.ndarray) -> float:
    """Shoelace signed area of a closed loop given as (N, 2)."""
    x, y = xy[:, 0], xy[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def to_three(xyz: np.ndarray) -> np.ndarray:
    """FastF1 plan space -> Three.js space. The ONE place this mapping lives.

        three.x =  ff1.X
        three.y =  ff1.Z
        three.z = -ff1.Y

    The minus is not optional (CLAUDE.md); dropping it mirrors the track.
    """
    out = np.empty_like(xyz)
    out[:, 0] = xyz[:, 0]
    out[:, 1] = xyz[:, 2]
    out[:, 2] = -xyz[:, 1]
    return out


class StageWriter:
    """Dumps each pipeline stage so intermediates can be inspected without
    re-running the slow session load. No-op when no directory is given."""

    def __init__(self, directory: str | None):
        self.dir = Path(directory) if directory else None
        if self.dir:
            self.dir.mkdir(parents=True, exist_ok=True)

    def array(self, name: str, arr: np.ndarray) -> np.ndarray:
        if self.dir is not None:
            np.save(self.dir / (name + ".npy"), arr)
        return arr

    def doc(self, name: str, obj: object) -> object:
        if self.dir is not None:
            (self.dir / (name + ".json")).write_text(
                json.dumps(obj, indent=2), encoding="utf-8"
            )
        return obj


# --------------------------------------------------------------------------
# Step 1 - load
# --------------------------------------------------------------------------

def enable_cache(path: str = ".fastf1-cache") -> str:
    """Enable the FastF1 on-disk cache. Must run before the first load; an
    uncached session.load() costs minutes every iteration."""
    import fastf1

    Path(path).mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(path)
    return path


def load_session(year: int, event: str, session_type: str = "R"):
    """Step 1. Load a session with position data. Slow on a cache miss."""
    import fastf1

    session = fastf1.get_session(year, event, session_type)
    session.load(laps=True, telemetry=True, weather=False, messages=False)
    return session


# --------------------------------------------------------------------------
# Step 2 - pick laps
# --------------------------------------------------------------------------

def pick_laps(session, max_laps: int = 20, per_driver: int = 3) -> list:
    """Step 2. Quick laps only, no in/out laps, nothing under SC/VSC/red.

    Spread across drivers (round-robin, up to `per_driver` each) so the median
    in step 5 averages over different racing lines rather than one driver's
    habits.
    """
    laps = session.laps
    laps = laps.pick_wo_box()                          # no in-laps / out-laps
    laps = laps.pick_track_status("456", how="none")   # no SC, red flag, VSC
    laps = laps.pick_accurate()                        # FastF1's quality flag
    laps = laps.pick_quicklaps()                       # within 107% of median

    if len(laps) == 0:
        raise RuntimeError(
            "Step 2 selected zero laps. Loosen the filters or try a different "
            "session (qualifying often has cleaner laps than a race)."
        )

    by_driver: dict[str, list] = {}
    for _, lap in laps.iterrows():
        by_driver.setdefault(lap["Driver"], []).append(lap)
    for drv in by_driver:
        by_driver[drv].sort(key=lambda lap: lap["LapTime"])
        by_driver[drv] = by_driver[drv][:per_driver]

    chosen: list = []
    drivers = sorted(by_driver)
    for rank in range(per_driver):
        for drv in drivers:
            if rank < len(by_driver[drv]) and len(chosen) < max_laps:
                chosen.append(by_driver[drv][rank])
    return chosen


# --------------------------------------------------------------------------
# Step 3 - per-lap position data
# --------------------------------------------------------------------------

def lap_positions(lap) -> np.ndarray:
    """Step 3. -> (M, 3) in metres. Drops non-OnTrack rows, exact (0, 0)
    samples (CLAUDE.md gotcha: they drag the spline to the origin) and
    consecutive duplicates (which would create zero-length segments)."""
    pos = lap.get_pos_data()
    if "Status" in pos.columns:
        pos = pos[pos["Status"] == "OnTrack"]

    xyz = pos[["X", "Y", "Z"]].to_numpy(dtype=float)
    xyz = xyz[np.isfinite(xyz).all(axis=1)]
    xyz = xyz[~((xyz[:, 0] == 0.0) & (xyz[:, 1] == 0.0))]

    xyz = xyz / 10.0  # FastF1 ships 1/10 m. Converted here, exactly once.

    if len(xyz) > 1:
        keep = np.concatenate([[True], _chord_lengths(xyz) > 1e-9])
        xyz = xyz[keep]
    return xyz


# --------------------------------------------------------------------------
# Step 4 - normalise
# --------------------------------------------------------------------------

def resample_relative(xyz: np.ndarray, n: int) -> np.ndarray:
    """Step 4. Resample to `n` points by *relative* distance around the lap,
    so laps with different sample counts line up index-for-index.

    The grid is [0, 1) with the endpoint excluded: the lap is a loop, so
    repeating the start point at the end would double-weight it in the median.
    """
    if len(xyz) < 4:
        raise ValueError("Step 4 needs at least 4 samples, got %d." % len(xyz))
    cum = _cumulative(xyz)
    t = cum / cum[-1]
    grid = np.linspace(0.0, 1.0, n, endpoint=False)
    return np.column_stack([np.interp(grid, t, xyz[:, i]) for i in range(3)])


# --------------------------------------------------------------------------
# Step 5 - median
# --------------------------------------------------------------------------

def median_laps(laps: Sequence[np.ndarray]) -> np.ndarray:
    """Step 5. Per-point median across laps, approximating the centreline.

    Individual laps follow the racing line and cut apexes; the deviations
    partly cancel. Not a survey - good enough at this scale. Do not collapse
    this back to a single fast lap (CLAUDE.md gotcha).
    """
    return np.median(np.stack(laps, axis=0), axis=0)


def lap_deviations(laps: Sequence[np.ndarray], median: np.ndarray) -> np.ndarray:
    """Max per-lap *lateral* deviation from the median centreline, metres.
    Diagnostic for check I.

    Measured as distance to the nearest point on the median, not index-for-
    index. Step 4 parameterises by relative distance, so two laps that brake
    at slightly different points drift out of phase with each other; comparing
    them index-for-index reads that along-track phase error as tens of metres
    of deviation, which is not what this check is about. Nearest-point
    distance measures how far off the centreline a lap actually ran, which is
    what "the track is only ~13 m wide" is a statement about.
    """
    from scipy.spatial import cKDTree

    tree = cKDTree(median[:, :2])
    return np.array([float(tree.query(lap[:, :2])[0].max()) for lap in laps])


# --------------------------------------------------------------------------
# Step 6 - smooth
# --------------------------------------------------------------------------

def smooth_loop(pts: np.ndarray, window: int, polyorder: int) -> np.ndarray:
    """Step 6. Savitzky-Golay over the closed loop.

    `mode='wrap'` is exactly the design doc's "wrap the ends before filtering",
    done by scipy rather than by hand.

    The window is in *points*, which is meaningless without the grid spacing -
    `run_pipeline` prints the equivalent in metres before filtering. Too wide
    and the Rettifilo chicane rounds off into a kink.

    On `polyorder`: for smoothing (deriv=0) orders 2 and 3 are the *same
    filter*, as are 4 and 5. Over a symmetric window the odd-degree term is
    antisymmetric and contributes nothing at the centre point, so the
    coefficients coincide. Measured on the Monza median, order 2 and order 3
    differ by 7e-13 m. The design doc's "polynomial order 2-3" is therefore
    one choice, not two, and the window is the only knob that matters. Order
    would start to matter at 4+, which is too flexible for this noise level.
    """
    if polyorder >= window:
        raise ValueError(
            "polyorder %d must be < window %d." % (polyorder, window))
    if window > len(pts):
        raise ValueError(
            "window %d exceeds point count %d." % (window, len(pts)))
    return savgol_filter(pts, window_length=window, polyorder=polyorder,
                         axis=0, mode="wrap")


# --------------------------------------------------------------------------
# Step 7 - resample by arc length
# --------------------------------------------------------------------------

def resample_arclength(pts: np.ndarray, spacing: float,
                       iterations: int = 2) -> np.ndarray:
    """Step 7. Re-parameterise to uniform spacing. This is what makes `s`
    meaningful: index i sits at s = i * spacing.

    The point count is round(L / spacing), so the realised spacing is L / K
    rather than exactly `spacing` - that is what keeps the loop closed with
    every segment equal, including the wrap segment (step 8).

    Iterated twice because resampling slightly changes the polyline length.
    """
    out = pts
    for _ in range(max(1, iterations)):
        cum = _cumulative(out, closed=True)     # length K+1, ends at total L
        total = cum[-1]
        k = max(4, int(round(total / spacing)))
        targets = np.arange(k) * (total / k)
        loop = np.vstack([out, out[:1]])        # closed, for interpolation only
        out = np.column_stack(
            [np.interp(targets, cum, loop[:, i]) for i in range(3)])
    return out


# --------------------------------------------------------------------------
# Step 8 - close the loop
# --------------------------------------------------------------------------

@dataclass
class SeamInfo:
    wrap_gap_m: float
    mean_spacing_m: float
    spacing_spread: float       # (max - min) / mean, over all segments
    seam_angle_deg: float


def close_loop(pts: np.ndarray) -> tuple[np.ndarray, SeamInfo]:
    """Step 8. The loop is left *undoubled* - point 0 is not repeated at the
    end, per the JSON schema ("loop not duplicated").

    "Force the last point to meet the first" is therefore realised as: the
    wrap-around segment is the same length as every other segment, and the
    tangent is continuous across the seam. Step 7's uniform resampling already
    guarantees this; here it is measured so checks F and G can assert on it.
    """
    seg = _chord_lengths(pts, closed=True)
    tan = tangents(pts)
    incoming = pts[0, :2] - pts[-1, :2]
    incoming = incoming / max(float(np.linalg.norm(incoming)), 1e-12)
    cos = float(np.clip(np.dot(incoming, tan[0]), -1.0, 1.0))

    info = SeamInfo(
        wrap_gap_m=float(seg[-1]),
        mean_spacing_m=float(seg.mean()),
        spacing_spread=float((seg.max() - seg.min()) / seg.mean()),
        seam_angle_deg=float(np.degrees(np.arccos(cos))),
    )
    return pts, info


# --------------------------------------------------------------------------
# Step 9 - elevation
# --------------------------------------------------------------------------

def apply_elevation(pts: np.ndarray, mode: str = "zero",
                    window: int = 101, polyorder: int = 2) -> np.ndarray:
    """Step 9. Monza is deliberately flat: `mode='zero'` writes z = 0.

    The `telemetry` path is kept live and working, not commented out - the next
    circuits (Spa, Austin) need it, and CLAUDE.md says not to delete it. The Z
    channel is noisy and not survey-grade, hence the much wider window.
    """
    out = pts.copy()
    if mode == "zero":
        out[:, 2] = 0.0
    elif mode == "telemetry":
        w = min(window, len(out))
        if w % 2 == 0:
            w -= 1
        out[:, 2] = savgol_filter(out[:, 2], window_length=w,
                                  polyorder=polyorder, mode="wrap")
    else:
        raise ValueError("Unknown elevation mode %r." % mode)
    return out


# --------------------------------------------------------------------------
# Step 10 - corners
# --------------------------------------------------------------------------

def corner_arclengths(circuit_info, centreline: np.ndarray,
                      event: str | None = None) -> list[dict]:
    """Step 10. Project each corner marker onto the centreline to get its `s`.

    `centreline` is the FastF1-space (N, 3) loop about to be written. The
    projection is `centreline.project_global` - the exact inverse of the
    renderer's `toWorld`, and the same code `extract_replay.py` projects
    telemetry with. It used to be a nearest-segment projection of its own,
    which measures `d` against the segment normal rather than the interpolated
    tangent's and derives `s` as fractional index times a nominal spacing; that
    round-trips with up to 0.891 m of error. One projection implementation, for
    the same reason there is one `toWorld`.

    It runs in Three.js space on the centreline *as written* - rounded to the
    JSON's 3 decimals - so the `s` it reports is measured on the same polyline
    the viewer and `extract_replay.py` read back.

    circuit_info positions are in the same 1/10 m frame as the telemetry.
    Its `Distance` column is carried through as a cross-check where present;
    it is derived from car telemetry and is not always populated.
    """
    names = CORNER_NAMES.get(event or "", {})
    frame = frame_from_three(np.round(to_three(centreline), 3))
    corners = []
    for _, row in circuit_info.corners.iterrows():
        ff1 = np.array([[row["X"], row["Y"], 0.0]], dtype=float) / 10.0
        p = to_three(ff1)[0, list(PLAN_COLS["three"])]
        s, d, _ = project_global(frame, p)
        offset = abs(d)
        number = int(row["Number"])
        ref = row["Distance"] if "Distance" in row.index else np.nan
        corners.append({
            "number": number,
            "letter": str(row["Letter"] or "") if "Letter" in row.index else "",
            "name": names.get(number),
            "s": round(s, 1),
            "_offsetM": round(offset, 1),
            "_fastf1DistanceM": (None if ref is None or not np.isfinite(ref)
                                 else round(float(ref), 1)),
        })
    corners.sort(key=lambda c: c["s"])
    return corners


# --------------------------------------------------------------------------
# Step 11 - build / write the document
# --------------------------------------------------------------------------

def build_doc(centreline_ff1: np.ndarray, corners: list[dict], *,
              name: str, year: int, width: float,
              rotation_deg: float) -> dict:
    """Step 11. Schema per section 5 of the design doc.

    The written centreline goes through `to_three` here, and the mapping
    itself lives only in `to_three` (step 10 and the checks call it too, so
    they see exactly what ships). `startFinishS` is 0 by
    construction: s = 0 is point 0 of the median lap, i.e. the lap-timing
    boundary. That is close to the painted line but not surveyed to it -
    adequate for the spike, worth knowing before anyone measures against it.
    """
    three = to_three(centreline_ff1)
    length = polyline_length(ground(three, "three"), closed=True)
    return {
        "name": name,
        "year": year,
        "lengthM": round(length, 1),
        "spacingM": round(length / len(three), 4),
        "widthM": width,
        "rotationDeg": round(float(rotation_deg), 2),
        "centerline": [[round(float(v), 3) for v in p] for p in three],
        "corners": [
            {"number": c["number"], "name": c["name"], "s": c["s"]}
            for c in corners
        ],
        "startFinishS": 0.0,
    }


def write_json(doc: dict, path: str) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return str(out)


# --------------------------------------------------------------------------
# Sanity checks - section 4, "Sanity checks before trusting the output"
# --------------------------------------------------------------------------

class CheckFailure(AssertionError):
    """Raised when one or more sanity checks fail."""


def check_a_length(centreline: np.ndarray, expected: float = MONZA_LENGTH_M,
                   tol: float = 0.02) -> str:
    length = polyline_length(centreline, closed=True)
    err = abs(length - expected) / expected
    assert err <= tol, (
        "[A] Track length %.1f m is %.2f%% from the published %.0f m "
        "(tolerance %.0f%%). Suspect step 7 (arc-length resampling) or the "
        "1/10 m -> m conversion in step 3."
        % (length, err * 100, expected, tol * 100))
    return "length %.1f m (%+.2f%% vs %.0f m)" % (length, (
        length - expected) / expected * 100, expected)


def check_b_corner_count(corners: list[dict], expected: int = 11) -> str:
    n = len(corners)
    assert n == expected, (
        "[B] Got %d corners from circuit_info, expected %d for Monza. Suspect "
        "the wrong event was loaded, or circuit_info is unavailable for this "
        "session." % (n, expected))
    return "%d corners" % n


def check_c_corner_monotonic(corners: list[dict]) -> str:
    s = [c["s"] for c in corners]
    bad = [(corners[i]["number"], s[i], corners[i + 1]["number"], s[i + 1])
           for i in range(len(s) - 1) if s[i + 1] <= s[i]]
    assert not bad, (
        "[C] Corner arc lengths are not strictly increasing: %s. Suspect step "
        "10 - a corner marker projected onto the wrong part of the loop, most "
        "likely near the start/finish seam." % (bad,))
    numbers = [c["number"] for c in corners]
    assert numbers == sorted(numbers), (
        "[C] Corners ordered by s give numbering %s, which is not ascending. "
        "The corner sequence does not match the direction of travel - suspect "
        "a reversed lap." % (numbers,))
    return "s increases monotonically, corners %d..%d" % (
        numbers[0], numbers[-1])


def check_d_first_corner(corners: list[dict], lo: float = 700.0,
                         hi: float = 1100.0) -> str:
    """The first corner after start/finish must be the Rettifilo chicane.

    The window brackets ~875 m, which is where FastF1's own telemetry-derived
    `Distance` column puts turn 1 - two independent measurements of the same
    thing, which is why the bound is anchored there rather than on a guess.
    Parabolica sits at ~5180 m, so a reversed lap misses this by a mile.
    """
    first = min(corners, key=lambda c: c["s"])
    assert lo <= first["s"] <= hi, (
        "[D] The first corner after start/finish is at s = %.1f m, outside "
        "the expected %.0f-%.0f m for the Rettifilo chicane. Near 5200 m you "
        "are looking at Parabolica, which means the lap runs backwards "
        "(CLAUDE.md: 'the corner sequence runs backwards')."
        % (first["s"], lo, hi))
    return "first corner at s = %.1f m (%s)" % (first["s"], first["name"])


def check_k_corner_cross_reference(corners: list[dict], length: float,
                                   expected: float = MONZA_LENGTH_M,
                                   tol: float = 0.02) -> str:
    """Cross-check every corner against FastF1's own `Distance` column.

    That column is integrated from car telemetry, so it is derived entirely
    independently of the projection in step 10. Compared as a *fraction* of
    lap length, because the two references disagree slightly on total length
    and an absolute tolerance would drift with s.
    """
    pairs = [(c, c["_fastf1DistanceM"]) for c in corners
             if c.get("_fastf1DistanceM") is not None]
    if not pairs:
        return "skipped - FastF1 supplied no Distance column"
    errs = [(c["number"], c["s"] / length, ref / expected,
             abs(c["s"] / length - ref / expected)) for c, ref in pairs]
    number, mine, theirs, worst = max(errs, key=lambda e: e[3])
    assert worst <= tol, (
        "[K] Corner %d sits at %.2f%% of the lap by projection but %.2f%% by "
        "FastF1's telemetry Distance - a %.2f%% disagreement (tolerance "
        "%.0f%%). Suspect step 10 projecting onto the wrong part of the loop."
        % (number, mine * 100, theirs * 100, worst * 100, tol * 100))
    return ("%d corners agree with FastF1 Distance to within %.2f%% of lap "
            "(worst: corner %d)" % (len(pairs), worst * 100, number))


def check_e_handedness(plan_three: np.ndarray) -> str:
    area = signed_area(plan_three)
    sense = "clockwise" if area > 0 else "counter-clockwise"
    assert np.sign(area) == EXPECTED_AREA_SIGN, (
        "[E] The (x, z) loop is %s (signed area %.0f m^2), but Monza runs "
        "clockwise. The track is MIRRORED - check the minus sign in "
        "to_three(): three.z must be -ff1.Y, not +ff1.Y." % (sense, area))
    return "%s, signed area %.3f km^2" % (sense, area / 1e6)


def check_f_uniform_spacing(centreline: np.ndarray, tol: float = 0.01) -> str:
    seg = _chord_lengths(centreline, closed=True)
    mean = float(seg.mean())
    worst = float(np.max(np.abs(seg - mean)) / mean)
    assert worst <= tol, (
        "[F] Segment lengths vary by %.2f%% about the mean %.3f m (tolerance "
        "%.0f%%); the wrap segment is %.3f m. `s` is only meaningful if "
        "spacing is uniform - suspect step 7."
        % (worst * 100, mean, tol * 100, seg[-1]))
    return ("spacing %.3f m, worst deviation %.3f%%, wrap segment %.3f m"
            % (mean, worst * 100, seg[-1]))


def check_g_seam_tangent(seam: SeamInfo, tol_deg: float = 5.0) -> str:
    assert seam.seam_angle_deg <= tol_deg, (
        "[G] The tangent turns %.2f deg across the start/finish seam "
        "(tolerance %.0f deg). The loop has a visible kink at s = 0 - suspect "
        "step 8, or a lap in step 2 whose start and end do not line up."
        % (seam.seam_angle_deg, tol_deg))
    return "seam tangent discontinuity %.2f deg" % seam.seam_angle_deg


def check_h_well_formed(centreline: np.ndarray, spacing: float) -> str:
    assert np.isfinite(centreline).all(), (
        "[H] The centreline contains NaN or Inf. Suspect an interpolation "
        "blowup in step 4 or 7, or a lap with too few samples.")
    zeros = int(np.sum((centreline[:, 0] == 0.0) & (centreline[:, 1] == 0.0)))
    assert zeros == 0, (
        "[H] %d centreline points sit exactly at the plan-view origin. Step "
        "3's zero-sample filter let something through and the spline is being "
        "dragged to the origin (CLAUDE.md gotcha)." % zeros)
    seg = _chord_lengths(centreline, closed=True)
    assert seg.min() > spacing / 10.0, (
        "[H] Shortest segment is %.4f m, under a tenth of the %.1f m spacing "
        "- there are near-duplicate points." % (seg.min(), spacing))
    return "%d points, all finite, no origin samples" % len(centreline)


def check_i_lap_agreement(devs: np.ndarray, tol_m: float = 25.0) -> str:
    worst = float(devs.max())
    assert worst <= tol_m, (
        "[I] One selected lap deviates up to %.1f m from the median "
        "(tolerance %.0f m). The track is ~13 m wide, so this is not a racing "
        "line - suspect a pit-lane or off-track lap surviving step 2's "
        "filters, which would bias the median." % (worst, tol_m))
    return "%d laps, worst deviation %.1f m, median %.1f m" % (
        len(devs), worst, float(np.median(devs)))


def check_j_elevation(centreline: np.ndarray, mode: str) -> str:
    if mode == "zero":
        bad = int(np.sum(centreline[:, 1] != 0.0))
        assert bad == 0, (
            "[J] Elevation mode is 'zero' but %d points have non-zero height. "
            "Suspect step 9." % bad)
        return "y = 0 everywhere (Monza is flat; telemetry path retained)"
    span = float(centreline[:, 1].max() - centreline[:, 1].min())
    return "elevation from telemetry, range %.2f m" % span


def run_checks(checks: Sequence[tuple[str, Callable[[], str]]]) -> bool:
    """Run every check, report all of them, then raise if any failed.

    Deliberately not fail-fast: one failure should not hide the other nine,
    and the plot is more useful alongside a full picture of what broke.
    """
    failures: list[str] = []
    print("\n  Sanity checks")
    print("  " + "-" * 74)
    for label, fn in checks:
        try:
            print("  PASS  %-18s %s" % (label, fn()))
        except AssertionError as exc:
            print("  FAIL  %-18s %s" % (label, exc))
            failures.append(str(exc))
    print("  " + "-" * 74)
    print("  %d/%d passed\n" % (len(checks) - len(failures), len(checks)))
    if failures:
        raise CheckFailure(
            "%d sanity check(s) failed; refusing to write JSON.\n%s"
            % (len(failures), "\n".join("  - " + f for f in failures)))
    return True


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

def run_pipeline(args) -> dict:
    stages = StageWriter(args.stage_dir)

    enable_cache(args.cache)
    print("  cache      %s" % args.cache)
    print("  loading    %d %s %s (slow on a cache miss)..."
          % (args.year, args.event, args.session))
    session = load_session(args.year, args.event, args.session)

    laps = pick_laps(session, max_laps=args.max_laps,
                     per_driver=args.per_driver)
    drivers = sorted({lap["Driver"] for lap in laps})
    print("  step 2     %d laps from %d drivers: %s"
          % (len(laps), len(drivers), ", ".join(drivers)))

    raw = []
    for lap in laps:
        xyz = lap_positions(lap)
        if len(xyz) >= 4:
            raw.append(xyz)
            stages.array("03_lap_%s_%d" % (lap["Driver"], int(lap["LapNumber"])),
                         xyz)
    counts = [len(x) for x in raw]
    print("  step 3     %d usable laps, %d-%d samples each "
          "(~%.1f m between samples)"
          % (len(raw), min(counts), max(counts),
             MONZA_LENGTH_M / float(np.mean(counts))))

    normalised = np.stack([resample_relative(x, args.n_resample) for x in raw])
    stages.array("04_normalised", normalised)
    grid = MONZA_LENGTH_M / args.n_resample
    print("  step 4     resampled to %d points (~%.2f m grid)"
          % (args.n_resample, grid))

    median = median_laps(list(normalised))
    stages.array("05_median", median)
    devs = lap_deviations(list(normalised), median)
    print("  step 5     median across laps, worst lap deviation %.1f m"
          % devs.max())

    print("  step 6     savgol window=%d polyorder=%d mode=wrap -> %.0f m "
          "of track" % (args.savgol_window, args.savgol_polyorder,
                        args.savgol_window * grid))
    smoothed = smooth_loop(median, args.savgol_window, args.savgol_polyorder)
    stages.array("06_smoothed", smoothed)

    arclen = resample_arclength(smoothed, args.spacing)
    stages.array("07_arclen", arclen)
    print("  step 7     %d points at %.3f m spacing"
          % (len(arclen), polyline_length(arclen) / len(arclen)))

    closed, seam = close_loop(arclen)
    stages.array("08_closed", closed)
    print("  step 8     seam gap %.3f m, tangent %.2f deg"
          % (seam.wrap_gap_m, seam.seam_angle_deg))

    final = apply_elevation(closed, mode=args.elevation)
    stages.array("09_centreline", final)
    print("  step 9     elevation mode '%s'" % args.elevation)

    circuit_info = session.get_circuit_info()
    if circuit_info is None:
        raise RuntimeError("circuit_info unavailable for this session.")
    realised = polyline_length(final, closed=True) / len(final)
    corners = corner_arclengths(circuit_info, final, event=args.event)
    stages.doc("10_corners", corners)
    print("  step 10    %d corners, max projection offset %.1f m"
          % (len(corners), max(c["_offsetM"] for c in corners)))

    rotation = getattr(circuit_info, "rotation", 0.0) or 0.0
    doc = build_doc(final, corners, name=args.event, year=args.year,
                    width=args.width, rotation_deg=rotation)
    # Checks run on the Three.js-space output - the artefact that actually
    # ships - not on the ff1-space intermediate, so a mistake in to_three()
    # cannot slip past them.
    three = to_three(final)
    plan = ground(three, "three")

    run_checks([
        ("A length", lambda: check_a_length(plan)),
        ("B corner count", lambda: check_b_corner_count(corners)),
        ("C corner order", lambda: check_c_corner_monotonic(corners)),
        ("D first corner", lambda: check_d_first_corner(corners)),
        ("E handedness", lambda: check_e_handedness(plan)),
        ("F uniform spacing", lambda: check_f_uniform_spacing(plan)),
        ("G seam tangent", lambda: check_g_seam_tangent(seam)),
        ("H well formed", lambda: check_h_well_formed(plan, realised)),
        ("I lap agreement", lambda: check_i_lap_agreement(devs)),
        ("J elevation", lambda: check_j_elevation(three, args.elevation)),
        ("K corner cross-ref", lambda: check_k_corner_cross_reference(
            corners, polyline_length(plan, closed=True))),
    ])
    return doc


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Extract a track centreline from FastF1 position data.")
    p.add_argument("--year", type=int, default=2024)
    p.add_argument("--event", default="Monza")
    p.add_argument("--session", default="R")
    p.add_argument("--out", default="public/tracks/monza.json")
    p.add_argument("--cache", default=".fastf1-cache")
    p.add_argument("--stage-dir", default=None,
                   help="dump every intermediate stage here for inspection")
    p.add_argument("--n-resample", type=int, default=2000)
    p.add_argument("--savgol-window", type=int, default=15)
    p.add_argument("--savgol-polyorder", type=int, default=3)
    p.add_argument("--spacing", type=float, default=5.0)
    p.add_argument("--width", type=float, default=13.0)
    p.add_argument("--max-laps", type=int, default=20)
    p.add_argument("--per-driver", type=int, default=3)
    p.add_argument("--elevation", default="zero", choices=["zero", "telemetry"])
    p.add_argument("--dry-run", action="store_true",
                   help="run everything and report checks, but write no JSON")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    print("\n  extract_track  %s %d (%s)" % (args.event, args.year, args.session))
    print("  " + "=" * 74)
    try:
        doc = run_pipeline(args)
    except CheckFailure as exc:
        print("\n  %s\n" % exc, file=sys.stderr)
        return 1

    if args.dry_run:
        print("  DRY RUN - not writing %s\n" % args.out)
    else:
        print("  wrote      %s (%d points)\n"
              % (write_json(doc, args.out), len(doc["centerline"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
