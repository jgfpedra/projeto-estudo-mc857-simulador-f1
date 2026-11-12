#!/usr/bin/env python3
"""REALISMO-1 C2-A — atribuição de reentrada, report-only.

Lê somente os CSVs N=0 commitados da promocao-1 e a geometria frozen.
Não importa o simulador/controller e não executa corrida.

Reentrada observável: linha 5 Hz com offtrack=0 imediatamente precedida,
para o mesmo carro, por linha offtrack=1. Para cada transição registra:
body_x/body_y, s, lateral signed = obs4*6, margem lateral = 6-|signed_lat|,
speed e erro de rumo = atan2(obs5, obs6). Nova saída = primeira linha
offtrack=1 do mesmo carro em (t_reentry, t_reentry+10s].

Parâmetros derivados, congelados no relatório:
  theta_H = 20 graus = 0.3490658504 rad. É o limiar angular de alinhamento
             do protocolo de reentrada já observado na telemetria frozen.
  m_H     = 0.5 m. É o maior degrau de 0.25 m que não excede o menor p75
             de margem na reentrada entre as duas pistas (Interlagos ~0.514,
             Monaco ~0.726).
  T_H     = 24.0 s. É ceil(max(p95 do tempo até |heading_err|<=theta_H e
             margem>=m_H, por pista)); p95 observado Monaco ~23.25s.
Esses parâmetros são recomendações para o prereg C2; este script não altera
produção nem os aplica ao controller.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from scripts import realismo_metrics as RM  # noqa: E402

TRACK_RUNS = {
    "interlagos": "1_R1_INTERLAGOS_RACE",
    "monaco": "3_R3_MONACO_RACE",
}
PROMO = BACKEND / "experiments" / "composite-1" / "promocao-1"
OUT_DIR = BACKEND / "experiments" / "realismo-1" / "c2"
THETA_H_DEG = 20.0
THETA_H_RAD = math.radians(THETA_H_DEG)
M_H_M = 0.5
T_H_S = 24.0
NEW_EXIT_WINDOW_S = 10.0
HALF_WIDTH_M = 6.0


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def heading_at_s(geo, s: float) -> float:
    wps, _diff, seg, seg_cum, length, seg_head = geo.geom
    sm = float(s) % float(length)
    j = int(np.searchsorted(seg_cum, sm, side="right") - 1)
    j = min(max(j, 0), len(seg_head) - 1)
    return float(seg_head[j])


def _first_exit_after(g: pd.DataFrame, t0: float):
    out = g[(g.t_s > t0) & (g.t_s <= t0 + NEW_EXIT_WINDOW_S) & (g.offtrack == 1)]
    if out.empty:
        return None
    row = out.iloc[0]
    return dict(tick=int(row.tick), t_s=float(row.t_s), s=float(row.s),
                dt_s=float(row.t_s - t0))


def _time_to_alignment(g: pd.DataFrame, start_index: int):
    future = g.iloc[start_index:]
    ok = ((future.heading_error_rad.abs() <= THETA_H_RAD)
          & (future.lateral_margin_m >= M_H_M)
          & (future.offtrack == 0))
    if not ok.any():
        return None
    row = future.loc[ok].iloc[0]
    return dict(tick=int(row.tick), t_s=float(row.t_s),
                dt_s=float(row.t_s - g.iloc[start_index].t_s))


def analyze_track(track: str, stem: str) -> dict:
    main = PROMO / f"{stem}.csv"
    events = PROMO / f"{stem}_events.csv"
    log = PROMO / f"{stem}.log"
    geo = RM.track_geometry(track)
    df = pd.read_csv(main, comment="#").sort_values(["drv", "tick"]).reset_index(drop=True)
    df["signed_lat_m"] = df["obs4"].astype(float) * HALF_WIDTH_M
    df["lateral_margin_m"] = HALF_WIDTH_M - df["signed_lat_m"].abs()
    df["heading_error_rad"] = np.arctan2(df["obs5"], df["obs6"])
    df["track_heading_rad"] = [heading_at_s(geo, s) for s in df["s"]]
    df["motion_heading_rad"] = np.nan
    for drv, g in df.groupby("drv", sort=False):
        idx = g.index.to_list()
        for prev_i, cur_i in zip(idx[:-1], idx[1:]):
            dx = float(df.at[cur_i, "body_x"] - df.at[prev_i, "body_x"])
            dy = float(df.at[cur_i, "body_y"] - df.at[prev_i, "body_y"])
            if math.hypot(dx, dy) > 1e-9:
                df.at[cur_i, "motion_heading_rad"] = math.atan2(dy, dx)

    rows = []
    for drv, g0 in df.groupby("drv", sort=False):
        g = g0.reset_index(drop=True)
        for i in range(1, len(g)):
            if int(g.offtrack.iloc[i - 1]) != 1 or int(g.offtrack.iloc[i]) != 0:
                continue
            row = g.iloc[i]
            t0 = float(row.t_s)
            exit_after = _first_exit_after(g, t0)
            aligned = _time_to_alignment(g, i)
            rec = dict(
                drv=str(drv), reentry_tick=int(row.tick), reentry_t_s=t0,
                s=float(row.s), body_x=float(row.body_x), body_y=float(row.body_y),
                speed_mps=float(row.speed), signed_lat_m=float(row.signed_lat_m),
                lateral_margin_m=float(row.lateral_margin_m),
                heading_error_rad=float(row.heading_error_rad),
                heading_error_deg=float(math.degrees(row.heading_error_rad)),
                abs_heading_error_deg=float(abs(math.degrees(row.heading_error_rad))),
                track_heading_rad=float(row.track_heading_rad),
                motion_heading_rad=(None if pd.isna(row.motion_heading_rad)
                                    else float(row.motion_heading_rad)),
                new_exit_within_10s=bool(exit_after),
                exit_after_10s=exit_after,
                time_to_alignment=aligned,
            )
            rows.append(rec)
    reentries = pd.DataFrame(rows)
    if reentries.empty:
        raise RuntimeError(f"sem reentradas observáveis: {track}")

    reentries_for_stats = reentries.copy()
    reentries_for_stats["alignment_dt_s"] = reentries_for_stats.time_to_alignment.map(
        lambda x: None if x is None else x["dt_s"])
    aligned_times = reentries_for_stats.alignment_dt_s.dropna().astype(float)
    new = reentries_for_stats.new_exit_within_10s.astype(int)
    corr_heading = float(np.corrcoef(
        reentries_for_stats.abs_heading_error_deg.to_numpy(float), new.to_numpy(float))[0, 1])
    corr_margin = float(np.corrcoef(
        reentries_for_stats.lateral_margin_m.to_numpy(float), new.to_numpy(float))[0, 1])
    corr_speed = float(np.corrcoef(
        reentries_for_stats.speed_mps.to_numpy(float), new.to_numpy(float))[0, 1])
    p75_margin = float(reentries_for_stats.lateral_margin_m.quantile(0.75))
    p95_align = float(aligned_times.quantile(0.95)) if len(aligned_times) else None
    return dict(
        track=track, run=stem, source_sha256=dict(
            main=sha256_file(main), events=sha256_file(events), log=sha256_file(log),
            track=geo.file_sha256),
        n_rows=int(len(df)), n_drivers=int(df.drv.nunique()),
        n_reentries=int(len(reentries)),
        n_new_exit_10s=int(reentries_for_stats.new_exit_within_10s.sum()),
        new_exit_rate_10s=float(reentries_for_stats.new_exit_within_10s.mean()),
        n_aligned=int(aligned_times.size),
        alignment_time_s=dict(
            p50=float(aligned_times.quantile(0.50)),
            p95=p95_align, max=float(aligned_times.max())) if len(aligned_times) else None,
        reentry_stats=dict(
            abs_heading_error_deg=dict(
                median=float(reentries_for_stats.abs_heading_error_deg.median()),
                p75=float(reentries_for_stats.abs_heading_error_deg.quantile(0.75)),
                p95=float(reentries_for_stats.abs_heading_error_deg.quantile(0.95))),
            lateral_margin_m=dict(
                median=float(reentries_for_stats.lateral_margin_m.median()),
                p75=p75_margin,
                p95=float(reentries_for_stats.lateral_margin_m.quantile(0.95))),
            speed_mps=dict(
                median=float(reentries_for_stats.speed_mps.median()),
                p95=float(reentries_for_stats.speed_mps.quantile(0.95))),
        ),
        correlations=dict(
            abs_heading_error_deg_vs_new_exit_10s=corr_heading,
            lateral_margin_m_vs_new_exit_10s=corr_margin,
            speed_mps_vs_new_exit_10s=corr_speed),
        reentries=rows,
    )


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tracks = [analyze_track(track, stem) for track, stem in TRACK_RUNS.items()]
    pooled_times = [
        r["time_to_alignment"]["dt_s"]
        for track in tracks for r in track["reentries"]
        if r["time_to_alignment"] is not None]
    p75_margin_min = min(t["reentry_stats"]["lateral_margin_m"]["p75"] for t in tracks)
    theta_derived = dict(
        value_deg=THETA_H_DEG, value_rad=THETA_H_RAD,
        rationale="limiar angular frozen de alinhamento usado no protocolo de rejoin; "
                   "a análise N0 reporta esse limiar e mede sua associação com nova saída",
    )
    margin_derived = dict(
        value_m=M_H_M, p75_min_across_tracks=p75_margin_min,
        rationale="maior degrau de 0,25 m não superior ao menor p75 de margem na reentrada",
    )
    p95_pooled = float(np.quantile(np.asarray(pooled_times, dtype=float), 0.95))
    params = dict(
        theta_H=theta_derived, m_H=margin_derived,
        T_H=dict(value_s=T_H_S, observed_p95_pooled=p95_pooled,
                 rationale="teto de 24 s = ceil do p95 máximo observado para satisfazer "
                           "theta_H e m_H; Monaco é o caso limitante"),
    )
    out = dict(
        schema="c2a-attribution-v1", source="promocao-1 N0 frozen",
        parameters=params, tracks=tracks,
        method=dict(
            reentry="offtrack 1 -> 0 in 5 Hz CSV; signed_lat=obs4*6; "
                     "heading_error=atan2(obs5,obs6)",
            new_exit="first offtrack=1 for same driver in (reentry, reentry+10s]",
            alignment="first on-track row with abs(heading_error)<=theta_H and "
                       "lateral_margin>=m_H",
            no_simulation=True),
    )
    out_path = OUT_DIR / "C2A_ATTRIBUTION.json"
    if out_path.exists():
        raise FileExistsError(out_path)
    out_path.write_text(json.dumps(out, sort_keys=True, indent=2,
                                   ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"C2A -> {out_path}")
    for t in tracks:
        print(t["track"], t["n_reentries"], t["n_new_exit_10s"],
              t["reentry_stats"]["abs_heading_error_deg"],
              t["reentry_stats"]["lateral_margin_m"],
              t["alignment_time_s"], t["correlations"])
    print("parameters", json.dumps(params, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
