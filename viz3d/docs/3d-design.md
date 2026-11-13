# 3D visualisation — design notes

Scope: a standalone spike. One circuit (Monza, 2024), rendered in Three.js, with
cars moving along it. No backend, no simulation engine, no 2D integration.

The point is to learn the tooling and to prove out the one architectural
decision that the group project depends on: positioning cars by distance-along-
track rather than by world coordinates.

---

## 1. Why Monza

- Effectively flat, so elevation can be stubbed to zero without looking wrong.
- Simple layout: long straights, four braking zones, no tunnels or GPS
  blackspots.
- High speed makes camera work read well, which makes progress visible.

Once the pipeline works, additional circuits are mostly a re-run of the
extraction script. Spa or Austin next, for elevation; a street circuit after
that, for walls.

---

## 2. Architecture

```
FastF1 session  ──(offline, python)──>  public/tracks/monza.json  ──>  viewer
                  scripts/extract_track.py                            (R3F)
```

Extraction runs **once** and its output is committed. The viewer is a static
site with no Python dependency and no network calls at runtime. This keeps the
spike self-contained and makes it trivial to hand to a teammate.

Later, the group project replaces the hand-written motion source with a live
event stream. Nothing about the track geometry or the `(s, d)` mapping changes.

---

## 3. The `(s, d)` model

A car's state on track is two numbers:

- `s` — arc length along the lap, metres, `0` at start/finish, wrapping at
  track length.
- `d` — lateral offset from the centreline, metres, positive to the right of the
  direction of travel.

World position comes from evaluating the track spline at `s` to get a point and
a tangent, building a frame `(tangent, right, up)`, and offsetting by `d` along
`right`. Car heading is the tangent, plus a small yaw when `d` is changing.

**It is a road frame, not the textbook Frenet frame.** The Frenet normal is
`dt/ds`, which points to the inside of the turn, is undefined on a straight,
and flips sign wherever curvature crosses zero — on Monza that is every
straight and the midpoint of every chicane. Anything placed on the ribbon with
such a frame inverts at each of those points. `src/track/frame.ts` derives the
frame from a fixed world up instead:

```
right = normalize(tangent × up)      up = normalize(right × tangent)
```

so `up` is constant on a flat circuit and will vary only with banking. Signed
curvature is computed *from* this frame, never the reverse.

Why this matters:

- The eventual simulator produces lap times, positions and gaps — quantities
  that are naturally 1D. It should emit `(s, d)`, not coordinates.
- Overtakes become "car A's `d` crosses car B's `d` while the gap in `s`
  closes". Trivially detectable, trivially animatable.
- Track geometry can be swapped without touching anything that generates motion.
- The 2D view in the group project can consume the identical stream.

---

## 4. Track extraction pipeline

`scripts/extract_track.py`, roughly:

1. **Load.** `fastf1.get_session(2024, 'Monza', 'R')`, `session.load()`. Enable
   the cache first. Position data is available from 2018 onward.

2. **Pick laps.** Take quick laps only (`laps.pick_quicklaps()`), excluding
   in-laps, out-laps and anything under safety car. Aim for 10–20 laps across
   several drivers.

3. **Per lap:** `lap.get_pos_data()`, drop rows where `Status` is not `OnTrack`,
   drop `(0, 0)` samples, convert from 1/10 m to metres.

4. **Normalise.** Resample each lap to a fixed `N` points by *relative* distance
   (0 to 1 around the lap) so laps of different sample counts align.

5. **Median.** Take the per-point median of `X` and `Y` across laps. This
   approximates the centreline: individual laps follow the racing line and cut
   apexes, but the deviations partly cancel. It is not a survey, and it is good
   enough at this scale.

6. **Smooth.** `scipy.signal.savgol_filter` over the closed loop — `mode='wrap'`
   handles the ends, no need to pad by hand. Tune against the Rettifilo
   chicane; over-smoothing rounds it off.

   A window in *points* means nothing on its own — what matters is its width
   in metres, which depends on the step-4 grid. Pick the metres first, then
   derive the point count. Measured on Monza 2024, peak curvature retained
   through the chicane's tighter apex:

   | window | metres | peak curvature retained |
   |--------|--------|-------------------------|
   | 9 | 26 m | 110% — still passing noise through |
   | 15 | 43 m | 101% |
   | 21 | 61 m | 91% |
   | 31 | 90 m | 77% — visibly rounded |

   So: around 40–45 m. At `N = 2000` (≈2.9 m grid) that is window 15.

   **Polynomial order is not a knob.** For smoothing (`deriv=0`) the
   Savitzky-Golay coefficients for order 2k and 2k+1 are identical — over a
   symmetric window the odd-degree term is antisymmetric and contributes
   nothing at the centre point. Orders 2 and 3 are the same filter, measured
   difference 7e-13 m. Order would only start to matter at 4+, which is too
   flexible for this noise level. Only the window does anything.

   **Values used for the committed `monza.json`:** `--savgol-window 15`,
   `--savgol-polyorder 3`, `mode='wrap'`, on the `--n-resample 2000` grid — so
   a 43 m window. The elevation path, unused for Monza but live for later
   circuits, smooths `Z` separately with window 101 and polyorder 2; the `Z`
   channel is much noisier than the plan view and needs the wider window.

7. **Resample by arc length.** Re-parameterise to uniform spacing of ~5 m. This
   is what makes `s` meaningful. Compute cumulative chord length, then
   interpolate to a uniform grid.

