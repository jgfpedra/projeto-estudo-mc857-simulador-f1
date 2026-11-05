# CLAUDE.md

## What this repo is

A standalone spike for the 3D visualisation layer of an F1 race simulator
(MC857, group "F1maça"). **This is not the group project repo.** The goal is to
get one circuit — Monza, 2024 — rendering in Three.js with cars moving along it,
and to get familiar with the toolchain before any of this is integrated.

Design rationale, data pipeline details and the milestone list live in
`docs/3d-design.md`. Read it before making architectural changes.

## Non-goals

Do not build these unless explicitly asked. They belong to the group project,
not to this spike:

- FastAPI backend, WebSocket streaming, or any live server
- The race simulation engine itself (tyre model, strategy, ERS, weather)
- 2D HUD, leaderboard, or 2D↔3D view transitions
- "Key moment" cinematic triggers (overtakes, pit stops, incidents)
- Collision physics or crash animation
- The Ollama race-engineer agent
- More than one circuit (phase 0's `interlagos_v2` was explicitly requested as
  evidence for the geometry-source decision; it is not a second supported
  circuit)

If a task seems to need one of these, say so and propose the smallest stub that
unblocks the current milestone instead.

## Stack

- **Viewer:** Vite + React + TypeScript + react-three-fiber + drei
- **Data extraction:** Python 3.11+, FastF1, numpy, scipy — offline scripts only
- Pin versions in `package.json` / `requirements.txt`. Don't upgrade Three.js or
  R3F mid-milestone; the R3F ↔ Three.js version pairing is easy to break.

## Commands

```bash
# Viewer
npm install
npm run dev          # Vite dev server
npm run build        # typecheck + bundle
npm run typecheck
npm test             # vitest, one run
npm run test:watch
npm run snapshot     # build, then render-verify in headless Chromium (see below)

# Track extraction (run once per circuit, output is committed)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/extract_track.py --circuit monza --year 2024 --out public/tracks/monza.json

# Phase 0: the engine's frozen tracks (group repo, read-only) - see
# docs/phase0-geometry-report.md for the full commands
python scripts/convert_frozen_track.py --circuit monza --frozen <frozen>/Monza_v1.json     --corners-from public/tracks/monza.json --out public/tracks/monza_v1.json
python scripts/overlay_frozen.py --frozen-dir <frozen>   # docs/phase0/ plots + metrics
```

## Conventions

### Units

- FastF1 position data is in **1/10 m**. Convert to metres exactly once, inside
  `scripts/extract_track.py`. Everything downstream of the JSON is in metres.
- Angles in the JSON are degrees; angles in TypeScript are radians. Convert at
  the load boundary, not scattered through the render code.

### Coordinates

FastF1 gives a plan view: `X`/`Y` are ground plane, `Z` is elevation. Three.js
has **Y up**. The mapping is:

```
three.x =  ff1.X
three.y =  ff1.Z
three.z = -ff1.Y
```

The `-` on Y is not optional. Dropping it produces a mirrored track that looks
plausible until you notice the corner sequence runs backwards.

### Position model

Cars are positioned by `(s, d)`, never by raw world coordinates:

- `s` — arc-length distance along the lap in metres, `0` at the start/finish
  line, increasing in the direction of travel, wrapping at track length.
- `d` — lateral offset in metres from the centreline, **positive to the right**
  of the direction of travel.

The renderer converts `(s, d)` to world position by evaluating the track spline
and its Frenet frame. Keep this boundary clean — it is the one piece of this
spike that carries over to the group project unchanged.

## Hard rules

- **No real F1 branding.** No team liveries, sponsor logos, team badges, or
  official-style driver numbers. Use a generic open-wheel model recoloured with
  approximate palettes. Formula One's marks are trademarked and this project
  will be shown publicly.
- **Every third-party asset gets a line in `ASSETS.md`**: source URL, author,
  licence, date downloaded. No model, texture, HDRI or font enters the repo
  without one. CC0 preferred; CC BY is fine with attribution recorded.
- **Don't commit** `.fastf1-cache/` or raw session data. **Do commit** the
  extracted JSON in `public/tracks/` — it is small, and it means the viewer runs
  without anyone installing Python.

## Verifying rendering

