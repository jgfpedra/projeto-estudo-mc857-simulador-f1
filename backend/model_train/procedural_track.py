"""Gerador de pistas procedurais fechadas (Parte 2).

Gera circuitos sintéticos com features controladas (hairpins, esses, retas
de frenagem) para ampliar o pool de DAgger sem decorar circuitos reais.

Pipeline:
  1. Polígono base em elipse (seed determinística)
  2. Perturbação de vértices: hairpins (dentes profundos), esses
     (alternância interna/externa), retas (vértices colineares)
  3. Spline Catmull-Rom centrípeta (reutiliza track.py — sem overshoot)
  4. Subdivisão ≤4 m (preserva comprimento exato)
  5. GATE: kappa máx ≤ fronteira física × margem; professor ≥19/20

O R_min é LIDO de physics_frontier.json (nunca hardcoded).

Uso:
  from backend.model_train.procedural_track import generate_track
  track = generate_track(seed=42)  # Track object
  env = F1MultiContextEnv(track=track)  # ou por nome via resolve_track
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

_MODEL_DIR = Path(__file__).resolve().parent
_FRONTIER_PATH = _MODEL_DIR / "physics_frontier.json"


def load_r_min(v_ref: float = 10.0, grip: str = "real") -> float:
    """Lê R_min(v_ref) do physics_frontier.json. NUNCA hardcode."""
    if not _FRONTIER_PATH.exists():
        raise FileNotFoundError(
            f"physics_frontier.json não encontrado em {_FRONTIER_PATH}. "
            "Rode model_train/physics_radius_calibration.py primeiro.")
    data = json.load(open(_FRONTIER_PATH))
    frontier = data["frontier"][grip]
    key = str(int(v_ref))
    if key not in frontier or frontier[key] is None:
        # fallback: maior velocidade com fronteira conhecida
        known = {int(k): v for k, v in frontier.items() if v is not None}
        if not known:
            raise ValueError("Fronteira física vazia — rode a calibração.")
        best_v = max(known)
        return float(known[best_v])
    return float(frontier[key])


def _ellipse_radius(a: float, rx: float, ry: float) -> float:
    """Raio de uma elipse no ângulo polar a."""
    return rx * ry / math.sqrt((ry * math.cos(a)) ** 2 + (rx * math.sin(a)) ** 2)


def generate_track(
    seed: int,
    width_m: float = 12.0,
    target_length_m: float = 4000.0,
    n_hairpins: int = 1,
    n_esses: int = 1,
    n_base_points: int = 12,
    hairpin_margin_m: float = 2.0,
    rng_jitter: float = 0.15,
) -> Optional["object"]:
    """Gera uma pista procedural fechada.

    Args:
        seed: reprodutibilidade total (mesmo seed → mesma pista).
        width_m: largura do asfalto (10-15m).
        target_length_m: comprimento aproximado (3-7 km).
        n_hairpins: número de hairpins (dentes profundos no polígono).
        n_esses: número de sequências de esses (3 vértices alternados).
        n_base_points: vértices do polígono base (10-16).
        hairpin_margin_m: margem sobre R_min da fronteira física.
        rng_jitter: desordem aleatória dos vértices (0=regular, 0.3=caótico).

    Returns:
        Track object ou None se o gate de kappa rejeitar.
    """
    from backend.domain.track import (Track, _catmull_rom_spline,
                                       _resample_closed_polyline)

    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    # --- 1. R_min da fronteira (NUNCA hardcode) ---------------------------
    r_min_raw = load_r_min(v_ref=10.0, grip="real")
    r_hairpin = r_min_raw + hairpin_margin_m

    # --- 2. Polígono base em elipse ---------------------------------------
    # elipse com razão de aspecto aleatória (pistas não são circulares)
    aspect = rng.uniform(0.65, 0.95)
    r_x = target_length_m / (2 * math.pi)
    r_y = r_x * aspect

    # ângulos dos vértices (com jitter angular para variedade)
    base_angles = np.linspace(0, 2 * math.pi, n_base_points, endpoint=False)
    jitter = np_rng.uniform(-rng_jitter, rng_jitter, n_base_points) * (2 * math.pi / n_base_points)
    angles = np.sort(base_angles + jitter)

    # raios base com variação suave
    radii = np.array([_ellipse_radius(a, r_x, r_y) for a in angles])
    # perturbação radial aleatória (moderada — o spline suaviza)
    radii += np_rng.uniform(-0.08, 0.08, n_base_points) * r_x

    # --- 3. Pontos cartesianos base ---------------------------------------
    base_pts = [(radii[i] * math.cos(angles[i]), radii[i] * math.sin(angles[i]))
                for i in range(n_base_points)]

    # --- 3b. Features: INSERÇÃO de pontos que traçam a forma ---------------
    # O Catmull-Rom suaviza qualquer perturbação dos vértices base — para
    # criar HAIRPINS de R≈10m é preciso INSERIR 3 pontos que traçam o U-turn
    # diretamente (entrada → ápice → saída), não empurrar vértices.
    idx_all = list(range(n_base_points))
    # amostra hairpins SEM sobreposição (hi-1 e hi+1 não podem ser hairpin)
    candidates = idx_all[:]
    hairpin_indices = []
    for _ in range(min(n_hairpins, len(candidates) // 3)):
        if not candidates:
            break
        hi = rng.choice(candidates)
        hairpin_indices.append(hi)
        # remove hi e vizinhos dos candidatos
        candidates = [c for c in candidates
                      if abs(c - hi) > 1 and abs(c - hi) < n_base_points - 1]

    # FASE 1: computa os pontos U de cada hairpin (sem modificar a lista)
    hairpin_repl = {}
    for hi in hairpin_indices:
        prev = base_pts[(hi - 1) % n_base_points]
        here = base_pts[hi % n_base_points]
        nxt = base_pts[(hi + 1) % n_base_points]
        ddx = float(nxt[0] - prev[0]); ddy = float(nxt[1] - prev[1])
        dl = math.hypot(ddx, ddy) or 1.0
        ux, uy = ddx / dl, ddy / dl
        px, py = -uy, ux
        entry = (float(here[0] - ux * r_hairpin * 1.2),
                 float(here[1] - uy * r_hairpin * 1.2))
        apex = (float(here[0] + px * r_hairpin * 1.8),
                float(here[1] + py * r_hairpin * 1.8))
        exit_ = (float(here[0] + ux * r_hairpin * 1.2),
                 float(here[1] + uy * r_hairpin * 1.2))
        hairpin_repl[hi] = [entry, apex, exit_]

    # FASE 2: flattens (substitui os slots dos hairpins pelos trios)
    pts = []
    for i, p in enumerate(base_pts):
        if i in hairpin_repl:
            pts.extend(hairpin_repl[i])
        else:
            pts.append(p)

    # ESSES: insere pares alternados entre vértices não-hairpin
    # (após o flatten, os índices mudaram; usamos posições RELATIVAS)
    n_flat = len(pts)
    esse_amp = r_x * 0.10
    remaining_slots = [i for i in range(0, n_flat, max(1, n_flat // 12))
                      if not any(math.hypot(pts[i][0]-p[0], pts[i][1]-p[1]) < r_hairpin*3
                                 for p in pts if isinstance(p, tuple))]
    for ei in range(min(n_esses, max(0, len(remaining_slots) - 2))):
        si = remaining_slots[ei * 2 % len(remaining_slots)]
        p_here = pts[si % n_flat]
        # deslocamento perpendicular alternado
        ang = math.atan2(p_here[1], p_here[0]) + math.pi / 2
        for k, sign in enumerate([1, -1, 1]):
            idx = (si + k) % n_flat
            if idx < len(pts):
                off = sign * esse_amp * (0.8 if k == 1 else 1.0)
                pts[idx] = (pts[idx][0] + math.cos(ang) * off,
                            pts[idx][1] + math.sin(ang) * off)

    # remove duplicatas / pontos muito próximos (proteção numérica)
    clean_pts = []
    for p in pts:
        if not clean_pts or math.hypot(p[0] - clean_pts[-1][0],
                                        p[1] - clean_pts[-1][1]) > 3.0:
            clean_pts.append(p)
    if len(clean_pts) < 6:
        return None

    # --- 5. Spline + resample ≤4m ----------------------------------------
    smooth = _catmull_rom_spline(clean_pts, samples_per_segment=16)
    wps = _resample_closed_polyline(smooth, spacing_m=4.0)
    if len(wps) < 50:
        return None

    # --- 6. GATE de kappa (consome a fronteira) ---------------------------
    wps_arr = np.array(wps)
    # kappa via heading central (mesma fórmula de velocity_profile)
    dx = np.roll(wps_arr[:, 0], -1) - np.roll(wps_arr[:, 0], 1)
    dy = np.roll(wps_arr[:, 1], -1) - np.roll(wps_arr[:, 1], 1)
    heading = np.arctan2(dy, dx)
    dh = np.roll(heading, -1) - heading
    dh = (dh + math.pi) % (2 * math.pi) - math.pi
    # espaçamento médio (após subdivisão deve ser ≤4m)
    closed = np.vstack([wps_arr, wps_arr[:1]])
    seg_lens = np.hypot(np.diff(closed[:, 0]), np.diff(closed[:, 1]))
    ds_avg = float(seg_lens.mean())
    kappa_raw = dh / max(ds_avg, 0.5)
    # suavização 20m (igual ao v_plan)
    half_w = max(1, int(20.0 / ds_avg / 2))
    pad = np.concatenate([kappa_raw[-half_w:], kappa_raw, kappa_raw[:half_w]])
    ks = np.convolve(pad, np.ones(2 * half_w + 1) / (2 * half_w + 1), mode="valid")
    k_max = float(np.abs(ks).max())

    # limite: R_hairpin permitido (fronteira + margem) → kappa_max permitido
    kappa_max_allowed = 1.0 / max(r_hairpin * 0.8, 3.0)  # 20% de folga no gate
    if k_max > kappa_max_allowed * 1.3:
        return None  # rejeita: curvatura acima do física + folga

    # --- 7. Track object ---------------------------------------------------
    track_name = f"procedural_s{seed}"
    track = Track.from_waypoints(
        name=track_name,
        waypoints=[(float(x), float(y)) for x, y in wps],
        width_m=width_m,
        source="procedural",
        metadata={
            "seed": seed,
            "kappa_max": k_max,
            "r_hairpin_target": r_hairpin,
            "r_min_frontier": r_min_raw,
            "n_hairpins": n_hairpins,
            "n_esses": n_esses,
            "n_base_points": n_base_points,
            "width_m": width_m,
        },
    )
    return track


def generate_pool(seeds: List[int], **kwargs) -> List["object"]:
    """Gera um pool de pistas; retorna apenas as que passam no gate."""
    pool = []
    for seed in seeds:
        t = generate_track(seed, **kwargs)
        if t is not None:
            pool.append(t)
    return pool