8. **Close the loop.** Read this together with the schema in section 5 ("loop
   not duplicated"): point 0 is *not* repeated at the end. Closing the loop
   means the wrap-around segment is the same length as every other segment and
   the tangent is continuous across the seam — not that there is a duplicate
   vertex. Step 7 gives this for free if the point count is `round(L /
   spacing)`, since the realised spacing is then `L / K` and the loop closes
   exactly. Measured: wrap segment 5.002 m against a 5.002 m mean, seam
   tangent 0.01°.

9. **Elevation.** For Monza, write `z = 0`. The `Z` channel exists in the
   telemetry but is noisy and not survey-grade; it needs heavy smoothing and is
   only worth the effort on circuits where elevation is a feature.

10. **Corners.** `session.get_circuit_info()` gives corner locations, marshal
    lights and marshal sectors, plus a rotation angle that aligns the telemetry
    coordinate system with the official track map orientation. It is manually
    created and not highly accurate, but it is fine for annotation. Project each
    corner onto the centreline to get its `s`.

    Two things it does *not* give. Corner **names** — only `Number` and an
    optional `Letter`, so names are hand-written in `CORNER_NAMES` and are
    annotation only. And its positions are in the same 1/10 m frame as the
    telemetry, so they need the same conversion. Project with
    `scripts/centreline.py`'s `project_global` — the exact inverse of the
    renderer's `(s, d) → world` mapping derived in section 6B, and the same
    code `extract_replay.py` projects telemetry with. One projection
    implementation, for the same reason there is one `toWorld`.

    This used to be a nearest-*segment* projection of its own, which the first
    cut wrongly called that inverse: it measures `d` against the segment
    normal rather than the interpolated tangent's (they differ by up to 7.93°
    on Monza) and round-trips with up to 0.891 m of error. Corner markers sit
    within 0.7 m of the centreline, where the difference is small: switching
    moved T2 from 944.1 to 944.0 m and left the other ten unchanged at 0.1 m
    resolution.

    The `Distance` column is worth carrying through as a cross-check: it is
    integrated from car telemetry, so it is derived independently of the
    projection. On Monza 2024 the two agree to within 1.02% of lap length.

11. **Write JSON.**

### Sanity checks before trusting the output

Written as real assertions in `extract_track.py`, each carrying the measured
value and the step to suspect, run through a harness that reports all of them
rather than failing fast — one failure shouldn't hide the rest. Writing the
JSON is gated on all of them passing.

- Total length ≈ 5793 m for Monza, and expect to land slightly **under** it:
  the median of racing lines cuts apexes, so the centreline is short by
  construction. Measured 5756.9 m, −0.62%. More than a percent or two in
  either direction means the resampling is wrong.
- Corner `s` values are monotonically increasing in the order 1…11.
- The first corner after start/finish is the Rettifilo chicane, at **~875 m** —
  not the ~600 m the long main straight might suggest. FastF1's own `Distance`
  column puts turn 1 at 873.8 m against 888.9 m by projection, which is a
  usefully independent second opinion.
- **Mirrored and reversed are different failures and need different checks.**
  A reversed lap keeps the shape but runs the corner sequence backwards —
  caught by corner 1 landing near 875 m instead of near Parabolica at ~5180 m.
  A mirrored track (the dropped minus in `three.z = -ff1.Y`) keeps the corner
  order but reflects the shape, so the corner check passes happily. Only the
  sign of the loop's signed area catches it: Monza runs clockwise, which in
  Three.js `(x, z)` is a positive shoelace area. Confirm that sign against the
  plot once rather than deriving it on paper — it is easy to invert a
  convention and then assert the inverted version.
- Watch which two columns you measure with. In FastF1 space the ground plane
  is `(X, Y)`; in Three.js space Y is up, so it is `(x, z)`. Using `[0, 1]` on
  a Three.js array silently measures along the elevation axis, which on a flat
  circuit reports roughly half the true lap length instead of erroring.
- Plot it in matplotlib before ever loading it into Three.js. Debugging geometry
  in a 3D scene is much harder than debugging it in a 2D plot. Plot **curvature
  against `s`** as well as the plan view — a chicane can look perfectly fine in
  plan while its curvature peaks have been shaved off, and at map scale the
  difference between a good window and a bad one is a couple of metres.

---

## 5. Track JSON schema

Values below are the ones actually produced for Monza 2024, not illustrations.

```jsonc
{
  "circuit": "monza",          // id; reference.ts is keyed by this, not by name
  "name": "Monza",
  "year": 2024,
  "lengthM": 5756.9,           // measured; the published figure is 5793
  "spacingM": 5.0017,          // L / N, not exactly 5 - that is what closes the loop
  "widthM": 13.0,              // constant for v0; per-point later
  "rotationDeg": 95.0,         // from circuit_info, for map-aligned views
  "centerline": [              // metres, arc-length ordered, loop not duplicated
    [x, y, z],                 // Three.js space: y is up and 0 throughout for Monza
    ...
  ],
  "corners": [
    { "number": 1, "name": "Variante del Rettifilo (1)", "s": 888.9 }
  ],
  "startFinishS": 0.0
}
```

`circuit` was added in phase 0 (docs/phase0-geometry-report.md), when the
engine's frozen `Monza_v1` had to be checked against the same Monza facts under
a different name. Converted engine tracks also carry `variant`, `year: null`,
`uniformSpacing: false` with `spacingMinM` / `spacingMaxM` (their vertices are
kept verbatim at 2-4 m, and `frame.ts` never assumed uniform spacing), and a
`source` provenance block.

1151 points at 5.0017 m spacing, 54 KB. Well under 200 KB; fine to commit and
fine to parse at load. If it ever matters, switch to flat `Float32Array` in a
binary blob, but not before it matters.

Note `spacingM` is `lengthM / 1151`, deliberately not the 5.0 that was asked
for. Forcing exactly 5 m would leave a short or long segment at the seam and
break the uniformity that makes `s` meaningful; letting the spacing float by a
couple of millimetres keeps every segment equal instead.

`startFinishS` is 0 by construction, but `s = 0` is point 0 of the median lap —
the lap-timing boundary, not the surveyed painted line. Close enough for the
spike; worth knowing before anyone measures against it.

---

## 6. Motion source for the spike

No simulator yet. Two stand-ins, in order:

**A. Synthetic.** Each car gets a constant base speed plus a small per-corner
slowdown derived from local curvature, and a fixed `d` offset so the field
doesn't overlap. Enough to exercise the rendering path.

M3 ships the degenerate case of this: one car, constant 60 m/s, `d` held at
whatever the slider says. No curvature slowdown yet — it would have made the
one thing under test, that `s` advances smoothly and wraps cleanly, harder to
read rather than easier.

**B. Real telemetry replay.** M6. Project actual position samples onto the
centreline to recover `(s, d)` per car per timestamp. This is the more
interesting one, because the projection step (world → `(s, d)`) is exactly the
inverse of what the renderer does, and getting both directions consistent
validates the whole model.

