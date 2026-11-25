"""Compare engine recordings side by side: the phase 3b race-level numbers.

Phase 3b, step 3. Reads the JSONL recordings and, for each, the JSON report
`check_recording.py --json` wrote beside it (`<name>.check.json`), so the
header, progress, round-trip, overtake and |d_m| numbers come from that one
script rather than a second implementation. Adds what it does not measure:

- lap times per car, best and median, from the engine's own `lap_times_s`
  (header). A lap after a stop carries the engine's 22 s pit time, so the
  median is also given without those laps;
- final order and completed laps;
- off-track share, and excursions: contiguous runs of |d_m| > half width per
  car, with start, end and max |d_m|;
- pit stops per car (header `pit_events`), the lap they were taken at and
  tyres before / after;
- the weather the tyres saw: tyre life lost per completed lap, divided by the
  compound's dry wear for that track length, is the engine's
  `weather_wear_penalty` (1.0 = dry; the ticks do not carry the weather);
- stops: samples at < 1 m/s after the first 10 s, per car.

    python scripts/compare_recordings.py a.jsonl b.jsonl c.jsonl --json out.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

#: TyreModel.life_decay_per_lap, backend/domain/tyre.py (read, not imported:
#: this script runs on Windows without the backend's dependencies). The
#: recordings' own tyre life is the check: a dry lap must lose exactly this
#: times length_km / 4.5.
LIFE_DECAY = {"HARD": 4.0, "MEDIUM": 5.5, "SOFT": 7.5, "INTERMEDIATE": 6.0, "WET": 4.5}


def load(path: Path):
    with path.open(encoding="utf-8") as fh:
        header = json.loads(fh.readline())
        ticks = [json.loads(line) for line in fh if line.strip()]
    return header, ticks


def one(path: Path) -> dict:
    header, ticks = load(path)
    check_path = path.with_suffix(".check.json")
    check = json.loads(check_path.read_text(encoding="utf-8")) if check_path.exists() else None
    rec = header["recording"]
    ids = [d["driver_id"] for d in header["drivers"]]
    half_w = header["track"]["width_m"] / 2
    length_km = header["track"]["length_m"] / 1000
    n = len(ticks)
    t = np.array([tk["sim_ts"] for tk in ticks])
    d = np.zeros((n, len(ids)))
    v = np.zeros((n, len(ids)))
    life = np.zeros((n, len(ids)))
    lap = np.zeros((n, len(ids)), dtype=int)
    comp = [[None] * len(ids) for _ in range(n)]
    prog_end = {p["driver_id"]: p["progress_m"] for p in ticks[-1]["positions"]}
    for i, tk in enumerate(ticks):
        for p in tk["positions"]:
            j = ids.index(p["driver_id"])
            d[i, j] = p["d_m"]
            v[i, j] = p["velocity_mps"]
            life[i, j] = p["tyre_life_pct"]
            lap[i, j] = p["lap"]
            comp[i][j] = p["tyre_compound"]
    off = np.abs(d) > half_w

    excursions = []
    for j, did in enumerate(ids):
        i = 0
        while i < n:
            if off[i, j]:
                k = i
                while k + 1 < n and off[k + 1, j]:
                    k += 1
                excursions.append({"driver": did, "from_s": float(t[i]), "to_s": float(t[k]),
                                   "samples": k - i + 1, "lap": int(lap[i, j]) + 1,
                                   "max_abs_d_m": round(float(np.abs(d[i:k + 1, j]).max()), 2)})
                i = k + 1
            else:
                i += 1

    # weather_wear_penalty implied by each completed lap's tyre wear
    penalties = []
    for j in range(len(ids)):
        for i in range(1, n):
            if lap[i, j] == lap[i - 1, j] + 1 and life[i, j] < life[i - 1, j]:
                c = comp[i - 1][j]
                dry = LIFE_DECAY[c] * length_km / 4.5
                penalties.append((life[i - 1, j] - life[i, j]) / dry)

    lap_times = rec.get("lap_times_s", {})
    pit_events = rec.get("pit_events", [])
    pit_laps = {did: [] for did in ids}
    for e in pit_events:
        pit_laps[e["driver_id"]].append(e["lap"])
    laps_out = {}
    for did in ids:
        lt = lap_times.get(did, [])
        clean = [x for k, x in enumerate(lt, start=1) if (k - 1) not in pit_laps[did]]
        laps_out[did] = {
            "laps": len(lt),
            "best_s": round(min(lt), 3) if lt else None,
            "median_s": round(statistics.median(lt), 3) if lt else None,
            "median_excl_pit_lap_s": round(statistics.median(clean), 3) if clean else None,
            "pit_charged_laps": [k + 1 for k in pit_laps[did]],
        }

    stopped = {did: int(((v[:, j] < 1.0) & (t > 10.0)).sum()) for j, did in enumerate(ids)}
    final_laps = rec.get("final_laps", {})
    out = {
        "file": path.name,
        "track": header["track"]["name"],
        "length_m": header["track"]["length_m"],
        "interlagos_tuning": rec.get("interlagos_tuning"),
        "ticks": n,
        "sim_s": rec["realtime_factor"]["sim_s"],
        "realtime_factor": rec["realtime_factor"],
        "final_order": rec["final_order"],
        "final_laps": final_laps,
        # the race ends the moment the leader completes num_laps, so a car on
        # one lap fewer may still be on the lead lap: lapped is by progress gap
        "gap_to_leader_laps": {did: round((max(prog_end.values()) - prog_end[did])
                                          / header["track"]["length_m"], 2) for did in rec["final_order"]},
        "lapped": [did for did in rec["final_order"]
                   if max(prog_end.values()) - prog_end[did] >= header["track"]["length_m"]],
        "lap_times": laps_out,
        "field_best_lap_s": min(x["best_s"] for x in laps_out.values() if x["best_s"]),
        "field_median_lap_s": round(statistics.median(
            [x for did in ids for k, x in enumerate(lap_times.get(did, []))
             if k not in pit_laps[did]]), 3) if lap_times else None,
        "pit_events": pit_events,
        "pit_laps": pit_laps,
        "pitting_flag_true_samples": sum(p["pitting"] for tk in ticks for p in tk["positions"]),
        "weather_wear_penalty": {"laps": len(penalties),
                                 "min": round(min(penalties), 4) if penalties else None,
                                 "max": round(max(penalties), 4) if penalties else None},
        "off_track_fraction": round(float(off.mean()), 5),
        "off_track_samples": int(off.sum()),
        "excursions": excursions,
        "abs_d_m": {f"p{q:g}": round(float(np.percentile(np.abs(d), q)), 3)
                    for q in (50, 90, 99, 99.9, 100)},
        "stopped_samples_after_10s": stopped,
    }
    if check:
        out["check"] = {
            "sha_ok": check["header"]["sha_ok"], "length_ok": check["header"]["length_ok"],
            "monotonic_cars": len(check["progress"]["monotonic_cars"]),
            "backwards_ticks": check["progress"]["backwards_ticks"],
            "dropped_steps": check["progress"]["dropped_steps_count"],
            "round_trip_max_m": {"on": check["round_trip_m"]["on_track"].get("p100"),
                                 "off": check["round_trip_m"]["off_track"].get("p100")},
            "not_bracketed": check["round_trip_m"]["not_bracketed"],
            "pairwise_swaps": check["overtakes"]["pairwise_swaps"],
            "swaps_lap1": check["overtakes"]["swaps_lap1"],
            "net_overtakes": check["overtakes"]["net_swaps_excluding_2s_flickers"],
            "swaps_involving_off_track": check["overtakes"]["swaps_involving_off_track"],
            "sign_corr": check["sign_check"]["corr_d_m_vs_d_engine_on_track"],
            "heading_minus_tangent_on_track_p99_deg":
                check["heading_minus_tangent_deg"]["on_track"].get("p99"),
            "heading_minus_tangent_max_deg": max(
                check["heading_minus_tangent_deg"]["on_track"].get("p100", 0),
                check["heading_minus_tangent_deg"]["off_track"].get("p100", 0) or 0),
        }
    else:
        out["check"] = None
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("recordings", type=Path, nargs="+")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()
    rows = [one(p) for p in args.recordings]
    print(json.dumps(rows, indent=1))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
