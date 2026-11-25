"""Check an engine recording before anything renders it.

Phase 3, step 3. Reads only the JSONL (`record_race.py`'s output, or the
trimmed fixture): the track block carries its own waypoints, so nothing here
needs the backend.

    python scripts/check_recording.py .cache/recordings/interlagos_seed42_3laps.jsonl
    python scripts/check_recording.py public/recordings/engine-interlagos-seed42.jsonl --json out.json

Reported, all as distributions rather than pass/fail where there is no sourced
threshold:

1. **Header**: the waypoints hash back to `geometry_sha256` (the engine's
   `track_identity` recipe), and our frame measures `length_m`.
2. **Progress**: per car, every tick where `progress_m` goes backwards, and
   every tick where it stalls while the car really moved (the engine's
   `_update_race_progress` drops a step larger than `max(30, 3 v dt + 10)`) -
   each tagged with the car's `|d_m|` so off-track recoveries are named.
3. **Round trip**: `position_xy` against `to_world(s_m, d_m)`, our Python port
   of the viewer's `toWorld`, on-track and off-track counted separately. Plus
   whether the refined projector actually bracketed each sample: interlagos_v2
   is not monotone everywhere (phase 0 report section 5).
4. **Overtakes**: every change in the running order between consecutive
   ticks, as pairwise swaps, split into the opening lap and the rest.
5. **|d_m|**: percentiles, and how much of the race is beyond the half width.

Also: the sign of `d_m` against the engine's own +left segment-normal lateral
(expect `d_m ~ -d_engine`), how far `progress_m` sits from our unwrapped `s`
(that gap is what the viewer's camera, which follows `progress_m`, is off the
car by), heading against the track tangent, and the chord sag of linear `xy`
interpolation at the recording's tick rate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from centreline import brackets, frame_from_three, segment_index, to_world, wrap_s  # noqa: E402


def pct(a, qs=(0, 50, 90, 99, 99.9, 100)):
    a = np.asarray(a, dtype=float)
    if a.size == 0:
        return {}
    return {f"p{q:g}": round(float(np.percentile(a, q)), 4) for q in qs}


def load(path: Path):
    with path.open(encoding="utf-8") as fh:
        header = json.loads(fh.readline())
        ticks = [json.loads(line) for line in fh if line.strip()]
    return header, ticks


def build_frame(track: dict):
    wps = np.asarray(track["waypoints"], dtype=np.float64)
    sf = int(track["start_finish_waypoint"])
    rolled = np.roll(wps, -sf, axis=0)
    xyz = np.column_stack([rolled[:, 0], np.zeros(len(rolled)), -rolled[:, 1]])
    return wps, frame_from_three(xyz, width_m=float(track["width_m"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("recording", type=Path)
    ap.add_argument("--json", type=Path, default=None, help="also write the report here")
    args = ap.parse_args()

    header, ticks = load(args.recording)
    track = header["track"]
    wps, frame = build_frame(track)
    half_w = frame.width_m / 2.0
    L = frame.length_m
    report: dict = {"file": str(args.recording), "ticks": len(ticks),
                    "sim_s": [ticks[0]["sim_ts"], ticks[-1]["sim_ts"]]}

    # 1. header ------------------------------------------------------------
    sha = hashlib.sha256(wps.tobytes()).hexdigest()[:16]
    report["header"] = {
        "geometry_sha256": track["geometry_sha256"], "recomputed": sha,
        "sha_ok": sha == track["geometry_sha256"],
        "length_m": track["length_m"], "frame_length_m": frame.length_m,
        "length_ok": abs(frame.length_m - track["length_m"]) < 1e-6,
        "n_wp": len(wps), "sf_idx": track["start_finish_waypoint"],
    }

    ids = [d["driver_id"] for d in header["drivers"]]
    n = len(ticks)
    t = np.array([tk["sim_ts"] for tk in ticks])
    dt = float(np.median(np.diff(t))) if n > 1 else 0.1
    ch = {k: np.zeros((n, len(ids))) for k in
          ("x", "y", "hdg", "v", "prog", "s", "d", "pos")}
    for i, tk in enumerate(ticks):
        if len(tk["positions"]) != len(ids):
            raise SystemExit(f"tick {i}: {len(tk['positions'])} cars, header has {len(ids)}")
        for p in tk["positions"]:
            j = ids.index(p["driver_id"])
            ch["x"][i, j], ch["y"][i, j] = p["position_xy"]
            ch["hdg"][i, j] = p["heading_deg"]
            ch["v"][i, j] = p["velocity_mps"]
            ch["prog"][i, j] = p["progress_m"]
            ch["s"][i, j] = p["s_m"]
            ch["d"][i, j] = p["d_m"]
            ch["pos"][i, j] = p["position"]
        order = [p["position"] for p in tk["positions"]]
        if order != list(range(1, len(ids) + 1)):
            raise SystemExit(f"tick {i}: positions not in race order: {order}")
        progs = [p["progress_m"] for p in tk["positions"]]
        if any(a < b for a, b in zip(progs, progs[1:])):
            raise SystemExit(f"tick {i}: race order disagrees with progress_m")
    off = np.abs(ch["d"]) > half_w

    # our s, unwrapped per car (the per-tick advance is far below L / 2)
    s_un = np.zeros_like(ch["s"])
    s_un[0] = ch["s"][0]
    for i in range(1, n):
        step = (ch["s"][i] - ch["s"][i - 1] + L / 2) % L - L / 2
        s_un[i] = s_un[i - 1] + step
    # anchor each car's unwrapped s on its progress at tick 0
    s_un += np.round((ch["prog"][0] - s_un[0]) / L) * L

    # 2. progress ----------------------------------------------------------
    dprog = np.diff(ch["prog"], axis=0)
    ds = np.diff(s_un, axis=0)
    backwards, stalls = [], []
    for j, did in enumerate(ids):
        for i in np.nonzero(dprog[:, j] < -1e-6)[0]:
            backwards.append({"driver": did, "t": float(t[i + 1]), "dprog_m": round(float(dprog[i, j]), 3),
                              "ds_m": round(float(ds[i, j]), 3), "abs_d_m": round(abs(float(ch["d"][i + 1, j])), 2),
                              "off_track": bool(off[i + 1, j] or off[i, j])})
        # a dropped step: our s advanced, progress did not follow
        for i in np.nonzero(np.abs(ds[:, j] - dprog[:, j]) > 5.0)[0]:
            stalls.append({"driver": did, "t": float(t[i + 1]), "dprog_m": round(float(dprog[i, j]), 3),
                           "ds_m": round(float(ds[i, j]), 3), "abs_d_m": round(abs(float(ch["d"][i + 1, j])), 2)})
    gap = s_un - ch["prog"]
    report["progress"] = {
        "monotonic_cars": [did for j, did in enumerate(ids) if not np.any(dprog[:, j] < -1e-6)],
        "backwards_ticks": len(backwards),
        "backwards_off_track": sum(b["off_track"] for b in backwards),
        "backwards_by_car": {did: sum(b["driver"] == did for b in backwards) for did in ids},
        "backwards_worst": sorted(backwards, key=lambda b: b["dprog_m"])[:10],
        "dropped_steps": stalls[:20],
        "dropped_steps_count": len(stalls),
        "s_minus_progress_m": {"on_track": pct(gap[~off]), "off_track": pct(gap[off]),
                               "final_by_car": {did: round(float(gap[-1, j]), 3) for j, did in enumerate(ids)}},
    }

    # 3. round trip --------------------------------------------------------
    err = np.zeros_like(ch["s"])
    bracketed = np.zeros(ch["s"].shape, dtype=bool)
    for i in range(n):
        for j in range(len(ids)):
            p = np.array([ch["x"][i, j], -ch["y"][i, j]])
            w = to_world(frame, ch["s"][i, j], ch["d"][i, j])
            err[i, j] = float(np.hypot(*(w - p)))
            k = int(segment_index(frame, float(wrap_s(frame, ch["s"][i, j]))))
            bracketed[i, j] = any(brackets(frame, kk % len(frame.points), p) for kk in (k - 1, k, k + 1))
    report["round_trip_m"] = {
        "on_track": {"n": int((~off).sum()), **pct(err[~off])},
        "off_track": {"n": int(off.sum()), **pct(err[off])},
        "over_1cm": int((err > 0.01).sum()),
        "not_bracketed": {"on_track": int((~bracketed & ~off).sum()),
                          "off_track": int((~bracketed & off).sum())},
    }

    # 4. overtakes ---------------------------------------------------------
    first_lap_end = None
    for i, tk in enumerate(ticks):
        if tk["leader_lap"] >= 1:
            first_lap_end = float(t[i])
            break
    swaps = []
    for i in range(1, n):
        a, b = ch["pos"][i - 1], ch["pos"][i]
        for j in range(len(ids)):
            for k in range(j + 1, len(ids)):
                if (a[j] - a[k]) * (b[j] - b[k]) < 0:
                    winner, loser = (j, k) if b[j] < b[k] else (k, j)
                    swaps.append({"t": float(t[i]), "gained": ids[winner], "lost": ids[loser],
                                  "off_track": bool(off[i, j] or off[i, k] or off[i - 1, j] or off[i - 1, k])})
    # a swap undone within 2 s is a flicker, not an overtake
    net = []
    for sw in swaps:
        undone = any(o["t"] > sw["t"] and o["t"] - sw["t"] <= 2.0 and o["gained"] == sw["lost"]
                     and o["lost"] == sw["gained"] for o in swaps)
        redo = any(o["t"] < sw["t"] and sw["t"] - o["t"] <= 2.0 and o["gained"] == sw["lost"]
                   and o["lost"] == sw["gained"] for o in swaps)
        if not undone and not redo:
            net.append(sw)
    report["overtakes"] = {
        "position_changes": int(sum(np.any(ch["pos"][i] != ch["pos"][i - 1]) for i in range(1, n))),
        "pairwise_swaps": len(swaps),
        "swaps_lap1": sum(s["t"] <= (first_lap_end or math.inf) for s in swaps),
        "swaps_after_lap1": sum(s["t"] > (first_lap_end or math.inf) for s in swaps),
        "swaps_involving_off_track": sum(s["off_track"] for s in swaps),
        "net_swaps_excluding_2s_flickers": len(net),
        "net_list": net[:40],
        "leader_first_lap_end_s": first_lap_end,
        "grid_order": [d["driver_id"] for d in header["drivers"]],
        "final_order": [p["driver_id"] for p in ticks[-1]["positions"]],
    }

    # 5. |d| -----------------------------------------------------------------
    absd = np.abs(ch["d"])
    report["abs_d_m"] = {**pct(absd), "half_width_m": half_w,
                         "off_track_fraction": round(float(off.mean()), 5),
                         "off_track_samples": int(off.sum()),
                         "off_track_by_car": {did: int(off[:, j].sum()) for j, did in enumerate(ids)}}

    # extras -----------------------------------------------------------------
    # engine lateral: +left, measured against the segment normal of the
    # nearest segment (place_grid's (nx, ny) = (-dy, dx) / len)
    AB = np.roll(wps, -1, axis=0) - wps
    seg = np.hypot(AB[:, 0], AB[:, 1])
    d_eng = np.zeros_like(ch["d"])
    for i in range(n):
        for j in range(len(ids)):
            px, py = ch["x"][i, j], ch["y"][i, j]
            rel = np.column_stack([px - wps[:, 0], py - wps[:, 1]])
            tt = np.clip((rel * AB).sum(1) / seg**2, 0, 1)
            foot = wps + AB * tt[:, None]
            k = int(np.argmin(np.hypot(*(foot - [px, py]).T)))
            d_eng[i, j] = ((px - wps[k, 0]) * -AB[k, 1] + (py - wps[k, 1]) * AB[k, 0]) / seg[k]
    on = ~off
    report["sign_check"] = {
        "corr_d_m_vs_d_engine_on_track": round(float(np.corrcoef(ch["d"][on], d_eng[on])[0, 1]), 5),
        "d_m_plus_d_engine_on_track": pct(np.abs(ch["d"][on] + d_eng[on])),
    }

    # heading vs tangent at s_m (engine heading: radians CCW from +x, in degrees)
    hdiff = np.zeros_like(ch["s"])
    for i in range(n):
        for j in range(len(ids)):
            sw = float(wrap_s(frame, ch["s"][i, j]))
            k = int(segment_index(frame, sw))
            kk = (k + 1) % len(frame.points)
            segl = (frame.s[kk] - frame.s[k]) % L or 1.0
            f = (sw - frame.s[k]) / segl
            tan = frame.tangent[k] * (1 - f) + frame.tangent[kk] * f       # three plan (x, z)
            track_hdg = math.degrees(math.atan2(-tan[1], tan[0]))          # back to engine (x, y)
            hdiff[i, j] = (ch["hdg"][i, j] - track_hdg + 180) % 360 - 180
    report["heading_minus_tangent_deg"] = {"on_track": pct(np.abs(hdiff[on])),
                                           "off_track": pct(np.abs(hdiff[off]))}

    # chord sag: distance from the chord midpoint of (i, i+1) to the circle
    # through (i-1, i, i+1): what linear xy interpolation cuts off a corner
    sag = []
    for j in range(len(ids)):
        P = np.column_stack([ch["x"][:, j], ch["y"][:, j]])
        for i in range(1, n - 1):
            a, b, c = P[i - 1], P[i], P[i + 1]
            ab, bc, ca = np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)
            area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
            if area2 < 1e-9 or bc < 1e-6:
                sag.append(0.0)
                continue
            R = ab * bc * ca / (2 * area2)
            sag.append(R - math.sqrt(max(R * R - (bc / 2) ** 2, 0.0)))
    report["lerp_chord_sag_m"] = {"dt_s": dt, **pct(sag)}

    report["speed_mps"] = pct(ch["v"])
    report["recording_meta"] = header.get("recording", {})
    print(json.dumps(report, indent=1, default=str))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    ok = report["header"]["sha_ok"] and report["header"]["length_ok"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
