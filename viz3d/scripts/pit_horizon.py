"""How many laps until the first pit stop, from the engine's own code.

Phase 3b, step 1. Run in WSL like the recorder (`scripts/pit_horizon.sh`).

The engine decides a stop in `SimulationEngine._complete_lap`, once per car per
completed lap: `car.apply_lap(track.length_km, driver.aggressive)` burns the
lap's fuel, `tyre.apply_lap(track.length_km, weather.grip_factor,
driver.aggressive)` wears the tyre, the weather steps, and then
`state.needs_pit(config.fuel_threshold_kg, config.tyre_life_threshold)` is
asked. This replays exactly that bookkeeping, with the backend's own classes,
for the recorder's grid (`run_race_10_cars.build_grid_drivers`) on each track
and the recorder's `SimulationConfig` thresholds (the recorder sets neither,
so they are the dataclass defaults). Nothing here is physics: wear and fuel per
lap do not depend on how the lap was driven, only on track length, compound,
`aggressive` and the weather's `grip_factor`.

Weather is the one input that is not fixed: the recorder's `WeatherModel` is
seeded and can leave DRY, and a lower `grip_factor` wears dry tyres faster. So
the horizon is reported for DRY (grip 1.0) and for the worst state the model
can reach (WET at its 0.45 floor) as a bracket; the recording itself says
which happened.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from record_race import load_race_script  # noqa: E402


def first_pit_lap(driver, length_km: float, grip: float, fuel_thr: float, tyre_thr: float,
                  max_laps: int = 200):
    state = driver.initial_state()
    for lap in range(1, max_laps + 1):
        state.car.apply_lap(length_km, driver.aggressive)
        state.tyre.apply_lap(length_km, grip, driver.aggressive)
        if state.needs_pit(fuel_thr, tyre_thr):
            why = []
            if state.car.fuel_kg <= fuel_thr:
                why.append("fuel")
            if state.tyre.tyre_life <= tyre_thr:
                why.append("tyre")
            return lap, why, round(state.tyre.tyre_life, 2), round(state.car.fuel_kg, 2)
    return None, [], round(state.tyre.tyre_life, 2), round(state.car.fuel_kg, 2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    rr = load_race_script()
    import backend.domain.track_resolution as tr
    from backend.domain import BASE_CONDITIONS, WeatherKind
    from backend.engine import SimulationConfig

    cfg = SimulationConfig()
    fields = {f.name: f.default for f in dataclasses.fields(SimulationConfig)}
    fuel_thr, tyre_thr = cfg.fuel_threshold_kg, cfg.tyre_life_threshold
    assert (fuel_thr, tyre_thr) == (fields["fuel_threshold_kg"], fields["tyre_life_threshold"])

    tracks = {"interlagos_v2": tr.load_track_frozen("interlagos", strict=True)}
    saved = tr.FROZEN_TRACKS_DIR
    tr.FROZEN_TRACKS_DIR = ROOT / "viz3d" / "exports"
    try:
        tracks["interlagos_2023_v1"] = tr.load_track_frozen("interlagos_2023", strict=True)
    finally:
        tr.FROZEN_TRACKS_DIR = saved

    dry = BASE_CONDITIONS[WeatherKind.DRY].grip_factor
    worst = 0.45   # WeatherState.grip_factor's floor for WET
    drivers = rr.build_grid_drivers()
    report = {"fuel_threshold_kg": fuel_thr, "tyre_life_threshold": tyre_thr,
              "pit_time_s": cfg.pit_time_s, "tracks": {}}
    for name, track in tracks.items():
        rows = {}
        for d in drivers:
            lap_dry, why, life, fuel = first_pit_lap(d, track.length_km, dry, fuel_thr, tyre_thr)
            lap_wet, *_ = first_pit_lap(d, track.length_km, worst, fuel_thr, tyre_thr)
            rows[d.driver_id] = {"compound": d.starting_tyre_compound.value,
                                 "aggressive": d.aggressive,
                                 "first_pit_lap_dry": lap_dry, "reason": why,
                                 "tyre_life_at_pit": life, "fuel_kg_at_pit": fuel,
                                 "first_pit_lap_worst_weather": lap_wet}
        fuel_per_lap = drivers[0].initial_state().car.consume_fuel_per_lap(track.length_km, 1.0)
        report["tracks"][name] = {
            "length_km": round(track.length_km, 4),
            "fuel_per_lap_kg": round(fuel_per_lap, 4),
            "first_pit_lap_dry": min(r["first_pit_lap_dry"] for r in rows.values()),
            "drivers": rows,
        }
    print(json.dumps(report, indent=1))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
