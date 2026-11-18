"""PROF-CONTROL-1 — feedforward cinemático + lookahead modulado (professor solo).

Mecanismo pinado no §3 de ``PREREG_PROF_CONTROL_1.md`` (freeze ``53ea581``):

1. **Feedforward cinemático:** ``δ_ff(s) = arctan(L · κ_local(s))`` com
   ``L = 3,4 m`` (wheelbase canônica do ``ReferenceController``) e ``κ_local``
   instantânea ASSINADA (perfil canônico de janela mínima sobre os waypoints
   da pista frozen — nunca a suavizada de 30 m);
2. **Lookahead modulado:** ``ld_eff = clip(k_ld·v, ld_min, ld_max) · g(κ)``,
   ``g(κ) = 1/(1 + c_ld·|κ_local(s)|)``;
3. **Esterço comandado:** ``steer_cmd = clip((δ_ff + δ_pp)/steer_limit_rad(v),
   −1, 1)`` — o pure pursuit existente vira termo residual de correção
   lateral; pacing/v_plan/governor intocados;
4. **``c_ld`` derivado por regra fixada** a partir do segmento 3 de
   ``LAGO_ANATOMY.json`` (SHA ``81d3393f…``):
   ``c_ld = (ld_base/ld_alvo − 1)/κ_w`` com
   ``ld_base = clip(k_ld·v_exit, ld_min, ld_max)``,
   ``ld_alvo = s_exit − s_ratio_max`` e ``κ_w = κ máx da janela do segmento 3``
   — o valor que mantém o ponto de perseguição dentro do arco nas condições
   exatas em que a C01 sai.

Flag ``--prof-control`` default OFF; OFF é byte-idêntico ao professor
histórico (o caminho OFF não executa nenhuma das funções deste módulo).
Nenhum comportamento neural ou composite é alterado.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Optional

BACKEND = Path(__file__).resolve().parent.parent

ANATOMY_PATH = BACKEND / "experiments" / "prof-control-1" / "LAGO_ANATOMY.json"
SEGMENTO_ALVO = 3          # segmento 3 do LAGO_ANATOMY (primeira volta completa com saída)
K_LD_DEFAULT = 0.6
LD_MIN_M = 5.0
LD_MAX_M = 45.0
WHEELBASE_DEFAULT_M = 3.4

_DERIVED_CACHE: Optional[Dict[str, Any]] = None
_DERIVED_CACHE_KEY: Optional[str] = None


def delta_ff(kappa_signed: float, wheelbase_m: float = WHEELBASE_DEFAULT_M) -> float:
    """δ_ff = arctan(L·κ) — esterço cinemático de base, com o sinal da curva.

    Em reta (κ=0) vale 0.0: a reta preserva exatamente o comportamento OFF."""
    value = math.atan(float(wheelbase_m) * float(kappa_signed))
    if not math.isfinite(value):
        raise ValueError("delta_ff não finito")
    return value


def lookahead_gain_factor(kappa_abs: float, c_ld: float) -> float:
    """g(κ) = 1/(1 + c_ld·|κ|): 1,0 em reta; encurta o lookahead no ápice."""
    denom = 1.0 + float(c_ld) * abs(float(kappa_abs))
    if not math.isfinite(denom) or denom <= 0.0:
        raise ValueError("ganho de lookahead não finito")
    return 1.0 / denom


def steer_command(delta_ff_rad: float, delta_pp_rad: float,
                  steer_limit_rad: float) -> float:
    """steer_cmd = clip((δ_ff + δ_pp)/limite, −1, 1) — confinamento estrito."""
    if not all(math.isfinite(float(x)) for x in (delta_ff_rad, delta_pp_rad,
                                                 steer_limit_rad)):
        raise ValueError("entradas de esterço não finitas")
    if float(steer_limit_rad) <= 0.0:
        raise ValueError("limite de esterço deve ser positivo")
    return float(max(-1.0, min(1.0, (float(delta_ff_rad) + float(delta_pp_rad))
                                    / float(steer_limit_rad))))


def derive_c_ld(anatomy_path: Optional[Path] = None,
                k_ld: float = K_LD_DEFAULT,
                ld_min: float = LD_MIN_M,
                ld_max: float = LD_MAX_M,
                log: bool = True) -> Dict[str, Any]:
    """Deriva ``c_ld`` pela regra pinada no §3 do prereg (segmento 3).

    Registra todos os intermediários e falha loud em dados ausentes ou não
    finitos. Cacheada por (caminho, k_ld, ld_min, ld_max) por processo."""
    global _DERIVED_CACHE, _DERIVED_CACHE_KEY
    path = Path(anatomy_path) if anatomy_path is not None else ANATOMY_PATH
    cache_key = f"{path}|{k_ld}|{ld_min}|{ld_max}"
    if _DERIVED_CACHE is not None and _DERIVED_CACHE_KEY == cache_key:
        return dict(_DERIVED_CACHE)

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    lap = next((l for l in data["laps"]
                if l.get("segmento") == SEGMENTO_ALVO), None)
    if lap is None:
        raise ValueError(f"segmento {SEGMENTO_ALVO} ausente em {path}")
    saida = lap["saidas"]
    tick_exit = saida.get("tick")
    if tick_exit is None:
        raise ValueError("segmento 3 sem saída registrada (ocorreu=False?)")

    ticks = lap["ticks"]
    idx = ticks["t_s"].index(saida["t_s"])  # igualdade exata (mesma fonte)
    v_exit = float(ticks["v_mps"][idx])
    s_exit = float(saida["s_m"])
    s_ratio_max = float(lap["s_no_ratio_max"])
    kappa_w = float(lap["kappa_max_1m"])

    ld_base = float(min(max(k_ld * v_exit, ld_min), ld_max))
    ld_alvo = s_exit - s_ratio_max
    if ld_alvo <= 0.0:
        raise ValueError("ld_alvo não positivo: arco razão-máx→saída inválido")
    if kappa_w <= 0.0:
        raise ValueError("kappa_w não positivo")
    c_ld = (ld_base / ld_alvo - 1.0) / kappa_w

    record = {
        "c_ld": float(c_ld),
        "v_exit_mps": v_exit,
        "s_exit_m": s_exit,
        "s_ratio_max_m": s_ratio_max,
        "ld_base_m": ld_base,
        "ld_alvo_m": ld_alvo,
        "kappa_w_1m": kappa_w,
        "k_ld": float(k_ld),
        "ld_min_m": float(ld_min),
        "ld_max_m": float(ld_max),
        "segmento": SEGMENTO_ALVO,
        "fonte": str(path),
        "fonte_sha256_prefixo": str(data.get("origem", {}).get("csv_sha256", ""))[:16],
    }
    if not all(math.isfinite(float(record[key])) for key in
               ("c_ld", "v_exit_mps", "s_exit_m", "s_ratio_max_m",
                "ld_base_m", "ld_alvo_m", "kappa_w_1m")):
        raise ValueError("derivação de c_ld produziu valor não finito")
    if c_ld < 0.0:
        raise ValueError("c_ld negativo: ld_base < ld_alvo — prereg violado")

    if log:
        print(f"[prof-control] c_ld derivado (regra §3 do prereg, segmento "
              f"{SEGMENTO_ALVO} de {path.name}): v_exit={v_exit:.6f} m/s | "
              f"s_exit={s_exit:.3f} | s_ratio_max={s_ratio_max:.3f} | "
              f"ld_base={ld_base:.6f} | ld_alvo={ld_alvo:.3f} | "
              f"kappa_w={kappa_w:.6f} -> c_ld={c_ld:.6f}")
    _DERIVED_CACHE = dict(record)
    _DERIVED_CACHE_KEY = cache_key
    return dict(record)
