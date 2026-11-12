#!/usr/bin/env python3
"""SAIDAS-1 — Veredito e diagnóstico mecânico pré-registrado de saídas solo por curva.

Prereg: PREREG_SAIDAS_1.md (commit 1c24988, ANTES dos dados reais).
Padrao da casa: commit ANTES de rodar nos dados reais, com --selftest verde.

Perguntas:
  Q1: Quanto das saídas de pista é SOLO (sem tráfego a menos de D=15m em T=5s)?
  Q2: Quais curvas concentram as saídas? (ranking por curva, top-5)
  Q3: Modo de saída: slide, spin/rolamento ou linha reta?
  Q4: Velocidade de entrada: mediana + IQR a 1 s antes do evento por curva.

Uso:
  python scripts/saidas_verdict.py --selftest
  python scripts/saidas_verdict.py [caminho_A.csv caminho_B.csv] [--out-dir dir]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Resolver caminhos do projeto
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "model_train").exists() else SCRIPT_DIR.parent.parent
BACKEND_DIR = PROJECT_ROOT if (PROJECT_ROOT / "model_train").exists() else PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Constantes canônicas
TRACK_FILE = BACKEND_DIR / "model_train" / "tracks_frozen" / "interlagos_v2.json"
TRACK_SHA256 = "164876196eb12174"
TRACK_LEN = 4160.4
SF_S = 2655.0
HW = 6.00  # D0: half_width = 6.00 m
DT = 0.2   # amostragem 5 Hz
BOOTSTRAP_ROUNDS = 10000
BOOTSTRAP_SEED = 42

# Âncoras F4v15 para reconciliação obrigatória
ANCHOR_A_OFF = 22.1
ANCHOR_B_OFF = 25.2
ANCHOR_A_EVENTS = 180
ANCHOR_B_EVENTS = 219

# ---------------------------------------------------------------------------
# PROF-MONACO-1 (prereg 2aa018c §5): config por pista. O caminho Interlagos
# NÃO muda — as constantes acima/seguem sendo a fonte do fluxo canônico.
# ---------------------------------------------------------------------------
TRACKS = {
    "interlagos": {
        "file": BACKEND_DIR / "model_train" / "tracks_frozen" / "interlagos_v2.json",
        "sha256": "164876196eb12174",
        "hw": 6.00,          # width_m 12,0 / 2 (D0)
        "generic_names": False,
    },
    "monaco": {
        "file": BACKEND_DIR / "model_train" / "tracks_frozen" / "Monaco_v2.json",
        "sha256": "67ca11dc211c8c78",   # ADOÇÃO-H-2: mirror F1DB canônico
        "hw": 6.00,          # width_m 12,0 (IGUAL Interlagos — fórmula D0 carrega)
        "generic_names": True,   # SEM nomes oficiais (lição FASE-H-1; hairpin = κmax máx)
    },
}


# ----------------------------------------------------------------------------
# 1. Geometria do Traçado e Curvas
# ----------------------------------------------------------------------------
def load_track_geometry(track_path: Path = TRACK_FILE) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """Carrega waypoints e pré-computa geometria de referência."""
    data = json.loads(track_path.read_text())
    wps = np.array(data["waypoints"], dtype=np.float64)
    closed = np.vstack([wps, wps[:1]])
    diff = np.diff(closed, axis=0)
    seg = np.hypot(diff[:, 0], diff[:, 1])
    seg_cum = np.concatenate([[0.0], np.cumsum(seg)])[:-1]
    seg_head = np.arctan2(diff[:, 1], diff[:, 0])
    total_len = float(seg.sum())
    return wps, diff, seg, seg_cum, total_len, seg_head


def build_corner_definitions(wps: np.ndarray, kappa_thresh: float = 0.006,
                             merge_gap_m: float = 40.0,
                             generic_names: bool = False) -> List[Dict]:
    """Deriva complexos de curva contíguos a partir do perfil de curvatura suavizado.

    PROF-MONACO-1: generic_names=True (Monaco_v2) usa rótulos GEOMÉTRICOS
    ('Complexo de curva NN') — SEM atribuição oficial de turns (lição
    FASE-H-1); o hairpin identifica-se por κmax máximo. default False =
    Interlagos com a lista canônica (byte-idêntico ao SAIDAS-1)."""
    from model_train.velocity_profile import compute_kappa_profile

    s_arr, kappa_arr = compute_kappa_profile(wps, ds_target=4.0, smooth_window_m=30.0)
    abs_k = np.abs(kappa_arr)
    above = abs_k > kappa_thresh
    n = len(above)

    raw_blocks = []
    i = 0
    while i < n:
        if above[i]:
            j = i
            while j < n and above[j]:
                j += 1
            s0 = s_arr[i]
            s1 = s_arr[min(j, n - 1)]
            kmax = float(abs_k[i:j].max())
            raw_blocks.append([s0, s1, kmax])
            i = j
        else:
            i += 1

    # Fusão de blocos contíguos com gap < merge_gap_m
    merged = []
    for b in raw_blocks:
        if not merged:
            merged.append(b)
        else:
            prev = merged[-1]
            gap = b[0] - prev[1]
            if gap < merge_gap_m:
                merged[-1] = [prev[0], b[1], max(prev[2], b[2])]
            else:
                merged.append(b)

    # Wrap-around entre início e fim
    if len(merged) > 1 and (s_arr[-1] - merged[-1][1] + merged[0][0]) < merge_gap_m:
        merged[0] = [merged[-1][0] - s_arr[-1], merged[0][1], max(merged[-1][2], merged[0][2])]
        merged.pop()

    names = [
        "Descida do Lago (T4/T5)",
        "Ferradura (T6/T7)",
        "Curva do Laranjinha (T8)",
        "Pinheirinho Entrada",
        "Pinheirinho (T9)",
        "Bico de Pato (T10)",
        "Mergulho (T11)",
        "Junção (T12)",
        "Subida dos Boxes (T13/T14)",
        "Senna S (T1/T2)",
        "Curva do Sol (T3)",
    ]

    corners = []
    for idx, (s0, s1, kmax) in enumerate(merged):
        if generic_names:
            cname = f"Complexo de curva {idx+1:02d}"
        else:
            cname = names[idx] if idx < len(names) else f"Curva {idx+1}"
        corners.append({
            "id": f"C{idx+1:02d}",
            "name": cname,
            "s0": float(s0),
            "s1": float(s1),
            "kmax": float(kmax),
        })
    return corners


def match_corner(s_val: float, corners: List[Dict], track_len: float = TRACK_LEN) -> Tuple[str, str]:
    """Associa coordenada s a uma curva C01..C11 ou Reta."""
    s_mod = s_val % track_len
    margin_m = 30.0  # margem de aproximação/frenagem
    for c in corners:
        s0, s1 = c["s0"], c["s1"]
        if s0 < 0:
            if s_mod >= (s0 % track_len) or s_mod <= (s1 + margin_m):
                return c["id"], c["name"]
        else:
            if (s0 - margin_m) <= s_mod <= (s1 + margin_m):
                return c["id"], c["name"]
    return "Reta", "Reta / Outro"


# ----------------------------------------------------------------------------
# 2. Reconstrução de Trajetória, Velocidade e Modos Cinemáticos
# ----------------------------------------------------------------------------
def project_car_xy(s_arr: np.ndarray, slat_arr: np.ndarray,
                   wps: np.ndarray, diff: np.ndarray, seg: np.ndarray,
                   seg_cum: np.ndarray, seg_head: np.ndarray,
                   total_len: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reconstrói posições mundiais (x, y) e heading da linha central a partir de (s, slat)."""
    s_mod = s_arr % total_len
    j = np.clip(np.searchsorted(seg_cum, s_mod, side="right") - 1, 0, len(wps) - 1)
    t = (s_mod - seg_cum[j]) / np.maximum(seg[j], 1e-9)
    xc = wps[j, 0] + t * diff[j, 0]
    yc = wps[j, 1] + t * diff[j, 1]
    yaw = seg_head[j]
    x = xc - slat_arr * np.sin(yaw)
    y = yc + slat_arr * np.cos(yaw)
    return x, y, yaw


