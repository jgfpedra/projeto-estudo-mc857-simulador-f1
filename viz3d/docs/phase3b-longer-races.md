# Phase 3b: longer races, pit stops, and our Interlagos in the engine

**Question.** With races long enough for pit stops, how does the engine's race
look on its own Interlagos (with and without the controller's Interlagos
tuning) and on ours? And what is a pit stop in the engine, so the 3D can show
one honestly?

**Short answer.**

- The first stop needs **12 laps** under the recorder's real config when the
  weather stays dry. That is the three SOFT starters reaching `tyre_life <= 18%`
  (fuel would last ~94 laps). All three races were recorded at **15 laps**. The
  seeded weather turns damp after about the 4th lap, so the SOFT starters
  actually stopped one lap earlier, at the end of **lap 11** (LEC at lap 12 in
  (b)). No MEDIUM or HARD starter reaches the threshold in 15 laps.
- **A pit stop in the engine is bookkeeping at the lap line, not a place.** On
  one tick the tyres are swapped and `pit_stops` goes up. The car does not slow
  down, leave the track or stop, and the engine's `pitting` flag is never true.
  The 22 s pit time is added to the *next* lap's time. Running order and race
  progress ignore it. The viewer now shows exactly that, in the car panel and
  on the timeline, with no pit lane drawn.
- Like for like, untuned v2 (b) against ours (c), one seed: the untuned
  controller laps ours **~11% faster** (best 108.7 s against 122.1 s, field
  median 118.8 s against 131.0 s). It leaves the track less (0.39% of samples
  against 1.41%) and never loses progress (0 backward ticks against 132). The
  phase 0b solo laps point the same way (119.4 s against 129.4 s). This is an
  observation from one seed, not a conclusion.

Commands. Recorder and horizon run in WSL (Ubuntu-22.04, `~/venvs/sim`, through
the `.sh` files). The rest runs from `viz3d/`:

```bash
wsl -d Ubuntu-22.04 -- bash /mnt/c/<...>/viz3d/scripts/pit_horizon.sh --json viz3d/.cache/pit_horizon.json
wsl -d Ubuntu-22.04 -- bash /mnt/c/<...>/viz3d/scripts/record_phase3b.sh 15     # (a), (b), (c) in turn
python scripts/check_recording.py .cache/recordings/<run>.jsonl --json .cache/recordings/<run>.check.json
python scripts/compare_recordings.py .cache/recordings/interlagos_seed42_15laps_a_tuned.jsonl \
    .cache/recordings/interlagos_seed42_15laps_b_untuned.jsonl \
    .cache/recordings/interlagos_2023_seed42_15laps_c_ours.jsonl --json .cache/recordings/compare_15laps.json
python scripts/trim_recording.py .cache/recordings/interlagos_2023_seed42_15laps_c_ours.jsonl \
    --from-s 1340 --out public/recordings/engine-interlagos2023-seed42-pit.jsonl
npm run typecheck && npm test && npm run snapshot
```

## 1. Race length, from the code

The engine decides on a stop in `SimulationEngine._complete_lap`
(`backend/engine/simulation.py`), once per car per completed lap. The steps
are: `car.apply_lap` burns the lap's fuel, `tyre.apply_lap` wears the tyre,
the weather steps, then `needs_pit(config.fuel_threshold_kg,
config.tyre_life_threshold)` is asked. The recorder never sets the thresholds,
so they are `SimulationConfig`'s defaults: **fuel <= 6.0 kg or tyre life <=
18.0%**, with `pit_time_s` 22.0. `backend/config/__init__.py` has other values
(40 kg, 35%), but the engine does not read that file.

`scripts/pit_horizon.py` replays that bookkeeping with the backend's own
classes. It uses the recorder's grid (`build_grid_drivers`: 110 kg tanks, full,
740 kW, `aggressive` 1.0) and each track's `length_km`. Wear per lap is
`life_decay_per_lap × weather_wear_penalty × length_km / 4.5 × aggressive`.
Fuel per lap is `0.35 × 740/735 × length_km × 0.75`.

