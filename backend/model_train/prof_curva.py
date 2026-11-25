"""Módulo de teto local de curvatura no professor solo (PROF-CURVA-1).

Lê em runtime a fronteira física empírica de skidpad medida em
`physics_frontier_current.json` (medida até 25 m/s) e deriva o teto de velocidade
local a partir da curvatura local instantânea, sem a suavização excessiva de 30 m.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np

from backend.model_train.velocity_profile import (
    PhysicsParams,
    VelocityProfile,
    compute_kappa_profile,
)


def _instantaneous_kappa_profile(
    waypoints: np.ndarray,
    ds_target: float = 4.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return the unsmoothed local curvature on the standard arc grid.

    ``compute_kappa_profile(..., smooth_window_m=0)`` still keeps its minimum
    three-sample window for backwards compatibility. PROF-CURVA needs the
    actual local signal at a corner, so it performs the same resampling and
    heading-difference calculation without a moving-window operation.
    """
    wps = np.asarray(waypoints, dtype=np.float64)
    if wps.ndim != 2 or wps.shape[1] != 2 or len(wps) < 3:
        raise ValueError("waypoints deve ser um array (N, 2) com N >= 3")
    if ds_target <= 0.0:
        raise ValueError("ds_target deve ser positivo")

    closed = np.vstack([wps, wps[:1]])
    seg_len = np.hypot(np.diff(closed[:, 0]), np.diff(closed[:, 1]))
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    total = float(cum[-1])
    if total <= 0.0:
        raise ValueError("waypoints possui comprimento de arco zero")

    n = max(20, int(total / ds_target))
    s_arr = np.linspace(0.0, total, n, endpoint=False)
    idx = np.searchsorted(cum, s_arr, side="right") - 1
    idx = np.clip(idx, 0, len(seg_len) - 1)
    t = (s_arr - cum[idx]) / np.maximum(seg_len[idx], 1e-9)
    x = wps[idx, 0] * (1.0 - t) + wps[(idx + 1) % len(wps), 0] * t
    y = wps[idx, 1] * (1.0 - t) + wps[(idx + 1) % len(wps), 1] * t

    dx = np.roll(x, -1) - np.roll(x, 1)
    dy = np.roll(y, -1) - np.roll(y, 1)
    heading = np.arctan2(dy, dx)
    dh = np.roll(heading, -1) - heading
    dh = (dh + math.pi) % (2.0 * math.pi) - math.pi
    kappa = np.clip(dh / ds_target, -0.25, 0.25)
    return s_arr, kappa


