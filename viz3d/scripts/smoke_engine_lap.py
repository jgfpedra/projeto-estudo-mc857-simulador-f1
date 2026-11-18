"""Smoke test: one solo dry lap on each exported track, in the real engine.

Phase 0b, step 5. No backend changes: this imports the backend as it is and
drives it exactly like its own clean-lap test
(`backend/tests/test_rule_based_race_controller.py::
test_rule_based_race_controller_clean_lap_interlagos`) - VER in the Red Bull
specs, dry `WeatherModel`, `SimulationConfig(num_laps=1, logic_step_hz=10,
physics_sub_steps=24, gui=False, random_seed=42)`, `place_grid`,
`RuleBasedRaceController(track, seed=42)`, 0.1 s ticks until lap 1 completes.

Tracks:
- `exports/*_v1.json`, each built into a `Track` by the backend's own
  `load_track_frozen` (hash-checked, `strict=True`), with its
  `FROZEN_TRACKS_DIR` pointed at `viz3d/exports/` for the call - nothing is
  copied into `backend/`;
- `interlagos_v2`, the engine's own frozen Interlagos, as the baseline.
  `backend/engine/racing_lines/README.md` ("Ritmo de volta") reports 112.7 s
  and 4.32 m max lateral deviation for this exact run.

Reported per track: lap time (the engine's own `lap_times[0]`), max |lateral
deviation| of the car centre from the centreline (`ctrl._project`, as the
test measures it), samples within 0.5 m of the edge, and whether the
controller's Interlagos-specific tuning activated. That tuning (lateral factor
0.65, 10 m/s^2, the local racing line) is keyed on the sha256 of the waypoint
array (`INTERLAGOS_GEOMETRY_SHA256`), so it activates only on interlagos_v2:
the exports run on the conservative defaults (0.58, 6 m/s^2), and their lap
times are not comparable to 112.7 s without that caveat.

Run from the repository root with an environment that has the backend's
dependencies: `backend/requirements.txt` plus joblib and gymnasium. pybullet
ships Linux wheels only, so on Windows use WSL with the venv in the Linux home:

    wsl -d Ubuntu-22.04 -- bash -lc "python3 -m venv ~/venvs/sim &&         ~/venvs/sim/bin/pip install -r backend/requirements.txt joblib gymnasium"
    ~/venvs/sim/bin/python viz3d/scripts/smoke_engine_lap.py   # from /mnt/c/.../repo

Also runs interlagos_v2 with the tuning forced off (script-side, no backend
change) as the same-environment baseline for the untuned exports. Results go
to `viz3d/.cache/smoke_engine_lap.json` (gitignored).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "viz3d" / "exports"
sys.path.insert(0, str(ROOT))

SEED = 42
DT = 0.1
MAX_TICKS = 3000          # 300 s of sim time; the README lap is 112.7 s
README_V2_LAP_S = 112.7
README_V2_MAX_LAT_M = 4.32
README_V2_UNTUNED_LAP_S = 126.1


def build_tracks():
    """(label, track, force_untuned). The extra interlagos_v2 row with the
    tuning forced off is the same-environment counterpart of the README's
    untuned 126.1 s, so the exports (always untuned) have a like-for-like
    baseline."""
    import backend.domain.track_resolution as tr

    v2 = tr.load_track_frozen("interlagos", strict=True)
    tracks = [("interlagos_v2 (engine)", v2, False),
              ("interlagos_v2 (tuning off)", v2, True)]
    original = tr.FROZEN_TRACKS_DIR
    tr.FROZEN_TRACKS_DIR = EXPORTS
    try:
        for f in sorted(EXPORTS.glob("*_v1.json")):
            key = f.name[: -len("_v1.json")]
            tracks.append((f"{key} (export)", tr.load_track_frozen(key, strict=True), False))
    finally:
        tr.FROZEN_TRACKS_DIR = original
    return tracks


def solo_lap(track, force_untuned: bool = False) -> dict:
    from backend.domain import BASE_CONDITIONS, CarSpecs, Driver, WeatherKind, WeatherModel
    from backend.engine import RuleBasedRaceController, SimulationConfig, SimulationEngine
    from backend.scripts.run_race_10_cars import place_grid

    driver = Driver("VER", "Max Verstappen", CarSpecs("Red Bull", 750, 798, 110))
    cfg = SimulationConfig(num_laps=1, logic_step_hz=10.0, physics_sub_steps=24,
                           gui=False, random_seed=SEED)
    wm = WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY])
    engine = SimulationEngine(config=cfg, track=track, drivers=[driver], weather_model=wm)
    if force_untuned:
        # Script-side only: blank the class's geometry key for the duration of
        # the constructor, so `_apply_local_racing_line` finds no match and the
        # controller keeps its default factor, acceleration and line. The
        # backend file is untouched and the attribute is restored at once.
        saved = RuleBasedRaceController.INTERLAGOS_GEOMETRY_SHA256
        RuleBasedRaceController.INTERLAGOS_GEOMETRY_SHA256 = ""
        try:
            ctrl = RuleBasedRaceController(track, seed=SEED)
        finally:
            RuleBasedRaceController.INTERLAGOS_GEOMETRY_SHA256 = saved
    else:
        ctrl = RuleBasedRaceController(track, seed=SEED)
    engine.setup()
    try:
        place_grid(engine, track, [driver])
        engine.set_controller("VER", ctrl)
        engine.race_started = True

        max_lat, max_lat_s, edge, ticks = 0.0, 0.0, 0, 0
        t0 = time.perf_counter()
        for ticks in range(1, MAX_TICKS + 1):
            engine._step_tick(DT, cfg.physics_sub_steps)
            pos = engine.physics.get_state(engine.handles["VER"])
            s, lat = ctrl._project("VER", pos["x"], pos["y"])
            if abs(lat) > max_lat:
                max_lat, max_lat_s = abs(lat), s
            if abs(lat) > ctrl._half_width - 0.5:
                edge += 1
            if engine.states["VER"].lap >= 1:
                break
        state = engine.states["VER"]
        return {
            "completed": state.lap >= 1,
            "lapTimeS": round(state.lap_times[0], 2) if state.lap_times else None,
            "simTimeS": round(ticks * DT, 1),
            "maxLatM": round(max_lat, 2),
            "maxLatAtS": round(max_lat_s, 1),
            "halfWidthM": ctrl._half_width,
            "edgeSamples": edge,
            "interlagosTuning": bool(ctrl._interlagos_line_applied),
            "lateralGripFactor": ctrl._lateral_grip_factor,
            "maxTargetAccel": ctrl._max_target_accel_mps2,
            "wallS": round(time.perf_counter() - t0, 1),
            "nWp": len(track.waypoints),
            "lengthM": round(float(ctrl._track_len), 1),
            "sfIdx": int(track.start_finish_waypoint),
            "sha256": getattr(track, "frozen_sha256", None),
        }
    finally:
        close = getattr(engine, "close", None) or getattr(engine, "shutdown", None)
        if callable(close):
            close()


def main() -> int:
    rows = []
    for label, track, untuned in build_tracks():
        r = {"track": label, **solo_lap(track, force_untuned=untuned)}
        rows.append(r)
        print(f"  {label:<28} lap {r['lapTimeS']} s  max |lat| {r['maxLatM']} m "
              f"(half width {r['halfWidthM']}) at s {r['maxLatAtS']}  edge samples "
              f"{r['edgeSamples']}  Interlagos tuning {'ON' if r['interlagosTuning'] else 'off'} "
              f"(factor {r['lateralGripFactor']}, accel {r['maxTargetAccel']})")
    print(f"  README, interlagos_v2: tuned {README_V2_LAP_S} s (max |lat| {README_V2_MAX_LAT_M} m), "
          f"untuned {README_V2_UNTUNED_LAP_S} s")
    out = ROOT / "viz3d" / ".cache" / "smoke_engine_lap.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {out}")
    return 0 if all(r["completed"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