`scripts/extract_replay.py`, a sibling of the extractor rather than an extension
of it: track geometry and session replay are different artifacts with different
lifetimes. It reads `public/tracks/monza.json` rather than re-deriving the
centreline, because the viewer reads that file and a round trip against a
differently-derived centreline would measure the difference between two
centrelines instead of the projection.

### The inverse is an identity, and the obvious implementation is not

The renderer places a car at `c(s) + d * rhat(s)`, where `rhat` is built from the
**interpolated** tangent (`sampleAt`). So recovering `(s, d)` means solving

```
f(t) = (p - c(t)) . that(t) = 0 ,   then   d = (p - c(t)) . rhat(t)
```

on the containing segment — *not* finding the nearest point on the polyline.
`project_naive` — what step 10 above used for corner markers until it moved to
the refined projector — computes the nearest point, and it is wrong for this in two ways: it measures `d`
perpendicular to the **segment**, and it derives `s` as a fractional index times
a nominal spacing, which assumes the uniform spacing `frame.ts` deliberately
refuses to assume.

The cost of the segment normal is larger than it looks. The chord and the
interpolated tangent differ by up to half the per-segment tangent turn, which
peaks at **15.51° at s = 930** (Rettifilo T2), so α reaches **7.93° at s = 935**.
Measured over 22,145 probes — every 1.3 m round the lap at five values of `d` —
the naive projection round-trips with a maximum error of **0.891 m**, at
s = 936, d = +6.5. The refined one: **1.0e-12 m**, i.e. float noise.

That is the useful thing to know about this function: with `y = 0` on the
centreline, `rhat` and `that` span the plane, so the solution reproduces `p`
*exactly*. It is an identity, not an approximation, and check N's tolerance is a
precision tolerance (1e-9 m) rather than a geometric one. Anything above it is a
bug. `f` is strictly monotone on a segment (`f' = -segLen * (cos α - d·κ)`, with
`cos α ≥ 0.990` and measured `max |d·κ| = 0.041`), so four Newton steps from the
midpoint converge with no bisection and no risk of oscillation.

**The round trip is plan-view only, and that is structural.** Telemetry `Z` at
Monza spans 184.2–196.7 m — the circuit's height above sea level — while the
committed centreline's `y` is identically 0 by construction. A three-dimensional
residual would measure that datum and nothing about the projection. The fixture
stores two columns, not three, so there is no third number for a reader to
wonder about.

### The search window is insurance, not a fix

The plan was to constrain the nearest-point search to a window around the
previous `s`, on the grounds that Ascari and the Rettifilo double back enough
for a global search to jump. **Measured, that does not happen on Monza.** For
centreline points more than `W` apart along the lap, the closest they come in the
plan:

| W | closest approach | where |
|---|---|---|
| 25 m | 23.6 m | s 920 ↔ 945 — the Rettifilo |
| 100 m | 82.8 m | s 900 ↔ 1000 |
| 200 m | 162.0 m | s 5047 ↔ 5247 — Parabolica across its own chord |
| 1200 m | 268.5 m | the global floor |

A wrong match needs the two stretches to be within `2 |d|` of each other. The
tightest self-approach on the lap *is* at the Rettifilo, so the instinct about
where was right — but at 23.6 m it would take a car 11.8 m off the centreline to
be mis-assigned, against a 6.5 m half-width. Ascari does not appear at all; its
doubling-back is too wide to come near itself. Check L confirms the stronger
version directly: over 3,990 real samples the windowed answer is **identical** to
an unconstrained one.

The window stays, because it is still the right algorithm for a stateful sweep,
because the branch it searches is what makes `s` come out unwrapped without a
separate lap-counting pass, and because a street circuit will have the ambiguity
Monza lacks. It is recorded here as measured headroom rather than as a fix.

What the window did need was a better centre. Anchoring on the previous sample
fails: the per-sample advance has a p99.9 of 75.7 m and a maximum of 314.7 m, so
2.18% of samples escape a ±40 m window. Centring on a **velocity prediction**
drops that to 0.005%. Predict-then-correct is the design; the width is secondary.

### The position stream has a good clock problem, not a bad position problem

The single most useful measurement in this milestone. Consecutive raw samples
routinely imply 130–150 m/s against a real Monza peak near 98, and 5.75% of steps
exceed 105 m/s. The first cut treated those as position glitches and rejected
them, which threw away **6.5% of the race**.

They are not position glitches. The implied speeds come in pairs — a fast step
followed by a slow one — and over a 1 s baseline **0.00%** of steps exceed
105 m/s, with a maximum of 106.5. The timestamps arrive quantised to 20 ms with
roughly ±0.12 s of scatter about the true sampling instant; the coordinates are
fine. Two consequences run through the whole script:

- **Nothing is rejected on a per-step speed test.** The guard tests displacement
  over a jitter-widened interval, and over the race window of all twenty cars it
  rejects **0 of 356,040 samples**. It stays only so that a session with a genuine
  dropout cannot pass silently.
- **`s` is estimated, not interpolated.** Linear interpolation through jittery
  timestamps puts the jitter straight into the output as ±7 m of along-track
  position at racing speed.

### Estimating `s`, and why `d` is resampled against something else

`s` comes from a smoothing spline against time (`make_smoothing_spline`,
λ = 1.2), chosen as the **least** smoothing for which no grid step is physically
impossible:

| λ | steps over 105 m/s | speed sd vs FastF1 | departure from raw |
|---|---|---|---|
| 0.25 | 0.049% | 2.47 m/s | 20.7 m |
| 0.60 | 0.012% | 2.30 | 21.8 |
| **1.20** | **0.000%** | **2.37** | 23.0 |
| 2.00 | 0.000% | 2.57 | 24.2 |

A spline rather than a window filter, and that distinction was earned: local
quadratic fits over ±1.1 s left 0.14–0.88% of grid steps implying over 105 m/s,
because a fit evaluated independently at each grid point has no reason to agree
with its neighbour and the fitted series carries fit-to-fit wiggle that
differentiates into noise. Tricube weighting made it worse, not better. One
spline over the whole series has no such seam. Braking survives: the minimum
speed through the Rettifilo lands within 1 m/s of the reference channel.

