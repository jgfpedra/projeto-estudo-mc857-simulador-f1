# Phase 3: an engine race, recorded and played in the 3D

**Question.** Can a race from the group's engine be recorded in the tick format
the group is agreeing on, and played back in the 3D with the track taken from
the recording itself?

**Short answer.** Yes. A headless 10-car, 3-lap race (seed 42, apex-rules) runs
at **4.36× real time** in WSL, and its 3,299 ticks check clean: every car's
`progress_m` is monotonic, `toWorld(s_m, d_m)` returns `position_xy` to
**0.7 mm** on track and off, and `d_m` is the engine's lateral with the sign
flipped (correlation −0.99998). The viewer's new `engine` source puts every car
on the engine's own pose, 3×10⁻⁵ m from `position_xy` as read back from the
GPU instance matrices, in all three camera modes.

Run from the repository root (recorder, WSL) and from `viz3d/` (the rest):

```bash
wsl -d Ubuntu-22.04 -- bash /mnt/c/<...>/viz3d/scripts/record_race.sh   # -> .cache/recordings/
python scripts/check_recording.py .cache/recordings/interlagos_seed42_3laps.jsonl
python scripts/trim_recording.py .cache/recordings/interlagos_seed42_3laps.jsonl \
    --out public/recordings/engine-interlagos-seed42.jsonl
npm test && npm run snapshot                                          # ?track=engine
```

## 1. Recorder (`scripts/record_race.py`)

It drives the race the way `backend/scripts/run_race_10_cars.py` drives its
default `apex-rules` profile, reproducing that script's loop rather than calling
`engine.run()`. The two differ: `run()` steps the weather to lap 1 before the
first tick, publishes a race-start event and caps the tick count, and the 10-car
script does none of these.

- Grid, seeded variance and layout come from the script's own functions, which
  are imported rather than copied (`build_grid_drivers`,
  `resolve_race_randomization`, `place_grid`). With seed 42 and no `--variance`
  the apex-rules default is `grid`: the starting order is shuffled to GAS HAM
  RUS VER PIA PER LEC NOR ALO SAI. Compounds stay as `GRID_DRIVERS_CONFIG` sets
  them.
- Weather `seeded`, `SimulationConfig` with the script's values (10 Hz, 24
  sub-steps, `track_progress_laps=True`, `input_stale_after_s=300`), except
  `gui=False` (its `--no-gui`) and `realtime=False`. The script itself cannot
  turn realtime off, because its `--realtime` is `store_true` with
  `default=True`. Realtime only sleeps between ticks.
- `place_grid(layout="f1", jitter=None)`, one `RuleBasedRaceController(track,
  seed=42)` shared by all cars, `race_started = True`, then
  `_step_tick(0.1, 24)` until `race_finished`. Display-only code is left out:
  the leaderboard print, the 3D labels and the authority counter.
- Track: `load_track_frozen("interlagos")` → `interlagos_v2.json` (frozen sha
  `164876196eb12174`, geometry sha `24461ba0b6c38983`, 1131 waypoints, 4160.4 m,
  `sf_idx` 729, width 12 m).

**Real-time factor** (WSL Ubuntu 22.04, Python 3.10.12, 12 cores, one process):

| | wall | simulated / wall |
|---|---|---|
| loop incl. recording and projection | 75.8 s | **4.36×** |
| `_step_tick` only | 69.6 s | 4.74× |
| setup (imports, track, spawn) | 2.4 s | |

329.9 s were simulated. RUS completed 3 laps first, and the final order was RUS
VER HAM GAS PIA ALO PER LEC SAI NOR. The recording header has `git.backend_dirty: true`
because of a pre-existing local edit to
`backend/experiments/prof-grip-1/corridas/CTRL_Interlagos_OFF.log`, a log file
the engine does not read. No backend code was changed.

## 2. Format

JSONL. Line 1 is the static race block, shaped like `GET /races/{id}`:
`race_id`, `num_laps`, `track {name, source, geometry_sha256, length_m, width_m,
start_finish_waypoint, waypoints}`, and `drivers {driver_id, name, grid_position}`.
It also carries a `recording` block with provenance (seed, profile, realtime
factor, git, and `trimmed` on the fixture). `source` is `mirror`, the
`track_identity` term for `load_track_frozen`. `geometry_sha256` is
`track_identity`'s own hash, and the viewer recomputes it at load and refuses a
mismatch.

