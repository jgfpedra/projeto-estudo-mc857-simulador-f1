#!/usr/bin/env python3
"""PROF-GRIP-1 (sequência) — viabilidade do gatilho preditivo e autoridade
de frenagem (REVISÃO Kamm). Report-only, determinístico, offline.

REVISÃO metodológica (Correção do Dono sobre a v1.0):

1. **Excursões encadeadas agrupam-se**: um evento é o cruzamento de
   |lat| > 6,0 m; se entre dois cruzamentos o carro NÃO retornou para
   |lat| < 3,0 m, são UMA excursão (cascata — ex.: excursões 4/9/14/19 da
   Junção eram re-saídas da mesma excursão).
2. **Janela de gatilho = aproximação da própria curva**: arco de no máximo
   150 m antes do ápice (com wrap) até t_exit. Se o carro já entra na
   janela com |lat| ≥ limiar → classe explícita ``JÁ-FORA/CASCATA``.
3. **v_safe dupla convenção no ápice**: instantânea (κ da geometria frozen
   sem suavização; Junção R≈7,93 m → ≈28,5 km/h) e suavizada (perfil
   canônico 30 m; R≈13,5 m → ≈37 km/h), com o grip mínimo observado na
   janela da crônica.
4. **Autoridade pelo Círculo de Kamm**: no instante do gatilho,
   ``a_brake_rem = sqrt(max(0, (tyre_grip·9,81)² − a_lat(t_trigger)²))`` —
   a frenagem longitudinal que SOBRA após a demanda lateral; a autoridade
   compara ``a_brake_rem·Δt_aviso`` contra ``Δv_req`` (nas duas convenções
   de v_safe). No ápice a demanda consome ~100% da aderência: frear lá não
   desacelera — a autoridade física pertence ao pacing de entrada.
5. **Custo de ritmo integrado:** ``t_lap = ∫ ds / min(v_plan(s),
   v_safe(s))`` com v_safe por convenção × grip {0,842 (novo), 0,807 (fim
   de vida REF)} nas janelas das 4 crônicas, contra a Guarda 123,05 s.

Saídas exclusivas (determinísticas, ``cmp=0`` entre execuções):
``experiments/prof-grip-1/WARNING_TIME_FEASIBILITY.json`` e ``.md``.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND))

from scripts import saidas_verdict as SV  # noqa: E402
from scripts.prof_lago_anatomy import (  # noqa: E402  canônicos
    kappa_interp_fn,
    segment_laps,
    sha256_file,
)
from scripts.prof_lat_threshold_audit import (  # noqa: E402
    contiguous_events,
    sector_of,
)
from model_train.velocity_profile import VelocityProfile  # noqa: E402

VERSION = "prof-grip-1/warning-time-feasibility-v2.0-kamm"

REF_CSV = BACKEND / "experiments" / "prof-grip-1" / "corridas" / "CTRL_Interlagos_OFF.csv"
REF_SHA256 = "c00391ab21033dae1a03db2cd7f7fd6983baa47d67b0828bec503d93778e9b3a"
TRACK_FILE = BACKEND / "model_train" / "tracks_frozen" / "interlagos_v2.json"
TRACK_SHA_PIN = "164876196eb12174"

HORIZONS_S = [0.0, 0.4, 0.8, 1.2]
LAT_LIMS_M = [3.5, 4.0]
APPROACH_WINDOW_M = 150.0   # arco máximo antes do ápice (busca do gatilho)
RETURN_THRESHOLD_M = 3.0    # retorno < 3,0 m separa excursões encadeadas
HALF_WIDTH_M = 6.0
GRAVITY = 9.81
KRONICAS = ("C01", "C06", "C07", "C08")
GUARDA_S = 123.05
GRIPS_TLAP = [0.842, 0.807]  # pneu novo / fim de vida (REF)

OUT_JSON = BACKEND / "experiments" / "prof-grip-1" / "WARNING_TIME_FEASIBILITY.json"
OUT_MD = BACKEND / "experiments" / "prof-grip-1" / "WARNING_TIME_FEASIBILITY.md"


def v_lat_series(lat: np.ndarray, t: np.ndarray) -> np.ndarray:
    """v_lat = d(|lat|)/dt por diferença central (numpy.gradient, 5 Hz)."""
    return np.asarray(np.gradient(lat, t), dtype=float)


def lat_pred_series(lat: np.ndarray, v_lat: np.ndarray, horizon: float) -> np.ndarray:
    """lat_pred(t) = |lat(t)| + |v_lat(t)|·T."""
    return np.abs(lat) + np.abs(v_lat) * float(horizon)


def v_safe(kappa: float, grip: float) -> float:
    """v_safe = sqrt(max(0,1, grip·9,81) / max(1e-4, κ)) — resposta exata."""
    kappa_eff = max(1e-4, float(kappa))
    a_lat_cap = max(0.1, float(grip) * GRAVITY)
    return math.sqrt(a_lat_cap / kappa_eff)


def kamm_brake_rem(grip: float, a_lat: float) -> float:
    """Frenagem longitudinal remanescente pelo Círculo de Kamm:
    sqrt(max(0, (grip·9,81)² − a_lat²))."""
    cap = float(grip) * GRAVITY
    return math.sqrt(max(0.0, cap * cap - float(a_lat) ** 2))


def lap_time_of(v_plan: np.ndarray, ds: float) -> float:
    """t_lap = Σ ds / max(v, 0,5) sobre o laço fechado."""
    v = np.maximum(np.asarray(v_plan, dtype=np.float64), 0.5)
    return float(np.sum(ds / v))


def integrate_vsafe_lap(v_base: np.ndarray, s_arr: np.ndarray, mask: np.ndarray,
                        kappa_fn, grip: float) -> float:
    """t_lap com v_safe(s) = sqrt(max(0,1, grip·9,81)/max(1e-4, κ(s))) como
    teto dentro da máscara (janelas das 4 crônicas); fora, v_plan intacto."""
    v = np.asarray(v_base, dtype=np.float64).copy()
    v_safe_grid = np.array([v_safe(kappa_fn(float(sv)), grip) for sv in s_arr])
    v[mask] = np.minimum(v[mask], v_safe_grid[mask])
    return lap_time_of(v, float(s_arr[1] - s_arr[0]))


def group_excursions(events: Sequence[Tuple[int, int]],
                     lat: np.ndarray,
                     return_threshold: float = RETURN_THRESHOLD_M
                     ) -> Tuple[List[Tuple[int, int]], int]:
    """Agrupa cruzamentos encadeados: se entre dois cruzamentos de 6,0 m o
    carro NÃO retornou a |lat| < return_threshold, é a mesma excursão.
    Retorna (excursões agrupadas, nº de cascatas absorvidas)."""
    grouped: List[Tuple[int, int]] = []
    cascades = 0
    for (a, b) in events:
        if grouped:
            pa, pb = grouped[-1]
            lo, hi = pb + 1, a - 1
            if hi >= lo and float(np.min(lat[lo:hi + 1])) >= return_threshold:
                grouped[-1] = (pa, b)
                cascades += 1
                continue
        grouped.append((a, b))
    return grouped, cascades


def approach_window_indices(s: np.ndarray, i_exit: int, s_apex: float,
                            track_len: float,
                            max_back: float = APPROACH_WINDOW_M) -> List[int]:
    """Ticks da aproximação: arco de no máximo max_back m antes do ápice
    (com wrap) até t_exit, contíguo ao walking-back a partir de i_exit."""
    idxs: List[int] = []
    i = i_exit
    while i >= 0:
        dist = (float(s_apex) - float(s[i])) % track_len
        if dist <= max_back:
            idxs.append(i)
            i -= 1
        else:
            break
    return list(reversed(idxs))


def analyze_events(df: pd.DataFrame, kappa_smooth_at, kappa_inst_at,
                   corners: Sequence[Dict[str, Any]], track_len: float,
                   windows4: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
    lat = df["lat"].to_numpy(float)
    t = df["t_s"].to_numpy(float)
    s = df["s"].to_numpy(float)
    v = df["speed"].to_numpy(float)
    grip = df["tyre_grip"].to_numpy(float)

    v_lat = v_lat_series(lat, t)
    raw_events = contiguous_events(lat > HALF_WIDTH_M)
    grouped, cascades = group_excursions(raw_events, lat)

    excursions: List[Dict[str, Any]] = []
    per_corner: Dict[str, Dict[str, Any]] = {
        cid: {"n_excursions": 0, "n_ja_fora": 0, "n_sem_gatilho": 0,
              "n_com_gatilho": 0, "dt_real_s": [], "a_brake_rem_ms2": []}
        for cid in KRONICAS}

    for (a, b) in grouped:
        i_exit = a
        i_latmax = a + int(np.argmax(lat[a:b + 1]))
        s_apex = float(s[i_latmax])
        win4 = next((cid for cid, w in windows4.items()
                     if w[0] <= s_apex <= w[1]), None)
        if win4 is None:
            win4 = sector_of(s_apex, corners, track_len)
        exc: Dict[str, Any] = {
            "i_exit": i_exit,
            "t_exit_s": round(float(t[i_exit]), 3),
            "dur_s": round(float(t[b] - t[a]) + 0.2, 3),
            "lat_max_m": round(float(lat[a:b + 1].max()), 4),
            "s_apex_m": round(s_apex, 3),
            "curva": win4,
            "ticks_acima_6m": int(np.sum(lat[a:b + 1] > HALF_WIDTH_M)),
            "por_config": {},
        }
        widx = approach_window_indices(s, i_exit, s_apex, track_len)
        exc["n_ticks_janela_aprox"] = len(widx)
        for T in HORIZONS_S:
            pred = lat_pred_series(lat, v_lat, T)
            for lim in LAT_LIMS_M:
                cfg: Dict[str, Any] = {}
                if not widx:
                    cfg["classe"] = "SEM-JANELA"
                elif float(lat[widx[0]]) >= lim:
                    cfg["classe"] = "JÁ-FORA/CASCATA"
                else:
                    trig = next((i for i in widx if pred[i] >= lim), None)
                    if trig is None:
                        cfg["classe"] = "SEM-GATILHO"
                    else:
                        cfg["classe"] = "GATILHO"
                        dt_w = round(max(0.0, float(t[i_exit] - t[trig])), 3)
                        v_trig = float(v[trig])
                        g_trig = float(grip[trig])
                        a_lat_trig = v_trig * v_trig * abs(kappa_smooth_at(
                            float(s[trig])))
                        a_rem = kamm_brake_rem(g_trig, a_lat_trig)
                        vs_smooth = v_safe(kappa_smooth_at(s_apex), g_trig)
                        vs_inst = v_safe(kappa_inst_at(s_apex), g_trig)
                        cfg.update({
                            "t_trigger_s": round(float(t[trig]), 3),
                            "delta_t_aviso_s": dt_w,
                            "v_trigger_mps": round(v_trig, 3),
                            "v_trigger_kmh": round(v_trig * 3.6, 3),
                            "grip_trigger": round(g_trig, 4),
                            "a_lat_demanda_ms2": round(a_lat_trig, 3),
                            "a_brake_rem_ms2": round(a_rem, 3),
                            "v_safe_suavizada_kmh": round(vs_smooth * 3.6, 3),
                            "v_safe_instantanea_kmh": round(vs_inst * 3.6, 3),
                            "delta_v_req_inst_mps": round(max(0.0, v_trig - vs_inst), 3),
                            "delta_v_req_smooth_mps": round(max(0.0, v_trig - vs_smooth), 3),
                        })
                        cfg["autoridade_kamm_inst"] = (
                            "APROVADO" if a_rem * dt_w >=
                            cfg["delta_v_req_inst_mps"] else "INSUFICIENTE")
                        cfg["autoridade_kamm_smooth"] = (
                            "APROVADO" if a_rem * dt_w >=
                            cfg["delta_v_req_smooth_mps"] else "INSUFICIENTE")
                exc["por_config"][f"T{T}_lim{lim}"] = cfg
        excursions.append(exc)
        if win4 in per_corner:
            per_corner[win4]["n_excursions"] += 1

    # grip mínimo observado dentro de cada janela de crônica (fonte p/ v_safe)
    for cid, w in windows4.items():
        mask = (s >= w[0]) & (s <= w[1])
        per_corner[cid]["grip_min_janela"] = (round(float(np.min(grip[mask])), 4)
                                              if mask.any() else None)

    # consolida por crônica (sobre as excursões atribuídas)
    for exc in excursions:
        cid = exc["curva"]
        if cid not in per_corner:
            continue
        pc = per_corner[cid]
        for cfg in exc["por_config"].values():
            if cfg.get("classe") == "JÁ-FORA/CASCATA":
                pc["n_ja_fora"] += 1
            elif cfg.get("classe") == "SEM-GATILHO":
                pc["n_sem_gatilho"] += 1
            elif cfg.get("classe") == "GATILHO":
                pc["n_com_gatilho"] += 1
                pc["dt_real_s"].append(cfg["delta_t_aviso_s"])
                pc["a_brake_rem_ms2"].append(cfg["a_brake_rem_ms2"])

    for cid, pc in per_corner.items():
        pc["dt_real_medio_s"] = (round(float(np.mean(pc["dt_real_s"])), 3)
                                 if pc["dt_real_s"] else None)
        pc["dt_real_min_s"] = (round(float(np.min(pc["dt_real_s"])), 3)
                               if pc["dt_real_s"] else None)
        pc["a_brake_rem_min_ms2"] = (round(float(np.min(pc["a_brake_rem_ms2"])), 3)
                                     if pc["a_brake_rem_ms2"] else None)

    # agregados por (T, lim) sobre excursões com GATILHO real
    agreg = {}
    for T in HORIZONS_S:
        for lim in LAT_LIMS_M:
            key = f"T{T}_lim{lim}"
            classes = [e["por_config"][key]["classe"] for e in excursions]
            dts = [e["por_config"][key]["delta_t_aviso_s"] for e in excursions
                   if e["por_config"][key]["classe"] == "GATILHO"]
            agreg[key] = {
                "n_excursions": len(excursions),
                "n_gatilho": len(dts),
                "n_ja_fora": classes.count("JÁ-FORA/CASCATA"),
                "n_sem_gatilho": classes.count("SEM-GATILHO"),
                "delta_t_medio_s": round(float(np.mean(dts)), 3) if dts else None,
                "delta_t_min_s": round(float(np.min(dts)), 3) if dts else None,
                "aprovado_kamm_inst": sum(
                    1 for e in excursions
                    if e["por_config"][key].get("autoridade_kamm_inst") == "APROVADO"),
                "aprovado_kamm_smooth": sum(
                    1 for e in excursions
                    if e["por_config"][key].get("autoridade_kamm_smooth") == "APROVADO"),
            }
    return {
        "n_cruzamentos_raw": len(raw_events),
        "n_excursions": len(grouped),
        "n_cascatas_absorvidas": cascades,
        "excursions": excursions,
        "per_corner": per_corner,
        "agregados_por_config": agreg,
    }


def main() -> int:
    if not REF_CSV.exists():
        print(f"ERRO: telemetria ausente: {REF_CSV}", file=sys.stderr)
        return 2
    ref_sha = sha256_file(REF_CSV)
    if ref_sha != REF_SHA256:
        print(f"ERRO: SHA da telemetria divergente: {ref_sha}", file=sys.stderr)
        return 2
    with TRACK_FILE.open("r", encoding="utf-8") as f:
        track = json.load(f)
    if track.get("sha256") != TRACK_SHA_PIN:
        print(f"ERRO: SHA da pista divergente: {track.get('sha256')}", file=sys.stderr)
        return 2
    wps = np.array(track["waypoints"], dtype=np.float64)
    closed = np.vstack([wps, wps[:1]])
    track_len = float(np.hypot(*np.diff(closed, axis=0).T).sum())

    kappa_smooth_at = kappa_interp_fn(wps)
    from backend.model_train.prof_curva import _instantaneous_kappa_profile
    k_s, k_inst = _instantaneous_kappa_profile(wps, ds_target=4.0)
    kappa_inst_at = (lambda s: float(np.interp(
        s % float(k_s[-1] + (k_s[1] - k_s[0])), k_s, np.abs(k_inst))))

    corners = SV.build_corner_definitions(
        wps, kappa_thresh=0.006, merge_gap_m=40.0, generic_names=False)
    windows4 = {}
    for cid in KRONICAS:
        c = next((c for c in corners if c["id"] == cid), None)
        if c is None:
            print(f"ERRO: {cid} ausente na definição canônica", file=sys.stderr)
            return 2
        windows4[cid] = (float(c["s0"]), float(c["s1"]))

    df = pd.read_csv(REF_CSV, comment="#")
    n_laps = int(segment_laps(df["s"].to_numpy(float), track_len).max() + 1)

    result = analyze_events(df, kappa_smooth_at, kappa_inst_at, corners,
                            track_len, windows4)

    # ---- custo de ritmo integrado (v_safe nas janelas das 4 crônicas) ----
    vp = VelocityProfile(wps, grip_mult=0.788, sf=0.80, ds_target=4.0,
                         smooth_window_m=20.0)
    s_arr = np.asarray(vp.s_arr, dtype=np.float64)
    v_base = np.asarray(vp.v_plan, dtype=np.float64)
    ds = float(s_arr[1] - s_arr[0])
    mask4 = np.zeros(len(s_arr), dtype=bool)
    for w in windows4.values():
        mask4 |= (s_arr >= w[0]) & (s_arr <= w[1])
    t_lap_base = lap_time_of(v_base, ds)
    tlap_rows = []
    for conv_label, kappa_fn in (("suavizada", kappa_smooth_at),
                                 ("instantanea", kappa_inst_at)):
        for grip in GRIPS_TLAP:
            t = integrate_vsafe_lap(v_base, s_arr, mask4, kappa_fn, grip)
            tlap_rows.append({
                "convencao": conv_label, "grip": grip,
                "t_lap_piso_s": round(t, 3),
                "delta_vs_base_s": round(t - t_lap_base, 3),
                "guarda_estoura": bool(t > GUARDA_S),
            })
    result["custo_ritmo_integrado"] = {
        "piso_base_s": round(t_lap_base, 3),
        "guarda_s": GUARDA_S,
        "cenario": tlap_rows,
        "nota": "v_safe(s) = sqrt(max(0,1, grip·9,81)/max(1e-4, κ(s))) "
                "aplicado nas janelas das 4 crônicas; piso sem frenagens a "
                "montante (limite inferior do lap corrido)",
    }

    payload = {
        "schema_version": VERSION,
        "origem": {
            "csv": str(REF_CSV.relative_to(BACKEND)),
            "csv_sha256_prefix": ref_sha[:16],
            "n_linhas_dados": int(len(df)),
            "n_laps": n_laps,
        },
        "pista": {"sha256_pin": TRACK_SHA_PIN, "comprimento_m": round(track_len, 3)},
        "metodo": {
            "v_lat": "d(|lat|)/dt por diferença central (5 Hz)",
            "lat_pred": "|lat| + |v_lat|·T",
            "janela_de_busca": f"arco ≤ {APPROACH_WINDOW_M} m antes do ápice "
                               "(com wrap) até t_exit; entrada já ≥ limiar = "
                               "JÁ-FORA/CASCATA",
            "agrupamento": f"cruzamentos de 6,0 m encadeados (retorno nunca "
                           f"< {RETURN_THRESHOLD_M} m) = UMA excursão",
            "kamm": "a_brake_rem = sqrt(max(0, (tyre_grip·9,81)² − a_lat²)) "
                    "com a_lat = v²·κ(s_trigger) suavizada",
            "v_safe": "dupla convenção no ápice: instantânea (κ frozen sem "
                      "suavização) e suavizada (30 m); grip = mínimo "
                      "observado na janela da crônica",
            "horizontes_s": HORIZONS_S,
            "limiares_m": LAT_LIMS_M,
        },
        **result,
    }

    for out in (OUT_JSON, OUT_MD):
        if out.exists():
            print(f"ERRO: saída já existe (escrita exclusiva): {out}", file=sys.stderr)
            return 3
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    linhas = [
        "# WARNING TIME FEASIBILITY (v2 Kamm) — gatilho preditivo, autoridade e t_lap",
        "",
        f"**Data:** 2026-11-07 · **Método:** report-only (zero corrida nova) · "
        f"**Instrumento:** `scripts/prof_warning_time_feasibility.py` "
        f"(determinístico, `cmp=0` ×2) · **Fonte:** `CTRL_Interlagos_OFF.csv` "
        f"(SHA `c00391ab…`).",
        "",
        f"**Agrupamento:** {result['n_cruzamentos_raw']} cruzamentos brutos de "
        f"6,0 m → **{result['n_excursions']} excursões** após agrupar "
        f"encadeadas ({result['n_cascatas_absorvidas']} cascatas absorvidas — "
        f"retorno nunca < {RETURN_THRESHOLD_M} m).",
        "",
        "## Tabela por crônica (excursões atribuídas ao ápice)",
        "",
        "| crônica | excursões | gatilho real | já-fora/cascata | sem gatilho | "
        "Δt aviso médio (s) | Δt aviso mín (s) | a_brake_rem mín (m/s²) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cid in KRONICAS:
        pc = result["per_corner"][cid]
        linhas.append(
            f"| {cid} | {pc['n_excursions']} | {pc['n_com_gatilho']} | "
            f"{pc['n_ja_fora']} | {pc['n_sem_gatilho']} | "
            f"{pc['dt_real_medio_s']} | {pc['dt_real_min_s']} | "
            f"{pc['a_brake_rem_min_ms2']} |")
    outras = result["n_excursions"] - sum(result["per_corner"][c]["n_excursions"]
                                          for c in KRONICAS)
    linhas.append(f"| outras/reta | {outras} | — | — | — | — | — | — |")

    linhas += [
        "",
        "## v_safe no ápice por crônica (dupla convenção, grip mín da janela)",
        "",
        "| crônica | grip | R instantâneo (m) | v_safe inst (km/h) | "
        "R suavizado (m) | v_safe suav (km/h) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cid in KRONICAS:
        w = windows4[cid]
        g = result["per_corner"][cid]["grip_min_janela"] or 0.807
        s_apex, best = None, -1.0
        for i in range(len(s_arr)):
            if w[0] <= s_arr[i] <= w[1] and abs(kappa_smooth_at(float(s_arr[i]))) > best:
                best = abs(kappa_smooth_at(float(s_arr[i])))
                s_apex = float(s_arr[i])
        k_s_apex = abs(kappa_smooth_at(s_apex)) if s_apex is not None else None
        k_i_apex = abs(kappa_inst_at(s_apex)) if s_apex is not None else None
        r_i = 1.0 / k_i_apex if k_i_apex else None
        r_s = 1.0 / k_s_apex if k_s_apex else None
        vi = v_safe(k_i_apex, g) * 3.6 if k_i_apex else None
        vv = v_safe(k_s_apex, g) * 3.6 if k_s_apex else None
        linhas.append(
            f"| {cid} | {g} | {round(r_i, 2) if r_i else '—'} | "
            f"{round(vi, 1) if vi else '—'} | {round(r_s, 2) if r_s else '—'} | "
            f"{round(vv, 1) if vv else '—'} |")

    linhas += [
        "",
        "## Agregados por configuração (T, limiar) — excursões com GATILHO real",
        "",
        "| config | gatilho | já-fora | sem gatilho | Δt médio (s) | Δt mín (s) | "
        "Kamm APROVADO (inst) | Kamm APROVADO (suav) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, a in result["agregados_por_config"].items():
        linhas.append(
            f"| {key} | {a['n_gatilho']} | {a['n_ja_fora']} | "
            f"{a['n_sem_gatilho']} | {a['delta_t_medio_s']} | "
            f"{a['delta_t_min_s']} | {a['aprovado_kamm_inst']} | "
            f"{a['aprovado_kamm_smooth']} |")

    linhas += [
        "",
        "## Custo de ritmo integrado (v_safe nas janelas das 4 crônicas)",
        "",
        f"Piso base (v_plan histórico): **{round(t_lap_base, 3)} s** · Guarda: "
        f"**{GUARDA_S} s**.",
        "",
        "| convenção | grip | t_lap piso (s) | Δ vs base | guarda? |",
        "|---|---:|---:|---:|---|",
    ]
    for row in tlap_rows:
        linhas.append(
            f"| {row['convencao']} | {row['grip']} | {row['t_lap_piso_s']} | "
            f"{row['delta_vs_base_s']:+.3f} | "
            f"{'ESTOURA' if row['guarda_estoura'] else 'cabe'} |")

    linhas += [
        "",
        "## Leitura (report-only; veredito é do Dono)",
        "",
        "- excursões encadeadas agrupam-se (cascata); os Δt de aviso são "
        "medidos DENTRO da janela de aproximação da própria crônica "
        "(≤ 150 m de arco antes do ápice); entradas já ≥ limiar são "
        "JÁ-FORA/CASCATA;",
        "- a autoridade usa o Círculo de Kamm: no ápice a demanda lateral "
        "consome a aderência e a frenagem remanescente ≈ 0 — a autoridade "
        "física pertence ao pacing de entrada;",
        "- o custo de ritmo integrado quantifica o piso da intervenção "
        "preventiva (v_safe no ápice) contra a Guarda.",
    ]
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    print(f"cruzamentos brutos {result['n_cruzamentos_raw']} → excursões "
          f"{result['n_excursions']} ({result['n_cascatas_absorvidas']} cascatas)")
    for cid in KRONICAS:
        pc = result["per_corner"][cid]
        print(f"{cid}: exc {pc['n_excursions']} | gatilho {pc['n_com_gatilho']} | "
              f"já-fora {pc['n_ja_fora']} | Δt méd {pc['dt_real_medio_s']} s | "
              f"Δt mín {pc['dt_real_min_s']} s | a_rem mín "
              f"{pc['a_brake_rem_min_ms2']}")
    for key, a in result["agregados_por_config"].items():
        print(f"{key}: gatilho {a['n_gatilho']} | já-fora {a['n_ja_fora']} | "
              f"Δt méd {a['delta_t_medio_s']} | Δt mín {a['delta_t_min_s']} | "
              f"Kamm APROV inst/suav {a['aprovado_kamm_inst']}/{a['aprovado_kamm_smooth']}")
    for row in tlap_rows:
        print(f"t_lap [{row['convencao']} grip {row['grip']}]: "
              f"{row['t_lap_piso_s']} s (Δ{row['delta_vs_base_s']:+.3f}, guarda "
              f"{'ESTOURA' if row['guarda_estoura'] else 'cabe'})")
    print(f"OK -> {OUT_JSON} + {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