def classify_excursion_mode(xs: np.ndarray, ys: np.ndarray, chassis_yaws: np.ndarray,
                            speeds: np.ndarray, ev_idx: int, dt: float = DT,
                            spin_thresh_deg_s: float = 45.0,
                            slide_thresh_deg: float = 10.0,
                            window_s: float = 2.0) -> str:
    """Classifica modo cinemático da saída (SPIN, SLIDE, LINHA-RETA) na janela pré-evento."""
    ticks_win = int(round(window_s / dt))  # 10 ticks = 2.0 s
    w_start = max(0, ev_idx - ticks_win)
    w_end = ev_idx

    if w_end <= w_start:
        return "LINHA-RETA"

    dx = np.diff(xs)
    dy = np.diff(ys)
    v_angles = np.arctan2(dy, dx)

    dyaw = np.diff(chassis_yaws)
    dyaw = (dyaw + np.pi) % (2 * np.pi) - np.pi
    yaw_rates_deg_s = np.degrees(np.abs(dyaw / dt))

    # Ângulo de sideslip / deriva lateral
    slip_rad = (v_angles - chassis_yaws[:-1] + np.pi) % (2 * np.pi) - np.pi
    slip_deg = np.degrees(np.abs(slip_rad))

    rates_win = yaw_rates_deg_s[w_start:w_end]
    slips_win = slip_deg[w_start:w_end]
    speeds_win = speeds[w_start:w_end]

    # Critério SPIN: taxa de guinada >= 45 deg/s sustentada por >= 0.5 s (3 ticks de dt=0.2s)
    sustained = 0
    max_sustained = 0
    for r in rates_win:
        if r >= spin_thresh_deg_s:
            sustained += 1
            max_sustained = max(max_sustained, sustained)
        else:
            sustained = 0

    if max_sustained >= 3:  # 3 * 0.2 s = 0.6 s >= 0.5 s
        return "SPIN"

    # Critério SLIDE: slip >= 10 deg na janela (com guarda de velocidade > 2.0 m/s)
    valid_slide = False
    for sl, sp in zip(slips_win, speeds_win):
        if sp >= 2.0 and sl >= slide_thresh_deg:
            valid_slide = True
            break

    if valid_slide:
        return "SLIDE"

    return "LINHA-RETA"


# ----------------------------------------------------------------------------
# 3. Extração e Análise Completa de Saídas
# ----------------------------------------------------------------------------
def extract_excursions(df: pd.DataFrame, corners: List[Dict], geom: Tuple) -> Tuple[pd.DataFrame, Dict]:
    """Extrai todos os episódios de saída contíguos e quantifica Q1..Q4."""
    wps, diff, seg, seg_cum, total_len, seg_head = geom

    df = df.copy()
    df["slat"] = df["obs4"] * HW
    xs, ys, track_yaws = project_car_xy(
        df["s"].values, df["slat"].values, wps, diff, seg, seg_cum, seg_head, total_len
    )
    df["x"] = xs
    df["y"] = ys
    herr = np.arctan2(df["obs5"].values, df["obs6"].values)
    df["chassis_yaw"] = (track_yaws + herr + np.pi) % (2 * np.pi) - np.pi

    # Tabela dinâmica de posições para cálculo de distância entre carros
    pos_x = df.pivot(index="tick", columns="drv", values="x")
    pos_y = df.pivot(index="tick", columns="drv", values="y")
    drivers = sorted(df["drv"].unique())

    events = []
    for drv in drivers:
        sub = df[df["drv"] == drv].sort_values("tick").reset_index(drop=True)
        off = sub["offtrack"].values
        ticks = sub["tick"].values
        t_s = sub["t_s"].values
        speeds = sub["speed"].values
        s_vals = sub["s"].values
        xs_d = sub["x"].values
        ys_d = sub["y"].values
        yaws_d = sub["chassis_yaw"].values

        i = 0
        while i < len(off):
            if off[i] == 1:
                j = i
                while j < len(off) and off[j] == 1:
                    j += 1
                ev_tick = int(ticks[i])
                dur_s = (j - i) * DT

                # Q1: Tráfego nos T=5.0 s anteriores (25 ticks a 5 Hz)
                w5_start = max(0, ev_tick - 25)
                min_d = np.inf
                for other in drivers:
                    if other == drv:
                        continue
                    dx_other = pos_x.loc[w5_start:ev_tick, drv] - pos_x.loc[w5_start:ev_tick, other]
                    dy_other = pos_y.loc[w5_start:ev_tick, drv] - pos_y.loc[w5_start:ev_tick, other]
                    dists = np.hypot(dx_other, dy_other)
                    min_d = min(min_d, float(dists.min()))

                # Q2: Localização por curva
                cid, cname = match_corner(s_vals[i], corners, total_len)

                # Q3: Modo cinemático na janela de 2.0 s
                mode = classify_excursion_mode(xs_d, ys_d, yaws_d, speeds, i, dt=DT)

                # Q4: Velocidade 1.0 s antes do evento (5 ticks anteriores)
                idx_1s = max(0, i - 5)
                v_1s = float(speeds[idx_1s])

                events.append({
                    "drv": drv,
                    "tick": ev_tick,
                    "t_s": float(t_s[i]),
                    "dur_s": float(dur_s),
                    "s": float(s_vals[i]),
                    "corner_id": cid,
                    "corner_name": cname,
                    "min_d_5s": float(min_d),
                    "is_solo_15": bool(min_d >= 15.0),
                    "is_solo_10": bool(min_d >= 10.0),
                    "is_solo_20": bool(min_d >= 20.0),
                    "mode": mode,
                    "v_1s_mps": v_1s,
                    "v_1s_kmh": v_1s * 3.6,
                })
                i = j
            else:
                i += 1

    ev_df = pd.DataFrame(events)

    # Reconciliação
    total_ticks = len(df)
    off_ticks = int(df["offtrack"].sum())
    off_pct = round(100.0 * off_ticks / total_ticks, 1)
    reconcil = {
        "total_ticks": total_ticks,
        "off_ticks": off_ticks,
        "off_pct": off_pct,
        "n_events": len(ev_df),
        "dur_median": float(ev_df["dur_s"].median()) if len(ev_df) > 0 else 0.0,
    }
    return ev_df, reconcil