**`d` is interpolated against arc length, not time**, and this is not a detail.
The systematic part of `d` swings 1.7 m across the 25 m of the Rettifilo, while
the smoothing scale is over 100 m of track at racing speed — so smoothing `d` in
time would flatten exactly the feature the lateral report exists to measure.
Measured: the profile spans −0.93 to +0.80 m resampled against arc length,
against −0.77 to +0.67 smoothed in time. 13% of the signal, thrown away for
nothing.

### Output rate: 5 Hz

The source median `dt` is **0.240 s (4.17 Hz)**, p99 0.480, max 1.799. 5 Hz is the
coarsest round rate at or above the source's own, and it divides a second exactly
so a timeline tick is an integer number of samples and the viewer needs no search
— `index = floor(t * hz)`. Resampling above the source rate buys bytes and no
information: measured reconstruction error at the source's own timestamps is
0.76 m at 2 Hz, 0.36 at 4 Hz, **0.27 at 5 Hz**, 0.08 at 10 Hz for double the
bytes.

### Schema

The row-oriented draft this section used to carry — `frames: [{t, cars: [...]}]`
— is 42,500 repeated key sets at twenty cars and five laps. Columnar per car,
integer channels, minified (unlike the track file's `indent=1`: 42,500 integers
is not a file anyone reads by eye):

```jsonc
{
  "name": "Monza", "year": 2024, "session": "R",
  "trackLengthM": 5756.9425,   // parseReplay refuses a mismatched centreline
  "hz": 5,
  "t0S": 3438.4,               // session time of sample 0
  "samples": 2243,             // per car, identical for every car
  "fromLap": 2, "toLap": 6,
  "pitAbsDM": 8.0,
  "cars": [
    {
      "code": "ALB", "name": "Alexander Albon",
      "s0M": 28426.89,
      "dsMm": [ … ],           // samples-1 ints, millimetre along-track deltas
      "dCm":  [ … ],           // samples ints, absolute centimetres
      "lapNumber": [2, 3, 4, 5, 6, 7],
      "lapStartS": [ … ],      // unwrapped metres, official timing boundary
      "lapStartT": [ … ]       // seconds since t0S
    }
  ]
}
```

19 cars × 2243 samples, **379 KB**, about 76 KB a lap. Larger than the 54 KB
track and above the "well under 200 KB" remark in section 5 — that remark was
about a file a human reads. The lever if it ever matters is `--to-lap`, not the
rate or the precision; the binary escape hatch section 5 anticipates would
trigger at the whole race, which is 3.5 MB of JSON against 1.8 MB of `int16`.

Three things are deliberately absent.

**No speed channel.** The viewer derives it from `s`, so it cannot disagree with
the rate `s` advances — which matters because `rig.ts` feeds `speedMps` forward
into the chase camera's anchor, where an inconsistency becomes a steady-state
offset from the car. A plain central difference, no smoothing: because `s` is
already a spline, adding a boxcar changed the agreement with FastF1's independent
`Speed` channel from sd 1.99 to 2.02 m/s, i.e. not at all. So there is no
smoothing constant that has to be kept identical in two languages.

The agreement is the useful number, because `Speed` comes from car telemetry and
knows nothing about the centreline or the projection: per-car bias runs
**-0.07 to +0.28 m/s**, at worst 0.41% of a lap average, with sd 1.8-3.1 m/s and
correlation 0.989-0.996. A bias that small is an independent confirmation that
the projection and the lap length are right to about four parts in a thousand.

**No colour.** The viewer assigns `PALETTE[floor(i / 2) % 10]` by car index
exactly as `buildField` does, so the rule about liveries in CLAUDE.md lives in the
file that renders. Cars are written in race order, so the swatch row doubles as a
running order.

**No per-sample lap number.** `lapStartS` is five numbers per car instead of
2,243, and lap number is recoverable exactly with a search. It also keeps the two
lap numbers distinct, which they are: the official timing boundary and the
geometric `s = 0` crossing disagree by **up to 13.1 m** (mean −0.5, sd 2.9), which
is the `startFinishS` caveat in section 5, now measured. An index would have
silently changed meaning if `--hz` changed; `s` does not.

### Picking the window

`--from-lap` defaults to scoring every candidate window and taking the cleanest:
a car is kept if it has a timed lap for every lap of the window and never leaves
the ribbon during it. Pit visits are detected from `|d| > 8 m` rather than from
FastF1's pit columns — Monza's pit lane runs parallel to the start of the main
straight about 18 m to the right of the centreline, so the projection already
knows, and using it cross-checks `d` at the same time.

Chosen: **laps 2–6, 19 cars, 448.6 s**. One car is dropped for pitting on laps 5
and 6; one retired on lap 7 and so has no timed laps after it. Ties are broken
towards the earlier window, because the field is still closed up early in a race.

Two race-messiness items turn out not to exist here and are recorded so nobody
implements them speculatively: `session.track_status` has exactly one row,
`AllClear`, so there is **no safety car** in this race at all; and 42% of the
session is pre-race, which the window clipping removes.

### What the lateral offsets actually say

The question the milestone existed to answer: the centreline is a median across
racing lines rather than a survey, so `d` carries a systematic component. Over
33,497 on-track samples, in metres, positive to the right of travel:

| p0.1 | p5 | p50 | p95 | p99.9 |
|---|---|---|---|---|
| −0.97 | −0.39 | **−0.06** | +0.16 | +0.84 |

mean **−0.088**, sd **0.187**, max |d| 1.035.

Split into a systematic profile — mean `d` per centreline sample, shared by the
whole field — and a residual, the profile spans **−0.928 m at s = 905 to +0.795 m
at s = 930** and explains **95.5%** of the variance. Both extremes are 25 m apart
and both are the Rettifilo, which is exactly where the 43 m Savitzky-Golay window
rounds the chicane off (step 6). Worst corner means: Rettifilo T1 −0.34,
Parabolica −0.31, Ascari T9 −0.26, Lesmo 1 −0.25, Lesmo 2 −0.24. The straights
are clean to 7 cm.

**So the systematic offset is ±0.93 m worst case and 0.29 m at p90, localised
almost entirely at one chicane, on a 13 m ribbon with a 2.0 m car. It does not
matter.**

The consequence that *does* matter was not expected. Once the shared profile is
removed the residual has an sd of **0.040 m**, and every one of the 19 cars has a
mean `d` between −0.085 and −0.093 m. Real telemetry against this centreline
carries almost no lateral information: cars drive in single file and will
visually intersect whenever two of them are close. That is a property of
measuring against a median of racing lines, not a bug to hunt — and it is why the
synthetic field stays selectable rather than being replaced. It is the only thing
on screen that exercises `d` across the width of the ribbon.

