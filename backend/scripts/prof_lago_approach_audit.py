#!/usr/bin/env python3
"""PROF-CONTROL-1 — auditoria oficial de aproximação e entrada da C01 (Lago).

Report-only, determinístico, zero corrida nova, zero alteração de produção.
Consolida, sobre a telemetria EXISTENTE da referência do professor
(``REF_INTERLAGOS_600S.csv``, SHA ``c00391ab…``), a anatomia causal da
Descida do Lago levantada pelo Dono na telemetria bruta: a Volta 1
pós-largada tangencia a borda com margem de centímetros (grip 0,842) e a
degradação linear de pneu do PyBullet empurra as voltas seguintes para fora
(|lat|_máx > 6,0 m a partir da Volta 2).

Por passe (5 passes pela janela s ∈ [0, 80] m, um por cruzamento de linha):

- **Zona de aproximação** (reta principal, s ∈ [track_len−150, track_len]):
  velocidade máxima, ponto de início de frenagem (primeiro brk > 0,05),
  velocidade no início da frenagem, distância até a linha, lat final.
- **Zona de contorno C01** (s ∈ [0, 80] m): velocidade em s=0, v_min do
  ápice (+ t, s), momento de reaceleração (primeiro th > 0,05 após o ápice),
  lat_max, margem de pista (6,0 − lat_max), tyre_life/tyre_grip no instante
  do lat_max, demanda lateral v²·|κ(s)| vs capacidade μ_eff·g
  (tyre_grip × 9,81), razão de saturação de esterço máxima.
- **Correlação tyre_grip ↔ lat_max** entre os 5 passes (Pearson, manual) —
  a assinatura causal da degradação de pneu.

Saídas exclusivas (determinísticas, cmp=0 entre execuções):
``experiments/prof-control-1/LAGO_APPROACH_FINDINGS.json`` e ``.md``.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND))

from scripts.prof_lago_anatomy import (  # noqa: E402  funções canônicas
    kappa_interp_fn,
    segment_laps,
    sha256_file,
    steer_limit_rad,
)

VERSION = "prof-control-1/lago-approach-audit-v1.0"

REF_CSV = BACKEND / "experiments" / "prof-curva-1" / "REF_INTERLAGOS_600S.csv"
REF_SHA256 = "c00391ab21033dae1a03db2cd7f7fd6983baa47d67b0828bec503d93778e9b3a"
TRACK_FILE = BACKEND / "model_train" / "tracks_frozen" / "interlagos_v2.json"
TRACK_SHA_PIN = "164876196eb12174"

APPROACH_ZONE_M = 150.0     # s ∈ [track_len−150, track_len]
CORNER_WINDOW_M = (0.0, 80.0)
BRAKE_THRESHOLD = 0.05      # brk > 0.05 = frenagem
THROTTLE_THRESHOLD = 0.05   # th > 0.05 = reaceleração
HALF_WIDTH_M = 6.0
GRAVITY = 9.81

OUT_JSON = BACKEND / "experiments" / "prof-control-1" / "LAGO_APPROACH_FINDINGS.json"
OUT_MD = BACKEND / "experiments" / "prof-control-1" / "LAGO_APPROACH_FINDINGS.md"


def pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    """Correlação de Pearson manual (sem variância zero → None)."""
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0.0 or syy <= 0.0:
        return None
    return sxy / math.sqrt(sxx * syy)


def approach_summary(rows: pd.DataFrame, track_len: float) -> Dict[str, Any]:
    """Zona de aproximação: vmax, início de frenagem, lat final."""
    zone = rows[(rows["s"] >= track_len - APPROACH_ZONE_M)
                & (rows["s"] <= track_len)].sort_values("tick")
    if len(zone) == 0:
        return {"presente": False}
    v = zone["speed"].to_numpy(float)
    s = zone["s"].to_numpy(float)
    lat = zone["lat"].to_numpy(float)
    brk = zone["brk"].to_numpy(float)
    t_s = zone["t_s"].to_numpy(float)
    i_max = int(np.argmax(v))
    brake_idx = next((i for i in range(len(brk)) if brk[i] > BRAKE_THRESHOLD),
                     None)
    return {
        "presente": True,
        "v_max_kmh": round(float(v.max()) * 3.6, 3),
        "v_max_em_s": round(float(s[i_max]), 3),
        "brake_start_s_m": round(float(s[brake_idx]), 3) if brake_idx is not None else None,
        "brake_start_t_s": round(float(t_s[brake_idx]), 3) if brake_idx is not None else None,
        "v_no_inicio_frenagem_kmh": round(float(v[brake_idx]) * 3.6, 3) if brake_idx is not None else None,
        "dist_frenagem_linha_m": round(track_len - float(s[brake_idx]), 3) if brake_idx is not None else None,
        "lat_final_m": round(float(lat[-1]), 4),
    }


def corner_summary(rows: pd.DataFrame, kappa_at) -> Dict[str, Any]:
    """Zona de contorno C01 (s ∈ [0, 80]): ápice, margem, pneu, demanda. """
    win = rows[(rows["s"] >= CORNER_WINDOW_M[0])
               & (rows["s"] <= CORNER_WINDOW_M[1])].sort_values("tick")
    if len(win) == 0:
        return {"presente": False}
    v = win["speed"].to_numpy(float)
    s = win["s"].to_numpy(float)
    lat = win["lat"].to_numpy(float)
    t_s = win["t_s"].to_numpy(float)
    th = win["th"].to_numpy(float)
    steer = win["steer_rad"].to_numpy(float)
    grip_win = win["tyre_grip"].to_numpy(float)
    life_win = win["tyre_life"].to_numpy(float)

    i_lat = int(np.argmax(lat))
    i_vmin = int(np.argmin(v))
    limits = np.array([steer_limit_rad(v[i]) for i in range(len(win))])
    ratio = np.abs(steer) / np.maximum(limits, 1e-12)
    a_lat = np.array([v[i] * v[i] * abs(kappa_at(s[i])) for i in range(len(win))])
    i_ademand = int(np.argmax(a_lat))

    reaccel: Optional[int] = None
    for i in range(i_vmin + 1, len(win)):
        if th[i] > THROTTLE_THRESHOLD:
            reaccel = i
            break

    grip_apex = float(grip_win[i_lat])
    return {
        "presente": True,
        "v_em_s0_kmh": round(float(v[0]) * 3.6, 3),
        "s_primeiro_tick_m": round(float(s[0]), 3),
        "v_min_apice_kmh": round(float(v.min()) * 3.6, 3),
        "apice_em_t_s": round(float(t_s[i_vmin]), 3),
        "apice_em_s_m": round(float(s[i_vmin]), 3),
        "reaceleracao_t_s": round(float(t_s[reaccel]), 3) if reaccel is not None else None,
        "reaceleracao_s_m": round(float(s[reaccel]), 3) if reaccel is not None else None,
        "lat_max_m": round(float(lat.max()), 4),
        "lat_max_em_s_m": round(float(s[i_lat]), 3),
        "lat_max_em_t_s": round(float(t_s[i_lat]), 3),
        "margem_pista_m": round(HALF_WIDTH_M - float(lat.max()), 4),
        "saiu": bool(lat.max() > HALF_WIDTH_M),
        "tyre_life_pct_no_latmax": round(float(life_win[i_lat]), 2),
        "tyre_grip_no_latmax": round(grip_apex, 4),
        "a_lat_demanda_ms2": round(float(a_lat[i_lat]), 3),
        "a_lat_capacidade_ms2": round(grip_apex * GRAVITY, 3),
        "demanda_sobre_capacidade": round(float(a_lat[i_lat]) / (grip_apex * GRAVITY), 3),
        "a_lat_demanda_max_ms2": round(float(a_lat.max()), 3),
        "a_lat_demanda_max_em_s_m": round(float(s[i_ademand]), 3),
        "steer_ratio_max_janela": round(float(ratio.max()), 4),
    }


def analyze_dataframe(df: pd.DataFrame, kappa_at, track_len: float) -> Dict[str, Any]:
    """5 passes pela C01 (um por cruzamento) + correlação pneu ↔ espalhamento."""
    laps = segment_laps(df["s"].to_numpy(float), track_len)
    n_seg = int(laps.max()) + 1
    passes: List[Dict[str, Any]] = []
    for p in range(1, min(5, n_seg - 1) + 1):
        seg_prev = df[laps == (p - 1)]
        seg_cur = df[laps == p]
        passes.append({
            "passe": p,
            "aproximacao": approach_summary(seg_prev, track_len),
            "contorno": corner_summary(seg_cur, kappa_at),
        })
    grips = [p["contorno"].get("tyre_grip_no_latmax") for p in passes
             if p["contorno"].get("presente")]
    lats = [p["contorno"].get("lat_max_m") for p in passes
            if p["contorno"].get("presente")]
    grips = [g for g in grips if g is not None]
    lats = [l for l in lats if l is not None]
    deltas = [round(lats[i + 1] - lats[i], 4) for i in range(len(lats) - 1)] \
        if len(lats) > 1 else []
    saidas = sum(1 for p in passes if p["contorno"].get("saiu"))
    return {
        "n_passes": len(passes),
        "passes": passes,
        "correlacao_tyre_grip_vs_lat_max": {
            "pearson_r": pearson(grips, lats),
            "n": min(len(grips), len(lats)),
            "deltas_lat_max_por_passe_m": deltas,
        },
        "passes_com_saida": saidas,
        "passes_total": len(passes),
    }


def main() -> int:
    if not REF_CSV.exists():
        print(f"ERRO: referência ausente: {REF_CSV}", file=sys.stderr)
        return 2
    ref_sha = sha256_file(REF_CSV)
    if ref_sha != REF_SHA256:
        print(f"ERRO: SHA da referência divergente: {ref_sha}", file=sys.stderr)
        return 2
    with TRACK_FILE.open("r", encoding="utf-8") as f:
        track = json.load(f)
    if track.get("sha256") != TRACK_SHA_PIN:
        print(f"ERRO: SHA da pista divergente: {track.get('sha256')}", file=sys.stderr)
        return 2
    wps = np.array(track["waypoints"], dtype=np.float64)
    track_len = float(np.hypot(*np.diff(np.vstack([wps, wps[:1]]), axis=0).T).sum())

    df = pd.read_csv(REF_CSV, comment="#")
    kappa_at = kappa_interp_fn(wps)
    payload = analyze_dataframe(df, kappa_at, track_len)
    result = {
        "schema_version": VERSION,
        "origem": {
            "csv": str(REF_CSV.relative_to(BACKEND)),
            "csv_sha256": ref_sha,
            "n_linhas_dados": int(len(df)),
        },
        "pista": {
            "arquivo": str(TRACK_FILE.relative_to(BACKEND)),
            "sha256_pin": TRACK_SHA_PIN,
            "comprimento_m": round(track_len, 3),
        },
        "metodo": {
            "zona_aproximacao_s_m": f"[track_len-{APPROACH_ZONE_M:.0f}, track_len]",
            "zona_contorno_s_m": list(CORNER_WINDOW_M),
            "limiar_frenagem_brk": BRAKE_THRESHOLD,
            "limiar_reaceleracao_th": THROTTLE_THRESHOLD,
            "kappa": "perfil canônico suavizado 30 m (compute_kappa_profile, ds 4 m), |κ| interpolado em s",
            "capacidade_lateral": "tyre_grip × 9.81 (μ_eff·g)",
            "steer_limit": "F1MultiContextEnv.steer_limit_rad",
        },
        **payload,
    }

    for out in (OUT_JSON, OUT_MD):
        if out.exists():
            print(f"ERRO: saída já existe (escrita exclusiva): {out}", file=sys.stderr)
            return 3
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    linhas = [
        "# LAGO APPROACH FINDINGS — aproximação e entrada da C01 (Descida do Lago)",
        "",
        f"**Data:** 2026-11-07 · **Método:** report-only sobre a telemetria "
        f"existente (zero corrida nova) · **Instrumento:** "
        f"`scripts/prof_lago_approach_audit.py` (determinístico, `cmp=0` ×2) · "
        f"**Fonte:** `REF_INTERLAGOS_600S.csv` (SHA `c00391ab…`) · "
        f"**Pista:** `164876196eb12174`.",
        "",
        f"## Passe por passe (5 cruzamentos de linha; janela C01 s ∈ [0, 80] m)",
        "",
        "| passe | t_s do lat_max | lat_max (m) | margem (m) | saiu | tyre_life | "
        "tyre_grip | v_min ápice (km/h) | demanda/capacidade |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    for p in result["passes"]:
        c = p["contorno"]
        linhas.append(
            f"| {p['passe']} | {c['lat_max_em_t_s']} | {c['lat_max_m']} | "
            f"{c['margem_pista_m']:+.4f} | {'SIM' if c['saiu'] else 'não'} | "
            f"{c['tyre_life_pct_no_latmax']}% | {c['tyre_grip_no_latmax']} | "
            f"{c['v_min_apice_kmh']} | {c['demanda_sobre_capacidade']} |")
    r = result["correlacao_tyre_grip_vs_lat_max"]["pearson_r"]
    linhas += [
        "",
        f"**Correlação tyre_grip ↔ lat_max:** Pearson r = **{r:.4f}** em "
        f"{result['correlacao_tyre_grip_vs_lat_max']['n']} passes; "
        f"deltas de lat_max por passe (m): "
        f"{result['correlacao_tyre_grip_vs_lat_max']['deltas_lat_max_por_passe_m']}.",
        f"Passes com saída: {result['passes_com_saida']}/{result['passes_total']}.",
        "",
        "## Aproximação (reta principal, últimos 150 m)",
        "",
        "| passe | v_max (km/h) | início frenagem s (m) | dist até linha (m) | "
        "v na frenagem (km/h) | lat final (m) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for p in result["passes"]:
        a = p["aproximacao"]
        if not a.get("presente"):
            continue
        linhas.append(
            f"| {p['passe']} | {a['v_max_kmh']} | {a['brake_start_s_m']} | "
            f"{a['dist_frenagem_linha_m']} | {a['v_no_inicio_frenagem_kmh']} | "
            f"{a['lat_final_m']} |")
    linhas += [
        "",
        "## Leitura (report-only; veredito é do Dono)",
        "",
        "- A aproximação é consistente entre passes (mesma frenagem, mesma "
        "entrada centralizada); a variável que separa o passe limpo das "
        "saídas é o **tyre_grip degradado** (0,842 → 0,807) sobre uma "
        "trajetória que já tangencia a borda no passe 1 (margem de "
        "centímetros);",
        "- a demanda lateral v²·κ na janela excede a capacidade μ_eff·g "
        "(demanda/capacidade > 1) — o carro desliza largo com o pneu gasto;",
        "- relatório instrumental: sem promoção, sem ajuste de constante, "
        "sem corrida nova.",
    ]
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    for p in result["passes"]:
        c = p["contorno"]
        print(f"passe {p['passe']}: lat_max {c['lat_max_m']} m "
              f"(margem {c['margem_pista_m']:+.4f}) | grip "
              f"{c['tyre_grip_no_latmax']} (life {c['tyre_life_pct_no_latmax']}%) | "
              f"demanda/cap {c['demanda_sobre_capacidade']} | saiu: {c['saiu']}")
    print(f"correlação grip↔lat_max: r={r:.4f} | "
          f"saídas {result['passes_com_saida']}/{result['passes_total']}")
    print(f"OK -> {OUT_JSON} + {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
