#!/usr/bin/env python3
"""PROF-GRIP-1 (sequência) — validação FORA DA AMOSTRA do limiar de demanda
lateral e recálculo exato do custo de ritmo (forma fechada com downforce).
Report-only, determinístico, offline (zero corrida nova).

**Proveniência do limiar:** η = 0,615 foi calibrado EM AMOSTRA sobre
REF_INTERLAGOS_600S + CTRL_Interlagos_OFF + ON_Interlagos_N0
(``LATERAL_DEMAND_CALIBRATION``, SHA ``0175e662``-família). Este instrumento
testa o limiar CEGO nas realizações que NÃO participaram da calibração:
ON_Interlagos_N1..N4 (``--variedade 1..4`` — diversidade mecânica real).

**Teste cego** — para cada passagem pelas 4 crônicas (C01/C06/C07/C08) em
N1..N4, com a MESMA convenção da calibração (ápice = tick de |κ suavizada|
máxima na janela canônica):

    razao = (v_apex² · κ_inst(s_apex)) / PhysicsParams.a_lat(v_apex, grip_apex)
    predição = "LIMPA" se razao ≤ 0,615 senão "SAÍDA"

confrontada com o desfecho real (lat_max ≤ 6,0 m) → Matriz de Confusão
(positivo = SAÍDA) + acurácia, por crônica e global. Pergunta especial: as
passagens de C01 que ficaram LIMPAS em N1/N2 foram corretamente classificadas?

**Varredura das demais curvas:** para TODAS as curvas canônicas que não são
as 4 crônicas, o máximo de razão instantânea por tick sob o pacing histórico
(razão = v²·κ_inst/a_lat(v, grip)) nas N1..N4 — alguma já supera 0,615
(risco de saída nova)?

**Forma fechada exata com downforce** (η = 0,60 nas 4 janelas crônicas):

    c_m = c_downforce()/mass
    denom = κ_inst(s) − η·(1,8·grip)·c_m
    v_safe(s) = sqrt(η·(1,8·grip)·9,81 / denom)   se denom > 0; senão v_plan

    t_lap = ∫ ds / min(v_plan(s), v_safe(s))

para tyre_grip ∈ {0,807 (fim de vida REF), 0,842 (novo)}, contra a Guarda
123,05 s.

Saídas exclusivas (determinísticas, ``cmp=0`` entre execuções):
``experiments/prof-grip-1/OUT_OF_SAMPLE_VALIDATION.json`` e ``.md``.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND))

from model_train.velocity_profile import PhysicsParams  # noqa: E402
from model_train.velocity_profile import VelocityProfile  # noqa: E402
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

GRAVITY_MPS = 9.81

VERSION = "prof-grip-1/out-of-sample-validation-v1.0"

OOS_SOURCES = [
    ("ON_Interlagos_N1", BACKEND / "experiments" / "prof-grip-1" / "corridas" / "ON_Interlagos_N1.csv"),
    ("ON_Interlagos_N2", BACKEND / "experiments" / "prof-grip-1" / "corridas" / "ON_Interlagos_N2.csv"),
    ("ON_Interlagos_N3", BACKEND / "experiments" / "prof-grip-1" / "corridas" / "ON_Interlagos_N3.csv"),
    ("ON_Interlagos_N4", BACKEND / "experiments" / "prof-grip-1" / "corridas" / "ON_Interlagos_N4.csv"),
]
TRACK_FILE = BACKEND / "model_train" / "tracks_frozen" / "interlagos_v2.json"
TRACK_SHA_PIN = "164876196eb12174"

ETA_THRESHOLD = 0.615       # calibrado em amostra (LATERAL_DEMAND_CALIBRATION)
ETA_TARGET = 0.60           # alvo do mecanismo (forma fechada)
GRIPS_TLAP = [0.807, 0.842]
KRONICAS = ("C01", "C06", "C07", "C08")
HALF_WIDTH_M = 6.0
GUARDA_S = 123.05

OUT_JSON = BACKEND / "experiments" / "prof-grip-1" / "OUT_OF_SAMPLE_VALIDATION.json"
OUT_MD = BACKEND / "experiments" / "prof-grip-1" / "OUT_OF_SAMPLE_VALIDATION.md"


def closed_form_vsafe(kappa: float, grip: float, eta: float = ETA_TARGET,
                      c_m: Optional[float] = None) -> Optional[float]:
    """Forma fechada exata com downforce:

    denom = κ − η·(1,8·grip)·c_m; se denom > 0:
    v_safe = sqrt(η·(1,8·grip)·9,81 / denom); senão None (sem solução —
    o chamador mantém v_plan). Verificação: η·a_lat(v_safe, grip) = v_safe²·κ."""
    c_m_val = (PhysicsParams.c_downforce() / PhysicsParams.mass
               if c_m is None else float(c_m))
    eta_mu = float(eta) * (PhysicsParams.mu * float(grip))
    denom = float(kappa) - eta_mu * c_m_val
    if denom <= 0.0:
        return None
    value = math.sqrt(eta_mu * GRAVITY_MPS / denom)
    if not math.isfinite(value):
        raise ValueError("v_safe não finito")
    return value


def classify(razao: float, eta: float = ETA_THRESHOLD) -> str:
    """Predição cega pelo limiar calibrado."""
    return "LIMPA" if float(razao) <= eta else "SAÍDA"


def confusion(preds: List[str], actuals: List[str]) -> Dict[str, Any]:
    """Matriz de confusão com positivo = SAÍDA (o desfecho ruim)."""
    tp = sum(1 for p, a in zip(preds, actuals) if p == "SAÍDA" and a == "SAÍDA")
    fp = sum(1 for p, a in zip(preds, actuals) if p == "SAÍDA" and a == "LIMPA")
    tn = sum(1 for p, a in zip(preds, actuals) if p == "LIMPA" and a == "LIMPA")
    fn = sum(1 for p, a in zip(preds, actuals) if p == "LIMPA" and a == "SAÍDA")
    total = tp + fp + tn + fn
    return {
        "TP_saida_prev_e_real": tp, "FP_saida_prev_limpa_real": fp,
        "TN_limpa_prev_e_real": tn, "FN_limpa_prev_saida_real": fn,
        "acuracia": round((tp + tn) / total, 4) if total else None,
    }


def main() -> int:
    for _, path in OOS_SOURCES:
        if not path.exists():
            print(f"ERRO: telemetria OOS ausente: {path}", file=sys.stderr)
            return 2
    with TRACK_FILE.open("r", encoding="utf-8") as f:
        track = json.load(f)
    if track.get("sha256") != TRACK_SHA_PIN:
        print(f"ERRO: SHA da pista divergente: {track.get('sha256')}", file=sys.stderr)
        return 2
    wps = np.array(track["waypoints"], dtype=np.float64)
    closed = np.vstack([wps, wps[:1]])
    track_len = float(np.hypot(*np.diff(closed, axis=0).T).sum())

    corners = SV.build_corner_definitions(
        wps, kappa_thresh=0.006, merge_gap_m=40.0, generic_names=False)
    windows4: Dict[str, Tuple[float, float]] = {}
    outras: Dict[str, Tuple[float, float]] = {}
    for c in corners:
        if c["id"] in KRONICAS:
            windows4[c["id"]] = (float(c["s0"]), float(c["s1"]))
        else:
            outras[c["id"]] = (float(c["s0"]), float(c["s1"]))

    kappa_smooth_at = kappa_interp_fn(wps)
    from backend.model_train.prof_curva import _instantaneous_kappa_profile
    k_s, k_i = _instantaneous_kappa_profile(wps, ds_target=4.0)
    kappa_inst_at = (lambda s: float(np.interp(
        s % float(k_s[-1] + (k_s[1] - k_s[0])), k_s, np.abs(k_i))))

    c_m = PhysicsParams.c_downforce() / PhysicsParams.mass

    # ================= 1. teste cego do limiar (N1..N4) =================
    fontes: List[Dict[str, Any]] = []
    all_preds: List[str] = []
    all_actuals: List[str] = []
    per_corner_rows: Dict[str, List[Dict[str, Any]]] = {cid: [] for cid in KRONICAS}
    for label, path in OOS_SOURCES:
        df = pd.read_csv(path, comment="#")
        laps = segment_laps(df["s"].to_numpy(float), track_len)
        n_seg = int(laps.max()) + 1
        passes: List[Dict[str, Any]] = []
        for seg in range(n_seg):
            seg_rows = df[laps == seg]
            if len(seg_rows) == 0:
                continue
            for cid in KRONICAS:
                rows = seg_rows[
                    (seg_rows["s"] >= windows4[cid][0])
                    & (seg_rows["s"] <= windows4[cid][1])].sort_values("tick")
                if len(rows) == 0:
                    continue
                k_s_arr = np.array([abs(kappa_smooth_at(float(sv)))
                                    for sv in rows["s"].to_numpy(float)])
                i_apex = int(np.argmax(k_s_arr))
                v_apex = float(rows["speed"].iloc[i_apex])
                g_apex = float(rows["tyre_grip"].iloc[i_apex])
                k_inst_apex = abs(kappa_inst_at(float(rows["s"].iloc[i_apex])))
                razao = (v_apex ** 2 * k_inst_apex
                         / float(PhysicsParams.a_lat(v_apex, g_apex)))
                pred = classify(razao)
                lat_max = float(rows["lat"].max())
                actual = "LIMPA" if lat_max <= HALF_WIDTH_M else "SAÍDA"
                ps = {
                    "fonte": label, "segmento": seg + 1, "curva": cid,
                    "razao_inst_apex": round(razao, 4),
                    "predicao": pred, "desfecho_real": actual,
                    "lat_max_m": round(lat_max, 4),
                    "v_apex_kmh": round(v_apex * 3.6, 3),
                    "grip_apex": round(g_apex, 4),
                    "correto": pred == actual,
                }
                passes.append(ps)
                per_corner_rows[cid].append(ps)
        preds = [p["predicao"] for p in passes]
        actuals = [p["desfecho_real"] for p in passes]
        all_preds.extend(preds)
        all_actuals.extend(actuals)
        cm = confusion(preds, actuals)
        corretas_c01 = [p for p in passes
                        if p["curva"] == "C01" and p["desfecho_real"] == "LIMPA"
                        and p["correto"]]
        fontes.append({
            "fonte": label,
            "csv_sha256_prefix": sha256_file(path)[:16],
            "n_passes": len(passes),
            "confusao": cm,
            "c01_limpas_e_corretas": {
                "n_limpas_c01": len([p for p in passes
                                     if p["curva"] == "C01"
                                     and p["desfecho_real"] == "LIMPA"]),
                "n_corretamente_classificadas": len(corretas_c01),
            },
            "passes": passes,
        })

    cm_global = confusion(all_preds, all_actuals)
    per_corner_cm = {cid: confusion([p["predicao"] for p in rows],
                                    [p["desfecho_real"] for p in rows])
                     for cid, rows in per_corner_rows.items()}
    c01_limpas = [p for p in per_corner_rows["C01"]
                  if p["fonte"] in ("ON_Interlagos_N1", "ON_Interlagos_N2")
                  and p["desfecho_real"] == "LIMPA"]
    c01_limpas_ok = sum(1 for p in c01_limpas if p["correto"])

    # ================= 2. varredura das demais curvas =================
    varredura: List[Dict[str, Any]] = []
    for cid, w in sorted(outras.items()):
        max_razao = 0.0
        max_lat = 0.0
        n_exits = 0
        for _, path in OOS_SOURCES:
            df = pd.read_csv(path, comment="#")
            rows = df[(df["s"] >= w[0]) & (df["s"] <= w[1])]
            if len(rows) == 0:
                continue
            vv = rows["speed"].to_numpy(float)
            gg = rows["tyre_grip"].to_numpy(float)
            kk = np.array([abs(kappa_inst_at(float(sv)))
                           for sv in rows["s"].to_numpy(float)])
            razoes = np.array([
                (float(vv[i]) ** 2 * kk[i]) / float(PhysicsParams.a_lat(
                    float(vv[i]), float(gg[i]))) if float(vv[i]) > 0 else 0.0
                for i in range(len(rows))])
            max_razao = max(max_razao, float(razoes.max()))
            lm = float(rows["lat"].max())
            max_lat = max(max_lat, lm)
            n_exits += int((rows["lat"] > HALF_WIDTH_M).any())
        varredura.append({
            "curva": cid,
            "janela_m": [round(w[0], 3), round(w[1], 3)],
            "razao_inst_max_N1_N4": round(max_razao, 4),
            "risco_acima_0615": bool(max_razao > ETA_THRESHOLD),
            "lat_max_m_N1_N4": round(max_lat, 4),
            "n_fontes_com_saida": n_exits,
        })

    # ================= 3. t_lap forma fechada (η = 0,60) =================
    vp = VelocityProfile(wps, grip_mult=0.788, sf=0.80, ds_target=4.0,
                         smooth_window_m=20.0)
    s_arr = np.asarray(vp.s_arr, dtype=np.float64)
    v_base = np.asarray(vp.v_plan, dtype=np.float64)
    ds = float(s_arr[1] - s_arr[0])
    mask4 = np.zeros(len(s_arr), dtype=bool)
    for w in windows4.values():
        mask4 |= (s_arr >= w[0]) & (s_arr <= w[1])
    t_base = float(np.sum(ds / np.maximum(v_base, 0.5)))
    k_inst_grid = np.array([abs(kappa_inst_at(float(sv))) for sv in s_arr])
    tlap_rows = []
    for grip in GRIPS_TLAP:
        v = v_base.copy()
        for i in np.where(mask4)[0]:
            vs = closed_form_vsafe(k_inst_grid[i], grip, ETA_TARGET, c_m)
            if vs is not None:
                v[i] = min(v[i], vs)
        t = float(np.sum(ds / np.maximum(v, 0.5)))
        tlap_rows.append({
            "grip": grip,
            "eta": ETA_TARGET,
            "t_lap_piso_s": round(t, 3),
            "delta_vs_base_s": round(t - t_base, 3),
            "guarda_estoura": bool(t > GUARDA_S),
        })

    payload = {
        "schema_version": VERSION,
        "proveniencia": {
            "limiar_eta_calibrado_em_amostra": ETA_THRESHOLD,
            "calibrado_sobre": ["REF_INTERLAGOS_600S", "CTRL_Interlagos_OFF",
                                "ON_Interlagos_N0"],
            "oos_sobre": [label for label, _ in OOS_SOURCES],
            "pista_sha256_pin": TRACK_SHA_PIN,
            "comprimento_m": round(track_len, 3),
        },
        "metodo": {
            "razao": "v_apex²·κ_inst(s_apex)/a_lat(v_apex, grip_apex); ápice = "
                     "|κ suav| máx da janela (convenção da calibração)",
            "positivo_da_matriz": "SAÍDA (desfecho ruim)",
            "forma_fechada": "v_safe = sqrt(η·(1,8·grip)·9,81/(κ − η·(1,8·grip)·"
                             "c_m)) se denom > 0; c_m = "
                             f"{c_m:.8f}",
            "eta_target_tlap": ETA_TARGET,
            "grips_tlap": GRIPS_TLAP,
        },
        "teste_cego": {
            "global": cm_global,
            "por_crônica": per_corner_cm,
            "c01_limpas_N1_N2": {
                "n_limpas": len(c01_limpas),
                "n_corretamente_classificadas": c01_limpas_ok,
            },
            "fontes": fontes,
        },
        "varredura_outras_curvas": varredura,
        "t_lap_forma_fechada": {
            "piso_base_s": round(t_base, 3),
            "guarda_s": GUARDA_S,
            "cenario": tlap_rows,
        },
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
        "# OUT OF SAMPLE VALIDATION — limiar η=0,615 e forma fechada com downforce",
        "",
        f"**Data:** 2026-11-07 · **Método:** report-only sobre telemetria "
        f"existente (zero corrida nova) · **Instrumento:** "
        f"`scripts/prof_demand_out_of_sample.py` (determinístico, `cmp=0` ×2).",
        "",
        f"**Proveniência:** η=0,615 calibrado EM AMOSTRA (REF + CTRL_OFF + "
        f"ON_N0); teste cego sobre **ON N1..N4 (--variedade 1..4)** — "
        f"realizações fora da calibração.",
        "",
        "## Matriz de confusão global (positivo = SAÍDA)",
        "",
        "| | real SAÍDA | real LIMPA |",
        "|---|---:|---:|",
        f"| **prev SAÍDA** | TP {cm_global['TP_saida_prev_e_real']} | "
        f"FP {cm_global['FP_saida_prev_limpa_real']} |",
        f"| **prev LIMPA** | FN {cm_global['FN_limpa_prev_saida_real']} | "
        f"TN {cm_global['TN_limpa_prev_e_real']} |",
        "",
        f"**Acurácia de separação: {cm_global['acuracia']}** sobre "
        f"{len(all_preds)} passes fora da amostra.",
        "",
        "**Pergunta especial — C01 em N1/N2:** as passagens que ficaram LIMPAS "
        f"foram corretamente classificadas? "
        f"**{c01_limpas_ok}/{len(c01_limpas)}** ✓." if c01_limpas else
        f"**{c01_limpas_ok}/{len(c01_limpas)}**.",
        "",
        "## Matriz por crônica",
        "",
        "| crônica | TP | FP | TN | FN | acurácia |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cid, cm in per_corner_cm.items():
        linhas.append(
            f"| {cid} | {cm['TP_saida_prev_e_real']} | "
            f"{cm['FP_saida_prev_limpa_real']} | {cm['TN_limpa_prev_e_real']} | "
            f"{cm['FN_limpa_prev_saida_real']} | {cm['acuracia']} |")

    linhas += [
        "",
        "## Varredura das demais curvas (máx razão inst nas N1..N4)",
        "",
        "| curva | janela (m) | razão máx | risco > 0,615? | lat máx | "
        "fontes c/ saída |",
        "|---|---|---:|---|---:|---:|",
    ]
    for row in varredura:
        linhas.append(
            f"| {row['curva']} | {row['janela_m'][0]}–{row['janela_m'][1]} | "
            f"{row['razao_inst_max_N1_N4']} | "
            f"{'SIM' if row['risco_acima_0615'] else 'não'} | "
            f"{row['lat_max_m_N1_N4']} | {row['n_fontes_com_saida']}/4 |")

    linhas += [
        "",
        "## t_lap forma fechada (η = 0,60, janelas das 4 crônicas)",
        "",
        f"Piso base (v_plan histórico): **{round(t_base, 3)} s** · Guarda: "
        f"**{GUARDA_S} s** · c_m = {c_m:.8f} 1/m.",
        "",
        "| tyre_grip | t_lap piso (s) | Δ vs base | guarda? |",
        "|---:|---:|---:|---|",
    ]
    for row in tlap_rows:
        linhas.append(
            f"| {row['grip']} | {row['t_lap_piso_s']} | "
            f"{row['delta_vs_base_s']:+.3f} | "
            f"{'ESTOURA' if row['guarda_estoura'] else 'cabe'} |")

    linhas += [
        "",
        "## Leitura (report-only; veredito é do Dono)",
        "",
        "- a acurácia global é o teste do limiar fora da amostra; FN é o erro "
        "caro (prev LIMPA, saiu);",
        "- a varredura mostra se o alvo η=0,60 cria risco de saída nova nas "
        "demais curvas sob o pacing histórico;",
        "- o t_lap de forma fechada usa a capacidade REAL (downforce) — "
        "substitui as estimativas com μ_eff·g ≈ 8 m/s².",
    ]
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    print(f"matriz global: TP {cm_global['TP_saida_prev_e_real']} | "
          f"FP {cm_global['FP_saida_prev_limpa_real']} | "
          f"TN {cm_global['TN_limpa_prev_e_real']} | "
          f"FN {cm_global['FN_limpa_prev_saida_real']} | "
          f"acurácia {cm_global['acuracia']}")
    print(f"C01 N1/N2 limpas corretamente classificadas: "
          f"{c01_limpas_ok}/{len(c01_limpas)}")
    risco = [r["curva"] for r in varredura if r["risco_acima_0615"]]
    print(f"demais curvas com razão > 0,615: {risco or 'nenhuma'}")
    for row in tlap_rows:
        print(f"t_lap grip {row['grip']} (η={ETA_TARGET}): "
              f"{row['t_lap_piso_s']} s (Δ{row['delta_vs_base_s']:+.3f}, guarda "
              f"{'ESTOURA' if row['guarda_estoura'] else 'cabe'})")
    print(f"OK -> {OUT_JSON} + {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