---

## 7. Rendering notes

**Track ribbon.** Build a `BufferGeometry` directly rather than using
`ExtrudeGeometry` — you want per-vertex control for width variation and banking
later. For each centreline point, emit two vertices at `±width/2` along the
normal, then index them as a triangle strip. Add a second, wider, lower ribbon
underneath for run-off, and a third thin one at the edges for kerbs.

Built in `src/track/ribbon.ts` as of M2: two vertices per sample, the strip
wrapping back into sample 0 so the start/finish seam is a shared edge, `uv.x` =
lap fraction and `uv.y` = 0 (left) to 1 (right). The winding is anti-clockwise
seen from above, which is front-facing for an upward normal — reverse it and
the track disappears under any single-sided material.

**Verifying orientation in the viewer.** `src/track/verify.ts` re-runs the
extractor's geometric checks at load time and shows them in an overlay. This is
not redundant with `extract_track.py`: those checks prove the JSON was right
when it was *written*, whereas these prove the viewer's own frame convention
agrees with it. `buildFrame` fixes the handedness as `right = tangent × up`,
and car placement, chase cameras and overtake detection all read `right` out of
it, so a correct JSON buys nothing if that sign is wrong.

**Expected values never come from the artifact.** The first cut of these
checks compared the measured lap length against `lengthM` *from the same JSON*,
and located the first corner as a fraction of that same measured length. Both
passed unconditionally: one script wrote every number in the file in one pass,
so the file always agrees with itself. A JSON scaled by 1.1 throughout — wrong
geometry, perfectly self-consistent — sailed through.

Everything the checks expect now lives in `src/track/reference.ts`, keyed by
the JSON's `circuit` id (never its display name): published
circuit length, corner count, the window the first corner falls in, the sense
of rotation, per-corner handedness. Nothing in that file is derived from
`monza.json`. A check may still assert a *property* against the artifact alone
— corner numbers ascending, total turn summing to one revolution — because a
property is not a measurement, and there is nothing external to compare it to.

The rule generalises past this milestone: if the simulator ever validates its
own output, the expected values come from somewhere the simulator did not
write.

Two checks are worth calling out:

- **Per-corner handedness.** Curva Grande, both Lesmos and Parabolica are
  right-handers; Rettifilo is right-then-left; Ascari is left-right-left. Those
  are facts about the circuit rather than about a coordinate convention, which
  is what makes them useful — a mirrored track flips all eleven at once, and
  unlike the shoelace sign there is no way to talk yourself into the inverted
  version being correct. The expected sequence is `RLRLRRRLRLR`.
- **Scene-graph determinant.** Every other check runs on the data. This one
  runs on what reaches the GPU: a negative scale anywhere up the parent chain
  mirrors the track after all the data checks have passed, and nothing else
  would catch it.

**Seam continuity is a unit test, not a load-time check.** `sampleAt` is a
pure function, so it belongs under `vitest` — `src/track/frame.test.ts`, run by
`npm test`. It sweeps every 5 cm from `L - 1` to `L + 1` and asserts each step
advances 5 cm ± 5 mm with under 0.1° of tangent swing. Measured: step error
under a micron, tangent swing 0.0002°.

The ribbon indexing back into sample 0 does *not* cover this. That is the
geometry builder; `sampleAt` is the path a moving car takes, with its own wrap,
binary search and modulo segment length. A mistake there shows up as a jump or
a flick of heading once per lap, at the most visible point on track — so the
suite also asserts the sweep actually crossed `s = 0`, because three green
assertions that never reached the seam would be worse than no test.

The test reads the committed `monza.json` off disk through the real
`parseTrack`, rather than a synthetic loop: a hand-made circle would not have
the property under test, which is that the seam behaves like every other
segment of the real artifact.

Visually, the corner labels sit on the *outside* of each turn, which is the
same assertion in a form you can read at a glance: flip `right` and all eleven
jump to the inside. Chevrons every 250 m give the direction of travel, and the
default camera is near plan-view so the render can be held next to a circuit
map.

**Kerbs.** Red/white stripes are a texture with `RepeatWrapping`, UV `u` driven
by `s`. Only place them near corners, using the corner `s` values.

**Cars.** One glTF model, `InstancedMesh`, per-instance colour attribute. Wheels
as separate meshes if you want them spinning. Under ~10k triangles per car is
plenty at the camera distances involved.

None of that was M3. M3 was a 5.0 x 1.8 x 1.0 m box in `src/cars/Car.tsx`,
deliberately: debugging a glTF loader and a motion path simultaneously means
neither gets debugged. The box carried an orange block projecting past its front
face — asymmetry is the only way to tell at a glance that a car is facing
forward rather than backward, and it had to read from *above*, because the
default camera is near plan-view and a coloured vertical nose face would be
invisible from there.

**Swapping the box for a model.** M4 step 1 replaces it with
`public/models/raceCarRed.glb`, still one car, no instancing. "Swapping the
geometry is a one-line change" turned out to be optimistic by about a file: the
placement was right, but no model arrives already agreeing with a convention.

Measure before correcting. Raw, straight out of the file, this one is
1.345937 m long, 0.728833 m wide and 0.397014 m tall — roughly quarter scale
— with its bbox centre at (-0.350, +0.165, -0.663) and its tyres at
y = -0.033520. A Unity export whose root node carries a translation that pushes
the model off its own origin rather than onto it, so the origin is a reference
point for nothing.

It faces **+Z**, where `place.ts` wants -Z. Three things agree, which is the
point of listing them: the `wheelFront*` nodes sit at higher z than the
`wheelBack*` ones; the +Z end narrows to a nose while the -Z end keeps full
width and rises into a spoiler; and with forward = +Z the kit's own left/right
wheel names land on the correct sides, which they would not if the nose were
-Z. Guessing from one of those would have been a coin toss on a symmetric-ish
body.