def bootstrap_ci_solo(is_solo: np.ndarray, rounds: int = BOOTSTRAP_ROUNDS,
                      seed: int = BOOTSTRAP_SEED) -> Tuple[float, float, float]:
    """Calcula intervalo de confiança bootstrap 95% para a proporção solo."""
    rng = np.random.RandomState(seed)
    n = len(is_solo)
    if n == 0:
        return 0.0, 0.0, 0.0
    point_est = float(100.0 * np.mean(is_solo))
    boot_means = rng.choice(is_solo.astype(float), size=(rounds, n), replace=True).mean(axis=1) * 100.0
    low, high = np.percentile(boot_means, [2.5, 97.5])
    return point_est, float(low), float(high)


# ----------------------------------------------------------------------------
# 4. Self-test com Casos Sintéticos (Cinemática + Ruidoso)
# ----------------------------------------------------------------------------
def run_selftest() -> int:
    """Suíte mecânica de testes unitários com casos cinemáticos sintéticos."""
    print("=== EXECUTANDO SELFTEST (saidas_verdict.py) ===")
    dt = 0.2

    # Caso 1: Sintético SPIN (|dpsi/dt| >= 45 deg/s sustentado por >= 0.5s = 3 ticks)
    # 15 ticks em linha reta com rotação rápida de yaw
    t_spin = np.arange(15)
    xs_spin = 10.0 * t_spin * dt
    ys_spin = np.zeros_like(xs_spin)
    # Yaw girando a 60 deg/s durante ticks 2..7 (6 ticks = 1.2s)
    yaws_spin = np.zeros_like(xs_spin)
    for k in range(3, 9):
        yaws_spin[k] = yaws_spin[k - 1] + np.radians(60.0 * dt)
    for k in range(9, len(yaws_spin)):
        yaws_spin[k] = yaws_spin[k - 1]
    speeds_spin = np.full_like(xs_spin, 10.0)

    mode_spin = classify_excursion_mode(
        xs_spin, ys_spin, yaws_spin, speeds_spin, ev_idx=10, dt=dt
    )
    assert mode_spin == "SPIN", f"Erro no Caso 1: esperado SPIN, obtido {mode_spin}"
    print("  [PASS] Caso Sintético 1: SPIN (|dpsi/dt|=60°/s sustentado 1,0s -> classificado SPIN)")

    # Caso 2: Sintético SLIDE (slip >= 10 deg, yaw constante, sem spin)
    # Chassi apontado para 0 deg, mas velocidade a 20 deg
    t_slide = np.arange(15)
    speeds_slide = np.full_like(t_slide, 15.0, dtype=float)
    yaws_slide = np.zeros_like(t_slide, dtype=float)  # heading chassi = 0
    # Carro andando em 20 deg
    xs_slide = 15.0 * np.cos(np.radians(20.0)) * t_slide * dt
    ys_slide = 15.0 * np.sin(np.radians(20.0)) * t_slide * dt

    mode_slide = classify_excursion_mode(
        xs_slide, ys_slide, yaws_slide, speeds_slide, ev_idx=10, dt=dt
    )
    assert mode_slide == "SLIDE", f"Erro no Caso 2: esperado SLIDE, obtido {mode_slide}"
    print("  [PASS] Caso Sintético 2: SLIDE (deriva lateral 20° >= 10°, yaw estável -> classificado SLIDE)")

    # Caso 3: Sintético LINHA-RETA (yaw e velocidade alinhados, yaw rate < 5 deg/s)
    t_str = np.arange(15)
    speeds_str = np.full_like(t_str, 20.0, dtype=float)
    yaws_str = np.radians(np.full_like(t_str, 45.0, dtype=float))
    xs_str = 20.0 * np.cos(np.radians(45.0)) * t_str * dt
    ys_str = 20.0 * np.sin(np.radians(45.0)) * t_str * dt

    mode_str = classify_excursion_mode(
        xs_str, ys_str, yaws_str, speeds_str, ev_idx=10, dt=dt
    )
    assert mode_str == "LINHA-RETA", f"Erro no Caso 3: esperado LINHA-RETA, obtido {mode_str}"
    print("  [PASS] Caso Sintético 3: LINHA-RETA (alinhado, sem deriva -> classificado LINHA-RETA)")

    # Caso 4: Sintético RUIDOSO (velocidade quase zero < 0.5 m/s + jitter milimétrico)
    t_noisy = np.arange(15)
    speeds_noisy = np.full_like(t_noisy, 0.2, dtype=float)  # v baixa
    np.random.seed(123)
    xs_noisy = 0.2 * t_noisy * dt + np.random.normal(0, 0.01, size=len(t_noisy))
    ys_noisy = np.random.normal(0, 0.01, size=len(t_noisy))
    yaws_noisy = np.random.normal(0, np.radians(2.0), size=len(t_noisy))

    mode_noisy = classify_excursion_mode(
        xs_noisy, ys_noisy, yaws_noisy, speeds_noisy, ev_idx=10, dt=dt
    )
    assert mode_noisy == "LINHA-RETA", f"Erro no Caso 4: esperado LINHA-RETA com guarda de ruído, obtido {mode_noisy}"
    print("  [PASS] Caso Sintético 4: RUIDOSO (v < 0,5 m/s + ruído -> guarda atua, classificado LINHA-RETA)")

    # Teste de Bootstrap
    dummy_solo = np.array([1] * 80 + [0] * 20)
    pt, lo, hi = bootstrap_ci_solo(dummy_solo, rounds=1000, seed=42)
    assert abs(pt - 80.0) < 1e-5
    assert 70.0 <= lo <= 80.0 and 80.0 <= hi <= 90.0
    print(f"  [PASS] Bootstrap CI 95%: pt={pt:.1f}%, IC=[{lo:.1f}%, {hi:.1f}%]")

    # Teste de Geometria da Pista
    assert TRACK_FILE.exists(), f"Arquivo de pista não encontrado: {TRACK_FILE}"
    wps, diff, seg, seg_cum, total_len, seg_head = load_track_geometry(TRACK_FILE)
    assert abs(total_len - TRACK_LEN) < 1.0, f"Comprimento da pista {total_len} difere do esperado {TRACK_LEN}"
    corners = build_corner_definitions(wps)
    assert len(corners) == 11, f"Esperado 11 complexos de curva em Interlagos, obtido {len(corners)}"
    print(f"  [PASS] Geometria da Pista: {len(wps)} waypoints, L={total_len:.1f}m, 11 curvas identificadas")

    # PROF-MONACO-1 (prereg 2aa018c §5): geometria Monaco_v2 — curvas
    # GENÉRICAS por geometria; N >= 8; hairpin = κmax máx ≈ 1/11,34 m (±15%);
    # ordem de s; 0 curvas = fail-loud.
    mon = TRACKS["monaco"]
    assert mon["file"].exists(), f"Monaco_v2 não encontrado: {mon['file']}"
    m_wps, m_diff, m_seg, m_seg_cum, m_total, m_seg_head = load_track_geometry(mon["file"])
    assert 3200.0 < m_total < 3500.0, \
        f"comprimento Monaco {m_total:.1f} fora da banda (oficial 3337 m)"
    m_corners = build_corner_definitions(m_wps, generic_names=True)
    assert len(m_corners) >= 8, \
        f"esperado >= 8 complexos de curva em Monaco, obtido {len(m_corners)}"
    assert all(c["name"].startswith("Complexo de curva") for c in m_corners), \
        "nomes não-genéricos em Monaco (lição H-1 violada)"
    s_vals = [c["s0"] for c in m_corners]
    assert s_vals == sorted(s_vals), "curvas de Monaco fora da ordem de s"
    hair = max(m_corners, key=lambda c: c["kmax"])
    k_rmin = 1.0 / 11.34   # r_min do BUILDER (circle-fit grosso do mirror)
    # O perfil κ do instrumento (ds=4, smooth 30) é MAIS apertado que o
    # r_min do builder — métricas DISTINTAS (errata de calibração pré-coleta
    # no prereg §10); o PISO é o builder: o hairpin não pode ser mais frouxo.
    assert hair["kmax"] >= k_rmin, \
        f"hairpin κmax {hair['kmax']:.4f} < 1/11,34={k_rmin:.4f} (mais frouxo que o r_min do mirror — investigar)"
    print(f"  [PASS] Geometria Monaco_v2: L={m_total:.1f} m, {len(m_corners)} "
          f"complexos, hairpin geométrico={hair['id']} (κmax {hair['kmax']:.4f} "
          f"≈ R {1.0/hair['kmax']:.1f} m do perfil; r_min do builder = 11,34 m "
          f"— métricas distintas; método = κmax máximo)")

    print("\nTODOS OS SELF-TESTS PASSARAM (4/4 sintéticos + bootstrap + geometria Interlagos + geometria Monaco).")
    return 0


