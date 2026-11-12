#!/usr/bin/env python3
"""Veredito offline da bateria FAIL-FORENSICS-1b.

Consome CSVs race_diag_v3_3_res16d e contatos solver-side. Não chama o
simulador, não altera o ambiente e não filtra observações da medição.
Definições congeladas em experiments/fail-forensics-2/PREREG_FAIL_FORENSICS_1B.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))
import saidas_verdict as saidas  # noqa: E402 — classificador geométrico canônico

JUMP_THRESHOLDS_M = (10.0, 20.0, 30.0)
PRIMARY_JUMP_M = 30.0
CONTACT_LOOKBACK_TICKS = 10       # 1,0 s no relógio lógico de 10 Hz
RECOVERY_LOOKBACK_S = 10.0        # ecos de rejoin conforme PROF-MONACO-1
PROJECTION_LOOKBACK_S = 2.0
CONTACT_EPISODE_GAP_TICKS = 10    # mesmo par; no máximo 1 s entre ticks solver
RECOVERY_AUTHORITIES = {"rejoin", "recovery", "recovery_rejoin"}


def _arm_for(run: str) -> str:
    if run.startswith("composite"):
        return "composite"
    if run.startswith(("professor", "prof_")):
        return "professor"
    if run.startswith(("aluno", "blind")):
        return "aluno" if run.startswith("aluno") else "blind"
    return run.split("_", 1)[0]


def _number(v, default=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _segment_index(s_value: float, seg_cum: np.ndarray, total_len: float) -> int:
    s_mod = float(s_value) % total_len
    return int(np.clip(np.searchsorted(seg_cum, s_mod, side="right") - 1,
                       0, len(seg_cum) - 1))


def _projection_jumps(df: pd.DataFrame, geom: tuple, run: str, track: str):
    seg_cum, total_len = geom[3], float(geom[4])
    rows = []
    for drv, g in df.groupby("drv", sort=True):
        g = g.sort_values("tick").reset_index(drop=True)
        for i in range(1, len(g)):
            prev, cur = g.iloc[i - 1], g.iloc[i]
            dt = _number(cur.t_s) - _number(prev.t_s)
            if dt <= 0:
                continue
            raw = _number(cur.s) - _number(prev.s)
            ds = (raw + total_len / 2.0) % total_len - total_len / 2.0
            dodo = _number(cur.cum_dist) - _number(prev.cum_dist)
            err = abs(ds - dodo)
            s0, s1 = _number(prev.s), _number(cur.s)
            seg0 = _segment_index(s0, seg_cum, total_len)
            seg1 = _segment_index(s1, seg_cum, total_len)
            seg_hops = abs(seg1 - seg0)
            seg_hops = min(seg_hops, len(seg_cum) - seg_hops)
            if err >= min(JUMP_THRESHOLDS_M):
                rows.append({
                    "run": run, "track": track, "drv": drv,
                    "tick_prev": int(prev.tick), "tick": int(cur.tick),
                    "t_s": _number(cur.t_s), "s_prev": s0, "s": s1,
                    "delta_s_wrapped_m": ds, "delta_cum_dist_m": dodo,
                    "abs_projection_error_m": err,
                    "segment_prev_derived": seg0, "segment_derived": seg1,
                    "segment_hops_cyclic": seg_hops,
                    "lat_prev": _number(prev.lat), "lat": _number(cur.lat),
                    "speed_mps": _number(cur.speed), "th": _number(cur.th),
                    "brk": _number(cur.brk), "steer_rad": _number(cur.steer_rad),
                    "authority": str(cur.authority),
                    "recovery_authority": int(str(cur.authority) in RECOVERY_AUTHORITIES),
                    "offtrack": int(_number(cur.offtrack)),
                })
    return rows


def _load_contacts(path: str, run: str):
    if not path or path == "-" or not Path(path).exists():
        return [], 0
    raw = pd.read_csv(path, comment="#")
    required = {"sub", "drv_a", "drv_b", "j_n", "dv_a", "dv_b"}
    if not required.issubset(raw.columns):
        raise ValueError(f"{path}: colunas de contato ausentes: {sorted(required - set(raw.columns))}")
    raw["tick"] = (pd.to_numeric(raw["sub"], errors="coerce").fillna(0).astype(int) // 24)
    raw["j_n"] = pd.to_numeric(raw["j_n"], errors="coerce").fillna(0.0)
    raw["dv_a"] = pd.to_numeric(raw["dv_a"], errors="coerce").fillna(0.0)
    raw["dv_b"] = pd.to_numeric(raw["dv_b"], errors="coerce").fillna(0.0)
    per_tick = []
    for (tick, a, b), g in raw.groupby(["tick", "drv_a", "drv_b"], dropna=False, sort=True):
        aa, bb = str(a), str(b)
        per_tick.append({
            "tick": int(tick), "drv_a": aa, "drv_b": bb,
            "pair": "|".join(sorted((aa, bb))),
            "solver_points": int(len(g)), "impulse_ns": float(g.j_n.sum()),
            "dv_a_max": float(g.dv_a.abs().max()),
            "dv_b_max": float(g.dv_b.abs().max()),
            "cx": float(pd.to_numeric(g.get("cx"), errors="coerce").mean()) if "cx" in g else None,
            "cy": float(pd.to_numeric(g.get("cy"), errors="coerce").mean()) if "cy" in g else None,
        })
    # Várias subetapas/pontos de contato do mesmo par são uma ocorrência; ticks
    # do mesmo par até 1 s apart são um episódio solver-side.
    per_tick.sort(key=lambda r: (r["pair"], r["tick"]))
    episodes = []
    current = None
    for r in per_tick:
        if current is None or r["pair"] != current["pair"] or \
                r["tick"] - current["tick_end"] > CONTACT_EPISODE_GAP_TICKS:
            if current is not None:
                episodes.append(current)
            current = {
                "run": run, "event_type": "CONTATO", "cause": "COLISÃO",
                "pair": r["pair"], "drv_a": r["drv_a"], "drv_b": r["drv_b"], "drivers": r["pair"],
                "tick": r["tick"], "tick_start": r["tick"], "tick_end": r["tick"],
                "solver_points": r["solver_points"], "impulse_ns": r["impulse_ns"],
                "delta_v_mps": max(r["dv_a_max"], r["dv_b_max"]),
                "cx": r["cx"], "cy": r["cy"],
            }
        else:
            current["tick_end"] = r["tick"]
            current["solver_points"] += r["solver_points"]
            current["impulse_ns"] += r["impulse_ns"]
            current["delta_v_mps"] = max(current["delta_v_mps"], r["dv_a_max"], r["dv_b_max"])
    if current is not None:
        episodes.append(current)
    return episodes, len(raw)


def _nearest_row(g: pd.DataFrame, tick: int):
    idx = (pd.to_numeric(g["tick"], errors="coerce") - tick).abs().idxmin()
    return g.loc[idx]


def _mode_at(g: pd.DataFrame, idx: int, geom: tuple):
    g = g.sort_values("tick").reset_index(drop=True)
    wps, diff, seg, seg_cum, total_len, seg_head = geom
    # SAIDAS-1 D0 reconstrução cinemática preservada verbatim.
    slat = g["obs4"].to_numpy(dtype=float) * saidas.HW
    xs, ys, track_yaws = saidas.project_car_xy(
        g["s"].to_numpy(dtype=float), slat, wps, diff, seg, seg_cum, seg_head, total_len)
    herr = np.arctan2(g["obs5"].to_numpy(dtype=float), g["obs6"].to_numpy(dtype=float))
    chassis = (track_yaws + herr + np.pi) % (2 * np.pi) - np.pi
    return saidas.classify_excursion_mode(xs, ys, chassis,
                                           g["speed"].to_numpy(dtype=float), idx,
                                           dt=saidas.DT)


def _find_prior_contact(contacts, drv: str, tick: int):
    eligible = []
    for c in contacts:
        if drv not in {c["drv_a"], c["drv_b"]}:
            continue
        if tick - CONTACT_LOOKBACK_TICKS <= c["tick_end"] <= tick:
            eligible.append(c)
    return max(eligible, key=lambda c: c["tick_end"]) if eligible else None


def _find_prior_jump(jumps, drv: str, t_s: float):
    eligible = [j for j in jumps if j["drv"] == drv and
                0.0 <= t_s - j["t_s"] <= PROJECTION_LOOKBACK_S]
    return max(eligible, key=lambda j: j["t_s"]) if eligible else None


def _has_recovery(g: pd.DataFrame, t_s: float):
    w = g[(g.t_s <= t_s) & (g.t_s >= t_s - RECOVERY_LOOKBACK_S)]
    return bool(w.authority.astype(str).isin(RECOVERY_AUTHORITIES).any())


def _event_row(run, track, event_type, drv, tick, g, geom, corners,
               excursion=None, contact=None, jumps=(), drivers=None,
               tick_end=None, extra=None):
    g = g.sort_values("tick").reset_index(drop=True)
    row = _nearest_row(g, int(tick))
    t_s = _number(row.t_s)
    s = _number(row.s)
    corner_id, corner_name = saidas.match_corner(s, corners, float(geom[4]))
    ix = int((pd.to_numeric(g.tick, errors="coerce") - int(tick)).abs().idxmin())
    mode = (excursion.get("mode") if excursion else _mode_at(g, ix, geom))
    prior_contact = contact or _find_prior_contact(extra["contacts"] if extra else [], str(drv), int(tick))
    recovery = _has_recovery(g, t_s)
    jump = _find_prior_jump(jumps, str(drv), t_s)

    if event_type == "CONTATO":
        cause = "COLISÃO"
    elif prior_contact is not None:
        cause = "COLISÃO"
    elif recovery:
        cause = "RECUPERAÇÃO"
    elif mode in {"SLIDE", "SPIN"} or corner_id != "Reta":
        cause = "CURVA"
    else:
        cause = "TRAJETÓRIA"

    return {
        "run": run, "track": track, "arm": _arm_for(run),
        "event_type": event_type, "cause": cause,
        "drivers": drivers or str(drv), "drv": str(drv),
        "tick": int(tick), "tick_end": int(tick_end if tick_end is not None else tick),
        "t_s": t_s, "s": s, "lat": _number(row.lat), "speed_mps": _number(row.speed),
        "th": _number(row.th), "brk": _number(row.brk), "steer_rad": _number(row.steer_rad),
        "authority": str(row.authority), "corner_id": corner_id,
        "corner_name": corner_name, "mode": str(mode),
        "prior_contact_tick": prior_contact["tick_end"] if prior_contact else None,
        "prior_impulse_ns": prior_contact["impulse_ns"] if prior_contact else None,
        "prior_delta_v_mps": prior_contact["delta_v_mps"] if prior_contact else None,
        "recovery_seen_10s": int(recovery),
        "projection_jump_preceding_2s_m": jump["abs_projection_error_m"] if jump else None,
        "segment_derived": _segment_index(s, geom[3], float(geom[4])),
        **(extra or {}).get("event_fields", {}),
    }


def _offtrack_events(df, run, track, geom, corners, contacts, jumps):
    extracted, _ = saidas.extract_excursions(df, corners, geom)
    lookup = {(str(r.drv), int(r.tick)): r._asdict()
              for r in extracted.itertuples(index=False)}
    out = []
    for drv, g in df.groupby("drv", sort=True):
        g = g.sort_values("tick").reset_index(drop=True)
        flag = pd.to_numeric(g.offtrack, errors="coerce").fillna(0).astype(int).to_numpy()
        i = 0
        while i < len(g):
            if flag[i] != 1:
                i += 1
                continue
            j = i + 1
            while j < len(g) and flag[j] == 1:
                j += 1
            tick = int(g.iloc[i].tick)
            ex = lookup.get((str(drv), tick))
            record = _event_row(run, track, "OFF_TRACK", drv, tick, g, geom,
                                corners, excursion=ex, jumps=jumps,
                                extra={"contacts": contacts, "event_fields":
                                       {"duration_s": _number(g.iloc[j - 1].t_s) - _number(g.iloc[i].t_s) + saidas.DT,
                                        "lat_abs_max_m": float(g.iloc[i:j].lat.abs().max())}})
            out.append(record)
            i = j
    return out


def _stuck_events(df, run, track, geom, corners, contacts, jumps):
    out = []
    t_end = float(df.t_s.max())
    for drv, g in df.groupby("drv", sort=True):
        g = g.sort_values("t_s").reset_index(drop=True)
        t = g.t_s.to_numpy(dtype=float)
        lat = g.lat.abs().to_numpy(dtype=float)
        cum = g.cum_dist.to_numpy(dtype=float)
        off = g.offtrack.to_numpy(dtype=int)
        for w0 in np.arange(0.0, t_end, 30.0):
            mask = (t >= w0) & (t < w0 + 30.0)
            if not mask.any() or not off[mask].any():
                continue
            progress = float(cum[mask].max() - cum[mask].min())
            lat_max = float(lat[mask].max())
            if lat_max <= 20.0 and progress >= 5.0:
                continue
            ix = int(np.flatnonzero(mask & (off == 1))[0])
            tick = int(g.iloc[ix].tick)
            out.append(_event_row(
                run, track, "PRESO_R3_30S", drv, tick, g, geom, corners,
                jumps=jumps, extra={"contacts": contacts, "event_fields": {
                    "window_start_s": float(w0), "window_end_s": float(w0 + 30.0),
                    "offtrack_ticks_in_window": int(off[mask].sum()),
                    "lat_abs_max_m": lat_max, "cum_dist_range_m": progress,
                    "stuck_reason": "lat>20m" if lat_max > 20.0 else "progress<5m",
                }}))
    return out


def _hesitation_events(df, run, track, geom, corners, contacts, jumps):
    out = []
    for drv, g in df.groupby("drv", sort=True):
        g = g.sort_values("t_s").reset_index(drop=True)
        speed = g.speed.to_numpy(dtype=float)
        ts = g.t_s.to_numpy(dtype=float)
        valid = ts > 20.0
        idxs = np.flatnonzero(valid)
        i = 0
        while i < len(idxs):
            ix = idxs[i]
            if speed[ix] >= 0.5:
                i += 1
                continue
            j = i + 1
            while j < len(idxs) and idxs[j] == idxs[j - 1] + 1 and speed[idxs[j]] < 0.5:
                j += 1
            end_idx = idxs[min(j, len(idxs)) - 1]
            duration = float(ts[end_idx] - ts[ix] + saidas.DT)
            if 0.3 <= duration < 3.0:
                out.append(_event_row(
                    run, track, "HESITACAO", drv, int(g.iloc[ix].tick), g,
                    geom, corners, jumps=jumps,
                    tick_end=int(g.iloc[end_idx].tick),
                    extra={"contacts": contacts, "event_fields": {"duration_s": duration}}))
            i = j
    return out


def _contact_events(df, contacts, run, track, geom, corners):
    rows = []
    by_driver = {str(d): g.sort_values("tick").reset_index(drop=True)
                 for d, g in df.groupby("drv", sort=True)}
    for c in contacts:
        drv = c["drv_a"] if c["drv_a"] in by_driver else c["drv_b"]
        if drv not in by_driver:
            rows.append({
                "run": run, "track": track, "arm": _arm_for(run),
                "event_type": "CONTATO", "cause": "COLISÃO", "drivers": c["drivers"],
                "drv": drv, "tick": c["tick_start"], "tick_end": c["tick_end"],
                "impulse_ns": c["impulse_ns"], "delta_v_mps": c["delta_v_mps"],
                "solver_points": c["solver_points"], "cx": c["cx"], "cy": c["cy"],
            })
            continue
        ev = _event_row(run, track, "CONTATO", drv, c["tick_start"], by_driver[drv],
                        geom, corners, contact=c, drivers=c["drivers"], tick_end=c["tick_end"],
                        extra={"event_fields": {"impulse_ns": c["impulse_ns"],
                                                "delta_v_mps": c["delta_v_mps"],
                                                "solver_points": c["solver_points"],
                                                "cx": c["cx"], "cy": c["cy"]}})
        ev["cause"] = "COLISÃO"
        rows.append(ev)
    return rows


def _projection_events(jumps, run, track, contacts, df, geom, corners):
    out = []
    by_driver = {str(d): g.sort_values("tick").reset_index(drop=True)
                 for d, g in df.groupby("drv", sort=True)}
    for j in jumps:
        drv = j["drv"]
        if drv not in by_driver:
            continue
        ev = _event_row(run, track, "SALTO_PROJECAO", drv, j["tick"],
                        by_driver[drv], geom, corners, contact=None,
                        jumps=(), extra={"contacts": contacts, "event_fields": {
                            "projection_error_m": j["abs_projection_error_m"],
                            "delta_s_wrapped_m": j["delta_s_wrapped_m"],
                            "delta_cum_dist_m": j["delta_cum_dist_m"],
                            "segment_prev_derived": j["segment_prev_derived"],
                            "segment_derived": j["segment_derived"],
                        }})
        out.append(ev)
    return out


def _read_run(label, track, csv_path, events_path):
    if track not in saidas.TRACKS:
        raise ValueError(f"pista desconhecida {track!r}; use {sorted(saidas.TRACKS)}")
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, comment="#")
    required = {"tick", "t_s", "drv", "speed", "s", "lat", "th", "brk",
                "steer_rad", "offtrack", "authority", "w_trans", "cum_dist",
                "obs4", "obs5", "obs6"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path}: contrato CSV v3.3 incompleto: {sorted(missing)}")
    if label.startswith("composite"):
        residual = {f"res_{i}" for i in range(16)}
        if not residual.issubset(df.columns):
            raise ValueError(f"{path}: perfil composite sem res_0..res_15")
    cfg = saidas.TRACKS[track]
    geom = saidas.load_track_geometry(cfg["file"])
    corners = saidas.build_corner_definitions(geom[0], generic_names=cfg["generic_names"])
    contacts, solver_rows = _load_contacts(events_path, label)
    jumps = _projection_jumps(df, geom, label, track)
    events = []
    events.extend(_offtrack_events(df, label, track, geom, corners, contacts, jumps))
    events.extend(_contact_events(df, contacts, label, track, geom, corners))
    events.extend(_stuck_events(df, label, track, geom, corners, contacts, jumps))
    events.extend(_hesitation_events(df, label, track, geom, corners, contacts, jumps))
    events.extend(_projection_events(jumps, label, track, contacts, df, geom, corners))
    for i, ev in enumerate(events, 1):
        ev["event_id"] = f"{label}:{ev['event_type']}:{i:05d}"
    dry = not bool(pd.to_numeric(df.w_trans, errors="coerce").fillna(0).astype(int).any())
    metadata = {
        "track": track, "track_sha256": __import__("hashlib").sha256(cfg["file"].read_bytes()).hexdigest(),
        "track_short_sha256": cfg["sha256"], "sf_idx": json.loads(cfg["file"].read_text())["sf_idx"],
        "waypoints": len(geom[0]), "track_length_m": float(geom[4]),
    }
    errors = [j["abs_projection_error_m"] for j in jumps]
    metrics = {
        "run": label, "track": track, "arm": _arm_for(label),
        "n_cars": int(df.drv.nunique()), "n_rows": int(len(df)),
        "n_ticks": int(df.tick.nunique()), "weather_dry_no_transitions": int(dry),
        "weather_transition_count": int(pd.to_numeric(df.w_trans, errors="coerce").fillna(0).sum()),
        "offtrack_pct": 100.0 * float(pd.to_numeric(df.offtrack, errors="coerce").fillna(0).mean()),
        "offtrack_episodes": sum(e["event_type"] == "OFF_TRACK" for e in events),
        "solver_contact_points": solver_rows, "solver_contact_episodes": len(contacts),
        "stuck_r3_windows": sum(e["event_type"] == "PRESO_R3_30S" for e in events),
        "hesitations": sum(e["event_type"] == "HESITACAO" for e in events),
        "projection_error_ge_10m": sum(x >= 10 for x in errors),
        "projection_error_ge_20m": sum(x >= 20 for x in errors),
        "projection_error_ge_30m": sum(x >= PRIMARY_JUMP_M for x in errors),
        "projection_error_p50_m": float(np.percentile(errors, 50)) if errors else 0.0,
        "projection_error_p95_m": float(np.percentile(errors, 95)) if errors else 0.0,
        **metadata,
    }
    return metrics, events, jumps


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selftest() -> int:
    """Golden check for Monaco anchors, projection jumps, and Interlagos R1/R2."""
    exp = BACKEND / "experiments"
    expected_hashes = {
        "fail-forensics-1/1_blind_interlagos_s0.csv":
            "47df0ed834e8e8a6a5c2f114cee6ee745230ce0f37d7682890debe9d3f15c733",
        "fail-forensics-1/1_blind_interlagos_s0_events.csv":
            "11e8c657b6ffc6ab65d98fbeb7af56983d1658447f0b1093edc8a862444ca3b9",
        "fail-forensics-1/2_composite_interlagos_s0.csv":
            "512ba0d2553b1c3acacc69582a6877a883f570aee4cf72658a7925f164310155",
        "fail-forensics-1/2_composite_interlagos_s0_events.csv":
            "1f79529e40117dd5eb3e53dcfe18ad6598e95d6ce2f1ccc83d377b82ccce7b54",
        "prof-monaco-1/prof_s0.csv":
            "282a175c03f484ccc0e5872b20a4e5d9c98c0bdba7dafb7d825fe3708213dfc9",
        "prof-monaco-1/prof_s0_rep.csv":
            "282a175c03f484ccc0e5872b20a4e5d9c98c0bdba7dafb7d825fe3708213dfc9",
        "prof-monaco-1/aluno_s0.csv":
            "f43c760a1dca3d7ca5697ec15c2960fd8c6a66541f35cd565fe9a725cf0ffca0",
        "prof-monaco-1/aluno_s0_rep.csv":
            "f43c760a1dca3d7ca5697ec15c2960fd8c6a66541f35cd565fe9a725cf0ffca0",
    }
    for rel, expected in expected_hashes.items():
        actual = _file_sha256(exp / rel)
        assert actual == expected, f"SHA-256 divergente: {rel}: {actual} != {expected}"

    # Os headers registram o seed, mas as linhas de dados dos seeds 0–4 são
    # réplicas exatas por braço na bateria solo Monaco já arquivada.
    mono = exp / "prof-monaco-1"
    for arm, body_sha in (("prof", "7ca6422e1908ecbdd4b54e81b66517996e6aa1325fbb69dc902b4f6154606d0d"),
                          ("aluno", "cd4e26c6036ad07d6b93ee1f54da171a194f2693f37e8f774f47b5a74b461ba7")):
        bodies = [(mono / f"{arm}_s{i}.csv").read_bytes().split(b"\n", 1)[1]
                  for i in range(5)]
        assert all(body == bodies[0] for body in bodies[1:]), f"réplicas Monaco {arm} divergiram"
        assert hashlib.sha256(bodies[0]).hexdigest() == body_sha, f"golden Monaco {arm} divergente"

    # Fixture mecânico: avanço normal não salta; teleporte de s sem odômetro
    # gera um evento localizado com segmentos derivados e magnitude esperada.
    jump_df = pd.DataFrame({
        "tick": [0, 1, 2], "t_s": [0.0, 0.2, 0.4], "drv": ["TST"] * 3,
        "speed": [10.0] * 3, "s": [0.0, 2.0, 55.0], "cum_dist": [0.0, 2.0, 4.0],
        "lat": [0.0] * 3, "th": [0.5] * 3, "brk": [0.0] * 3,
        "steer_rad": [0.0] * 3, "authority": ["policy"] * 3,
        "offtrack": [0] * 3,
    })
    jump_geom = (None, None, None, np.arange(0.0, 100.0, 10.0), 100.0, None)
    gotos = _projection_jumps(jump_df, jump_geom, "synthetic_goto", "monaco")
    assert len(gotos) == 1 and gotos[0]["tick"] == 2
    assert gotos[0]["abs_projection_error_m"] == 49.0
    assert gotos[0]["segment_hops_cyclic"] == 5

    professor, _, _ = _read_run(
        "professor_monaco_s0", "monaco",
        str(mono / "prof_s0.csv"), "-")
    aluno, _, _ = _read_run(
        "aluno_monaco_s0", "monaco",
        str(mono / "aluno_s0.csv"), "-")
    assert (professor["n_cars"], professor["n_rows"], round(professor["offtrack_pct"], 1)) == (1, 3000, 56.9)
    assert (aluno["n_cars"], aluno["n_rows"], round(aluno["offtrack_pct"], 1)) == (1, 3000, 45.0)
    assert professor["track_sha256"] == aluno["track_sha256"]

    blind, _, _ = _read_run(
        "blind_interlagos", "interlagos",
        str(exp / "fail-forensics-1/1_blind_interlagos_s0.csv"),
        str(exp / "fail-forensics-1/1_blind_interlagos_s0_events.csv"))
    composite, _, _ = _read_run(
        "composite_interlagos", "interlagos",
        str(exp / "fail-forensics-1/2_composite_interlagos_s0.csv"),
        str(exp / "fail-forensics-1/2_composite_interlagos_s0_events.csv"))
    assert (blind["n_cars"], blind["solver_contact_points"], blind["hesitations"],
            round(blind["offtrack_pct"], 1)) == (10, 53658, 3, 22.1)
    assert (composite["n_cars"], composite["solver_contact_points"], composite["hesitations"],
            round(composite["offtrack_pct"], 1)) == (10, 12691, 14, 25.2)
    print("SELFTEST OK: Monaco prof/aluno classification anchors + 5-seed replicas; synthetic projection jump; "
          "Interlagos blind/composite anchors (14 composite hesitations).")
    return 0


def _write_report(out_dir: Path, runs, event_frame, jump_frame, cause_frame, metrics_frame, cases):
    lines = [
        "# FAIL-FORENSICS-1b — relatório de medição",
        "",
        "**Rótulo:** diagnóstico report-only; uma realização por célula (`N=1`).",
        "**Escopo:** Etapa 1. Nenhuma promoção, mudança de comportamento, retreino, re-pin ou inferência estatística.",
        "",
        "## Integridade e condições",
        "",
    ]
    for r in runs:
        lines.append(f"- `{r['run']}` / {r['track']}: pista SHA-256 `{r['track_sha256']}`, SF {r['sf_idx']}, {r['waypoints']} waypoints, {r['n_cars']} carros, {r['n_ticks']} ticks, transições de clima {r['weather_transition_count']}.")
    lines += ["", "CSV composite: `res_0..res_15` presentes (checado pelo leitor); autoridade, clima, pneu e odômetro foram preservados.",
              "Os CSVs não têm x/y nem índice cru do `nearest_segment`: os saltos são medidos pelo `s` persistido contra `cum_dist`; os segmentos anterior/seguinte são derivados do `s` e da geometria frozen.",
              "", "## Resumo por corrida", "",
              "| Pista | Braço | N carros | Fora (%) | Saídas | contatos solver (episódios/pontos) | preso R3 | hesitações | saltos ≥10/20/30 m | erro p95 (m) |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in runs:
        lines.append(f"| {r['track']} | {r['arm']} | {r['n_cars']} | {r['offtrack_pct']:.2f} | {r['offtrack_episodes']} | {r['solver_contact_episodes']}/{r['solver_contact_points']} | {r['stuck_r3_windows']} | {r['hesitations']} | {r['projection_error_ge_10m']}/{r['projection_error_ge_20m']}/{r['projection_error_ge_30m']} | {r['projection_error_p95_m']:.2f} |")
    lines += ["", "## Pista × braço × causa-raiz", "",
              "| Pista | Braço | Causa | Off-track | Contato | Preso | Hesitação | Salto projeção | Total |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in cause_frame.to_dict("records"):
        lines.append(f"| {r['track']} | {r['arm']} | {r['cause']} | {r['OFF_TRACK']} | {r['CONTATO']} | {r['PRESO_R3_30S']} | {r['HESITACAO']} | {r['SALTO_PROJECAO']} | {r['total']} |")
    lines += ["", "## Casos exemplares", ""]
    for i, r in enumerate(cases, 1):
        lines.append(f"{i}. **{r['event_type']} / {r['cause']} — {r['run']}, {r['drv']}, tick {r['tick']} ({r['t_s']:.1f}s), s={r['s']:.1f}m, lat={r['lat']:.1f}m, v={r['speed_mps']:.1f}m/s.** {r.get('case_note','')}")
        lines.append(f"   Authority `{r['authority']}`; th/brk/steer = {r['th']:.2f}/{r['brk']:.2f}/{r['steer_rad']:.3f}; {r['corner_id']} {r['corner_name']}, modo {r['mode']}; impulso anterior {r.get('prior_impulse_ns')} N·s / Δv {r.get('prior_delta_v_mps')} m/s; salto antecedente {r.get('projection_jump_preceding_2s_m')} m.")
    lines += ["", "## Leitura e limites", "",
              "Interlagos cego/composite e Monaco cego são reconciliações de âncoras; Monaco Composite é exploração `N=1`. R3 solo replica o âncora `aluno_s0`; R4 tem 10 carros e não é pareado por grid com R3. Os arquivos Monaco prof/aluno s0–s4 têm linhas de dados repetidas por braço, com seed diferente só no cabeçalho: cinco arquivos, uma realização de dados por braço. A tabela mantém cada arquivo visível; não some esses registros como realizações independentes.",
              "Classificação causal é uma regra mecânica de precedência, não uma estimativa contrafactual. O contacto solver-side é a fonte de impulso; a amostragem a 5 Hz não é usada como substituto.",
              "Saltos primários exigem erro `|Δs_wrapped − Δcum_dist| ≥ 30 m`; contagens a 10/20 m são sensibilidade descritiva. Nenhum limiar altera execução ou exclui dados.",
              "", "## Dados recomendados para a Etapa 2", "",
              "Usar esses locais/ticks para coletar posição XY do corpo e índice/segmento de `nearest_segment` diretamente, sincronizados com `s`, `lat`, odômetro e authority; guardar pontos de contato do solver. Para Monaco, construir e revisar as bordas permitidas antes de qualquer gate de respeito à pista. Este relatório não deriva bordas a partir da linha central.", ""]
    (out_dir / "relatorio.md").write_text("\n".join(lines), encoding="utf-8")


def _select_cases(events):
    if events.empty:
        return []
    chosen = []
    candidates = [
        ("SALTO_PROJECAO", "projection_error_m", True, "Maior descontinuidade primária da projeção."),
        ("CONTATO", "impulse_ns", True, "Maior impulso solver-side agregado no episódio."),
        ("OFF_TRACK", "duration_s", True, "Maior episódio contíguo de saída."),
        ("PRESO_R3_30S", "offtrack_ticks_in_window", True, "Janela presa R3 com mais ticks off-track."),
        ("HESITACAO", "duration_s", True, "Hesitação de maior duração dentro da definição congelada."),
    ]
    seen = set()
    for kind, field, descending, note in candidates:
        sub = events[events.event_type == kind]
        if sub.empty:
            continue
        sub = sub.assign(_rank=pd.to_numeric(sub.get(field), errors="coerce").fillna(0))
        sub = sub.sort_values(["_rank", "run", "tick"], ascending=[not descending, True, True])
        r = sub.iloc[0].drop(labels=["_rank"]).to_dict()
        if r["event_id"] in seen:
            continue
        r["case_note"] = note
        chosen.append(r)
        seen.add(r["event_id"])
    return chosen[:5]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true",
                        help="valida golden Monaco, saltos sintéticos e âncoras Interlagos")
    parser.add_argument("--run", nargs=4, action="append", metavar=("LABEL", "TRACK", "CSV", "EVENTS"),
                        help="Repita: blind_interlagos interlagos CSV EVENTS; EVENTS pode ser '-'.")
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    if args.selftest:
        if args.run or args.out_dir:
            parser.error("--selftest não combina com --run ou --out-dir")
        return _selftest()
    if not args.run:
        parser.error("informe pelo menos um --run LABEL TRACK CSV EVENTS")
    if not args.out_dir:
        parser.error("--out-dir é obrigatório com --run")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_metrics, all_events, all_jumps = [], [], []
    seen = set()
    for label, track, csv_path, events_path in args.run:
        if label in seen:
            parser.error(f"label repetida: {label}")
        seen.add(label)
        metrics, events, jumps = _read_run(label, track, csv_path, events_path)
        all_metrics.append(metrics)
        all_events.extend(events)
        all_jumps.extend(jumps)
        print(f"[OK] {label}: {metrics['n_cars']} carros | fora {metrics['offtrack_pct']:.2f}% | "
              f"contatos solver {metrics['solver_contact_episodes']} eps/{metrics['solver_contact_points']} pontos | "
              f"saltos >=30m {metrics['projection_error_ge_30m']}")

    metrics_frame = pd.DataFrame(all_metrics)
    event_frame = pd.DataFrame(all_events)
    jump_frame = pd.DataFrame(all_jumps)
    cause_labels = ["COLISÃO", "CURVA", "RECUPERAÇÃO", "TRAJETÓRIA"]
    event_types = ["OFF_TRACK", "CONTATO", "PRESO_R3_30S", "HESITACAO", "SALTO_PROJECAO"]
    cause_rows = []
    for m in all_metrics:
        part = event_frame[event_frame.run == m["run"]] if not event_frame.empty else pd.DataFrame()
        for cause in cause_labels:
            row = {"run": m["run"], "track": m["track"], "arm": m["arm"], "cause": cause}
            for typ in event_types:
                row[typ] = int(((part.cause == cause) & (part.event_type == typ)).sum()) if not part.empty else 0
            row["total"] = sum(row[t] for t in event_types)
            cause_rows.append(row)
    cause_frame = pd.DataFrame(cause_rows)
    cases = _select_cases(event_frame)
    metrics_frame.to_csv(out_dir / "resumo_corridas.csv", index=False)
    event_frame.to_csv(out_dir / "eventos_classificados.csv", index=False)
    jump_frame.to_csv(out_dir / "saltos_projecao.csv", index=False)
    cause_frame.to_csv(out_dir / "causas_pista_braco.csv", index=False)
    pd.DataFrame(cases).to_csv(out_dir / "casos_exemplares.csv", index=False)
    _write_report(out_dir, all_metrics, event_frame, jump_frame, cause_frame, metrics_frame, cases)
    print(f"[OK] Relatório e tabelas em {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
