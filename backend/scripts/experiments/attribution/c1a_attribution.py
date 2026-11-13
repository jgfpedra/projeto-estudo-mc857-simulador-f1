#!/usr/bin/env python3
"""REALISMO-1 · C1-A — atribuição por canal (report-only, N=0 bytes commitados).

Pergunta: na janela de 1 s ANTES de cada saída na reta de largada (Z_RETA),
quanto do comando de esterço (espaço pré-tanh) vem do residual (g·r) e quanto
vem do solo (m_solo)? É a trava de falsificação do C1: se o esterço do
residual não explica >=50% do comando no sentido da saída, muter só o canal
de esterço do residual (C1-B) NÃO pode remover as saídas -> PARE.

Zero simulação. Lê apenas os CSVs N=0 commitados da promocao-1 e os pesos de
produção. Reusa:
  - realismo_metrics.analyze_run  -> eventos Z_RETA (zona + t<=10 s)
  - NumpyCompositeActor.residual_forward_only -> r EXATO de res_0..15 + NPZ
    de produção (6210fff6); cross-check contra a coluna r_norm do CSV
  - F1MultiContextEnv.steer_limit_rad -> a_steer = steer_rad / limite(v)

Reconstrução (linhas com authority='policy'; o esterço do policy não é tocado
por governor/launch_cap, mas th/brk sim, então o canal de esterço vale também
em governor — reportado à parte):
  a_steer = clip(steer_rad / steer_limit_rad(speed), -1+eps, 1-eps)
  pre     = atanh(a_steer) = m_solo_steer + g·r_steer     (g = g_gate)
  m_solo_steer = pre - g·r_steer
Sentido da saída: exit_dir = sign(obs4) na 1ª linha off-track (obs4 = lat com
sinal / meia-largura; a coluna 'lat' do CSV é módulo — lição D0).
Fração atribuível ao residual, por janela:
  frac = mean(g·r_steer·exit_dir) / mean(pre·exit_dir)
Headline da trava = mediana de frac sobre as janelas (por pista e pooled).
"""
from __future__ import annotations

# Resolve common imports from the scripts root after topic-based reorganization.
import os as _scripts_os
import sys as _scripts_sys
_scripts_root = _scripts_os.path.dirname(_scripts_os.path.dirname(_scripts_os.path.abspath(__file__)))
_backend_root = _scripts_os.path.dirname(_scripts_root)
_project_root = _scripts_os.path.dirname(_backend_root)
for _script_path in (_scripts_root, _backend_root, _project_root):
    if _script_path not in _scripts_sys.path:
        _scripts_sys.path.insert(0, _script_path)