# ----------------------------------------------------------------------------
# 4b. PROF-MONACO-1 — Bateria multi-ep (prereg 2aa018c §4-5)
# ----------------------------------------------------------------------------
def cluster_bootstrap_off_pct(off_ticks_by_ep, total_by_ep,
                               rounds: int = BOOTSTRAP_ROUNDS,
                               seed: int = BOOTSTRAP_SEED) -> Tuple[float, float, float]:
    """Bootstrap 95% do fora% com a EP como unidade de reamostragem (cluster
    bootstrap — eps são as realizações independentes; pré-registrado §9)."""
    rng = np.random.RandomState(seed)
    offs = np.asarray(list(off_ticks_by_ep), dtype=float)
    tots = np.asarray(list(total_by_ep), dtype=float)
    n = len(offs)
    if n == 0 or tots.sum() == 0:
        return 0.0, 0.0, 0.0
    pt = 100.0 * offs.sum() / tots.sum()
    idx = rng.randint(0, n, size=(rounds, n))
    boot = 100.0 * offs[idx].sum(axis=1) / np.maximum(tots[idx].sum(axis=1), 1e-9)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return float(pt), float(lo), float(hi)


def anatomy_cascade(ev_df: pd.DataFrame, wanderer_s: float = 60.0,
                    cascade_s: float = 10.0) -> pd.DataFrame:
    """PROF-MONACO-1 Q3: anatomia das excursões por driver.

    Classes (separação validada na review; convenção raiz/eco da FASE R4):
      WANDERER: duração contígua > 60 s (precedência — pré-registrado);
      REJOIN-CASCATA: início <= 10 s após o FIM da excursão anterior do
        MESMO driver;
      SAIDA_LIMPA: caso contrário."""
    ev = ev_df.sort_values(["drv", "t_s"]).reset_index(drop=True).copy()
    ev["classe"] = "SAIDA_LIMPA"
    for drv, g in ev.groupby("drv", sort=False):
        idxs = g.index.tolist()
        prev_end = None
        for i in idxs:
            dur = float(ev.at[i, "dur_s"])
            t0 = float(ev.at[i, "t_s"])
            if dur > wanderer_s:
                ev.at[i, "classe"] = "WANDERER"
            elif prev_end is not None and (t0 - prev_end) <= cascade_s:
                ev.at[i, "classe"] = "REJOIN-CASCATA"
            prev_end = t0 + dur
    return ev


