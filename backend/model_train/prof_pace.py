#!/usr/bin/env python3
"""PROF-PACE-1 — pacing preventivo com razão alvo fixa (η) nas 4 crônicas.

Mecanismo congelado no ``PREREG_PROF_PACE_1.md`` (freeze ``947c091``):

- **grip_mode = fixed**: ``grip_ref = 0,7895474400345001`` CONSTANTE durante
  toda a corrida (sem leitura por tick, sem atualização por volta);
- **escada de η pré-declarada** (nenhum valor livre): ``eta1 = 0,48848`` /
  ``eta2 = 0,40000``, selecionados somente por estágio;
- **ordem congelada:** ``v_ctrl = 0,93·v_plan`` →
  ``v_seed = min(v_ctrl, v_safe(s))`` → ``v_target_cap`` = passadas
  backward/forward de ``prof_curva.py`` sobre v_seed. O 0,93 fica EMBUTIDO
  no perfil capado — o controlador NÃO aplica margin adicional;
- **paridade estrutural com o instrumento:** o cap é construído por
  ``build_v_target_cap`` de ``scripts/experiments/controller/prof_pace_margin_derivation.py`` (o
  instrumento homologado) — mesma função, mesmas constantes, mesmas
  janelas canônicas;
- **cap restrito:** somente professor, somente Interlagos (pin
  ``164876196eb12174``), somente as janelas canônicas de C01/C06/C07/C08;
  **fora de Interlagos: no-op explícito** (perfil histórico como-is);
- pacing-only: esterço, rejoin, governor, física, pista frozen,
  ``run_race_10_cars.py`` intocados. Flag ``--prof-pace`` default OFF;
  OFF byte-idêntico ao professor histórico.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent

VERSION = "prof-pace-1/mechanism-v1.0"

GRIP_REF = 0.7895474400345001
GRIP_MODE = "fixed"
INTERLAGOS_SHA_PIN = "164876196eb12174"
ETA_LADDER: Dict[str, float] = {"eta1": 0.48848, "eta2": 0.40000}
KRONICAS = ("C01", "C06", "C07", "C08")


def eta_from_name(name: str) -> float:
    """Resolve o η da escada congelada (nenhum valor livre é aceito)."""
    if name not in ETA_LADDER:
        raise ValueError(
            f"η '{name}' fora da escada congelada {sorted(ETA_LADDER.keys())}")
    return float(ETA_LADDER[name])


def is_interlagos(track_sha: str) -> bool:
    """True somente se o SHA da pista frozen corresponde a Interlagos."""
    return str(track_sha) == INTERLAGOS_SHA_PIN


def chronic_windows(wps: np.ndarray, kappa_thresh: float = 0.006,
                    merge_gap_m: float = 40.0) -> Dict[str, Tuple[float, float]]:
    """Janelas canônicas (s0, s1) de C01/C06/C07/C08 via
    ``build_corner_definitions`` (fonte única das regiões)."""
    import sys as _sys
    backend_dir = Path(__file__).resolve().parent.parent
    for path in (str(backend_dir.parent), str(backend_dir)):
        if path not in _sys.path:
            _sys.path.insert(0, path)
    from scripts import saidas_verdict as SV  # noqa: E402
    corners = SV.build_corner_definitions(
        wps, kappa_thresh=kappa_thresh, merge_gap_m=merge_gap_m,
        generic_names=False)
    out: Dict[str, Tuple[float, float]] = {}
    for cid in KRONICAS:
        c = next((c for c in corners if c["id"] == cid), None)
        if c is None:
            raise ValueError(f"{cid} ausente na definição canônica de curvas")
        out[cid] = (float(c["s0"]), float(c["s1"]))
    return out


def kappa_inst_interpolator(wps: np.ndarray, ds_target: float = 4.0
                            ) -> Callable[[float], float]:
    """κ instantânea ASSINADA→|κ| interpolada (janela mínima, convenção do
    prereg — nunca a suavizada de 30 m)."""
    from backend.model_train.prof_curva import _instantaneous_kappa_profile
    k_s, k_i = _instantaneous_kappa_profile(
        np.asarray(wps, dtype=np.float64), ds_target=ds_target)
    total = float(k_s[-1] + (k_s[1] - k_s[0]))

    def kappa_inst(s: float) -> float:
        return abs(float(np.interp(float(s) % total, k_s, np.abs(k_i))))

    return kappa_inst


def build_capped(v_plan: np.ndarray, s_arr: np.ndarray, kappa_arr: np.ndarray,
                 windows4: Dict[str, Tuple[float, float]], kappa_inst_fn,
                 eta_name: str) -> Dict[str, Any]:
    """Perfil capado via o INSTRUMENTO homologado (paridade estrutural):
    ``build_v_target_cap(v_plan, |κ|, s_arr, janelas, κ_inst, η, grip_ref)``.

    ``v_plan`` = perfil histórico completo (com as passadas). Retorna dict
    com v_seed, v_target_cap e o interpolador v_at(s)."""
    from scripts.experiments.controller.prof_pace_margin_derivation import (  # noqa: E402
    build_v_target_cap,
    window_mask,
)
    eta = eta_from_name(eta_name)
    k_smooth = np.abs(np.asarray(kappa_arr, dtype=np.float64))
    seed, v_cap = build_v_target_cap(
        np.asarray(v_plan, dtype=np.float64), k_smooth,
        np.asarray(s_arr, dtype=np.float64), dict(windows4), kappa_inst_fn,
        eta, GRIP_REF)
    total = float(s_arr[-1] + (s_arr[1] - s_arr[0]))
    mask = window_mask(np.asarray(s_arr, dtype=np.float64), dict(windows4),
                       total)

    def v_at(s: float) -> float:
        return float(np.interp(float(s) % total, s_arr, v_cap))

    return {
        "eta_name": eta_name, "eta": eta, "grip_ref": GRIP_REF,
        "grip_mode": GRIP_MODE, "windows4": dict(windows4),
        "s_arr": s_arr, "v_seed": seed, "v_target_cap": v_cap,
        "mask": mask, "total_s_m": total, "v_at": v_at,
    }


def noop_reason(track_sha: str) -> str:
    """Motivo do no-op fora de Interlagos (para o log do runner)."""
    if is_interlagos(track_sha):
        return ""
    return (f"prof-pace no-op: pista {str(track_sha)[:16]} ≠ Interlagos "
            f"({INTERLAGOS_SHA_PIN[:16]})")
