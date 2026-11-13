# CLAUDE.md

## What this is

The 3D visualisation spike for the F1 race simulator (MC857, group "F1maça").
It now lives inside the group repo at `viz3d/` (brought in with
`git subtree`, history kept), but it is **still a separate app**: own
`package.json`, own `requirements.txt`, no imports from `frontend/` or
`backend/`, and nothing in it may read files outside `viz3d/` (typecheck, tests,
snapshot and extraction never do). The exceptions are the backend-integration
scripts - phase 0b's `verify_export_backend.py` and `smoke_engine_lap.py`,
phase 3's `record_race.py` and phase 3b's `pit_horizon.py` - which import the
backend by design and change nothing in it. Run every command below from `viz3d/` unless it says otherwise. The goal is unchanged: one circuit — Monza,
2024 — rendering in Three.js with cars moving along it.

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
- More circuits than asked for. Monza is the circuit; Interlagos (phase 0's
  `interlagos_v2`, phase 0b's own extraction and its engine-format export) was
  explicitly requested as evidence for the geometry-source decision

If a task seems to need one of these, say so and propose the smallest stub that
unblocks the current milestone instead.

## Stack

- **Viewer:** Vite 8.2.2 + React 19.3.0 + TypeScript 6.0.3 +
  react-three-fiber 9.8.2 + drei 10.7.9 + three 0.169.0; vitest 5.1.0,
  @vitejs/plugin-react 6.1.1, @types/node 24.13.4. React, Vite, plugin-react,
  TypeScript and their types match `frontend/package-lock.json`, so the 3D can
  move into the frontend app later. Needs Node `^22.12`, `^24` or `>=26`
  (vitest 5's engines; Vite 8 alone accepts `^20.19 || >=22.12`).
- **Data extraction:** Python 3.11+, FastF1, numpy, scipy — offline scripts only
- Pin versions in `package.json` / `requirements.txt`. Don't upgrade Three.js or
  R3F mid-milestone; the R3F ↔ Three.js version pairing is easy to break.
- R3F 9 connects pointer events after its children first mount, so a drei
  `<Html>` mounted at once re-targets a commit later and, under React 19,
  renders empty. Mount `<Html>` only once `events.connected` is set, as
  `src/track/OrientationAids.tsx` does.

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

# Track extraction (run once per circuit, output is committed). FastF1 3.8.3,
# always offline: --cache must be an existing cache (outside the repo; read a copy)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/extract_track.py --circuit monza --year 2024 --cache <cache> --out public/tracks/monza.json
python scripts/extract_replay.py --cache <cache>      # after any monza.json change
python scripts/extract_track.py --circuit interlagos --year 2023 --start-finish timing-line --cache <cache> --out public/tracks/interlagos.json

# Phase 0b: engine-format export (exports/, never backend/), proof, smoke lap
python scripts/export_frozen_track.py --track public/tracks/interlagos.json --name "..." --out exports/interlagos_2023_v1.json
cd .. && python viz3d/scripts/verify_export_backend.py   # backend's own load_track_frozen
python viz3d/scripts/smoke_engine_lap.py                 # backend deps + joblib, gymnasium; pybullet = Linux/WSL

# Phase 3: record an engine race (WSL), check it, trim the committed fixture
wsl -d Ubuntu-22.04 -- bash /mnt/c/<...>/viz3d/scripts/record_race.sh   # -> .cache/recordings/
python scripts/check_recording.py .cache/recordings/interlagos_seed42_3laps.jsonl
python scripts/trim_recording.py .cache/recordings/interlagos_seed42_3laps.jsonl --out public/recordings/engine-interlagos-seed42.jsonl

# Phase 3b: first-pit horizon, the three 15-lap races (a v2 tuned, b v2 untuned,
# c our export), compare, trim the pit fixture (docs/phase3b-longer-races.md)
wsl -d Ubuntu-22.04 -- bash /mnt/c/<...>/viz3d/scripts/pit_horizon.sh
wsl -d Ubuntu-22.04 -- bash /mnt/c/<...>/viz3d/scripts/record_phase3b.sh 15
python scripts/compare_recordings.py .cache/recordings/*_15laps_*.jsonl   # after check_recording --json on each
python scripts/trim_recording.py .cache/recordings/interlagos_2023_seed42_15laps_c_ours.jsonl --from-s 1340 --out public/recordings/engine-interlagos2023-seed42-pit.jsonl

# Phase 0: the engine's frozen tracks, vendored read-only in vendor/tracks_frozen/
# (see PROVENANCE.md there) - docs/phase0-geometry-report.md has the full commands
python scripts/convert_frozen_track.py --circuit monza --frozen vendor/tracks_frozen/Monza_v1.json --corners-from public/tracks/monza.json --out public/tracks/monza_v1.json
python scripts/overlay_frozen.py --frozen-dir vendor/tracks_frozen   # docs/phase0/ plots + metrics
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
- screenshots orbit / chase / T-cam under every motion source a track has
  (synthetic, the Monza replay, the engine recording) and fails any canvas
  that is (near enough) one flat colour, measured with the DOM panels hidden;
- on `?track=engine`, pauses on three fixture ticks and requires every car's
  GPU instance matrix at the recording's `position_xy` / `heading_deg`, the
  car panel to show its position and `d_m`, and the T-cam at the followed
  car's pose plus its car-local offset;
- on `?track=engine_ours`, does the same on the pit fixture, plus the stop's
  tick and 20 ticks later following the car that pitted: the panel's tyre and
  pit lines and the timeline's PIT tag must equal the fixture, and the timeline
  must carry one mark per stop;
- steps the replay at 0.25x beside a front wheel with the debug wheel markers
  on, checks spin against distance travelled, scrubs the timeline backwards and
  requires the marker to return exactly.

Screenshots land in `.cache/snapshots/` (gitignored); exit code 1 on any
failure. Proven able to fail: a NaN in the camera position turns both orbit
shots into a single colour and the run exits 1; for the engine source, dropping
the minus in `z = -y` fails placement by 44 m-1.7 km and a NaN `progress_m`
flattens chase and T-cam, and anchoring the T-cam on `progress_m` again fails
the T-cam check (docs/phase3-engine-race.md section 5). First run needs
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
- **F1's live-timing archive needs a login** (401 since at least 2026-11-04).
  FastF1 is pinned to the backend's 3.8.3 and `enable_cache` always runs it
  offline, so only cached sessions load: our Monza cache, and the group's cache
  (São Paulo 2023/2024, among others). Never commit a cache; read from a copy so
  FastF1 cannot rewrite the original's pickles.
- **s = 0 placement.** Default s = 0 is each lap's first position sample, which
  lands a few metres past the line and moves between FastF1 versions.
  `--start-finish timing-line` puts it at the timing line instead (Interlagos
  uses it; Monza keeps the default, ~1 m off). Changing `monza.json` means
  regenerating the replay and round-trip fixture too.
- **Engine tracks are marker splines, not centrelines.** `Monza_v1` /
  `interlagos_v2` are centripetal Catmull-Rom through FastF1's corner markers
  (reproduced to 1e-12 m). Their known check failures are pinned in
  `src/track/expected-verdicts.json`; don't "fix" them by loosening a check.
- **Engine lateral is +left**: `d_ours = -d_engine`, and the engine measures it
  against the segment normal (our `project_naive`), not the refined projector.
- **Engine cars are placed by pose, not `(s, d)`.** The `engine` source is the
  one exception to the position model: the engine is the authority on where its
  cars are (a stopped car rejoining at 70 deg to the track would otherwise be
  drawn aligned with it). `progress_m` still drives the odometer, the order
  and the chase camera's trail and lookahead, but the follow cameras are held
  to the pose: the T-cam is bolted to it and the chase anchor sits on the car.
  `MotionState.posed` selects the path (and reaches the rig through
  `FollowState`); every source must write it.
- **An engine pit stop is bookkeeping, not a place.** It happens inside
  `_complete_lap` on one tick: tyres swapped (compound from the weather), fuel
  topped to 70% (often 0 kg), `pit_penalty_pending_s = 22` added to the *next*
  lap's time, never to `race_progress_m`. Nothing sets `pitting = True` and
  `Track.pit` is never read, so the car keeps racing on the line. Show it as
  state (car panel, timeline), never as a pit lane. The tick before a stop has
  the tyre life *before* that lap's wear.
- **`run_race_10_cars.py` is not `engine.run()`.** `run()` steps the weather to
  lap 1 first and caps ticks; the 10-car script does neither. The recorder
  reproduces the script's loop, and its realtime can only be turned off there.

## Layout

```
scripts/extract_track.py   # FastF1 → track JSON (offline, run rarely)
scripts/extract_replay.py  # FastF1 → (s, d) replay JSON
scripts/centreline.py      # the one (s, d) <-> world projector, shared by both
scripts/convert_frozen_track.py  # engine frozen track -> our JSON (phase 0)
scripts/overlay_frozen.py  # phase 0 overlay metrics + plots -> docs/phase0/
scripts/export_frozen_track.py   # our JSON -> engine frozen format (phase 0b)
scripts/verify_export_backend.py # exports' sha256 via backend load_track_frozen
scripts/smoke_engine_lap.py      # one solo lap per export in the real engine
scripts/record_race.py (+ .sh)   # headless 10-car engine race -> JSONL ticks (WSL)
scripts/record_phase3b.sh  # the three 15-lap phase 3b recordings, in turn
scripts/pit_horizon.py (+ .sh)   # first pit lap from the engine's wear/fuel code (WSL)
scripts/check_recording.py # progress, round trip, overtakes, |d| of a recording
scripts/compare_recordings.py    # lap times, order, excursions, pits across recordings
scripts/trim_recording.py  # full recording -> committed <= 1 MB fixture
scripts/multiviewer.py     # MultiViewer corner markers / lap outline, cached
scripts/snapshot.mjs       # headless render verification (npm run snapshot)
public/tracks/*.json       # committed track geometry
public/recordings/         # trimmed engine fixtures (?track=engine, ?track=engine_ours)
vendor/tracks_frozen/      # engine frozen tracks, copied byte-exact from feat/bot-ai
exports/                   # our Interlagos in the engine's frozen format
src/track/                 # spline, frame, ribbon, checks, ?track= registry
src/cars/                  # car model loading, instancing, (s,d) placement
src/cameras/               # orbit / chase / onboard
src/engine/                # recording parser, track from race block, engine source
src/App.tsx
docs/3d-design.md          # design rationale and milestones
docs/phase0-geometry-report.md  # engine frozen tracks vs ours: the evidence
docs/phase3-engine-race.md # an engine race recorded and played in the 3D
docs/phase3b-longer-races.md # 15-lap races, pit stops, v2 vs our Interlagos
ASSETS.md                  # third-party asset licences
```
