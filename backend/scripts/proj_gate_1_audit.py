#!/usr/bin/env python3
"""PROJ-GATE-1 audit; --selftest is fully synthetic and reads no run files."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
CSV_REQUIRED = (
    "tick", "t_s", "drv", "speed", "s", "lat", "offtrack", "authority",
    "cum_dist", "contacts", "car_car", "body_x", "body_y", "ns_raw",
)
EVENTS_REQUIRED = ("sub", "drv_a", "drv_b", "j_n", "dv_a", "dv_b")
SUMMARY_HESITATION = re.compile(r"HESITAÇÕES[^\n]*?:\s*(\d+)")


def _global_projection(x: float, y: float, waypoints: np.ndarray):
    """Return nearest global segment, projected s, and centerline point."""
    a = waypoints
    b = np.roll(a, -1, axis=0)
    ab = b - a
    seg_len = np.hypot(ab[:, 0], ab[:, 1])
    seg_cum = np.concatenate(([0.0], np.cumsum(seg_len)))[:-1]
    best_d2 = float("inf")
    best_idx = 0
    best_t = 0.0
    best_xy = (float(a[0, 0]), float(a[0, 1]))
    for i in range(len(a)):
        length2 = float(ab[i, 0] * ab[i, 0] + ab[i, 1] * ab[i, 1])
        if length2 < 1e-9:
            continue
        t = max(0.0, min(1.0,
                         ((x - a[i, 0]) * ab[i, 0] + (y - a[i, 1]) * ab[i, 1])
                         / length2))
        px = float(a[i, 0] + t * ab[i, 0])
        py = float(a[i, 1] + t * ab[i, 1])
        dx, dy = x - px, y - py
        d2 = dx * dx + dy * dy
        if d2 < best_d2:
            best_d2, best_idx, best_t, best_xy = d2, i, t, (px, py)
    s = float(seg_cum[best_idx] + best_t * seg_len[best_idx])
    return best_idx, s, best_xy, float(seg_len.sum())


def _wrapped_delta(delta: float, track_len: float) -> float:
    return (delta + track_len / 2.0) % track_len - track_len / 2.0


def _projection_proxy_counts(df: pd.DataFrame, track_len: float):
    counts = {10: 0, 20: 0, 30: 0}
    offtrack_pairs = 0
    for _, group in df.groupby("drv", sort=True):
        group = group.sort_values("tick").reset_index(drop=True)
        for i in range(1, len(group)):
            prev, cur = group.iloc[i - 1], group.iloc[i]
            # The v3.4 writer samples every two logical ticks. "Consecutive"
            # means adjacent emitted rows for this car, not tick+1.
            if int(cur.offtrack) != 1:
                continue
            offtrack_pairs += 1
            delta_s = _wrapped_delta(float(cur.s) - float(prev.s), track_len)
            delta_dist = float(cur.cum_dist) - float(prev.cum_dist)
            error = abs(delta_s - delta_dist)
            for threshold in counts:
                if error >= threshold:
                    counts[threshold] += 1
    return {"offtrack_pairs": offtrack_pairs,
            "ge10_m": counts[10], "ge20_m": counts[20], "ge30_m": counts[30]}


def _reacquisition_audit(df: pd.DataFrame, waypoints: np.ndarray):
    total = matches = 0
    mismatches = []
    for drv, group in df.groupby("drv", sort=True):
        group = group.sort_values("tick").reset_index(drop=True)
        for i in range(1, len(group)):
            prev, cur = group.iloc[i - 1], group.iloc[i]
            if int(prev.offtrack) != 1 or int(cur.offtrack) != 0:
                continue
            total += 1
            expected_ns, expected_s, _, track_len = _global_projection(
                float(cur.body_x), float(cur.body_y), waypoints)
            observed_ns = float(cur.ns_raw)
            s_error = abs(_wrapped_delta(float(cur.s) - expected_s, track_len))
            passed = (math.isfinite(observed_ns)
                      and observed_ns == int(observed_ns) == expected_ns
                      and s_error <= 1e-6)
            if passed:
                matches += 1
            else:
                mismatches.append({
                    "drv": str(drv), "tick": int(cur.tick),
                    "ns_raw": observed_ns, "nearest_global_ns": expected_ns,
                    "s_arc_error_m": s_error,
                })
    return {"reentries": total, "nearest_global_matches": matches,
            "non_nearest": len(mismatches), "mismatches": mismatches[:20]}


def _offtrack_episodes(df: pd.DataFrame) -> int:
    episodes = 0
    for _, group in df.groupby("drv", sort=True):
        off = group.sort_values("tick").offtrack.to_numpy(dtype=int)
        if len(off):
            episodes += int(np.sum((off == 1) & np.r_[True, off[:-1] == 0]))
    return episodes


def _stuck_windows(df: pd.DataFrame) -> int:
    windows = 0
    t_end = float(df.t_s.max())
    for _, group in df.groupby("drv", sort=True):
        group = group.sort_values("t_s")
        t = group.t_s.to_numpy(dtype=float)
        lat = np.abs(group.lat.to_numpy(dtype=float))
        cum = group.cum_dist.to_numpy(dtype=float)
        off = group.offtrack.to_numpy(dtype=int)
        for start in np.arange(0.0, t_end, 30.0):
            mask = (t >= start) & (t < start + 30.0)
            if not mask.any() or not off[mask].any():
                continue
            progress = float(cum[mask].max() - cum[mask].min())
            if lat[mask].max() > 20.0 or progress < 5.0:
                windows += 1
    return windows


def _summary_hesitations(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = SUMMARY_HESITATION.findall(text)
    if not matches:
        raise ValueError(f"resumo sem linha HESITAÇÕES: {path}")
    return int(matches[-1])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _audit(csv_path: Path, events_path: Path, track_path: Path,
           summary_path: Path) -> dict:
    print("AUDIT_SCHEMA_CSV_REQUIRED=" + ",".join(CSV_REQUIRED))
    print("AUDIT_SCHEMA_EVENTS_REQUIRED=" + ",".join(EVENTS_REQUIRED))
    print("AUDIT_SCHEMA_TRACK_REQUIRED=waypoints[x,y]")
    print("AUDIT_SCHEMA_SUMMARY_REQUIRED=HESITAÇÕES:<integer>")

    df = pd.read_csv(csv_path, comment="#")
    missing_csv = sorted(set(CSV_REQUIRED) - set(df.columns))
    if missing_csv:
        raise ValueError(f"CSV v3.4 {csv_path}: colunas ausentes {missing_csv}")
    if len(df) == 0:
        raise ValueError(f"CSV v3.4 vazio: {csv_path}")
    if df.duplicated(["drv", "tick"]).any():
        raise ValueError("CSV v3.4 tem chave (drv,tick) duplicada")

    events = pd.read_csv(events_path, comment="#")
    missing_events = sorted(set(EVENTS_REQUIRED) - set(events.columns))
    if missing_events:
        raise ValueError(f"events CSV {events_path}: colunas ausentes {missing_events}")
    # O pino do dono define contatos por linhas menos um cabeçalho. Também
    # publicamos registros CSV reais, que excluem comentário e nomes de coluna.
    event_lines = sum(1 for _ in events_path.open("rb"))
    contacts_line_metric = event_lines - 1

    track_data = json.loads(track_path.read_text(encoding="utf-8"))
    if "waypoints" not in track_data:
        raise ValueError(f"pista frozen sem waypoints: {track_path}")
    waypoints = np.asarray(track_data["waypoints"], dtype=np.float64)
    if waypoints.ndim != 2 or waypoints.shape[1] != 2 or len(waypoints) < 3:
        raise ValueError(f"geometria frozen inválida: {track_path}")
    seg_len = np.hypot(*(np.roll(waypoints, -1, axis=0) - waypoints).T)
    track_len = float(seg_len.sum())
    if not math.isfinite(track_len) or track_len <= 0:
        raise ValueError("comprimento da pista inválido")

    numeric = ["tick", "t_s", "speed", "s", "lat", "offtrack", "cum_dist",
               "body_x", "body_y", "ns_raw"]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="raise")
    if not np.isfinite(df[numeric].to_numpy(dtype=float)).all():
        raise ValueError("CSV v3.4 contém valor não finito em coluna obrigatória")
    df["offtrack"] = df.offtrack.astype(int)
    if not df.offtrack.isin([0, 1]).all():
        raise ValueError("offtrack contém valor fora de {0,1}")

    proxy = _projection_proxy_counts(df, track_len)
    reentry = _reacquisition_audit(df, waypoints)
    outside_pct = 100.0 * float(df.offtrack.mean())
    episodes = _offtrack_episodes(df)
    stuck_windows = _stuck_windows(df)
    hesitations = _summary_hesitations(summary_path)
    n_rows = int(len(df))
    n_ticks = int(df.tick.nunique())
    n_cars = int(df.drv.nunique())
    expected_sample_ticks = np.arange(0, 6000, 2)
    complete_by_car = all(
        len(g) == len(expected_sample_ticks) and np.array_equal(
            np.sort(g.tick.to_numpy(dtype=int)), expected_sample_ticks)
        for _, g in df.groupby("drv", sort=True))
    complete = (n_rows >= 30000 and n_ticks == len(expected_sample_ticks) and n_cars == 10
                and complete_by_car)

    gates = {
        "g2_proxy": proxy["ge10_m"] <= 2 and proxy["ge30_m"] == 0,
        "g3_reacquisition": (reentry["reentries"] > 0
                             and reentry["non_nearest"] == 0),
        "g4_nonworsening": (
            outside_pct <= 43.15 + 1e-12
            and episodes <= 346
            and stuck_windows <= 120
            and hesitations <= 12
            and contacts_line_metric <= 110795
            and complete
        ),
    }
    return {
        "audit_version": "1.0",
        "inputs": {
            "csv": str(csv_path), "csv_sha256": _sha256(csv_path),
            "events_csv": str(events_path), "events_sha256": _sha256(events_path),
            "track_json": str(track_path), "track_sha256": _sha256(track_path),
            "summary_log": str(summary_path), "summary_sha256": _sha256(summary_path),
        },
        "schema": {"csv_columns": len(df.columns), "events_columns": len(events.columns),
                   "required_csv_present": True, "required_events_present": True},
        "proxy": proxy,
        "reacquisition": reentry,
        "nonworsening": {
            "outside_pct": outside_pct, "offtrack_episodes": episodes,
            "stuck_windows_30s": stuck_windows, "hesitations_summary": hesitations,
            "events_file_lines": event_lines,
            "contacts_lines_minus_one_header": contacts_line_metric,
            "events_csv_data_rows": int(len(events)),
            "rows": n_rows, "ticks": n_ticks, "cars": n_cars,
            "complete_by_car": complete_by_car,
        },
        "gates": gates,
        "overall": "PASS" if all(gates.values()) else "PARE",
    }


def _selftest() -> int:
    # Synthetic rectangle only: no CSV, JSON track, or simulation file is read.
    waypoints = np.asarray([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float)
    on_ns, on_s, _, track_len = _global_projection(5.0, 0.0, waypoints)
    assert (on_ns, on_s, track_len) == (0, 5.0, 40.0)
    frame = pd.DataFrame([
        dict(tick=0, t_s=0.0, drv="A", offtrack=1, s=35.0, cum_dist=0.0,
             body_x=0.0, body_y=5.0, ns_raw=3),
        dict(tick=2, t_s=0.2, drv="A", offtrack=0, s=5.0, cum_dist=1.0,
             body_x=5.0, body_y=0.0, ns_raw=0),
        dict(tick=4, t_s=0.4, drv="A", offtrack=1, s=35.0, cum_dist=2.0,
             body_x=0.0, body_y=5.0, ns_raw=3),
    ])
    proxy = _projection_proxy_counts(frame, track_len)
    assert proxy == {"offtrack_pairs": 1, "ge10_m": 1, "ge20_m": 0, "ge30_m": 0}
    reentry = _reacquisition_audit(frame, waypoints)
    assert reentry["reentries"] == reentry["nearest_global_matches"] == 1
    assert reentry["non_nearest"] == 0
    print("PROJ_GATE_1_AUDIT_SELFTEST=PASS files_read=0 simulations_read=0")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true",
                        help="selftest sintético; não lê CSVs nem JSONs")
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--track-json", type=Path)
    parser.add_argument("--summary-log", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    if args.selftest:
        if any((args.csv, args.events, args.track_json, args.summary_log, args.json_out)):
            parser.error("--selftest não aceita arquivos de entrada/saída")
        return _selftest()
    required = (args.csv, args.events, args.track_json, args.summary_log)
    if any(value is None for value in required):
        parser.error("informe --csv, --events, --track-json e --summary-log")
    try:
        result = _audit(args.csv, args.events, args.track_json, args.summary_log)
    except Exception as exc:
        print(f"AUDIT=ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(serialized)
    if args.json_out:
        args.json_out.write_text(serialized + "\n", encoding="utf-8")
    return 0 if result["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