The corrections live in `src/cars/model.ts`, applied once at load, never in the
render path. A `CarModelSpec` names the model's own forward and up axes and which
dimension anchors the scale; `carModelMatrix` *derives* everything else from the measured
bounding box — rotation from `makeBasis(right, up, -forward)` transposed,
which is the inverse of the basis `carBasis` assembles one level down, then a
uniform scale, then a translation putting the plan centre on the origin and the
lowest point on y = 0. Nothing about this particular file is written down in the
correction path, so the next model is a spec change rather than an edit. The
measured numbers above appear only in `model.test.ts`, as a guard that fails
loudly if the file is swapped.

The scale is anchored on **width**, at the 2.0 m an F1 car is actually limited
to; the length falls out at 3.693 m because the placeholder is 1.85:1 where an
open-wheel car is nearer 2.8:1, and one uniform scale cannot satisfy both.
Width is the dimension to protect: `d` is metres across a 13 m ribbon, so car
width is the reference anyone reads lateral spacing against when fitting a grid.
Anchoring on length instead gave a 2.708 m car, 35% over the real maximum, which
would make a field look like it fits when it does not. A short car is visibly a
placeholder; an over-wide one is a plausible-looking lie. Non-uniform scale is
not the escape — it distorts the mesh rather than just mis-sizing it.

Changing that anchor is one spec field (`fit: { axis, metres }`) and the
correction path never learns which dimension was picked. It did not start that
way: the first cut could only express a target *length*, and generalising it
cost two lines in `carModelMatrix`. Worth recording, because "the next model is
a spec change" holds only for the axes the spec can actually express — the
claim is about the spec's vocabulary, not about the adapter being magic.

`RIDE_HEIGHT_M` is 1 cm and `Car.tsx` owns it, while the adapter's datum stays
exactly 0. The split is the point: where a model's lowest point is, is a fact
about the model; how far off the surface it then sits is a fact about placement,
which is what `h` means in `placeCar`. So there is one number to change, not two
that must agree, and the next model inherits the clearance without knowing it
exists.

It is insurance, not a measured fix, and the distinction is worth keeping
straight. The tyres really do end in flat facets — 64 of the model's vertices
sit at exactly the lowest point, 16 per wheel — so at `h = 0` they are coplanar
with the ribbon, which is the classic z-fighting setup. But no z-fighting could
be produced at `h = 0` from any angle: rendering the ribbon in a diagnostic
colour and counting pixels punching through the tyre gave zero, both at grazing
eye-level angles and from directly overhead. The facet is the underside of an
opaque wheel and is occluded in every view. The centimetre stays regardless: it
costs nothing, it is a plausible ride height, and the next model may put
bodywork lower than its tyres.

The model's materials are all `metallicFactor: 0` with no textures, so they read
correctly under the existing two lights with no environment map — but they are
single-sided, which is the first time `carBasis`'s determinant +1 guarantee has
had anything to bite on. On a symmetric box a mirrored basis was invisible; on
single-sided faces it turns the car inside out.

**Car placement.** `src/cars/place.ts`. Position is `toWorld(s, d, h)` and
nothing else; orientation is `makeBasis(right, up, -tangent)` on the frame's
own vectors, so local -Z is forward, +X is right and +Y is up.

The negation is load-bearing. `(right, up, tangent)` is left-handed — with
`tangent` along -z the columns are `(x, y, -z)` and the determinant is -1, so
the matrix mirrors the mesh as well as rotating it. That is `TrackRibbon`'s
scene-graph determinant check one level down, and it is invisible on a
symmetric box: it would surface as a subtly wrong model the day the box is
replaced, or as a wrong answer the first time anything reads `right` off a car
instead of off the frame. `src/cars/place.test.ts` asserts the determinant,
the three axis alignments and that `+d` displaces the car towards its own
right, at 1985 points around the lap.

Two smaller decisions. The car rides 5 cm above the ribbon — `y = 0` on Monza —
so the underside never z-fights with the surface, which is the same trick as
`MARKER_H` in `OrientationAids` and also happens to be a plausible ride height.
And `s` advances by `speed * delta` with `delta` capped at 0.1 s: `rAF` stops
while the tab is hidden, so the first frame back otherwise carries the whole
away-time and jumps the car several laps — arithmetically fine through `wrapS`,
but on screen indistinguishable from the start/finish discontinuity this
milestone exists to rule out.

`d` gets a slider (`src/cars/CarPanel.tsx`) rather than a constant. The sign
convention is the one thing here that a still frame cannot settle, and the
visual form of the check is concrete: at `d = +6.5` the car runs on the inside
of Parabolica, the opposite side from the `T11` label, which sits on the
outside. At `-6.5` they share a side.

**The twenty-car grid.** M4 step 2. `carGeometry` in `model.ts` flattens the
adapted model into geometry an `InstancedMesh` can draw: the adapter matrix is
baked into the *vertices* once, so an instance matrix is pure placement and
nothing per-frame has to remember this model needed correcting. Bodywork bakes
all the way into car-local space; wheel parts bake relative to their own centre,
because they keep turning.

The draw-call count is set by materials, not by choice. The exporter split the
mesh by material, so there are three body primitives and two per wheel — twelve
`InstancedMesh`es including the ribbon, against 221 objects drawn separately.
Merging tyre and rim per wheel would get that to eight, at the cost of faking
one of the two materials; not worth it.

**No texture was involved.** Kenney's kit is palette-textured at source, but
this GLB is a Unity export that baked the palette into four flat
`baseColorFactor` materials — UVs survive, no image is bound to anything. So
per-car colour is neither tinting a texture nor replacing one: it is
`instanceColor` on the single primitive whose material is named by the spec's
`paintMaterial`, with that material cloned and its own colour set to white so
the palette entry lands exactly instead of multiplying into the existing pink.
Trim, glass, tyres and rims stay uniform across the field. Ten colours, two cars
each, as a real grid is ten pairs; colours only, with generic names, because
CLAUDE.md rules out liveries, badges and official-style numbers and a flat
colour is none of those.

**Wheel radius is derived, never written down.** Each wheel node measures
0.4375 x 0.7745 x 0.7745 in car-local, so the axle is the axis of least extent
and the radius is half the mean of the other two: 0.3872 m. The wheel centres
come out at y = 0.3872 as well — exactly one radius above the datum, which is
an independent confirmation that the adapter put the contact plane where it
says. Spin is `-distance / radius`, rolling without slipping, so a visibly
scrubbing wheel would mean the radius is wrong rather than that a constant needs
tuning.