The other lines are ticks: `sim_ts`, `lap` (the `TickEvent`'s own minimum),
`leader_lap`, and `positions` in race order. Each position has `driver_id`,
`position`, `lap`, `position_xy`, `heading_deg`, `velocity_mps`, `progress_m`,
`s_m`, `d_m`, `tyre_compound`, `tyre_life_pct` and `pitting`. The shared fields
come from the engine's own `_snapshot_position`, so they use its rounding
(1 cm, 0.1°). `progress_m` is `engine.race_progress_m`.
`s_m` and `d_m` come from `centreline.py`'s refined projector against the same
waypoints, rolled so that s = 0 is waypoint 729. `d_m` is positive to the right
of travel. They are computed from the rounded `position_xy` that is written, so
each line is self-consistent.

Sizes: full race 7.6 MB in `.cache/recordings/` (gitignored). The committed
fixture `public/recordings/engine-interlagos-seed42.jsonl` is 999,495 bytes:
the first 419 ticks (0.1–41.9 s). That window holds the start, 18 of the net
position swaps and all 13 of Sainz's off-track samples.

## 3. The recording, checked (`scripts/check_recording.py`, full race)

| | result |
|---|---|
| header | waypoints hash to `24461ba0b6c38983`; our frame measures 4160.436950 m = `length_m` |
| `progress_m` monotonic | **all 10 cars**. 0 backward ticks, 0 dropped steps (the engine drops a step > max(30, 3·v·dt + 10) m) |
| off-track (\|d_m\| > 6 m) | 23 samples / 32,990 (0.07%), two excursions: **SAI 39.6–40.8 s, up to 9.22 m**, and **LEC 42.6–43.5 s, up to 7.03 m**. Neither made progress go backwards or drop a step |
| round trip on track (32,967) | p50 0.4 mm, p99 0.7 mm, **max 0.7 mm** |
| round trip off track (23) | max 0.6 mm |
| refined projector bracketed | every sample, including the off-track ones (interlagos_v2 is not monotone everywhere, phase 0 report §5, but nothing came near the fold) |
| overtakes | 52 ticks with an order change, **53 pairwise swaps** (37 on the opening lap, 16 after). 32 net after removing swaps undone within 2 s. None involved an off-track car |
| \|d_m\| | p50 1.09, p90 3.27, p99 4.37, p99.9 5.46, max 9.22 m |
| sign | `corr(d_m, d_engine)` = −0.99998 on track. \|d_m + d_engine\| p50 0.3 mm, p99 4.3 cm, max 0.66 m (segment normal against interpolated tangent at the kinks, as CLAUDE.md warns) |
| `s` (unwrapped) − `progress_m` | on track p50 0.0, p99.9 0.88 m, extremes −1.40 / +3.75 m. Same segment-normal effect: the engine projects onto the segment, we project onto the interpolated tangent |
| heading − track tangent | on track p50 1.1°, p99 21.8°, max 70.8° |
| chord sag of linear xy interpolation at 10 Hz | p50 7 mm, p99 19 mm, max 73 mm |

The 70.8° heading is Leclerc at 44.3 s. He is stopped, 4.9 m right of the
centreline, pointing across the track as the rule controller rejoins after his
excursion. This is the case for placing cars by pose. An `(s, d)` placement
would draw him aligned with the track.

No car pitted: `needs_pit` (tyre life < 18%, fuel < 6 kg) is not reached in 3
laps. `pitting` is always false here, so the pit path is not exercised by this
recording.

## 4. Viewer: the `engine` motion source

`?track=engine` (the picker's "Engine race · seed 42") loads the fixture.
`?recording=<url>` swaps in another recording, for example a full one under
`.cache/` through `/@fs/` in `npm run dev`.

- **Track from the recording.** `trackFromRecording` builds the centreline from
  the race block's waypoints, rolled to `start_finish_waypoint`, with
  `three.x = x, three.z = −y`. No local track JSON is read. The frame's s = 0 is
  the engine's start/finish line, so `progress_m` is an unwrapped s on it with
  no offset. The load is refused if the frame's length differs from `length_m`
  by more than 1 µm or the waypoints do not hash to `geometry_sha256`. Checks:
  A fails (interlagos_v2's −3.45%), E and F pass, and B, C, D, G skip because
  the block has no corners. These are pinned as `engine` in
  `expected-verdicts.json`.
- **Cars by pose.** `MotionState` gained `posed, x, z, yawRad`. `engineSource`
  sets them from `position_xy` (`z = −y`) and `heading_deg`
  (`yaw = heading − π/2`, because the mesh faces −Z). `Grid` then uses
  `poseMatrix` instead of `carMatrix`. The synthetic field and the replay
  write `posed = false` and are still placed by `(s, d)`.
- **`progress_m` for everything along the track.** It is interpolated linearly
  between ticks and drives `sUnwrapped`: the chase camera's damped trail and
  lookahead, the T-cam's roll, the wheel odometer, and the running order (`positionAt`, which ties to the
  lower grid slot as `ranked_drivers` does). The pose is interpolated linearly
  between ticks, heading the short way round. At 10 Hz that cuts corners by at
  most 73 mm. `speedMps` is the rate `progress_m` advances, not `velocity_mps`,
  because the rig feeds speed forward into a trail that follows `progress_m`.
- **Panel.** Position (`P4 ·`), `s` (progress within the lap), `d` (= `d_m`),
  speed and the lap being driven. The timeline shows the lap, the leader's lap
  out of `num_laps`, and the driver's position.
- **Cameras held to the pose.** `progress_m` is not where the car is:
  `toWorld(progress_m, d_m)` lands up to 0.86 m from `position_xy` on the
  ground over the full race (p99 0.38 m, p99.9 0.65 m; VER at 88.5 s). The
  3.75 m gap in s from section 3 is smaller on the ground because it happens
  at d = +5.35 m on the inside of a 7 m radius bend. So for a posed source the
  rig (`chasePose` / `onboardPose`) works from the car's interpolated pose,
  which `Grid` copies into `FollowState`; the synthetic field and the replay
  keep the `(s, d)` path, byte for byte.
  - **T-cam**: bolted to the pose. Position and aim are the car's `(x, z)`
    plus `fwdM` / `lookaheadM` along its nose (`yawRad`) and `heightM` /
    `targetHeightM` above the ground, so it sits 2.60 m behind the car's
    centre and looks along the car. Before, it took its position and
    direction from the track at `progress_m`: up to 1.80 m from that spot
    over the fixture, and on Leclerc's rejoin (stopped at 70.8° to the track,
    sim 44.4–44.5 s) only 0.80 m behind his centre, looking down the track
    rather than along the car. Roll still comes from the track curvature at
    `progress_m`.
  - **Chase**: the track-based pose (damped `u` trail, lookahead at
    `progress_m + 25 m`) translated by `position − toWorld(progress_m, d_m)`,
    so the anchor is on the car and the view direction is unchanged. Taking
    the direction from the car's heading instead would swing it through 70°
    as a car rejoins. Over sim 42–45 s around Leclerc's rejoin, simulated at
    60 fps, the chase heading changes at most 0.164°/frame (p99 0.163, mean
    0.039) before and after: the same numbers, 1e-14° apart, because only the
    position moved. The camera's per-frame step went from 0.414 m to 0.431 m
    at most, the car's own motion off `progress_m`.
  - **What the T-cam now shows** at the rejoin is the car turning: the
    engine's heading goes 36° → 67° to the track between 44.0 and 44.2 s, so
    the T-cam yaws 4.48°/frame there (looking down the track it never
    exceeded 0.14°/frame over 42–45 s). That is the recording's heading interpolated over two ticks, not
    camera noise.
  - **Orbit**: unchanged.

## 5. Verification

- `npm test`: 102 tests. `src/engine/engine.test.ts` covers the fixture through
  the viewer's own code. The TypeScript `toWorld(s_m, d_m)` lands on
  `position_xy` to 0.71 mm on track and 0.63 mm over the 13 off-track samples.
  `positionAt` reproduces the recorded position at every tick. The pose matrix
  puts every car at `position_xy` with its nose along `heading_deg`
  (determinant 1). The hash is checked, and a 1 mm waypoint edit changes it.
  `tracks.test.ts` builds the engine track from the fixture.
  `src/engine/camera.test.ts` holds the follow cameras to the pose at every
  tick, every car: the T-cam at `position_xy` plus its car-local offset and
  aimed along `heading_deg` (worst 3.8×10⁻¹³ m), also between ticks; the chase
  anchor on `position_xy` (3.8×10⁻¹³ m) with the trail and aim, relative to
  it, exactly the `(s, d)` ones. The old `progress_m` T-cam misses the same
  check by 1.80 m, and an unposed follow is bit-for-bit the `(s, d)` formulas
  whatever `x`, `z`, `yawRad` hold.
- `npm run snapshot`: the `engine` run renders orbit, chase and T-cam under the
  engine source and the synthetic field, with checks pinned and check J PASS.
  It then pauses on ticks 0, 205 and 399 (Sainz 9.11 m off track) and reads
  back every car's GPU instance matrix: worst position 2.9×10⁻⁵ m, worst nose
  against heading 4×10⁻⁸. The panel shows the recorded P and `d_m` at each of
  those ticks. On each, the live T-cam is within 6.1×10⁻⁶ m of the followed
  car's instance pose plus its local offset (tolerance 1 cm), view direction
  within 7.4×10⁻⁹.
- Synthetic and replay are unchanged: 27 paused screenshots (Monza synthetic
  and replay, engine-track synthetic; orbit, chase and T-cam; three clock
  times) are pixel-identical before and after the change, and two runs of the
  old build were pixel-identical to each other.
- **It can fail.** Dropping the minus in `out.z = −y` (cars mirrored, track
  untouched) fails all three placement ticks (44 m, 230 m, 1.7 km) and exits 1.
  A NaN in `progress_m` turns the engine chase and T-cam shots into one flat
  colour (0.000% non-background) and check J logs determinant NaN, also exit 1.
  Anchoring the T-cam on `progress_m` again fails the T-cam check at all three
  ticks, exit 1: 2.2 mm / 7.8 cm / 4.9 cm off, view direction 3.3×10⁻² /
  1.1×10⁻² / 3.5×10⁻² (up to 2°). At tick 0 the position alone would pass
  the 1 cm tolerance; the direction is what fails it there.

## 6. Open

- The pit path is unexercised (no pit stop in 3 laps). Done in
  `docs/phase3b-longer-races.md`: at 15 laps the SOFT starters stop, and
  `pitting` is never true - the engine does a stop as bookkeeping on one tick.
- The tick format is the one asked for. There is no `GET /races/{id}` in
  `backend/api` yet (only `POST /races` and the WebSocket), so "shaped like" is
  against the agreed shape, not against a live endpoint.
- One seed. Position swaps, excursions and the realtime factor are for this run
  and this machine.