def run_battery(files_a: List[str], files_b: List[str], track_key: str,
                label_a: str, label_b: str, out_dir: Path) -> int:
    """Bateria PROF-MONACO-1: extração POR EP (sem colisão drv/tick entre
    eps; solo intra-ep correto), tabelas Q1-Q4 + anatomia Q3 + Q4 mecânico
    por ICs cluster. O fluxo single-file Interlagos (golden) NÃO passa aqui."""
    cfg = TRACKS[track_key]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    geom = load_track_geometry(cfg["file"])
    wps = geom[0]
    corners = build_corner_definitions(wps, generic_names=cfg["generic_names"])
    hair = max(corners, key=lambda c: c["kmax"])
    total_len = geom[4]

    print("=" * 65)
    print(f" PROF-MONACO-1 — BATERIA {track_key.upper()} ({cfg['sha256']})")
    print("=" * 65)
    print(f"Curvas derivadas: {len(corners)} complexos (κ>0,006; merge 40 m) | "
          f"HAIRPIN geométrico = {hair['id']} (κmax {hair['kmax']:.4f} ≈ R "
          f"{1.0/hair['kmax']:.1f} m) s∈[{hair['s0']:.0f},{hair['s1']:.0f}]")
    print(f"Âncoras F4v15: N/A neste fluxo (bateria Monaco; cross-era = report)")
    print(f"Perfis: A = {label_a} ({len(files_a)} eps) | B = {label_b} ({len(files_b)} eps)\n")

    def extract_ep_list(files):
        evs, recs = [], []
        for k, f in enumerate(files):
            df = pd.read_csv(f, comment="#")
            ev, rec = extract_excursions(df, corners, geom)
            ev = ev.copy()
            ev["ep"] = k + 1
            ev["fonte"] = Path(f).name
            evs.append(ev)
            recs.append((Path(f).name, rec))
        return (pd.concat(evs, ignore_index=True) if evs
                else pd.DataFrame(columns=["drv"])), recs

    ev_a, recs_a = extract_ep_list(files_a)
    ev_b, recs_b = extract_ep_list(files_b)

    for lbl, recs in [(label_a, recs_a), (label_b, recs_b)]:
        print(f"--- Reconciliação por EP — {lbl} ---")
        for nome, rec in recs:
            print(f"  {nome}: fora={rec['off_pct']}% | eventos={rec['n_events']} "
                  f"| dur_med={rec['dur_median']:.1f}s")
    print()

    # ---- Σ solo por curva == total (FAIL-LOUD obrigatório; prereg §5) ----
    for lbl, ev in [(label_a, ev_a), (label_b, ev_b)]:
        if len(ev) == 0:
            continue
        soma = int(ev.groupby("corner_id")["is_solo_15"].sum().sum())
        total = int(ev["is_solo_15"].sum())
        assert soma == total, \
            f"[FAIL-LOUD] Σ solo por curva ({soma}) != total Q1 ({total}) — {lbl}"
    print("[PASS] Σ solo por curva == total em ambos os perfis (fail-loud).")

    # ---- Q1: ranking por curva (bootstrap de % por curva sobre eventos) ----
    print("\nQ1 — RANKING DE CURVAS POR EXCURSÕES (top-5):")
    q1_rows = []
    rng = np.random.RandomState(BOOTSTRAP_SEED)
    for lbl, ev in [(label_a, ev_a), (label_b, ev_b)]:
        tot = len(ev)
        for (cid, cname), grp in ev.groupby(["corner_id", "corner_name"]):
            n = len(grp)
            # IC bootstrap 95% do SHARE da curva (unidade = evento; seed 42)
            flags = (ev["corner_id"] == cid).values.astype(float)
            boot = rng.choice(flags, size=(BOOTSTRAP_ROUNDS, tot),
                              replace=True).mean(axis=1) * 100.0
            lo_c, hi_c = np.percentile(boot, [2.5, 97.5])
            q1_rows.append({
                "perfil": lbl, "curva_id": cid, "curva_nome": cname,
                "eventos": n, "pct_do_perfil": round(100.0 * n / tot, 1),
                "share_ci95_low": round(float(lo_c), 1),
                "share_ci95_high": round(float(hi_c), 1),
                "pct_solo_na_curva": round(100.0 * grp["is_solo_15"].mean(), 1),
            })
        # top-5 print
    q1 = pd.DataFrame(q1_rows)
    tops = {}
    for lbl, ev in [(label_a, ev_a), (label_b, ev_b)]:
        sub = q1[(q1.perfil == lbl)].sort_values("eventos", ascending=False)
        tops[lbl] = sub
        print(f"  {lbl}:")
        for r in sub.head(5).itertuples():
            print(f"    {r.curva_id} {r.curva_nome:<24s} -> {r.eventos:3d} "
                  f"excursões ({r.pct_do_perfil:4.1f}%)")
    top1 = tops[label_a].iloc[0]
    falsif_q1 = (top1["curva_id"] == "Reta")
    print(f"\n  Q1-mecânico: top-1 professor = {top1['curva_id']} "
          f"{top1['curva_nome']} ({top1['eventos']} excursões) | "
          f"{'FALSIDICAÇÃO-Q1: RETA no top-1 -> lead rejoin-cascata (report-only)' if falsif_q1 else 'expectativa hairpin/curva no top-1: consistente'}")
    q1.to_csv(out_dir / "tabela_q1_ranking.csv", index=False)

    # ---- Q2/Q3/Q4 por curva (v_med, IQR, modos) ----
    rows = []
    for lbl, ev in [(label_a, ev_a), (label_b, ev_b)]:
        for (cid, cname), grp in ev.groupby(["corner_id", "corner_name"]):
            v = grp["v_1s_kmh"]
            mc = grp["mode"].value_counts()
            rows.append({
                "perfil": lbl, "curva_id": cid, "curva_nome": cname,
                "eventos": len(grp),
                "v_1s_med_kmh": round(float(v.median()), 1) if len(grp) else 0.0,
                "v_1s_iqr_kmh": round(float(v.quantile(0.75) - v.quantile(0.25)), 1) if len(grp) else 0.0,
                "modos": (f"LR:{mc.get('LINHA-RETA',0)}/"
                          f"SL:{mc.get('SLIDE',0)}/SP:{mc.get('SPIN',0)}"),
            })
    resumo = pd.DataFrame(rows).sort_values(["perfil", "eventos"],
                                            ascending=[True, False])
    resumo.to_csv(out_dir / "tabela_resumo_bateria.csv", index=False)
    print("\nQ2 — Assinatura cinemática por curva (top-5 por perfil):")
    for lbl, ev in [(label_a, ev_a), (label_b, ev_b)]:
        sub = resumo[resumo.perfil == lbl].head(5)
        print(f"  {lbl}:")
        for r in sub.itertuples():
            print(f"    {r.curva_id} {r.curva_nome:<24s} n={r.eventos:3d} "
                  f"v_med={r.v_1s_med_kmh:5.1f} km/h IQR={r.v_1s_iqr_kmh:5.1f} "
                  f"[{r.modos}]")

    # ---- Q3: anatomia (rejoin-cascata × saída limpa × wanderer) ----
    print("\nQ3 — ANATOMIA DAS EXCURSÕES (cascata <=10s; wanderer >60s):")
    an_rows = []
    for lbl, ev in [(label_a, ev_a), (label_b, ev_b)]:
        if len(ev) == 0:
            continue
        evo = anatomy_cascade(ev)
        for cls, grp in evo.groupby("classe"):
            an_rows.append({
                "perfil": lbl, "classe": cls, "eventos": len(grp),
                "pct": round(100.0 * len(grp) / len(evo), 1),
                "tempo_acum_s": round(float(grp["dur_s"].sum()), 1),
            })
        evo.to_csv(out_dir / f"eventos_anatomia_{'prof' if lbl == label_a else 'aluno'}.csv",
                   index=False)
    an = pd.DataFrame(an_rows)
    if len(an):
        print(an.to_string(index=False))
    an.to_csv(out_dir / "tabela_anatomia.csv", index=False)

    # ---- Q4: fora% cluster bootstrap + veredito MECÂNICO por ICs ----
    print("\nQ4 — HERDADO OU DEGRADADO (fora% por braço; cluster bootstrap por ep):")
    stats = {}
    for lbl, recs in [(label_a, recs_a), (label_b, recs_b)]:
        offs = [r["off_ticks"] for _, r in recs]
        tots = [r["total_ticks"] for _, r in recs]
        pt, lo, hi = cluster_bootstrap_off_pct(offs, tots)
        stats[lbl] = (pt, lo, hi)
        print(f"  {lbl}: fora={pt:.2f}% [IC 95%: {lo:.2f}% - {hi:.2f}%] "
              f"({len(recs)} eps)")
    (pa, la, ha) = stats[label_a]   # professor
    (pb, lb_, hb) = stats[label_b]  # aluno
    pd_q4 = out_dir / "tabela_q4_herdado.csv"
    if lb_ > ha:
        verdict_q4 = ("DEGRADADO — aluno ACIMA do professor com ICs DISJUNTOS "
                      "(degradação do aluno; proposta de reparo = SÓ TEXTO)")
        code = 0
    elif la > hb:
        verdict_q4 = ("FALSIDICAÇÃO-Q4 — aluno ABAIXO do professor com ICs "
                      "DISJUNTOS (rótulos inconsistentes) -> PARE IMEDIATO")
        code = 4
    else:
        verdict_q4 = ("HERDADO — ICs SOBREPOSTOS (fora ≈ professor: baseline "
                      "dos rótulos/instrumento sob mirror)")
        code = 0
    print(f"\n  Q4-mecânico: {verdict_q4}")
    pd.DataFrame([{"perfil": k, "fora_pct": round(v[0], 2),
                   "ci_low": round(v[1], 2), "ci_high": round(v[2], 2)}
                  for k, v in stats.items()] +
                 [{"perfil": "VEREDITO", "fora_pct": 0.0, "ci_low": 0.0,
                   "ci_high": 0.0, "veredito": verdict_q4}]).to_csv(pd_q4, index=False)

    print(f"\nBateria concluída — tabelas em: {out_dir}")
    print("Q1 falsificação (reta no top-1): "
          f"{'DISPARADA (report-only)' if falsif_q1 else 'não disparada'}")
    return code