Two details that a still frame cannot settle, so both are asserted instead.
Wheel angle comes from *unwrapped* distance travelled, not from `s`: `s` resets
at the start/finish line and an angle derived from it would snap back once a
lap, at the most conspicuous point on track. And the roll direction is checked
by taking a point at the top of the tyre and requiring it to move towards local
-Z as the car advances.

**Check J: instance matrices apply no mirroring.** The sibling of the
scene-graph determinant check, and the reason it exists is specific: instancing
*composes* matrices where the single car *assigned* them, and one negative scale
component would mirror all twenty cars while every check in `verify.ts` still
passed. `grid.test.ts` asserts a determinant of exactly 1 over 24,000 matrices —
every car, every wheel, three laps round — and the viewer repeats it once on the
first populated frame over the 100 matrices actually handed to the GPU.

**What instancing bought, measured.** Twenty cars, same geometry, same camera,
same 1000x700 viewport, 300 frames a run with `finish()` at both ends, run
interleaved twice to catch drift:

| | draw calls | triangles | ms/frame |
|---|---|---|---|
| separate objects | 221 | 30,902 | 0.468, 0.518 |
| instanced | 12 | 30,902 | 0.083, 0.072 |

About 6x, and ~0.42 ms saved per frame. **It is a real difference and an
irrelevant one at this scale**: both sit far inside a 16.7 ms budget, and nobody
would see the separate version stutter. The reason to instance here is headroom
— the cost is now flat in car count rather than linear, so the number of cars
stops being a thing to worry about — not a frame rate anyone recovered today.

**Motion.** `field.ts` is pure and deterministic, no `Math.random`, so the grid
is identical on every reload and a screenshot means something. Cars are spread
over the whole lap rather than packed into a starting grid, because from the
near-plan default camera a tight grid is one clump of pixels. Speeds vary by
+/-5%, which is what makes the order evolve; there is still no overtaking logic,
no curvature slowdown and no strategy, exactly as section 6A describes.

The `d` slider is gone, replaced by a twenty-swatch selector showing the chosen
car's live `(s, d)`. The readout is polled from a ref at 12 Hz and written
straight to `textContent` rather than held in React state: at sixty updates a
second it would drag the whole Canvas subtree through the reconciler for a
number nobody can read that fast.

**Cameras.** M5. Three, switchable at runtime from `CameraPanel` or the number
keys, all owned by `src/cameras/CameraRig.tsx`:

- Orbit (drei `OrbitControls`) for development and inspection, unchanged.
- Chase — 9 m behind and 3.2 m up, damped so it lags into corners.
- Onboard — a T-cam 2.6 m behind the car's centre and 2.1 m up, rolling into
  corners.

Both follow the car `CarPanel` has selected, and both aim at a point that
*leads* it: `toWorld(s + lookahead, d)`, 25 m ahead for chase and 30 for the
T-cam. That really is a one-line use of the same `s → position` function, and it
is the only route into world space either camera uses.

The maths lives in `src/cameras/rig.ts`, pure and free of React and r3f so it can
be swept round the lap under `vitest`. `CameraRig.tsx` calls it once a frame and
copies the result onto the camera.

**The seam, again — but a different seam.** `sampleAt` was already proven
continuous across `s = 0` in M3. What is new in M5 is state that persists
*between* frames and is measured in arc length. Damp a wrapped `s` towards
another wrapped `s` and the camera flies a whole lap backwards the instant the
car crosses the line. So the rig holds its anchor in **unwrapped** metres and
never calls `wrapS` on anything it stores — only `toWorld` wraps, internally, at
the moment it evaluates the spline. Identical reasoning to the wheel spin one
milestone earlier, and it makes the crossing a non-event rather than a case to
handle: nothing subtracts two wrapped values, so nothing can jump by a lap
length.

**Damping needs a feed-forward term, and this is the one real bug in the
design.** `MathUtils.damp` is a first-order lag, `dx/dt = lambda (y - x)`, and
the target it chases here is a *ramp*, advancing at the car's speed. A lag
chasing a ramp settles a constant `v * tau` behind it: 18 m at 60 m/s with
tau = 0.3 s, against a configured trail of 9. The camera films from 27 m back,
and the obvious "fix" is to shrink `trailM` until the transient behaviour is
wrong instead. Riding the ramp forward first and damping only the residual leaves
a measured steady-state error of 9e-13 m, and keeps the transient the damping
exists for — which is what will matter in M6, when speed stops being constant.

**Roll is lateral acceleration, low-passed in distance.** `curvature * speed^2`
against a 4 g reference, clamped at 6 degrees, damped with its own 0.35 s
constant. Speed squared rather than curvature alone, so that M6's real speeds
bank a slow corner less than a fast one. The clamp is load-bearing rather than
defensive: the field holds 60 m/s through everything, so lateral acceleration
peaks at **18.7 g** at Rettifilo exit. 4 g sits between the lap's p90 (3.2 g) and
p99 (7.7 g) of smoothed curvature, leaving the roll pinned over 7.0% of the lap —
every real corner and nothing else.

The low-pass is seven taps over +/-15 m, one per centreline sample, and it is
there for the *kinks*: `curvatureAt` interpolates linearly between 5 m samples,
so the raw signal has a corner in it twelve times a second at racing speed, and
smoothing in time cannot remove those without dragging the corner entry with it.
It cuts the peak roll-target rate from 124 to 83 deg/s. Note that the main
straight did **not** need it — raw curvature there peaks at 0.00028 /m, a tenth
of a g, 0.15 degrees of roll. That was assumed to be a problem before it was
measured, and it was not one.

**Three things about `OrbitControls` that cost time.**

- `target0` is the world origin. The constructor does
  `this.target0 = this.target.clone()`, and drei builds the instance in `useMemo`
  during render — before the `target` prop reaches it at commit. Monza's fitted
  target is (478, 0, -504), so `reset()` throws the view half a kilometre across
  the map. `position0` happens to be right, which makes it look half-broken
  rather than broken. A `saveState()` in a mount layout effect repairs it.
- `camera.up` poisons it permanently. `update()` rebuilds its entire spherical
  basis from `camera.up` on every call. Leave the T-cam's roll on it and the
  orbit camera orbits a tilted axis with a tilted horizon, for good, with nothing
  to put it back. Reset `up` on every entry to orbit mode.
