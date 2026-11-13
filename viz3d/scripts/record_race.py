"""Record a headless 10-car race from the group's engine as JSONL ticks.

Phase 3, step 1. Run in WSL (pybullet has Linux wheels only), from the repo
root, through `viz3d/scripts/record_race.sh`:

    bash viz3d/scripts/record_race.sh            # seed 42, 3 laps, interlagos

**Driven exactly as `backend/scripts/run_race_10_cars.py` drives its default
`apex-rules` profile.** That script never calls `engine.run()`, and the two are
not equivalent: `run()` also steps the weather to lap 1 before the first tick,
publishes a race-start event and caps the tick count, none of which the 10-car
script does. So this reproduces the script's own loop instead:

- the grid, the seeded variance and the grid layout come from the script's own
  functions (`build_grid_drivers`, `resolve_race_randomization`, `place_grid`),
  imported from it rather than copied, so they cannot drift. With
  `--seed 42` and no `--variance`, the apex-rules default is `grid`: the
  starting order is shuffled by `racevar.shuffled_order` on the seed's own
  stream, and compounds stay as `GRID_DRIVERS_CONFIG` sets them;
- weather `seeded` (the script's default): `weather_rng_from_seed(seed)`;
- `SimulationConfig` with the script's values, except `gui=False` (its
  `--no-gui`) and `realtime=False`. The script cannot turn realtime off - its
  `--realtime` is `store_true` with `default=True` - and realtime only sleeps
  between ticks, it does not touch the physics;
- `engine.setup()`, `place_grid(layout="f1", jitter=None)` (`--variedade 0`),
  no anti-glue, `RuleBasedRaceController(track, seed=seed)` on every car;
- `race_started = True`, then `engine._step_tick(1 / hz, sub_steps)` until
  `race_finished`. The leaderboard print, the 3D labels and the authority
  counter are display-only and are left out.

One tick line is written after every `_step_tick`, at the point the engine
publishes its own `TickEvent`: `ranked_drivers()` order, the engine's own
`_snapshot_position` for the shared fields (so their rounding is the engine's),
plus `progress_m` (`engine.race_progress_m`), and `s_m` / `d_m` from our refined
projector (`centreline.py`) against the same waypoints, rolled so that s = 0 is
the start/finish waypoint. `d_m` is positive to the RIGHT of travel - the
engine's `f1_env` lateral is +left - and both are computed from the rounded
`position_xy` that is written, so the line is self-consistent: a reader's
`toWorld(s_m, d_m)` reproduces `position_xy` up to the stored precision.

Output: `viz3d/.cache/recordings/` (gitignored). `trim_recording.py` cuts the
committed test fixture from it.

Phase 3b additions (script-side only, the backend is unchanged):

- `--tracks-dir DIR` points the backend's `FROZEN_TRACKS_DIR` at `DIR` for the
  one `load_track_frozen` call, as `smoke_engine_lap.py` does, so
  `--track interlagos_2023 --tracks-dir viz3d/exports` races on our own
  Interlagos export (hash-checked by the backend's own loader);
- `--interlagos-tuning off` blanks `RuleBasedRaceController.
  INTERLAGOS_GEOMETRY_SHA256` while the controller is constructed, so its
  Interlagos-only line, lateral factor and acceleration never activate, as
  `smoke_engine_lap.py` does. The header records whether it was applied;
- every position also carries the engine state that a pit stop changes:
  `fuel_kg` (the engine's snapshot), `pit_stops` (`pit_stop_done`) and
  `pit_penalty_pending_s`. The header gains `pit_config` (the thresholds and
  pit time the engine ran with), per-driver `lap_times_s`, and `pit_events`:
  the tick on which each driver's `pit_stop_done` went up, with the lap,
  position, tyres and fuel before and after.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from centreline import frame_from_three, project_global, project_windowed, wrap_s  # noqa: E402

RACE_SCRIPT = ROOT / "backend" / "scripts" / "run_race_10_cars.py"
DEFAULT_OUT = ROOT / "viz3d" / ".cache" / "recordings"

#: The profile this reproduces. Only apex-rules: the neural profiles need
#: checkpoints and a batched inference step the recorder does not replicate.
PROFILE = "apex-rules"


def load_race_script():
    """Import `run_race_10_cars.py` as a module, without running `run_race()`.

    Its top level only sets up `sys.path`, checks for a `backend/.venv` (absent
    here, so no re-exec) and imports the engine; `run_race()` runs under
    `__main__` only.
    """
    spec = importlib.util.spec_from_file_location("run_race_10_cars", RACE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_head() -> dict:
    def run(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                                  text=True, check=True).stdout.strip()
        except Exception:
            return None
    return {"commit": run("rev-parse", "HEAD"),
            "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
            "backend_dirty": bool(run("status", "--porcelain", "--", "backend"))}


def rolled_frame(waypoints: np.ndarray, sf_idx: int, width_m: float):
    """Our centreline frame on the engine's waypoints, s = 0 at `sf_idx`.

    Engine plan `(x, y)` -> Three.js `(x, 0, -y)`, CLAUDE.md's mapping. Rolling
    a closed polyline changes no segment, so arc lengths only shift by the
    start/finish waypoint's own `s`, and the central-difference tangents are
    the same vectors at the same vertices.
    """
    rolled = np.roll(waypoints, -sf_idx, axis=0)
    xyz = np.column_stack([rolled[:, 0], np.zeros(len(rolled)), -rolled[:, 1]])
    return frame_from_three(xyz, width_m=width_m)


class Projector:
    """Per-car stateful wrapper: windowed search centred on a velocity prediction."""

    def __init__(self, frame, dt: float):
        self.frame = frame
        self.dt = dt
        self.prev: dict[str, float] = {}
        self.fallbacks = 0
        self.calls = 0

    def __call__(self, driver_id: str, xy, speed_mps: float):
        p = np.array([xy[0], -xy[1]], dtype=float)       # three plan (x, z)
        self.calls += 1
        prev = self.prev.get(driver_id)
        if prev is None:
            s, d, _ = project_global(self.frame, p)
        else:
            s, d, _, fell = project_windowed(self.frame, p, prev + speed_mps * self.dt)
            self.fallbacks += int(fell)
        s = float(wrap_s(self.frame, s))
        self.prev[driver_id] = s
        return s, d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--track", default="interlagos")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--laps", type=int, default=3)
    ap.add_argument("--hz", type=float, default=10.0, help="run_race_10_cars default")
    ap.add_argument("--sub-steps", type=int, default=24, help="run_race_10_cars default")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--tracks-dir", type=Path, default=None,
                    help="point the backend's FROZEN_TRACKS_DIR here for the track load")
    ap.add_argument("--interlagos-tuning", choices=("auto", "off"), default="auto",
                    help="off: keep the controller's Interlagos-only tuning from activating")
    ap.add_argument("--label", default=None, help="output name suffix")
    ap.add_argument("--max-sim-s", type=float, default=3600.0,
                    help="abort if the race has not finished by then (run_race has no cap)")
    args = ap.parse_args()

    t_setup = time.perf_counter()
    rr = load_race_script()
    from backend.domain import BASE_CONDITIONS, WeatherKind
    from backend.domain import WeatherModel
    from backend.domain.track_resolution import track_identity
    from backend.domain.weather import weather_rng_from_seed
    from backend.engine import RuleBasedRaceController, SimulationConfig, SimulationEngine
    from backend.model_train.f1_env import load_track_frozen

    use_rule_controller = rr.PROFILES[PROFILE].get("controller") == "apex-rules"
    assert use_rule_controller and rr.DEFAULT_PROFILE == PROFILE
    seed, variance = rr.resolve_race_randomization(args.seed, None, use_rule_controller)

    import backend.domain.track_resolution as tr
    saved_dir = tr.FROZEN_TRACKS_DIR
    if args.tracks_dir is not None:
        tr.FROZEN_TRACKS_DIR = args.tracks_dir.resolve()
    try:
        track = load_track_frozen(args.track, strict=True)
    finally:
        tr.FROZEN_TRACKS_DIR = saved_dir
    drivers = rr.build_grid_drivers()
    if variance not in ("off", "none", "0", ""):
        from backend.domain.racevar import (assign_compounds, parse_variance,
                                            shuffled_order, variance_rng_from_seed)
        vd = parse_variance(variance)
        if "compound" in vd:
            pool = [d.starting_tyre_compound for d in drivers]
            cmap = assign_compounds(variance_rng_from_seed(seed, "compound"),
                                    [d.driver_id for d in drivers], pool)
            for d in drivers:
                d.starting_tyre_compound = cmap[d.driver_id]
        if "grid" in vd:
            order = shuffled_order(variance_rng_from_seed(seed, "grid"), len(drivers))
            drivers = [drivers[k] for k in order]

    sim_config = SimulationConfig(
        race_id="f1_10_cars_race",
        num_laps=args.laps,
        logic_step_hz=args.hz,
        physics_sub_steps=args.sub_steps,
        gui=False,
        camera_mode="follow",
        draw_track=True,
        realtime=False,
        random_seed=seed,
        track_progress_laps=True,
        input_stale_after_s=300.0,
    )
    weather_model = WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY], config=None,
                                 rng=weather_rng_from_seed(seed))
    engine = SimulationEngine(config=sim_config, track=track, drivers=drivers,
                              weather_model=weather_model)
    engine.setup()
    rr.place_grid(engine, track, drivers, layout="f1", jitter=None)
    if args.interlagos_tuning == "off":
        saved_key = RuleBasedRaceController.INTERLAGOS_GEOMETRY_SHA256
        RuleBasedRaceController.INTERLAGOS_GEOMETRY_SHA256 = ""
        try:
            controller = RuleBasedRaceController(track, seed=seed)
        finally:
            RuleBasedRaceController.INTERLAGOS_GEOMETRY_SHA256 = saved_key
    else:
        controller = RuleBasedRaceController(track, seed=seed)
    tuning_applied = bool(getattr(controller, "_interlagos_line_applied", False))
    for drv in drivers:
        engine.set_controller(drv.driver_id, controller)

    wps = np.asarray(track.waypoints, dtype=np.float64)
    sf_idx = int(track.start_finish_waypoint)
    ident = track_identity(track, requested=args.track, fonte="mirror")
    frame = rolled_frame(wps, sf_idx, float(track.width_m))
    if abs(frame.length_m - engine._race_track_length) > 1e-6:
        raise SystemExit(f"frame length {frame.length_m} != engine {engine._race_track_length}")
    project = Projector(frame, 1.0 / args.hz)
    setup_s = time.perf_counter() - t_setup

    dt = 1.0 / sim_config.logic_step_hz
    ticks: list[str] = []
    pit_events: list[dict] = []
    last_pit = {d.driver_id: 0 for d in drivers}
    before = {d.driver_id: None for d in drivers}   # previous tick's snapshot
    step_wall = 0.0
    t_loop = time.perf_counter()
    engine.race_started = True
    try:
        while not engine.race_finished:
            t0 = time.perf_counter()
            engine._step_tick(dt, sim_config.physics_sub_steps)
            step_wall += time.perf_counter() - t0
            if engine.sim_ts > args.max_sim_s:
                raise SystemExit(f"race not finished after {args.max_sim_s} s of sim time")

            ranked = engine.ranked_drivers()
            laps = [engine.states[d.driver_id].lap for d in drivers]
            positions = []
            for pos, d in enumerate(ranked, start=1):
                snap = engine._snapshot_position(d)
                st = engine.states[d.driver_id]
                if st.pit_stop_done != last_pit[d.driver_id]:
                    prev = before[d.driver_id] or {}
                    pit_events.append({
                        "driver_id": d.driver_id, "tick": len(ticks),
                        "sim_ts": round(engine.sim_ts, 4), "lap": st.lap,
                        "stop": st.pit_stop_done, "position": pos,
                        "tyre_before": [prev.get("tyre_compound"), prev.get("tyre_life_pct")],
                        "tyre_after": [snap["tyre_compound"], snap["tyre_life_pct"]],
                        "fuel_before_kg": prev.get("fuel_kg"), "fuel_after_kg": snap["fuel_kg"],
                        "penalty_s": round(st.pit_penalty_pending_s, 3),
                    })
                    last_pit[d.driver_id] = st.pit_stop_done
                before[d.driver_id] = snap
                s_m, d_m = project(d.driver_id, snap["position_xy"], snap["velocity_mps"])
                positions.append({
                    "driver_id": d.driver_id,
                    "position": pos,
                    "lap": snap["lap"],
                    "position_xy": snap["position_xy"],
                    "heading_deg": snap["heading_deg"],
                    "velocity_mps": snap["velocity_mps"],
                    "progress_m": round(float(engine.race_progress_m[d.driver_id]), 3),
                    "s_m": round(s_m, 3),
                    "d_m": round(d_m, 3),
                    "tyre_compound": snap["tyre_compound"],
                    "tyre_life_pct": snap["tyre_life_pct"],
                    "pitting": snap["pitting"],
                    "fuel_kg": snap["fuel_kg"],
                    "pit_stops": st.pit_stop_done,
                    "pit_penalty_pending_s": round(st.pit_penalty_pending_s, 3),
                })
            ticks.append(json.dumps({
                "sim_ts": round(engine.sim_ts, 4),
                "lap": max(0, min(laps)),       # TickEvent's own definition
                "leader_lap": max(laps),
                "positions": positions,
            }, separators=(",", ":")))
    finally:
        engine.physics.close()
    loop_wall = time.perf_counter() - t_loop
    sim_s = engine.sim_ts

    rtf = {
        "sim_s": round(sim_s, 3),
        "loop_wall_s": round(loop_wall, 3),
        "engine_step_wall_s": round(step_wall, 3),
        "setup_wall_s": round(setup_s, 3),
        "rtf_loop": round(sim_s / loop_wall, 3),
        "rtf_engine_only": round(sim_s / step_wall, 3),
    }
    final = sorted(engine.drivers, key=lambda d: -engine.race_progress_m[d.driver_id])
    header = {
        "race_id": sim_config.race_id,
        "num_laps": args.laps,
        "track": {
            "name": track.name,
            "source": ident["fonte"],
            "requested": args.track,
            "tracks_dir": (str(args.tracks_dir.resolve().relative_to(ROOT)).replace("\\", "/")
                           if args.tracks_dir is not None else None),
            "geometry_sha256": ident["sha256"],
            "frozen_sha256": getattr(track, "frozen_sha256", None),
            "length_m": engine._race_track_length,
            "width_m": float(track.width_m),
            "start_finish_waypoint": sf_idx,
            "waypoints": wps.tolist(),
        },
        "drivers": [{"driver_id": d.driver_id, "name": d.name, "grid_position": i + 1}
                    for i, d in enumerate(drivers)],
        "recording": {
            "profile": PROFILE,
            "seed": seed,
            "variance": variance,
            "weather": "seeded",
            "hz": args.hz,
            "physics_sub_steps": args.sub_steps,
            "ticks": len(ticks),
            "projector_windowed_fallbacks": project.fallbacks,
            "final_order": [d.driver_id for d in final],
            "final_laps": {d.driver_id: engine.states[d.driver_id].lap for d in final},
            "interlagos_tuning": {"requested": args.interlagos_tuning, "applied": tuning_applied},
            "pit_config": {"fuel_threshold_kg": sim_config.fuel_threshold_kg,
                           "tyre_life_threshold": sim_config.tyre_life_threshold,
                           "pit_time_s": sim_config.pit_time_s},
            "pit_events": pit_events,
            "lap_times_s": {d.driver_id: [round(t, 3) for t in engine.states[d.driver_id].lap_times]
                            for d in drivers},
            "realtime_factor": rtf,
            "git": git_head(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "recorder": "viz3d/scripts/record_race.py",
        },
    }

    suffix = f"_{args.label}" if args.label else ""
    out = args.out or DEFAULT_OUT / f"{args.track}_seed{seed}_{args.laps}laps{suffix}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(header, separators=(",", ":")) + "\n")
        for line in ticks:
            fh.write(line + "\n")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()[:16]
    print(json.dumps({"out": str(out), "bytes": out.stat().st_size, "sha256": digest,
                      "ticks": len(ticks), **rtf, "final_order": header["recording"]["final_order"],
                      "interlagos_tuning": header["recording"]["interlagos_tuning"],
                      "pit_events": [(e["driver_id"], e["lap"], e["sim_ts"]) for e in pit_events]},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