# ----------------------------------------------------------------------------
# 5. Execução Principal e Emissão de Artefatos
# ----------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Veredito mecânico de saídas solo por curva (SAIDAS-1)")
    parser.add_argument("--selftest", action="store_true", help="Executa testes cinemáticos sintéticos")
    parser.add_argument("--file-a", "--ctrl", dest="file_a", default=None, help="Caminho CSV perfil A (v10-cego)")
    parser.add_argument("--file-b", "--comp", dest="file_b", default=None, help="Caminho CSV perfil B (composite)")
    parser.add_argument("--out-dir", default=None, help="Diretório de saída para tabelas")
    parser.add_argument("--track", default="interlagos", choices=sorted(TRACKS),
                        help="Pista (prereg 2aa018c §5): interlagos = caminho "
                             "canônico bit-idêntico; monaco = Monaco_v2 (sha "
                             "67ca11dc211c8c78) com curvas GENÉRICAS por "
                             "geometria")
    parser.add_argument("--label-a", default="A (v10-cego)",
                        help="Rótulo do perfil A (golden usa o default)")
    parser.add_argument("--label-b", default="B (composite)",
                        help="Rótulo do perfil B (golden usa o default)")
    parser.add_argument("--files-a", nargs="+", default=None,
                        help="PROF-MONACO-1: bateria multi-ep do perfil A")
    parser.add_argument("--files-b", nargs="+", default=None,
                        help="PROF-MONACO-1: bateria multi-ep do perfil B")
    parser.add_argument("files", nargs="*", help="Arquivos posicionais opcionais [file_a, file_b]")
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()

    # PROF-MONACO-1: bateria multi-ep (fluxo SEPARADO; golden não passa aqui)
    if args.files_a or args.files_b:
        if not args.files_a or not args.files_b:
            parser.error("--files-a e --files-b são obrigatórios JUNTOS (bateria)")
        out_batt = Path(args.out_dir) if args.out_dir else (
            BACKEND_DIR / "experiments" / "prof-monaco-1")
        return run_battery(args.files_a, args.files_b, args.track,
                           args.label_a, args.label_b, out_batt)

    # Suporte a argumentos posicionais se fornecidos
    if args.files:
        if len(args.files) >= 1 and not args.file_a:
            args.file_a = args.files[0]
        if len(args.files) >= 2 and not args.file_b:
            args.file_b = args.files[1]

    # Resolução de arquivos padrão
    def resolve_path(p_str: Optional[str], default_rel: str) -> Path:
        if p_str:
            p = Path(p_str)
            if p.exists():
                return p
        # Tentar caminhos padrão
        cands = [
            BACKEND_DIR / default_rel,
            PROJECT_ROOT / default_rel,
            Path(default_rel),
        ]
        for c in cands:
            if c.exists():
                return c
        raise FileNotFoundError(f"Arquivo não encontrado: {default_rel}")

    LBL_A, LBL_B = args.label_a, args.label_b
    file_a = resolve_path(args.file_a, "experiments/f4v15-wiring/1_controle.csv")
    file_b = resolve_path(args.file_b, "experiments/f4v15-wiring/2_allcomposite.csv")

    out_dir = Path(args.out_dir) if args.out_dir else (BACKEND_DIR / "experiments" / "saidas-1")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=================================================================")
    print(" CICLO SAIDAS-1 — DIAGNÓSTICO PRÉ-REGISTRADO DE SAÍDAS SOLO")
    print("=================================================================")
    print(f"Artefato Perfil A: {file_a}")
    print(f"Artefato Perfil B: {file_b}")
    print(f"Diretório de saída: {out_dir}\n")

    # 1. Carregar Geometria e Definir Curvas (por pista; prereg 2aa018c §5)
    _cfg = TRACKS[args.track]
    geom = load_track_geometry(_cfg["file"])
    wps = geom[0]
    corners = build_corner_definitions(wps, generic_names=_cfg["generic_names"])
    print(f"Geometria {args.track}: {len(corners)} complexos de curva mapeados.")

    # 2. Processar Perfil A e Perfil B
    df_a = pd.read_csv(file_a, comment="#")
    df_b = pd.read_csv(file_b, comment="#")

    ev_a, rec_a = extract_excursions(df_a, corners, geom)
    ev_b, rec_b = extract_excursions(df_b, corners, geom)

    # 3. RECONCILIAÇÃO OBRIGATÓRIA (FAIL-LOUD; âncoras F4v15 = Interlagos)
    if args.track != "interlagos":
        print("\n--- RECONCILIAÇÃO: âncoras F4v15 N/A (pista " + args.track + ") ---")
        print("[REPORT] Sem âncoras canônicas nesta pista; cross-era = report.")
    else:
        print("\n--- RECONCILIAÇÃO COM ÂNCORAS F4v15 ---")
        print(f"Perfil A ({LBL_A}): fora={rec_a['off_pct']}% (esperado {ANCHOR_A_OFF}%) | eventos={rec_a['n_events']} (esperado {ANCHOR_A_EVENTS}) | dur_med={rec_a['dur_median']:.1f}s")
        print(f"Perfil B ({LBL_B}): fora={rec_b['off_pct']}% (esperado {ANCHOR_B_OFF}%) | eventos={rec_b['n_events']} (esperado {ANCHOR_B_EVENTS}) | dur_med={rec_b['dur_median']:.1f}s")

        if rec_a["off_pct"] != ANCHOR_A_OFF or rec_b["off_pct"] != ANCHOR_B_OFF:
            print("\n[ERRO CRÍTICO / PARE]: A reconciliação temporal com as âncoras F4v15 FALHOU!")
            print(f"A: {rec_a['off_pct']} vs {ANCHOR_A_OFF} | B: {rec_b['off_pct']} vs {ANCHOR_B_OFF}")
            return 2

        if rec_a["n_events"] != ANCHOR_A_EVENTS or rec_b["n_events"] != ANCHOR_B_EVENTS:
            print("\n[ERRO CRÍTICO / PARE]: A contagem de episódios de excursão divergiu das âncoras!")
            print(f"A: {rec_a['n_events']} vs {ANCHOR_A_EVENTS} | B: {rec_b['n_events']} vs {ANCHOR_B_EVENTS}")
            return 2

        print("[PASS] Reconciliação bit-idêntica perfeita com as âncoras F4v15.")

    # 4. RESPOSTA Q1 — SAÍDAS SOLO
    print("\n=================================================================")
    print(" RESPOSTA Q1 — PROPORÇÃO DE SAÍDAS SOLO (SEM TRÁFEGO)")
    print("=================================================================")
    pt_a, lo_a, hi_a = bootstrap_ci_solo(ev_a["is_solo_15"].values)
    pt_b, lo_b, hi_b = bootstrap_ci_solo(ev_b["is_solo_15"].values)

    s10_a = 100.0 * ev_a["is_solo_10"].mean()
    s20_a = 100.0 * ev_a["is_solo_20"].mean()
    s10_b = 100.0 * ev_b["is_solo_10"].mean()
    s20_b = 100.0 * ev_b["is_solo_20"].mean()

    print(f"Perfil A (v10-cego):")
    print(f"  Eventos Totais: {len(ev_a)} ({len(ev_a)/1.0:.1f} / 100 voltas)")
    print(f"  SOLO Primário (D=15m, T=5s): {ev_a['is_solo_15'].sum()}/{len(ev_a)} = {pt_a:.1f}% [IC 95%: {lo_a:.1f}% - {hi_a:.1f}%]")
    print(f"  Sensibilidade: D=10m -> {ev_a['is_solo_10'].sum()}/{len(ev_a)} = {s10_a:.1f}% | D=20m -> {ev_a['is_solo_20'].sum()}/{len(ev_a)} = {s20_a:.1f}%")

    print(f"\nPerfil B (composite):")
    print(f"  Eventos Totais: {len(ev_b)} ({len(ev_b)/1.0:.1f} / 100 voltas)")
    print(f"  SOLO Primário (D=15m, T=5s): {ev_b['is_solo_15'].sum()}/{len(ev_b)} = {pt_b:.1f}% [IC 95%: {lo_b:.1f}% - {hi_b:.1f}%]")
    print(f"  Sensibilidade: D=10m -> {ev_b['is_solo_10'].sum()}/{len(ev_b)} = {s10_b:.1f}% | D=20m -> {ev_b['is_solo_20'].sum()}/{len(ev_b)} = {s20_b:.1f}%")

    # Salvar tabela Q1
    tab_q1 = pd.DataFrame([
        {
            "perfil": LBL_A,
            "total_eventos": len(ev_a),
            "eventos_solo": int(ev_a["is_solo_15"].sum()),
            "pct_solo": round(pt_a, 1),
            "ci95_low": round(lo_a, 1),
            "ci95_high": round(hi_a, 1),
            "pct_solo_10m": round(s10_a, 1),
            "pct_solo_20m": round(s20_a, 1),
        },
        {
            "perfil": LBL_B,
            "total_eventos": len(ev_b),
            "eventos_solo": int(ev_b["is_solo_15"].sum()),
            "pct_solo": round(pt_b, 1),
            "ci95_low": round(lo_b, 1),
            "ci95_high": round(hi_b, 1),
            "pct_solo_10m": round(s10_b, 1),
            "pct_solo_20m": round(s20_b, 1),
        },
    ])
    tab_q1.to_csv(out_dir / "tabela_q1_solo.csv", index=False)

    # 5. RESPOSTA Q2 — RANKING DE CURVAS
    print("\n=================================================================")
    print(" RESPOSTA Q2 — QUAIS CURVAS CONCENTRAM AS SAÍDAS (TOP-5)")
    print("=================================================================")
    def summarize_curvas(ev_df: pd.DataFrame, perfil_nm: str) -> pd.DataFrame:
        tot = len(ev_df)
        rows = []
        for (cid, cname), grp in ev_df.groupby(["corner_id", "corner_name"]):
            cnt = len(grp)
            pct = 100.0 * cnt / tot
            rows.append({
                "perfil": perfil_nm,
                "curva_id": cid,
                "curva_nome": cname,
                "eventos": cnt,
                "taxa_100v": cnt,
                "pct_do_perfil": round(pct, 1),
                "eventos_solo": int(grp["is_solo_15"].sum()),
                "pct_solo_na_curva": round(100.0 * grp["is_solo_15"].mean(), 1),
            })
        res = pd.DataFrame(rows).sort_values("eventos", ascending=False).reset_index(drop=True)
        res["rank"] = range(1, len(res) + 1)
        return res

    curvas_a = summarize_curvas(ev_a, LBL_A)
    curvas_b = summarize_curvas(ev_b, LBL_B)

    print("Top-5 Curvas — Perfil A (v10-cego):")
    for r in curvas_a.head(5).itertuples():
        print(f"  #{r.rank}: {r.curva_id} {r.curva_nome:<28s} -> {r.eventos:2d} saídas ({r.pct_do_perfil:4.1f}%) | solo: {r.pct_solo_na_curva:4.1f}%")

    print("\nTop-5 Curvas — Perfil B (composite):")
    for r in curvas_b.head(5).itertuples():
        print(f"  #{r.rank}: {r.curva_id} {r.curva_nome:<28s} -> {r.eventos:2d} saídas ({r.pct_do_perfil:4.1f}%) | solo: {r.pct_solo_na_curva:4.1f}%")

    tab_q2 = pd.concat([curvas_a, curvas_b], ignore_index=True)
    tab_q2.to_csv(out_dir / "tabela_q2_curvas.csv", index=False)

    # Cross-check aritmético estrito: a soma dos solos por curva DEVE fechar exatamente com o total Q1
    sum_solo_a = int(curvas_a["eventos_solo"].sum())
    sum_solo_b = int(curvas_b["eventos_solo"].sum())
    tot_solo_a = int(ev_a["is_solo_15"].sum())
    tot_solo_b = int(ev_b["is_solo_15"].sum())
    assert sum_solo_a == tot_solo_a, f"[FAIL] Discrepância aritmética Perfil A: {sum_solo_a} != {tot_solo_a}"
    assert sum_solo_b == tot_solo_b, f"[FAIL] Discrepância aritmética Perfil B: {sum_solo_b} != {tot_solo_b}"
    print(f"\nConsistência Aritmética Q1 x Q2:")
    print(f"  Perfil A: soma curvas ({sum_solo_a}) == total Q1 ({tot_solo_a}) -> PASS")
    print(f"  Perfil B: soma curvas ({sum_solo_b}) == total Q1 ({tot_solo_b}) -> PASS")

    # 6. RESPOSTA Q3 — MODO DE SAÍDA
    print("\n=================================================================")
    print(" RESPOSTA Q3 — MODO DE SAÍDA (SLIDE, SPIN, LINHA-RETA)")
    print("=================================================================")
    def summarize_modos(ev_df: pd.DataFrame, perfil_nm: str) -> pd.DataFrame:
        tot = len(ev_df)
        vc = ev_df["mode"].value_counts()
        rows = []
        for m in ["LINHA-RETA", "SLIDE", "SPIN"]:
            cnt = int(vc.get(m, 0))
            rows.append({
                "perfil": perfil_nm,
                "modo": m,
                "contagem": cnt,
                "pct": round(100.0 * cnt / tot, 1),
            })
        return pd.DataFrame(rows)

    modos_a = summarize_modos(ev_a, LBL_A)
    modos_b = summarize_modos(ev_b, LBL_B)

    print("Distribuição de Modos — Perfil A (v10-cego):")
    for r in modos_a.itertuples():
        print(f"  {r.modo:<12s}: {r.contagem:3d} ({r.pct:5.1f}%)")

    print("\nDistribuição de Modos — Perfil B (composite):")
    for r in modos_b.itertuples():
        print(f"  {r.modo:<12s}: {r.contagem:3d} ({r.pct:5.1f}%)")

    tab_q3 = pd.concat([modos_a, modos_b], ignore_index=True)
    tab_q3.to_csv(out_dir / "tabela_q3_modos.csv", index=False)

    # 7. RESPOSTA Q4 — VELOCIDADE DE ENTRADA
    print("\n=================================================================")
    print(" RESPOSTA Q4 — VELOCIDADE NA ENTRADA (1 s ANTES DO EVENTO)")
    print("=================================================================")
    def summarize_speed(ev_df: pd.DataFrame, perfil_nm: str) -> pd.DataFrame:
        rows = []
        for (cid, cname), grp in ev_df.groupby(["corner_id", "corner_name"]):
            v = grp["v_1s_mps"]
            v_med = float(v.median())
            v_iqr = float(v.quantile(0.75) - v.quantile(0.25))
            rows.append({
                "perfil": perfil_nm,
                "curva_id": cid,
                "curva_nome": cname,
                "n": len(grp),
                "v_med_mps": round(v_med, 1),
                "v_iqr_mps": round(v_iqr, 1),
                "v_med_kmh": round(v_med * 3.6, 1),
                "v_iqr_kmh": round(v_iqr * 3.6, 1),
            })
        return pd.DataFrame(rows).sort_values("n", ascending=False).reset_index(drop=True)

    speed_a = summarize_speed(ev_a, LBL_A)
    speed_b = summarize_speed(ev_b, LBL_B)

    print("Velocidade 1s pré-evento (Top Curvas) — Perfil A (v10-cego):")
    for r in speed_a.head(5).itertuples():
        print(f"  {r.curva_id} {r.curva_nome:<28s} (n={r.n:2d}): v_med={r.v_med_kmh:5.1f} km/h (IQR {r.v_iqr_kmh:4.1f} km/h) [{r.v_med_mps:.1f} m/s]")

    print("\nVelocidade 1s pré-evento (Top Curvas) — Perfil B (composite):")
    for r in speed_b.head(5).itertuples():
        print(f"  {r.curva_id} {r.curva_nome:<28s} (n={r.n:2d}): v_med={r.v_med_kmh:5.1f} km/h (IQR {r.v_iqr_kmh:4.1f} km/h) [{r.v_med_mps:.1f} m/s]")

    tab_q4 = pd.concat([speed_a, speed_b], ignore_index=True)
    tab_q4.to_csv(out_dir / "tabela_q4_velocidade.csv", index=False)

    # 8. Tabela Síntese Cruzada (Curva x Perfil)
    summary_rows = []
    all_curvas = sorted(set(ev_a["corner_id"].unique()) | set(ev_b["corner_id"].unique()))
    cname_map = {}
    for r in pd.concat([ev_a, ev_b]).itertuples():
        cname_map[r.corner_id] = r.corner_name

    for cid in all_curvas:
        cname = cname_map[cid]
        for p_name, ev_sub in [(LBL_A, ev_a), (LBL_B, ev_b)]:
            sub = ev_sub[ev_sub["corner_id"] == cid]
            n_sub = len(sub)
            if n_sub > 0:
                n_solo = int(sub["is_solo_15"].sum())
                pct_solo = round(100.0 * n_solo / n_sub, 1)
                v_med = round(float(sub["v_1s_kmh"].median()), 1)
                v_iqr = round(float(sub["v_1s_kmh"].quantile(0.75) - sub["v_1s_kmh"].quantile(0.25)), 1)
                m_cnt = sub["mode"].value_counts()
                m_str = f"LR:{m_cnt.get('LINHA-RETA',0)}/SL:{m_cnt.get('SLIDE',0)}/SP:{m_cnt.get('SPIN',0)}"
            else:
                n_solo = 0
                pct_solo = 0.0
                v_med = 0.0
                v_iqr = 0.0
                m_str = "0/0/0"
            summary_rows.append({
                "curva_id": cid,
                "curva_nome": cname,
                "perfil": p_name,
                "eventos": n_sub,
                "taxa_100v": n_sub,
                "pct_solo": pct_solo,
                "modos_lr_sl_sp": m_str,
                "v_1s_med_kmh": v_med,
                "v_1s_iqr_kmh": v_iqr,
            })
    tab_summary = pd.DataFrame(summary_rows)
    tab_summary.to_csv(out_dir / "tabela_resumo_curva_perfil.csv", index=False)

    # Salvar também os eventos detalhados para rastreabilidade auditável
    ev_a_out = ev_a.copy()
    ev_a_out["perfil"] = LBL_A
    ev_b_out = ev_b.copy()
    ev_b_out["perfil"] = LBL_B
    pd.concat([ev_a_out, ev_b_out], ignore_index=True).to_csv(out_dir / "eventos_saidas_detalhados.csv", index=False)

    print("\n=================================================================")
    print(f"VEREDITO CONCLUÍDO — Todas as 5 tabelas emitidas em: {out_dir}")
    print("=================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
