#!/usr/bin/env python3
"""PROF-GRIP-1 (sequência) — preparação offline do próximo ciclo de
mecanismo: escada fixa de η, perfil longitudinal completo e diagnóstico
descritivo. Report-only, determinístico, offline (zero corrida/PyBullet).

**Correção metodológica do Dono (obrigatória):** NÃO derivar η por
regressão de ``lat_max`` contra razão — ``lat_max`` é variável censurada e
descontínua (grama, rejoin, dinâmica longitudinal pós-saída); excursões de
até 39,7 m não estimam fronteira de segurança. Nenhum η < ~0,55 é
"identificado pelos dados" — essa faixa é extrapolação.

**Escada fixa de η (constantes de engenharia pré-declaradas, não
estimativas):**

    η1 = 0,8 × 0,6106 = 0,48848   (0,8 × a maior razão LIMPA da calibração)
    η2 = 0,40000

Regra de execução: iniciar com η1; se o estágio falhar nos gates,
executar o estágio previamente definido com η2; não criar valores novos
depois de observar resultados; não escolher entre η1/η2 pós-saídas.

**Aplicação do cap (ordem congelada):**

    v_ctrl  = 0,93 · v_plan                    # alvo histórico
    v_seed  = min(v_ctrl, v_safe(s))           # cap depois do 0,93,
                                               # antes das passadas
    v_target_cap = passadas backward/forward   # mesmo algoritmo de
                                               # prof_curva.py (Passo 2 +
                                               # fecho circular + Passo 3),
                                               # sobre v_seed

``v_safe(s)`` pela forma fechada exata com downforce, SOMENTE dentro das
janelas canônicas das 4 crônicas (fora: passthrough):

    c_m    = c_downforce()/mass
    A      = (1,8 · grip) · 9,81
    denom  = kappa_inst(s) − η · (1,8 · grip) · c_m
    v_safe = sqrt(η · A / denom)   se denom > 0; senão v_plan(s)

**Diagnóstico descritivo** (ON_N1..N4 SOMENTE para descrever): razão no
ápice, lat_max, LIMPA/SAÍDA, maior razão entre passagens LIMPAS,
distribuição por crônica. Ajuste opcional de lat_max × razão SOMENTE nas
passagens LIMPAS de C01 — rotulado: "diagnóstico indicativo, n pequeno,
uma única crônica, sem poder de derivar ou validar η" — não usado para
escolher η.

**Gates pré-declarados para o ciclo ON** (nada pode ser alterado após
observar resultados): ver §Gates do relatório.

Saídas exclusivas (determinísticas, ``cmp=0`` entre execuções):
``experiments/prof-grip-1/PACE_MARGIN_DERIVATION.json`` e ``.md``.
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
)
from scripts.prof_demand_out_of_sample import (  # noqa: E402  forma fechada
    closed_form_vsafe,
)

VERSION = "prof-grip-1/pace-margin-derivation-v2.0-horizonte"

REF_CSV = BACKEND / "experiments" / "prof-curva-1" / "REF_INTERLAGOS_600S.csv"
REF_SHA256 = "c00391ab21033dae1a03db2cd7f7fd6983baa47d67b0828bec503d93778e9b3a"
CTRL_CSV = BACKEND / "experiments" / "prof-grip-1" / "corridas" / "CTRL_Interlagos_OFF.csv"
ON_SOURCES = [
    ("ON_N1", BACKEND / "experiments" / "prof-grip-1" / "corridas" / "ON_Interlagos_N1.csv"),
    ("ON_N2", BACKEND / "experiments" / "prof-grip-1" / "corridas" / "ON_Interlagos_N2.csv"),
    ("ON_N3", BACKEND / "experiments" / "prof-grip-1" / "corridas" / "ON_Interlagos_N3.csv"),
    ("ON_N4", BACKEND / "experiments" / "prof-grip-1" / "corridas" / "ON_Interlagos_N4.csv"),
]
TRACK_FILE = BACKEND / "model_train" / "tracks_frozen" / "interlagos_v2.json"
TRACK_SHA_PIN = "164876196eb12174"

KRONICAS = ("C01", "C06", "C07", "C08")
HALF_WIDTH_M = 6.0
MARGIN_CONTROLLER = 0.93
GRAVITY_MPS = 9.81

# ---- ESCADA FIXA DE η (constantes de engenharia pré-declaradas) ----
MAX_RAZAO_LIMPA_CALIBRACAO = 0.6106   # maior razão LIMPA da calibração em amostra
ETA1 = 0.8 * MAX_RAZAO_LIMPA_CALIBRACAO   # 0,48848 (precisão completa)
ETA2 = 0.40000
ESCADA_ETA: Sequence[Tuple[str, float]] = [("eta1", ETA1), ("eta2", ETA2)]
# ---- fim da escada: NÃO derivada de regressão, não alterada pós-resultados ----

GRIPS = [0.807, 0.842]
GUARDA_S = 123.05
SF_PERFIL = 0.80           # sf canônico das passadas (wiring do professor)
DIAG_LABEL = ("diagnóstico indicativo, n pequeno, uma única crônica, "
              "sem poder de derivar ou validar η")

OUT_JSON = BACKEND / "experiments" / "prof-grip-1" / "PACE_MARGIN_DERIVATION.json"
OUT_MD = BACKEND / "experiments" / "prof-grip-1" / "PACE_MARGIN_DERIVATION.md"


# ------------------------------------------------------- forma fechada
def vsafe_grip(kappa_inst: float, grip: float, eta: float,
               c_m: Optional[float] = None) -> Optional[float]:
    """v_safe(s) pela forma fechada exata com downforce (fórmula do mandato).

    denom = κ_inst − η·(1,8·grip)·c_m; se denom > 0:
    v_safe = sqrt(η·A/denom) com A = (1,8·grip)·9,81; senão None
    (passthrough: o chamador mantém v_plan)."""
    c_m_val = (PhysicsParams.c_downforce() / PhysicsParams.mass
               if c_m is None else float(c_m))
    eta_mu = float(eta) * (PhysicsParams.mu * float(grip))
    denom = float(kappa_inst) - eta_mu * c_m_val
    if denom <= 0.0:
        return None
    a = eta_mu * GRAVITY_MPS
    value = math.sqrt(a / denom)
    if not math.isfinite(value):
        raise ValueError("v_safe não finito")
    return value


# ------------------------------------- perfil longitudinal completo
def propagate_longitudinal(v_seed: np.ndarray, k_smooth: np.ndarray,
                           ds: float, grip: float,
                           sf: float = SF_PERFIL) -> np.ndarray:
    """Passadas backward (frenagem com círculo de atrito) + fecho circular +
    forward (tração) — MESMA estrutura e constantes de prof_curva.py
    (Passo 2 + fecho + Passo 3), aplicadas sobre v_seed."""
    n = len(v_seed)
    v = np.asarray(v_seed, dtype=np.float64).copy()
    # Passo 2: passada BACKWARD (frenagem com círculo de atrito)
    for i in range(n - 2, -1, -1):
        v_next = v[(i + 1) % n]
        k_here = abs(float(k_smooth[i]))
        v_mid = v_next
        a_drag = PhysicsParams.c_drag() * v_mid * v_mid / PhysicsParams.mass
        v_brake = v_next
        for _ in range(4):
            a_max_here = PhysicsParams.a_lat(0.5 * (v_next + v_brake), grip) * sf
            a_lat_here = (v_brake * v_brake * k_here) if k_here > 1e-6 else 0.0
            a_brk_avail = math.sqrt(max(a_max_here * a_max_here
                                        - a_lat_here * a_lat_here, 0.0))
            a_brk = a_brk_avail + a_drag
            v_brake = math.sqrt(v_next * v_next
                                + 2.0 * max(a_brk, 0.3) * ds)
        v[i] = min(v[i], v_brake)
    # Fecho backward circular (200 m)
    for i in range(n - 1, max(n - 1 - int(200 / ds), -1), -1):
        v_next = v[(i + 1) % n]
        a_brk = PhysicsParams.a_brake(v_next, grip) * sf
        v_brake = math.sqrt(v_next * v_next + 2.0 * a_brk * ds)
        if v_brake < v[i]:
            v[i] = v_brake
    # Passo 3: passada FORWARD (tração)
    for i in range(1, n):
        v_prev = v[i - 1]
        a_acc = PhysicsParams.a_accel(v_prev, grip) * sf
        v_accel = math.sqrt(v_prev * v_prev + 2.0 * a_acc * ds)
        if v_accel < v[i]:
            v[i] = v_accel
    return np.clip(v, 0.0, 200.0)


def window_mask(s_arr: np.ndarray, windows4: Dict[str, Tuple[float, float]],
                total_len: float) -> np.ndarray:
    """Máscara das janelas com SUPORTE A WRAP: janela que cruza a linha
    (s0 < 0 ou s1 > total_len — ex.: C01 = (−32,0, 128,01)) cobre os DOIS
    lados de s=0 (o segmento wrapped + o segmento pós-linha)."""
    mask = np.zeros(len(s_arr), dtype=bool)
    for w in windows4.values():
        s0, s1 = float(w[0]), float(w[1])
        if s0 < 0.0 or s1 > total_len:
            mask |= ((s_arr >= (s0 % total_len))
                     | (s_arr <= (s1 % total_len)))
        else:
            mask |= (s_arr >= s0) & (s_arr <= s1)
    return mask


def build_v_target_cap(v_base: np.ndarray, k_smooth: np.ndarray,
                       s_arr: np.ndarray, windows4: Dict[str, Tuple[float, float]],
                       kappa_inst_at, eta: float, grip: float,
                       margin: float = MARGIN_CONTROLLER
                       ) -> Tuple[np.ndarray, np.ndarray]:
    """v_ctrl = 0,93·v_base; v_seed = min(v_ctrl, v_safe) nas janelas
    (passthrough fora); v_target_cap = passadas longitudinais sobre v_seed.
    Retorna (v_seed, v_target_cap)."""
    v_ctrl = margin * np.asarray(v_base, dtype=np.float64)
    seed = v_ctrl.copy()
    mask = window_mask(s_arr, windows4, float(s_arr[-1] + (s_arr[1] - s_arr[0])))
    for i in np.where(mask)[0]:
        vs = vsafe_grip(float(kappa_inst_at(float(s_arr[i]))), grip, eta)
        if vs is not None:
            seed[i] = min(seed[i], float(vs))
    v_target_cap = propagate_longitudinal(seed, k_smooth, float(s_arr[1] - s_arr[0]),
                                          grip)
    return seed, v_target_cap


# ------------------------------------------------------- diagnóstico
def descriptive_diagnosis(on_sources: Sequence[Tuple[str, Path]],
                          track_len: float, windows4: Dict[str, Tuple[float, float]],
                          kappa_smooth_at, kappa_inst_at) -> Dict[str, Any]:
    """Diagnóstico descritivo (ON_N1..N4 SOMENTE para descrever): razão no
    ápice, lat_max, LIMPA/SAÍDA, maior razão entre LIMPAS, distribuição por
    crônica; ajuste indicativo SOMENTE nas LIMPAS de C01 (sem poder de
    derivar ou validar η)."""
    passes: List[Dict[str, Any]] = []
    for label, path in on_sources:
        df = pd.read_csv(path, comment="#")
        laps = segment_laps(df["s"].to_numpy(float), track_len)
        n_seg = int(laps.max()) + 1
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
                lat_max = float(rows["lat"].max())
                passes.append({
                    "fonte": label, "segmento": seg + 1, "curva": cid,
                    "razao_inst_apex": round(razao, 4),
                    "lat_max_m": round(lat_max, 4),
                    "desfecho": "SAÍDA" if lat_max > HALF_WIDTH_M else "LIMPA",
                })
    por_curva: Dict[str, Any] = {}
    for cid in KRONICAS:
        rows = [p for p in passes if p["curva"] == cid]
        limpas = [p for p in rows if p["desfecho"] == "LIMPA"]
        por_curva[cid] = {
            "n_passes": len(rows),
            "n_limpa": len(limpas),
            "n_saida": len(rows) - len(limpas),
            "razao_max_limpa": round(max((p["razao_inst_apex"] for p in limpas),
                                         default=0.0), 4),
            "razao_max_geral": round(max((p["razao_inst_apex"] for p in rows),
                                         default=0.0), 4),
            "lat_max_range_m": [round(min((p["lat_max_m"] for p in rows),
                                          default=0.0), 4),
                                round(max((p["lat_max_m"] for p in rows),
                                          default=0.0), 4)],
        }
    # ajuste INDICATIVO somente nas LIMPAS de C01 (não usado para η)
    c01_limpas = [p for p in passes if p["curva"] == "C01"
                  and p["desfecho"] == "LIMPA" and p["lat_max_m"] < HALF_WIDTH_M]
    ajuste_c01: Optional[Dict[str, Any]] = None
    if len(c01_limpas) >= 3:
        xs = np.array([p["razao_inst_apex"] for p in c01_limpas])
        ys = np.array([p["lat_max_m"] for p in c01_limpas])
        mx, my = float(xs.mean()), float(ys.mean())
        sxx = float(((xs - mx) ** 2).sum())
        if sxx > 0.0:
            b = float(((xs - mx) * (ys - my)).sum() / sxx)
            ajuste_c01 = {
                "n": len(c01_limpas), "a": round(my - b * mx, 4),
                "b": round(b, 6), "r2": None,
                "rotulo": DIAG_LABEL,
            }
    return {
        "fontes": [label for label, _ in on_sources],
        "n_passes": len(passes),
        "passes": passes,
        "por_curva": por_curva,
        "ajuste_indicativo_c01_limpas": ajuste_c01,
        "ajuste_nota": DIAG_LABEL,
    }


# ------------------------------------------------- engajamento e gates
def engagement_for_stage(v_target_cap: np.ndarray, v_ctrl: np.ndarray,
                         s_arr: np.ndarray, window: Tuple[float, float],
                         exits: List[Dict[str, Any]], ds: float,
                         stage_label: str) -> Dict[str, Any]:
    idx = np.where((s_arr >= window[0]) & (s_arr <= window[1]))[0]
    engaged = v_target_cap[idx] < v_ctrl[idx] - 1e-9
    n_eng = int(engaged.sum())
    # maior trecho contínuo
    runs = contiguous_events(engaged)
    longest = max((b - a + 1 for a, b in runs), default=0) * ds
    v_hist_min = float(v_ctrl[idx].min())
    v_cap_min = float(v_target_cap[idx].min())
    # saídas com o cap ativo (mapeamento offline das saídas do CTRL_OFF)
    com_cap = 0
    sem_cap = 0
    for ex in exits:
        s_ex = ex["s_exit_m"]
        if window[0] <= s_ex <= window[1]:
            # o cap está ativo na vizinhança do cruzamento?
            near = [i for i in idx if abs(float(s_arr[i]) - s_ex) <= 8.0]
            ativo = any(v_target_cap[i] < v_ctrl[i] - 1e-9 for i in near)
            com_cap += int(ativo)
            sem_cap += int(not ativo)
    return {
        "estagio": stage_label,
        "cap_engajou_algum_ponto": bool(n_eng > 0),
        "n_ticks_engajados": n_eng,
        "extensao_engajada_m": round(n_eng * ds, 3),
        "pct_da_janela": round(100.0 * n_eng / max(len(idx), 1), 2),
        "maior_trecho_continuo_m": round(float(longest), 3),
        "v_historica_min_kmh": round(v_hist_min * 3.6, 3),
        "v_capada_min_kmh": round(v_cap_min * 3.6, 3),
        "exits_com_cap_ativo": com_cap,
        "exits_sem_cap_ativo": sem_cap,
        "janela_m": [round(window[0], 3), round(window[1], 3)],
    }


def apex_delta(v_target_cap: np.ndarray, v_ctrl: np.ndarray,
               s_arr: np.ndarray, window: Tuple[float, float],
               kappa_smooth_at) -> Dict[str, Any]:
    idx = np.where((s_arr >= window[0]) & (s_arr <= window[1]))[0]
    if len(idx) == 0:
        return {}
    k_arr = np.array([abs(kappa_smooth_at(float(sv))) for sv in s_arr[idx]])
    i_apex = int(np.argmax(k_arr))
    v_h = float(v_ctrl[idx][i_apex])
    v_c = float(v_target_cap[idx][i_apex])
    return {
        "v_historica_apex_kmh": round(v_h * 3.6, 3),
        "v_capada_apex_kmh": round(v_c * 3.6, 3),
        "delta_apex_kmh": round((v_h - v_c) * 3.6, 3),
        "delta_apex_pct": round(100.0 * (v_h - v_c) / max(v_h, 1e-9), 3),
    }


def main() -> int:
    for _, path, pin in [("REF", REF_CSV, REF_SHA256), ("CTRL_OFF", CTRL_CSV, None)] + \
            [(label, path, None) for label, path in ON_SOURCES]:
        if not path.exists():
            print(f"ERRO: telemetria ausente: {path}", file=sys.stderr)
            return 2
        sha = sha256_file(path)
        if pin is not None and sha != pin:
            print(f"ERRO: SHA divergente em {path}: {sha}", file=sys.stderr)
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
    for cid in KRONICAS:
        c = next((c for c in corners if c["id"] == cid), None)
        if c is None:
            print(f"ERRO: {cid} ausente na definição canônica", file=sys.stderr)
            return 2
        windows4[cid] = (float(c["s0"]), float(c["s1"]))

    kappa_smooth_at = kappa_interp_fn(wps)
    from backend.model_train.prof_curva import _instantaneous_kappa_profile
    k_s, k_i = _instantaneous_kappa_profile(wps, ds_target=4.0)
    kappa_inst_at = (lambda s: float(np.interp(
        s % float(k_s[-1] + (k_s[1] - k_s[0])), k_s, np.abs(k_i))))

    vp = VelocityProfile(wps, grip_mult=0.788, sf=0.80, ds_target=4.0,
                         smooth_window_m=20.0)
    s_arr = np.asarray(vp.s_arr, dtype=np.float64)
    v_base = np.asarray(vp.v_plan, dtype=np.float64)
    ds = float(s_arr[1] - s_arr[0])
    k_smooth_arr = np.array([abs(kappa_smooth_at(float(sv))) for sv in s_arr])
    mask4 = np.zeros(len(s_arr), dtype=bool)
    for w in windows4.values():
        mask4 |= (s_arr >= w[0]) & (s_arr <= w[1])
    v_ctrl = MARGIN_CONTROLLER * v_base

    # ---- diagnóstico descritivo (ON_N1..N4 somente para descrever) ----
    diagnostico = descriptive_diagnosis(ON_SOURCES, track_len, windows4,
                                        kappa_smooth_at, kappa_inst_at)

    # ---- saídas do CTRL_OFF mapeadas para o cap (projeção offline) ----
    df_ctrl = pd.read_csv(CTRL_CSV, comment="#")
    ctrl_events = contiguous_events(
        df_ctrl["lat"].to_numpy(float) > HALF_WIDTH_M)
    ctrl_exits = []
    for (a, b) in ctrl_events:
        ctrl_exits.append({
            "i_exit": int(a),
            "s_exit_m": round(float(df_ctrl["s"].iloc[a]), 3),
            "t_exit_s": round(float(df_ctrl["t_s"].iloc[a]), 3),
            "lat_max_m": round(float(df_ctrl["lat"].iloc[a:b + 1].max()), 4),
        })

    # ---- estágios η1/η2 × grips: perfil completo + engajamento + t_lap ----
    c_m = PhysicsParams.c_downforce() / PhysicsParams.mass
    estagios: List[Dict[str, Any]] = []
    for stage_label, eta in ESCADA_ETA:
        for grip in GRIPS:
            seed, v_cap = build_v_target_cap(
                v_base, k_smooth_arr, s_arr, windows4, kappa_inst_at,
                eta, grip)
            t_lap = float(np.sum(ds / np.maximum(v_cap, 0.5)))
            t_base = float(np.sum(ds / np.maximum(v_base, 0.5)))
            # piso otimista (referência inferior, rotulado)
            v_opt = np.where(mask4, np.minimum(v_ctrl, np.array([
                (vsafe_grip(float(kappa_inst_at(float(sv))), grip, eta)
                 or v_base[i]) for i, sv in enumerate(s_arr)])), v_ctrl)
            t_piso_otimista = float(np.sum(ds / np.maximum(v_opt, 0.5)))
            eng = {cid: engagement_for_stage(
                v_cap, v_ctrl, s_arr, windows4[cid], ctrl_exits, ds,
                f"{stage_label}|grip {grip}") for cid in KRONICAS}
            apex = {cid: apex_delta(v_cap, v_ctrl, s_arr, windows4[cid],
                                    kappa_smooth_at) for cid in KRONICAS}
            dist_afetada = float(sum(
                eng[cid]["extensao_engajada_m"] for cid in KRONICAS))
            estagios.append({
                "estagio": stage_label, "eta": float(eta), "grip": grip,
                "t_lap_v_target_cap_s": round(t_lap, 3),
                "t_base_v_plan_s": round(t_base, 3),
                "delta_vs_base_s": round(t_lap - t_base, 3),
                "folga_guarda_s": round(GUARDA_S - t_lap, 3),
                "guarda_estoura": bool(t_lap > GUARDA_S),
                "piso_otimista_s": round(t_piso_otimista, 3),
                "piso_otimista_rotulo": "referência inferior (piso otimista "
                                        "— não é estimativa final)",
                "distancia_afetada_m": round(dist_afetada, 3),
                "engajamento": eng,
                "apex_delta": apex,
                "premissas": "frenagem: círculo de atrito com downforce "
                             "(a_lat·sf − a_lat_demanda) + drag, piso 0,3 "
                             "m/s², 4 iterações, fecho circular 200 m; "
                             "aceleração: a_accel·sf (tração 55% + potência "
                             "− drag − rolling)",
            })
    floors_ok = all(not e["guarda_estoura"] for e in estagios)
    eta1_estages = [e for e in estagios if e["estagio"] == "eta1"]
    engajou_todas = all(
        any(eng["cap_engajou_algum_ponto"] for eng in e["engajamento"].values())
        for e in eta1_estages)
    if floors_ok and engajou_todas:
        conclusao = "PREPARADO PARA CICLO ON"
    elif floors_ok:
        conclusao = "CONDICIONADO A REVISÃO DO DONO"
    else:
        conclusao = "PARE — MECANISMO NÃO SUPORTADO PELO ESTUDO"

    payload = {
        "schema_version": VERSION,
        "correcao_metodologica": {
            "sem_regressao_para_eta": True,
            "lat_max_e_censurada": True,
            "faixa_eta_abaixo_de_055_e_extrapolacao": True,
            "escada_e_constante_de_engenharia": True,
        },
        "escada_eta": {
            "eta1": float(ETA1),
            "eta1_precisao_completa": repr(float(ETA1)),
            "eta2": float(ETA2),
            "origem_eta1": "0,8 × 0,6106 (maior razão LIMPA da calibração "
                           "em amostra)",
            "regra_execucao": [
                "iniciar o estágio com η1",
                "se o estágio falhar nos gates, executar o estágio "
                "previamente definido com η2",
                "não criar novos valores depois de observar os resultados",
                "não escolher entre η1 e η2 após ver as saídas",
            ],
        },
        "diagnostico_descritivo": diagnostico,
        "aplicacao_cap": {
            "ordem_congelada": ["v_ctrl = 0,93·v_plan",
                                "v_seed = min(v_ctrl, v_safe)",
                                "v_target_cap = passadas backward/forward "
                                "sobre v_seed (algoritmo de prof_curva.py)"],
            "c_m": round(c_m, 8),
            "janelas_canonicas_m": {cid: [round(w[0], 3), round(w[1], 3)]
                                    for cid, w in windows4.items()},
        },
        "estagios": estagios,
        "gates_pre_declarados": [
            "1. C01, C06, C07 e C08: zero saídas no estágio final",
            "2. C06, C07 e C08: se qualquer uma sair com o cap ativo no "
            "estágio final, declarar PARE e rejeitar a hipótese de "
            "suficiência do mecanismo",
            "3. se houver saída com o cap inativo, declarar falha de "
            "engajamento/cobertura, não falha física do limiar",
            "4. a Guarda de Ritmo deve ser avaliada pelo tempo observado no "
            "ciclo real, não pelo piso offline",
            "5. nenhum gate pode ser alterado após observar os resultados",
            "escalada η1→η2 pré-declarada (não é ajuste pós-fato)",
        ],
        "conclusao": conclusao,
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
        "# PACE MARGIN DERIVATION (v2 horizonte) — escada fixa de η e perfil completo",
        "",
        f"**Data:** 2026-11-07 · **Método:** report-only (zero corrida nova) · "
        f"**Instrumento:** `scripts/prof_pace_margin_derivation.py` "
        f"(determinístico, `cmp=0` ×2).",
        "",
        "## Correção metodológica (obrigatória)",
        "",
        "- SEM regressão de lat_max contra razão para derivar η: lat_max é "
        "censurada e descontínua (grama/rejoin/dinâmica pós-saída); "
        "excursões de até 39,7 m não estimam fronteira de segurança;",
        "- nenhum η < ~0,55 é \"identificado pelos dados\" (extrapolação);",
        "- a escada η1/η2 é constante de engenharia pré-declarada.",
        "",
        f"## Escada fixa de η",
        "",
        f"- **η1 = {float(ETA1):.5f}** (0,8 × 0,6106 — maior razão LIMPA da "
        f"calibração; precisão completa no JSON: {repr(float(ETA1))})",
        f"- **η2 = {float(ETA2):.5f}**",
        f"- regra: iniciar com η1; falha nos gates → escalada pré-declarada "
        f"para η2; nenhum valor novo pós-observação.",
        "",
        "## Diagnóstico descritivo (ON_N1..N4, por crônica)",
        "",
        "| crônica | passes | LIMPA | SAÍDA | razão máx LIMPA | razão máx geral | "
        "lat_max (m) |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for cid in KRONICAS:
        d = diagnostico["por_curva"][cid]
        linhas.append(
            f"| {cid} | {d['n_passes']} | {d['n_limpa']} | {d['n_saida']} | "
            f"{d['razao_max_limpa']} | {d['razao_max_geral']} | "
            f"{d['lat_max_range_m'][0]}–{d['lat_max_range_m'][1]} |")
    if diagnostico["ajuste_indicativo_c01_limpas"]:
        aj = diagnostico["ajuste_indicativo_c01_limpas"]
        linhas += [
            "",
            f"Ajuste indicativo nas LIMPAS de C01 (n={aj['n']}): "
            f"lat_max = {aj['a']} + {aj['b']}·razao — **{DIAG_LABEL}**.",
        ]
    linhas += [
        "",
        "## Perfil completo e custo de ritmo (η1 e η2 × grip)",
        "",
        f"Piso base (v_plan histórico): **{round(float(np.sum(ds / np.maximum(v_base, 0.5))), 3)} s** · "
        f"Guarda: **{GUARDA_S} s**.",
        "",
        "| estágio | η | grip | t_lap v_target_cap (s) | Δ vs base | folga Guarda | "
        "distância afetada (m) | piso otimista (s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for e in estagios:
        linhas.append(
            f"| {e['estagio']} | {e['eta']:.5f} | {e['grip']} | "
            f"{e['t_lap_v_target_cap_s']} | {e['delta_vs_base_s']:+.3f} | "
            f"{e['folga_guarda_s']} | {e['distancia_afetada_m']} | "
            f"{e['piso_otimista_s']} |")

    linhas += [
        "",
        "## Engajamento por estágio e crônica (η1, grip 0,842)",
        "",
        "| crônica | engajou? | extensão (m) | % janela | maior trecho (m) | "
        "v hist mín (km/h) | v cap mín (km/h) | saídas c/ cap | sem cap |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cid in KRONICAS:
        e = estagios[0]["engajamento"][cid]
        ap = estagios[0]["apex_delta"][cid]
        linhas.append(
            f"| {cid} | {'SIM' if e['cap_engajou_algum_ponto'] else 'não'} | "
            f"{e['extensao_engajada_m']} | {e['pct_da_janela']} | "
            f"{e['maior_trecho_continuo_m']} | {e['v_historica_min_kmh']} | "
            f"{e['v_capada_min_kmh']} | {e['exits_com_cap_ativo']} | "
            f"{e['exits_sem_cap_ativo']} |")
    linhas += [
        "",
        "## Δ no ápice por crônica (η1, grip 0,842)",
        "",
        "| crônica | v hist ápice (km/h) | v cap ápice (km/h) | Δ (km/h) | Δ % |",
        "|---|---:|---:|---:|---:|",
    ]
    for cid in KRONICAS:
        ap = estagios[0]["apex_delta"][cid]
        linhas.append(
            f"| {cid} | {ap['v_historica_apex_kmh']} | "
            f"{ap['v_capada_apex_kmh']} | {ap['delta_apex_kmh']} | "
            f"{ap['delta_apex_pct']} |")

    linhas += [
        "",
        "## Gates pré-declarados para o ciclo ON",
        "",
        "1. **C01, C06, C07 e C08: zero saídas no estágio final**;",
        "2. **C06, C07 e C08: se qualquer uma sair com o cap ativo no "
        "estágio final, declarar PARE e rejeitar a hipótese de suficiência "
        "do mecanismo**;",
        "3. se houver saída com o cap inativo, declarar **falha de "
        "engajamento/cobertura**, não falha física do limiar;",
        "4. a **Guarda de Ritmo** deve ser avaliada pelo tempo observado no "
        "ciclo real, **não** pelo piso offline;",
        "5. **nenhum gate pode ser alterado após observar os resultados**;",
        "a escalada η1→η2 é pré-declarada (não é ajuste pós-fato).",
        "",
        "\"Cap binda\" é apenas evidência de atuação — não autoridade "
        "suficiente, não eficácia, não prova de eliminação de saídas.",
        "",
        "## Custo de ritmo — premissas",
        "",
        "- frenagem: círculo de atrito com downforce "
        "(a_lat·sf − a_lat_demanda) + drag, piso 0,3 m/s², 4 iterações, "
        "fecho circular 200 m;",
        "- aceleração: a_accel·sf (tração 55% + potência − drag − rolling);",
        "- o piso otimista (1/min(0,93·v_plan, v_safe)) é referência "
        "inferior, rotulado — a estimativa final usa o perfil completo.",
        "",
        "**Compatível no modelo offline; não prova que o controlador "
        "fechado respeitará a Guarda.**",
        "",
        f"## Conclusão",
        "",
        f"**{conclusao}**",
        "",
        "Sem \"η seguro\", \"garantia de margem\" ou \"proteção comprovada\" "
        "antes da validação ON.",
    ]
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    print(f"cruzamentos→diagnóstico: {diagnostico['n_passes']} passes ON_N1..N4")
    print(f"escada: η1 {float(ETA1):.5f} | η2 {float(ETA2):.5f}")
    for e in estagios:
        print(f"{e['estagio']} grip {e['grip']}: t_lap {e['t_lap_v_target_cap_s']} s "
              f"(Δ{e['delta_vs_base_s']:+.3f}, folga {e['folga_guarda_s']} s, "
              f"guarda {'ESTOURA' if e['guarda_estoura'] else 'cabe'}) | "
              f"dist afetada {e['distancia_afetada_m']} m")
    for cid in KRONICAS:
        e = estagios[0]["engajamento"][cid]
        print(f"engajamento {cid} (η1, 0,842): binda "
              f"{e['cap_engajou_algum_ponto']} | extensão "
              f"{e['extensao_engajada_m']} m | Δ ápice "
              f"{estagios[0]['apex_delta'][cid]['delta_apex_kmh']} km/h")
    print(f"CONCLUSÃO: {conclusao}")
    print(f"OK -> {OUT_JSON} + {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