import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent.parent
BACKEND = SCRIPT_DIR.parent
for _p in (str(BACKEND), str(SCRIPT_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import scripts.analysis.realismo_metrics as RM          # noqa: E402
from model_train.f1_env import F1MultiContextEnv  # noqa: E402
from model_train.residual_gated import NumpyCompositeActor  # noqa: E402

SOLO = BACKEND / "model_train" / "v10_dagger" / "dagger_actor_best_weights.npz"
RES = BACKEND / "model_train" / "v15_residual" / "residual_best_weights.npz"
PROMO = BACKEND / "experiments" / "composite-1" / "promocao-1"
OUT_DIR = BACKEND / "experiments" / "realismo-1" / "c1"
RUNS = [("interlagos", "1_R1_INTERLAGOS_RACE"), ("monaco", "3_R3_MONACO_RACE")]
V_L_CAP = 12.6                 # teto pinado do plano (m/s)
T_L_MAX_S = 10.0               # teto temporal da janela de largada
PRE_WINDOW_TICKS = 10          # 1 s = 5 amostras 5 Hz = 10 ticks lógicos
EPS = 1e-9


def _residual_rows(df: pd.DataFrame, actor: NumpyCompositeActor):
    res_in = df[[f"res_{j}" for j in range(16)]].to_numpy(dtype=np.float64)
    r = np.asarray(actor.residual_forward_only(res_in.astype(np.float32)),
                   dtype=np.float64)
    r_norm_recomputed = np.linalg.norm(r, axis=1)
    return r, r_norm_recomputed


def analyze(track: str, stem: str, actor: NumpyCompositeActor) -> dict:
    log = PROMO / f"{stem}.log"
    main = PROMO / f"{stem}.csv"
    events = PROMO / f"{stem}_events.csv"
    payload = RM.analyze_run(run_id=stem, log=log, main_csv=main,
                             events_csv=events, track=track, expect_variedade=0)
    geo = RM.track_geometry(track)
    df = pd.read_csv(main, comment="#")
    df = df.sort_values(["drv", "tick"]).reset_index(drop=True)

    r, r_norm_recomputed = _residual_rows(df, actor)
    # cross-check: r recomputado de res_0..15 reproduz r_norm do CSV?
    r_norm_csv = df["r_norm"].to_numpy(dtype=np.float64)
    r_norm_max_abs_err = float(np.max(np.abs(r_norm_recomputed - r_norm_csv)))

    speed = df["speed"].to_numpy(dtype=np.float64)
    steer_rad = df["steer_rad"].to_numpy(dtype=np.float64)
    g = df["g_gate"].to_numpy(dtype=np.float64)
    authority = df["authority"].to_numpy(dtype=object)
    limit = np.array([F1MultiContextEnv.steer_limit_rad(v) for v in speed])
    a_steer = np.clip(steer_rad / limit, -1.0 + EPS, 1.0 - EPS)
    pre = np.arctanh(a_steer)                 # = m_solo_steer + g·r_steer
    gr_steer = g * r[:, 0]
    m_solo_steer = pre - gr_steer
    # sanidade tautológica: tanh(m_solo+g·r) reconstrói a_steer
    recon = np.tanh(m_solo_steer + gr_steer)
    recon_max_abs_err = float(np.max(np.abs(recon - a_steer)))

    df = df.assign(_pre=pre, _gr_steer=gr_steer, _msolo_steer=m_solo_steer,
                   _g=g, _auth=authority, _steer=steer_rad)
    idx_by_key = {(d, int(t)): i for i, (d, t)
                  in enumerate(zip(df["drv"], df["tick"]))}

    exits = payload["events"]["z_reta"]
    windows = []
    for e in exits:
        drv, start = e["drv"], int(e["tick"])
        exit_i = idx_by_key.get((drv, start))
        exit_dir = 0.0
        if exit_i is not None:
            exit_dir = float(np.sign(df.at[exit_i, "obs4"]))
        if exit_dir == 0.0:
            exit_dir = 1.0
        sub = df[(df["drv"] == drv) & (df["tick"] < start)
                 & (df["tick"] >= start - PRE_WINDOW_TICKS)]
        pol = sub[sub["_auth"] == "policy"]
        rec = dict(drv=drv, start_tick=start, t_s=float(e["t_s"]),
                   s=float(e["s"]), exit_dir=exit_dir,
                   n_rows=int(len(sub)), n_policy=int(len(pol)),
                   exit_speed=(float(df.at[exit_i, "speed"])
                               if exit_i is not None else None))
        if len(pol):
            pre_te = float((pol["_pre"] * exit_dir).mean())
            gr_te = float((pol["_gr_steer"] * exit_dir).mean())
            ms_te = float((pol["_msolo_steer"] * exit_dir).mean())
            rec.update(
                pre_toward_exit=pre_te, gr_toward_exit=gr_te,
                msolo_toward_exit=ms_te,
                g_mean=float(pol["_g"].mean()),
                steer_rad_mean=float(pol["_steer"].mean()),
                frac_residual=(gr_te / pre_te if abs(pre_te) > 1e-6 else None),
                abs_frac_residual=(float(abs(gr_te) / (abs(ms_te) + abs(gr_te)))
                                   if (abs(ms_te) + abs(gr_te)) > 1e-9 else None))
        windows.append(rec)

    fr = [w["frac_residual"] for w in windows
          if w.get("frac_residual") is not None]
    absfr = [w["abs_frac_residual"] for w in windows
             if w.get("abs_frac_residual") is not None]
    # reprodução do A1: esterço com g alto vs g~0 nas janelas pré-saída
    pre_rows = pd.concat([df[(df["drv"] == w["drv"])
                             & (df["tick"] < w["start_tick"])
                             & (df["tick"] >= w["start_tick"] - PRE_WINDOW_TICKS)]
                          for w in windows]) if windows else df.iloc[0:0]
    ghi = pre_rows[pre_rows["_g"] > 0.5]["_steer"]
    glo = pre_rows[pre_rows["_g"] < 0.01]["_steer"]

    exit_speeds = [w["exit_speed"] for w in windows if w["exit_speed"] is not None]
    return dict(
        track=track, run=stem,
        r_norm_max_abs_err=r_norm_max_abs_err,
        recon_max_abs_err=recon_max_abs_err,
        n_z_reta=len(windows),
        windows=windows,
        median_frac_residual=(float(np.median(fr)) if fr else None),
        median_abs_frac_residual=(float(np.median(absfr)) if absfr else None),
        n_windows_with_policy=len(fr),
        exit_speed_min=(min(exit_speeds) if exit_speeds else None),
        exit_speed_median=(float(np.median(exit_speeds)) if exit_speeds else None),
        exit_speed_max=(max(exit_speeds) if exit_speeds else None),
        steer_g_hi_mean=(float(ghi.mean()) if len(ghi) else None),
        steer_g_hi_n=int(len(ghi)),
        steer_g_lo_mean=(float(glo.mean()) if len(glo) else None),
        steer_g_lo_n=int(len(glo)),
        s_l_end=float(geo.z_reta[1]),
        payload_metrics_sha=payload["metrics_sha256"],
    )


def reach_check(track: str, stem: str, s_l_end: float, v_l: float) -> list:
    """Cada carro cruza S_L_END com v>=V_L antes de T_L_MAX? (viabilidade da
    janela D_L em N=0; a janela real é aplicada só no C1-B)."""
    df = pd.read_csv(PROMO / f"{stem}.csv", comment="#")
    geo = RM.track_geometry(track)
    L = geo.length_m
    grid_front = geo.grid_front
    out = []
    for drv, gdf in df.sort_values("tick").groupby("drv"):
        s = gdf["s"].to_numpy(dtype=np.float64)
        v = gdf["speed"].to_numpy(dtype=np.float64)
        t = gdf["t_s"].to_numpy(dtype=np.float64)
        # distância para a frente do grid até S_L_END, no círculo
        reached = None
        for k in range(len(s)):
            fwd = (s[k] - grid_front) % L
            half = L / 2.0
            past_end = ((s[k] - s_l_end) % L) < half and fwd < half
            if past_end and v[k] >= v_l:
                reached = (float(t[k]), float(s[k]), float(v[k]))
                break
        out.append(dict(drv=drv,
                        reached_t_s=(reached[0] if reached else None),
                        reached_s=(reached[1] if reached else None),
                        reached_v=(reached[2] if reached else None),
                        before_tmax=(reached is not None
                                     and reached[0] <= T_L_MAX_S)))
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    actor = NumpyCompositeActor(str(SOLO), str(RES))
    results = [analyze(track, stem, actor) for track, stem in RUNS]

    all_exit_speeds = []
    for r in results:
        all_exit_speeds += [w["exit_speed"] for w in r["windows"]
                            if w["exit_speed"] is not None]
    v_l_raw = max(all_exit_speeds) if all_exit_speeds else 0.0
    v_l = min(V_L_CAP, v_l_raw)

    reach = {}
    for (track, stem), r in zip(RUNS, results):
        reach[track] = reach_check(track, stem, r["s_l_end"], v_l)

    pooled_fr = []
    for r in results:
        pooled_fr += [w["frac_residual"] for w in r["windows"]
                      if w.get("frac_residual") is not None]
    out = dict(
        schema="c1a-attribution-v1",
        solo_npz=str(SOLO.relative_to(BACKEND)),
        residual_npz=str(RES.relative_to(BACKEND)),
        v_l_raw=v_l_raw, v_l=v_l, v_l_cap=V_L_CAP, t_l_max_s=T_L_MAX_S,
        pooled_median_frac_residual=(float(np.median(pooled_fr))
                                     if pooled_fr else None),
        lock_threshold=0.5,
        lock_pass=(bool(np.median(pooled_fr) >= 0.5) if pooled_fr else None),
        per_track=results,
        reach_check=reach,
    )
    out_path = OUT_DIR / "C1A_ATTRIBUTION.json"
    if out_path.exists():
        raise FileExistsError(out_path)
    out_path.write_text(json.dumps(out, sort_keys=True, indent=2,
                                   ensure_ascii=False) + "\n", encoding="utf-8")

    # ---- relatório legível ----
    print(f"[C1-A] residual npz sha16 = (produção 6210fff6); solo = {SOLO.name}")
    for r in results:
        print(f"\n== {r['track']} ({r['run']}) ==")
        print(f"  cross-check r_norm (recalc vs CSV) max|err| = {r['r_norm_max_abs_err']:.2e}")
        print(f"  recon tanh(m_solo+g·r) vs a_steer max|err| = {r['recon_max_abs_err']:.2e}")
        print(f"  Z_RETA janelas: {r['n_z_reta']} (com linhas policy: {r['n_windows_with_policy']})")
        print(f"  mediana frac_residual (g·r / pré, sentido saída) = {r['median_frac_residual']}")
        print(f"  mediana |g·r|/(|m_solo|+|g·r|)                    = {r['median_abs_frac_residual']}")
        print(f"  esterço médio g>0.5: {r['steer_g_hi_mean']} (n={r['steer_g_hi_n']}) | "
              f"g<0.01: {r['steer_g_lo_mean']} (n={r['steer_g_lo_n']})")
        print(f"  vel. no início da saída min/med/max = "
              f"{r['exit_speed_min']}/{r['exit_speed_median']}/{r['exit_speed_max']}")
    print(f"\n[C1-A] V_L_raw = {v_l_raw:.3f} m/s -> V_L = min(12.6, raw) = {v_l:.3f} m/s")
    print(f"[C1-A] pooled mediana frac_residual = {out['pooled_median_frac_residual']} "
          f"| trava >=0.5: {'PASS' if out['lock_pass'] else 'FAIL -> PARE'}")
    for track, rows in reach.items():
        n_ok = sum(1 for x in rows if x["before_tmax"])
        tmax = max((x["reached_t_s"] for x in rows if x["reached_t_s"] is not None),
                   default=None)
        print(f"[C1-A] {track}: {n_ok}/{len(rows)} carros cruzam S_L_END com v>=V_L "
              f"antes de {T_L_MAX_S}s | último em t={tmax}s")
    print(f"\n[C1-A] JSON -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