def load_physics_frontier(
    frontier_path: Union[str, Path],
    grip: float = 0.788,
) -> List[Tuple[float, float]]:
    """Carrega em runtime a grade de raios físicos viáveis por velocidade.

    Filtra as medições empíricas para a aderência solicitada (0.788 real ou 0.842 soft),
    descartando a classe QUEBRA (aceitando LIMPO e MARGINAL, onde o carro mantém
    trajetória circular sem perder o controle).

    Retorna uma lista ordenada de tuplas (R_min_m, v_mps).
    """
    path = Path(frontier_path)
    if not path.is_absolute():
        # Tenta resolver relativo ao backend se existir
        backend_dir = Path(__file__).resolve().parent.parent
        candidate = backend_dir / path
        if candidate.exists():
            path = candidate

    if not path.exists():
        raise FileNotFoundError(f"Arquivo de fronteira física não encontrado: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Identifica o grip mais próximo
    measurements = data.get("measurements", [])
    available_grips = sorted({m["grip"] for m in measurements})
    if not available_grips:
        raise ValueError(f"Nenhuma medição encontrada em {path}")

    closest_grip = min(available_grips, key=lambda g: abs(g - grip))

    # Para cada velocidade testada, determina o menor R_target sem QUEBRA
    speeds = data.get("protocol", {}).get("speeds_mps", [])
    pairs = []
    for v in speeds:
        valid_radii = [
            m["R_target"]
            for m in measurements
            if m["grip"] == closest_grip
            and math.isclose(float(m["v_target"]), float(v), rel_tol=0.0, abs_tol=1e-9)
            and m.get("classe") != "QUEBRA"
        ]
        if valid_radii:
            pairs.append((float(min(valid_radii)), float(v)))

    if not pairs:
        raise ValueError(f"Nenhum raio válido sem QUEBRA encontrado para grip {closest_grip}")

    pairs.sort(key=lambda item: item[0])
    return pairs


def get_v_cap(radius_m: float, frontier_pairs: List[Tuple[float, float]]) -> float:
    """Computa o teto de velocidade físico (m/s) para um raio de curvatura (m).

    Interpola linearmente sobre a fronteira empírica. Abaixo do raio mínimo
    medido, escala proporcionalmente a sqrt(R / R_min). Acima do raio máximo
    medido (40 m), libera sem teto artificial (200.0 m/s), permitindo que a
    dinâmica analítica de downforce e potência governe retas e curvas abertas.
    """
    r_min, v_min = frontier_pairs[0]
    r_max, v_max = frontier_pairs[-1]

    if radius_m > r_max:
        return 200.0

    if radius_m <= r_min:
        # Escala sub-linear sqrt(R/R_min) para raios ultracurtos (ex: Junção R~9m)
        r_eff = max(radius_m, 2.0)
        return float(v_min * math.sqrt(r_eff / r_min))

    # Interpolação linear por trechos
    for idx in range(len(frontier_pairs) - 1):
        r0, v0 = frontier_pairs[idx]
        r1, v1 = frontier_pairs[idx + 1]
        if r0 <= radius_m <= r1:
            fraction = (radius_m - r0) / (r1 - r0)
            return float(v0 + fraction * (v1 - v0))

    return 200.0


def build_capped_velocity_profile(
    waypoints: np.ndarray,
    frontier_path: Union[str, Path],
    grip_mult: float = 0.788,
    sf: float = 0.80,
    ds_target: float = 4.0,
    smooth_window_m: float = 20.0,
) -> VelocityProfile:
    """Constrói o VelocityProfile com teto local de curvatura do professor solo.

    1. Calcula a curvatura suavizada (para a aceleração lateral geral de downforce);
    2. Calcula a curvatura local instantânea (smooth_window=0) para capturar quinas;
    3. Para cada ponto de arco s, consulta a fronteira física para o raio local;
    4. Executa passadas backward (frenagem) e forward (tração) completas para garantir
       consistência dinâmica em todo o circuito.
    """
    frontier_pairs = load_physics_frontier(frontier_path, grip=grip_mult)

    # 1. Curvatura suavizada padrão
    s_arr, k_smooth = compute_kappa_profile(
        waypoints, ds_target=ds_target, smooth_window_m=smooth_window_m
    )
    # 2. Curvatura local instantânea (sem janela excessiva)
    _, k_raw = _instantaneous_kappa_profile(waypoints, ds_target=ds_target)

    # Curvatura local efetiva: considera a maior magnitude no ponto
    k_local = np.maximum(np.abs(k_smooth), np.abs(k_raw))

    # Tetos locais por raio
    v_caps = np.array(
        [get_v_cap(1.0 / max(k, 1e-5), frontier_pairs) for k in k_local],
        dtype=np.float64,
    )

    n = len(s_arr)
    ds = float(s_arr[1] - s_arr[0]) if n > 1 else 4.0
    v_plan = np.full(n, 200.0, dtype=np.float64)

    # Passo 1: limite de curva (física analítica com downforce + teto empírico de raio)
    KAPPA_SF_FLOOR = 0.10
    for i in range(n):
        k = abs(k_smooth[i])
        if k > 1e-6:
            sf_i = sf * min(1.0, KAPPA_SF_FLOOR / max(k, KAPPA_SF_FLOOR))
            mu_s = PhysicsParams.mu * grip_mult * sf_i
            c_m = PhysicsParams.c_downforce() / PhysicsParams.mass
            denom = k - mu_s * c_m
            if denom > 1e-6:
                v_plan[i] = math.sqrt(mu_s * PhysicsParams.g / denom)
        # Aplicação do teto local de curvatura empírico
        v_plan[i] = min(v_plan[i], v_caps[i])

    # Passo 2: passada BACKWARD (frenagem com círculo de atrito)
    for i in range(n - 2, -1, -1):
        v_next = v_plan[(i + 1) % n]
        k_here = abs(k_smooth[i])
        v_mid = v_next
        a_drag = PhysicsParams.c_drag() * v_mid * v_mid / PhysicsParams.mass
        v_brake = v_next
        for _ in range(4):
            a_max_here = PhysicsParams.a_lat(0.5 * (v_next + v_brake), grip_mult) * sf
            a_lat_here = v_brake * v_brake * k_here if k_here > 1e-6 else 0.0
            a_brk_avail = math.sqrt(max(a_max_here * a_max_here - a_lat_here * a_lat_here, 0.0))
            a_brk = a_brk_avail + a_drag
            v_brake = math.sqrt(v_next * v_next + 2.0 * max(a_brk, 0.3) * ds)
        v_plan[i] = min(v_plan[i], v_brake)

    # Fecho backward circular
    for i in range(n - 1, max(n - 1 - int(200 / ds), -1), -1):
        v_next = v_plan[(i + 1) % n]
        a_brk = PhysicsParams.a_brake(v_next, grip_mult) * sf
        v_brake = math.sqrt(v_next * v_next + 2.0 * a_brk * ds)
        if v_brake < v_plan[i]:
            v_plan[i] = v_brake

    # Passo 3: passada FORWARD (tração)
    for i in range(1, n):
        v_prev = v_plan[i - 1]
        a_acc = PhysicsParams.a_accel(v_prev, grip_mult) * sf
        v_accel = math.sqrt(v_prev * v_prev + 2.0 * a_acc * ds)
        if v_accel < v_plan[i]:
            v_plan[i] = v_accel

    v_plan = np.clip(v_plan, 0.0, 200.0)

    # Instancia o objeto VelocityProfile e substitui o v_plan calculado
    vp = VelocityProfile(
        waypoints,
        grip_mult=grip_mult,
        sf=sf,
        ds_target=ds_target,
        smooth_window_m=smooth_window_m,
    )
    vp.v_plan = v_plan
    return vp