| | interlagos_v2 (4160.4 m) | ours (4225.4 m) |
|---|---|---|
| fuel per lap | 1.10 kg → threshold after ~94 laps | 1.12 kg → ~93 laps |
| SOFT (VER, LEC, RUS), dry | **lap 12** | **lap 12** |
| MEDIUM (NOR, HAM, PIA, SAI, GAS), dry | lap 17 | lap 16 |
| HARD (PER, ALO), dry | lap 23 | lap 22 |
| SOFT, worst weather (WET, grip 0.45) | lap 6 | lap 6 |

First stop: 12 laps. Recorded: **15** (12 + 3). The margin covers the slowest
SOFT car reaching its 12th lap before the leader's 15th, and one lap after the
stop so its charged lap time is in the recording. 15 is under the 25-lap cap,
and the thresholds were left alone.

The weather moved the stop. Tyre wear per completed lap, divided by the dry
wear, is the engine's `weather_wear_penalty`. In all three recordings it takes
two values, ×1.0 (dry/cloudy) and ×1.5 (DAMP, `grip_factor` 0.75). The first
damp lap is about the 4th, and the weather changes several times after that.
The ticks do not carry the weather, so this is read from the tyres. With damp
laps mixed in, the SOFTs crossed 18% one lap early.

## 2. The three recordings

Same seed 42, apex-rules profile, grid (shuffled to GAS HAM RUS VER PIA PER LEC
NOR ALO SAI), seeded weather, 15 laps, 10 Hz with 24 sub-steps. Recorded one
after another, single process, WSL Ubuntu 22.04, Python 3.10.12.

| | track | Interlagos tuning | sim time | wall (loop) | real-time factor loop / engine only | ticks | file |
|---|---|---|---|---|---|---|---|
| (a) | interlagos_v2 | **on** (engine as is) | 1774.6 s | 424.1 s | **4.18×** / 4.56× | 17,746 | 51.1 MB |
| (b) | interlagos_v2 | **forced off** | 1985.9 s | 473.7 s | **4.19×** / 4.57× | 19,859 | 57.2 MB |
| (c) | `exports/interlagos_2023_v1.json` | off (not keyed to it) | 1779.7 s | 405.5 s | **4.39×** / 4.79× | 17,797 | 51.3 MB |

Setup took 0.8–2.6 s. Full recordings are in `.cache/recordings/` (gitignored).
Phase 3's 3-lap run was 4.36× on the same machine.

Recorder changes (`scripts/record_race.py`, script-side only, backend
untouched):

- `--tracks-dir`: points `FROZEN_TRACKS_DIR` at `viz3d/exports` for the one
  `load_track_frozen` call, as `smoke_engine_lap.py` does. The backend's own
  loader hash-checks the export.
- `--interlagos-tuning off`: blanks `INTERLAGOS_GEOMETRY_SHA256` while the
  controller is built, as `smoke_engine_lap.py` does.
  `recording.interlagos_tuning.applied` reads back
  `_interlagos_line_applied`: true for (a), false for (b) and (c).
