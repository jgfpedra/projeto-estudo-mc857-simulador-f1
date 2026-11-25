"""PROF-GRIP-1 — pacing grip-sensível nas 4 crônicas de Interlagos.

Mecanismo pinado no §2 de ``PREREG_PROF_GRIP_1.md`` (freeze ``715c677``):

    fator(t)      = min(1, sqrt(max(0,1, grip_atual(t)) / 0,85)) · sqrt(1/1,10)
    v_target(s,t) = v_plan(s) · fator(t)          [SOMENTE nas janelas canônicas
                    de C01/C06/C07/C08 — fora delas: v_plan histórico]
    v_exec        = min(v_tgt_histórico, v_target)  # o teto nunca eleva

- ``grip_atual(t)`` = ``tyre.grip_multiplier(weather.kind, track_temp)`` do
  estado físico do tick — a MESMA expressão da coluna telemetrada
  ``tyre_grip`` (fonte única de verdade);
- pacing-only: nenhum termo de esterço; rejoin/governor/física intocados;
- flag ``--prof-grip`` default OFF: o caminho OFF não executa nenhuma função
  deste módulo (bit-identidade byte a byte).

Funções puras e testáveis; a única dependência externa é o
``build_corner_definitions`` canônico (``scripts/saidas_verdict.py``), via
import preguiçoso.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

GRIP_REF = 0.85
GRIP_FLOOR = 0.1            # piso de finitude (fórmula do mandato)
F_RESERVA = math.sqrt(1.0 / 1.10)   # 10% de margem física (§2 do prereg)
WINDOW_CORNERS = ("C01", "C06", "C07", "C08")

VERSION = "prof-grip-1/mechanism-v1.0"


def fator_grip(grip_atual: float, grip_ref: float = GRIP_REF,
               f_reserva: float = F_RESERVA) -> float:
    """fator(grip) = min(1, sqrt(max(0,1, grip)/grip_ref)) · f_reserva.

    Monótono não-decrescente no grip; teto 1,0·f_reserva (nunca escala para
    cima); piso de finitude max(0,1, grip) conforme o mandato."""
    grip = max(float(GRIP_FLOOR), float(grip_atual))
    sqrt_part = math.sqrt(grip / float(grip_ref))
    value = min(1.0, sqrt_part) * float(f_reserva)
    if not math.isfinite(value):
        raise ValueError("fator de grip não finito")
    return value


def corner_windows(wps, kappa_thresh: float = 0.006,
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
    for cid in WINDOW_CORNERS:
        c = next((c for c in corners if c["id"] == cid), None)
        if c is None:
            raise ValueError(f"{cid} ausente na definição canônica de curvas")
        out[cid] = (float(c["s0"]), float(c["s1"]))
    return out


def grip_in_window(s: float, windows) -> bool:
    if hasattr(windows, "values"):  # dict {cid: (s0, s1)} do caminho do runner
        windows = windows.values()
    return any(float(w[0]) <= float(s) <= float(w[1]) for w in windows)


def cap_v_target(v_plan_here: float, v_tgt_historico: float, s: float,
                 grip_atual: float, windows) -> float:
    """Teto grip-sensível: dentro das janelas, alvo = v_plan(s)·fator(t)
    (fórmula §2 do prereg, SEM o margin histórico — que é restaurado pelo
    min contra o alvo histórico); fora das janelas: alvo histórico exato.
    O teto nunca ELEVA o alvo. Aceita dict {cid: (s0,s1)} ou sequência."""
    if not all(math.isfinite(float(x)) for x in (v_plan_here, v_tgt_historico,
                                                 s, grip_atual)):
        raise ValueError("entradas do teto grip-sensível não finitas")
    v_tgt = float(v_tgt_historico)
    if grip_in_window(s, windows):
        v_cap = float(v_plan_here) * fator_grip(grip_atual)
        v_tgt = min(v_tgt, v_cap)
    if not math.isfinite(v_tgt):
        raise ValueError("v_target não finito")
    return v_tgt


def guard_professor_path(controller: str, has_mixed: bool,
                         professor_in_mixed: bool) -> bool:
    """Guarda do runner: --prof-grip só engaja no caminho professor
    (solo professor, ou grupo professor explícito em --mixed)."""
    if controller == "professor" and not has_mixed:
        return True
    if controller == "mixed" and professor_in_mixed:
        return True
    return False