**Use `npm run snapshot`, not the editor's preview pane.** The pane cannot run
`requestAnimationFrame`, so it never shows motion — M3, M5 and M6 all closed
without anyone seeing a car move. `scripts/snapshot.mjs` serves `dist/`, loads it
in headless Chromium with `?probe` (which mounts `src/probe.tsx`), and:

- waits for 60 drawn frames, failing if the counter stays at zero or stalls;
- requires the viewer's 7 orientation checks and check J to log PASS;
- screenshots orbit / chase / T-cam under both motion sources and fails any
  canvas that is (near enough) one flat colour, measured with the DOM panels
  hidden;
- steps the replay at 0.25x beside a front wheel with the debug wheel markers
  on, checks spin against distance travelled, scrubs the timeline backwards and
  requires the marker to return exactly.

Screenshots land in `.cache/snapshots/` (gitignored); exit code 1 on any
failure. Proven able to fail: a NaN in the camera position turns both orbit
shots into a single colour and the run exits 1. First run needs
`npx playwright install chromium`.

## Known gotchas

- **Mirrored track.** See the coordinate mapping above. Verify with the sign of
  the loop's signed area: Monza runs clockwise, which in Three.js `(x, z)` is a
  positive shoelace area. The corner-order check below does *not* catch this —
  mirroring reflects the shape but leaves the corner sequence intact.
- **Reversed lap.** A different failure with a similar smell. Verify by checking
  that the first corner after start/finish is the Rettifilo chicane at ~875 m,
  not Parabolica at ~5180 m.
- **Ground-plane columns.** In FastF1 space the plan is `(X, Y)` and `Z` is
  elevation; in Three.js space `y` is up, so the plan is `(x, z)`. Measuring
  lengths with columns `[0, 1]` on a Three.js array silently projects onto the
  elevation axis — on a flat circuit that reports about half the true lap
  length rather than raising anything.
- **Racing line ≠ centreline.** A single fast lap cuts apexes. The extraction
  script medians across drivers to approximate the centreline; don't "simplify"
  it back to one lap.
- **Zero coordinates.** Some samples at session start are `(0, 0)`. Filter them
  before fitting, or the spline gets dragged to the origin.
- **`session.load()` is slow.** Enable the FastF1 cache before the first call or
  every iteration costs minutes.
- **Monza is deliberately flat.** Keep the elevation code path in place and feed
  it `Z = 0` for now. Don't delete it; the next circuits need it.
- **Monaco is off the table** for this spike — GPS drops in the tunnel.
- **F1's live-timing archive returns 401** (since at least 2026-11-04), so
  FastF1 cannot download sessions that are not already in `.fastf1-cache/`.
  Monza 2024 is cached; São Paulo is not, which is why phase 0 has no
  Interlagos centreline of ours.
- **Engine tracks are marker splines, not centrelines.** `Monza_v1` /
  `interlagos_v2` are centripetal Catmull-Rom through FastF1's corner markers
  (reproduced to 1e-12 m). Their known check failures are pinned in
  `src/track/expected-verdicts.json`; don't "fix" them by loosening a check.
- **Engine lateral is +left**: `d_ours = -d_engine`, and the engine measures it
  against the segment normal (our `project_naive`), not the refined projector.

## Layout

```
scripts/extract_track.py   # FastF1 → track JSON (offline, run rarely)
scripts/extract_replay.py  # FastF1 → (s, d) replay JSON
scripts/centreline.py      # the one (s, d) <-> world projector, shared by both
scripts/convert_frozen_track.py  # engine frozen track -> our JSON (phase 0)
scripts/overlay_frozen.py  # phase 0 overlay metrics + plots -> docs/phase0/
scripts/multiviewer.py     # MultiViewer corner markers / lap outline, cached
scripts/snapshot.mjs       # headless render verification (npm run snapshot)
public/tracks/*.json       # committed track geometry
src/track/                 # spline, frame, ribbon, checks, ?track= registry
src/cars/                  # car model loading, instancing, (s,d) placement
src/cameras/               # orbit / chase / onboard
src/App.tsx
docs/3d-design.md          # design rationale and milestones
docs/phase0-geometry-report.md  # engine frozen tracks vs ours: the evidence
ASSETS.md                  # third-party asset licences
```