- Every position also carries `fuel_kg`, `pit_stops` (`pit_stop_done`) and
  `pit_penalty_pending_s`. The header carries `pit_config`, per-driver
  `lap_times_s` (the engine's own) and `pit_events`.

## 3. Comparison

`check_recording.py` (all three, full race):

| | (a) v2 tuned | (b) v2 untuned | (c) ours |
|---|---|---|---|
| header (hash, length) | ok | ok | ok |
| round trip max on / off track | 0.8 / 0.9 mm | 0.9 / 1.0 mm | 0.7 / 0.7 mm |
| refined projector bracketed | every sample | every sample | every sample |
| `progress_m` monotonic | 8 of 10 cars, **71** backward ticks | 7 of 10, **132** | **10 of 10, 0** |
| dropped steps | 0 | 0 | 0 |
| pairwise swaps (lap 1) | 83 (37) | 91 (37) | 122 (47) |
| **net overtakes** (2 s flickers removed) | 60 | 67 | **88** |
| swaps involving an off-track car | 8 | 14 | 7 |
| `corr(d_m, d_engine)` on track | −0.99996 | −0.99995 | −1.00000 |
| heading − tangent, on-track p99 / max overall | 21.7° / 107.0° | 35.8° / **179.8°** | **9.8°** / 81.3° |

From `compare_recordings.py`:

| | (a) | (b) | (c) |
|---|---|---|---|
| field best lap / median lap (pit-charged laps excluded) | 107.0 / 117.1 s | 122.1 / 131.0 s | 108.7 / 118.8 s |
| off-track share (\|d_m\| > 6 m) | 1.07% (1,904) | 1.41% (2,790) | **0.39%** (702) |
| excursions (median length) | 20 (1.5 s) | **52** (4.7 s) | 23 (0.6 s) |
| \|d_m\| p50 / p90 / p99 / p99.9 / max | 0.46 / 2.91 / 7.49 / 31.7 / 38.8 m | 0.40 / 2.91 / 7.06 / 24.8 / 28.0 m | 0.56 / 3.10 / **4.18** / 43.8 / **46.8** m |
| samples under 1 m/s after 10 s | 116 | 106 | **0** |
| `pitting` true | 0 | 0 | 0 |

Lap times per car, the engine's own `lap_times_s`. The median includes the
pit-charged lap, which is +22 s, and the standing-start lap 1.

| car (grid) | start tyre | (a) best / median | (b) best / median | (c) best / median | stop after lap a / b / c |
|---|---|---|---|---|---|
| GAS (P1) | MEDIUM | 110.7 / 117.3 | 125.4 / 135.0 | 111.6 / 118.6 | – / – / – |
| HAM (P2) | MEDIUM | 110.5 / 116.6 | 123.8 / 129.8 | 112.7 / 119.5 | – / – / – |
| RUS (P3) | SOFT | 107.8 / 114.8 | 122.1 / 130.1 | 108.7 / 116.5 | 11 / 11 / 11 |
| VER (P4) | SOFT | 107.0 / 111.0 | 122.1 / 126.0 | 108.7 / 113.9 | 11 / 11 / 11 |
| PIA (P5) | MEDIUM | 111.6 / 118.2 | 126.3 / 133.7 | 112.6 / 121.0 | – / – / – |
| PER (P6) | HARD | 112.3 / 119.7 | 124.8 / 136.9 | 113.9 / 121.3 | – / – / – |
| LEC (P7) | SOFT | 109.2 / 117.2 | 122.7 / 130.8 | 110.3 / 117.0 | 11 / **12** / 11 |
| NOR (P8) | MEDIUM | 110.1 / 119.1 | 125.5 / 134.0 | 111.0 / 119.7 | – / – / – |
| ALO (P9) | HARD | 111.4 / 116.8 | 125.9 / 131.4 | 113.2 / 119.3 | – / – / – |
| SAI (P10) | MEDIUM | 111.9 / 118.4 | 125.5 / 135.4 | 111.4 / 118.7 | – / – / – |

Final order. The race ends the instant the leader completes lap 15. The gap is
the leader's `progress_m` lead, in laps.

| | final order | gaps (laps) |
|---|---|---|
| (a) | VER RUS LEC HAM PIA PER NOR SAI GAS ALO | 0, 0.11, 0.32, 1.58, 1.67, 1.91, 1.93, 1.95, 1.96, 2.29 |
| (b) | VER RUS LEC HAM ALO NOR PER SAI GAS PIA | 0, 0.36, 0.89, 1.39, 1.58, 1.63, 1.65, 1.85, 1.89, 2.08 |
| (c) | VER RUS LEC GAS NOR ALO SAI PIA PER HAM | 0, 0.26, 0.41, 1.60, 1.71, 1.77, 1.82, 1.82, 1.86, 1.91 |

**Common to all three.** The three SOFT starters finish 1-2-3, in the same
order, and are the only cars on the lead lap. Everyone else is 1.4–2.3 laps
down. The likely mechanism is in the tyre model. Grip is `grip_<weather> ×
(0.85 + 0.15 × life)`, and in DAMP a SOFT has 0.60, a MEDIUM 0.58, a HARD 0.55
and an INTERMEDIATE 0.95. Only the SOFT starters wear down to the threshold, so
only they get INTERMEDIATEs (lap 12 for VER on (c): 107.3 s driven, against
118.8 s on lap 10). The other seven run slicks in the damp to the flag. The lap
that ends in the stop, the last on worn SOFTs, is the slowest of each stopper's
race in all nine cases (VER 162.5 s on (c), up to 196.3 s for LEC on (b)). This is the engine's strategy model, the same on every track.

**Like for like, (b) against (c).** Both run the controller's defaults
(lateral factor 0.58, 6 m/s²). On ours it is faster for every car: best laps
are 10.9–14.5 s quicker, and the race is 206 s shorter for the same 15 leader
laps. It is cleaner: about a third of the off-track share, excursions of 0.6 s
median against 4.7 s, no backward progress and no car below 1 m/s. On-track
heading stays closer to the tangent (p99 9.8° against 35.8°). It also produces
more net overtakes (88 against 67, with 47 swaps on lap 1 against 37). Our
track is 65 m (1.6%) longer, so the gap is not length. A centreline from
telemetry is smoother than v2's marker spline (phase 0 report), which is the
obvious candidate, not a measured cause. (c) without tuning is also within
0.3% of (a)'s race time with tuning (1779.7 s against 1774.6 s).

**Only on one track.**

- (b) only: a car at **179.8°** to the tangent, i.e. facing backwards. LEC
  stops after lap 12 instead of 11: he reached his laps later relative to the
  weather changes, so his SOFTs saw one damp lap fewer (19.1% before the lap,
  against 26.4% for VER). 52 excursions, most of them 4–9 s at 7–8 m that
  recur lap after lap from lap 11 on, for nearly every car.
- (c) only: the largest excursion of the three. HAM and SAI together at sim
  1730 s, s ≈ 211→288 m just after the line, out to 46.4 and 46.8 m for 37 s
  and 18 s. HAM falls P6 → P10. Progress kept moving forward (2 m/s and 5 m/s
  through it), so nothing was dropped or reversed. It is the whole of (c)'s
  p99.9.
- (a) only: none of its own kind. It has multi-car excursions like the others
  (NOR, ALO and SAI at ~1242–1287 s; GAS and RUS at ~1581 s). ALO ends 2.29
  laps down, the largest gap of the three races.

One seed, one machine. The differences above are what this seed did. Both
interlagos_v2 runs share the cars that stop and the final top three, and
diverge everywhere else.

## 4. What the engine does during a pit stop

From the code (`_complete_lap`, `_perform_pit`, `DriverState.perform_pit_stop`)
and recording (c):

1. **When.** Inside `_complete_lap`, on the tick the car's `race_progress_m`
   crosses its next lap boundary (`track_progress_laps=True`). The tyre is
   worn for that lap, the weather steps, and `needs_pit` is asked.
2. **What changes.** The compound is picked from the weather *now*: DRY/CLOUDY
   → MEDIUM, DAMP → INTERMEDIATE, WET → WET. All nine stops here went to
   INTERMEDIATE. Tyre life goes to 100% and age to 0. Fuel is topped up to 70%
   of the tank (77 kg). With ~98 kg aboard that adds **0 kg**: fuel went from
   98.83 to 97.72 kg, which is just the lap's consumption. Then
   `pit_penalty_pending_s = 22.0`, `pit_stop_done += 1`, `pitting = False`.
3. **Where the car is.** On the racing line, at the start/finish line, at
   racing speed: VER 65.3 → 65.5 → 66.0 m/s across the stop tick on (c),
   still P1. **Nothing in the backend ever sets `pitting = True`.** The
   physics branch that holds a pitting car still (`if state.pitting:`, zero
   throttle, full brake) is unreachable. So is `_check_lap_completion`'s
   pitting skip. `Track.pit` (`PitLane`, entry/exit waypoints, speed limit) is
   only serialised in `Track.to_dict`; the engine never reads it.
4. **What the tick shows.** On one tick (0.1 s), `tyre_compound`,
   `tyre_life_pct` and `fuel_kg` change, `lap` goes up (it is the lap line),
   `pit_stops` goes from 0 to 1 and `pit_penalty_pending_s` from 0 to 22.
   `pitting` stays false: 0 true samples in 554,020 car-ticks across the
   three races. The tick before the stop shows tyre life *before* the last
   lap's wear (VER: SOFT 25.2%). The worn value, at or below 18%, is never in a
   tick, because wear, decision and swap all happen in one call.
5. **How long.** The 22 s exists only as a number. It is pending for one lap
   (VER 107.3 s, RUS 108.5 s, LEC 110.5 s on (c)), then added to that lap's
   `lap_times` and `total_time_s` (VER lap 12: 129.3 s = 107.3 + 22.0). It
   never touches `race_progress_m`, so `ranked_drivers`, every tick's running
   order, the finish (leader's lap count) and the `RaceEndEvent` order ignore
   it. A stop costs no position on track. Only `total_time_s` in the end
   classification carries it.

**In the viewer**, no pit lane is drawn and the car is not moved; it is drawn
where the engine says it is.

- **Car panel** (engine source): a tyre line, `tyres INTERMEDIATE 100.0% · 1
  stop`. While a stop's penalty is pending, an amber line reads `PIT end of
  lap 11: SOFT (25.2% before that lap) → INTERMEDIATE 100.0%, +22.0 s on lap
  12's time (car not stopped)`. If the engine ever does set `pitting`, the
  line reads `PITTING (engine flag)`. The prose under the panel says what a
  stop is.
- **Timeline**: one mark per stop under the scrub bar, amber and taller for
  the followed car. The hover gives car, lap, tyres, penalty and sim time. The
  lap readout gains `· PIT +22 s` while it is pending.
- Data path: `parseRecording` reads the new fields when present (phase 3
  recordings parse as before, `hasPitFields: false`). It derives `pitEvents`
  from the ticks, not the header, so a trimmed window still finds its stops.
  `pitStateAt` / `tyreText` / `pitText` live in `src/engine/source.ts`.

**Fixture.** `public/recordings/engine-interlagos2023-seed42-pit.jsonl`,
998,759 bytes: 335 ticks, sim 1340.0–1373.4 s of (c), with VER's stop at
tick 52 (1345.2 s) and RUS's at tick 188 (1358.8 s). The header keeps the full
race's `lap_times_s` and `pit_events`, plus the `trimmed` note.

## 5. Viewer

The track picker has **"Engine race · our Interlagos · pit"** (`?track=engine_ours`)
next to "Engine race · seed 42". The track is built from the fixture's race
block, as for `engine`. Checks: A passes (4225.4 m against 4309 m, −1.94%), E
and F pass, B C D G skip (no corners). Pinned as `engine_ours` in
`expected-verdicts.json`.

## 6. Verification

- `npm run typecheck`: clean.
- `npm test`: **110 tests pass** (102 before). New: `src/engine/pit.test.ts`,
  7 tests, and the `engine_ours` verdict row in `tracks.test.ts`. On the pit
  fixture they check: size ≤ 1 MB, the hash, `toWorld` round trip < 1 mm, and
  `positionAt` matching every tick. Every derived stop matches the recorder's
  `pit_events`: tick, lap, tyres before and after, penalty. A stop is one tick
  at the lap line: lap +1, life 100, penalty 22, car above 20 m/s and
  advancing, `pitting` never true. The pit line is active exactly while the
  lap after the stop is driven. The phase 3 fixture shows no pit state.
- `npm run snapshot`: **all checks pass**, exit 0. The new `engine_ours` run is
  reached through the picker. It renders orbit, chase and T-cam under the
  engine source and the synthetic field (non-background 1.78–38.91%), with
  verdicts as pinned and check J PASS. The timeline shows 2 pit marks, one per
  stop in the fixture. Then it pauses on ticks 0, 52 (VER's stop), 72 and 334,
  following VER on the pit ticks. On each tick, placement from the GPU
  instance matrices is ≤ 1.7×10⁻⁵ m, and the panel shows the recorded P and
  `d_m`. The T-cam is within 1.6×10⁻⁵ m. On 52 and 72 the panel's tyre line,
  pit line (visible) and timeline tag equal the text rebuilt from the file.
  Phase 3's `engine` run is unchanged and passes. The pit ticks are found in
  the file, not hard-coded.
- The recordings' headers have `git.backend_dirty: true`, from the same
  pre-existing edit to `backend/experiments/prof-grip-1/corridas/CTRL_Interlagos_OFF.log`
  as phase 3. No backend file was changed.

## 7. Open

- One seed. Pace, excursions and overtakes above are one realisation, and so
  are the weather's timing and the pit laps it moved.
- The pit model has no on-track cost. A stop changes tyres on the line at
  racing speed and charges 22 s to a lap time that the order ignores. That is
  the engine's behaviour, reported, not changed. If the group wants stops to
  cost position, it is an engine change: use `pitting` and `Track.pit`, or
  fold `pit_penalty_pending_s` into the order.
- Refuelling to 70% does nothing in a race this short (tanks start full at
  110 kg). Only HARD/MEDIUM starters in a longer race would show a second
  stop.