- `saveState` saves whatever the camera happens to be at, so establishing the
  home pose means *writing* the position, not reading it. `CameraRig` mounts
  inside the `<Suspense>` that waits on the car model, and Vite remounts it on
  every edit while `<Canvas>` and its camera survive untouched — which is how
  this was found, with the T-cam's ground-level pose enshrined as the orbit home.

**`<Canvas camera={{ … }}>` is applied once and is never reactive.** r3f compares
`state.camera` — the instance — against the options *object*, which can never
match, so the re-apply branch is dead after the first commit. Per-mode field of
view has to be mutated on the camera with an explicit `updateProjectionMatrix()`.
Skip that call and a window resize commits it later, which is a bug that only
shows up when someone drags the window edge.

**Where the follow state comes from.** `Grid` already keeps an unwrapped odometer
per car for the wheels, so the rig reads the same channel: the `readout` ref
grows `sUnwrapped` and `carIndex`. `sUnwrapped` is `s0 + odometer`, not the
odometer alone — `dist` is seeded to zero while `s` is seeded to the car's grid
offset, and a camera following the odometer would sit most of a lap from the car
it is meant to be behind. `carIndex` is what lets the rig tell a selection change
(kilometres in one frame, cut to it) from motion (damp it).

`CameraRig` renders immediately after `<Grid>` inside the same `<Suspense>`, so
its `useFrame` subscribes second and reads this frame's state: r3f sorts
subscribers by priority with a stable sort and subscribes from a layout effect,
so sibling order decides among equal priorities. Everything stays at priority 0 —
a single positive-priority subscriber anywhere switches the whole loop to manual
rendering.

**What the tests cover, and the one thing they cannot.** `src/cameras/rig.test.ts`
sweeps a lap in the house style. Three assertions carry their weight, verified by
breaking the code and watching the right one fail: removing the feed-forward
gives 17.5 m of trail error against a 0.05 m tolerance; disabling the low-pass
pushes the roll-target rate to 124 deg/s against 100; replacing `damp` with a
per-frame fraction makes 30 Hz and 240 Hz disagree by 7.2 m over the same wall
clock. The seam sweep counts crossings and asserts exactly one, so it cannot pass
without having reached the line.

What no test settles is the *sign* of the roll — whether banking with the corner
or against it looks right is a convention, not a derivation. On screen: positive
curvature is a right-hander, a positive roll about the view direction rolls the
camera clockwise, and that reads as banking into the turn. Confirmed against
Rettifilo T2 (left) and Parabolica (right), which tilt opposite ways.

One more thing worth knowing. The T-cam is placed at `toWorld(s + fwdM, d)` while
the car is placed rigidly on its own basis, so the two disagree by up to 0.42 m
longitudinally at Rettifilo — a 16% variation in how far back the camera sits, in
the tightest corner only. That is the price of routing every world position
through `toWorld`. A rigid mount would mean a second path from `(s, d)` into
world space, and then there would be two of them to keep honest.

**Lighting.** One directional light with shadows, a hemisphere light for fill,
and an HDRI environment map for reflections. Don't spend time here until the
geometry is right.

---

## 8. Milestones

| # | Goal | Done when | Status |
|---|------|-----------|--------|
| M0 | Project scaffold | Vite + R3F renders a spinning cube; typecheck passes | done |
| M1 | Track extraction | `monza.json` committed; matplotlib plot looks like Monza; length checks out | done |
| M2 | Track renders | Ribbon visible, orbit camera, correct orientation and corner order | done |
| M3 | One car moves | Single car driving the lap via `(s, d)` at constant speed, box stand-in, `d` adjustable at runtime | done |
| M4 | Full grid | 20 instanced cars from the real glTF model with wheels, distinct colours, per-car offsets, no z-fighting | done |
| M5 | Cameras | Orbit / chase / onboard switchable, damped follow | done |
| M6 | Telemetry replay | Real 2024 Italian GP positions projected to `(s, d)` and replayed | done |
| Phase 0 | Engine geometry | The engine's frozen tracks converted, checked, overlaid and rendered beside ours; see docs/phase0-geometry-report.md | done |
| Phase 3 | Engine race | A headless 10-car engine race recorded as JSONL ticks, checked, and played by an `engine` motion source on a track built from the recording; see docs/phase3-engine-race.md | done |

M0–M3 is the core of the spike. M4–M6 is where it starts looking like something.

Rough estimate: M1 and M2 are the slow ones, a few days each with debugging.
M3–M5 are faster than they look once the spline exists.

---

## 9. Parked for later

Recorded so the decisions aren't re-litigated, explicitly **not** in scope now:

- 2D↔3D transitions. Preferred approach when the time comes: keep one scene
  always alive and make the "2D view" a top-down orthographic camera on it, so
  switching views is a camera move rather than a mode switch.
- Key-moment triggers: overtake, pit stop, lap-one Turn 1, safety car, DRS zone.
- Weather: particle rain, wet-road material swap, spray cones.
- Crashes: scripted, not simulated. The simulator decides the outcome; the
  renderer plays a canned spin, smoke burst and debris with ballistic arcs and
  no contact resolution.
- Additional circuits, elevation, banking, walls, grandstands as billboards.

---

## 10. Data sources

- **FastF1** — *as of 2026-11-04, F1's live-timing archive answers HTTP 401 to
  unauthenticated requests*, so FastF1 3.4.4 can no longer download sessions
  that are not already cached; Monza 2024 works only from `.fastf1-cache/`
  (docs/phase0-geometry-report.md section 6). Position and car telemetry from
  2018 onward; `X`, `Y`, `Z` in
  1/10 m plus an `OnTrack`/`OffTrack` status flag. `get_circuit_info()` supplies
  corner, marshal light and marshal sector positions and the track rotation
  angle (manually created, approximate, adequate for annotation).
- **`bacinger/f1-circuits`** — MIT-licensed circuit outlines in GeoJSON with
  altitude referenced to start/finish. Useful as a cross-check; lower fidelity
  than telemetry for this purpose.
- **Car models** — CC0 preferred (Poly Haven, Quaternius, Kenney). Sketchfab
  licences vary per model, mostly CC BY; check each one and record it in
  `ASSETS.md`.
