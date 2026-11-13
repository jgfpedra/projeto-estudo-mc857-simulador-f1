"""PROF-CONTROL-1 — testes do instrumento de anatomia da Descida do Lago.

Sintético com resposta conhecida: fórmula do teto de esterço, segmentação de
laps por wrap de s, janela s ∈ [0, 80] m e classificação A/B/CINZA.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model_train.f1_env import F1MultiContextEnv  # noqa: E402
from scripts.experiments.controller.prof_lago_anatomy import (  # noqa: E402
    RATIO_A,
    RATIO_B,
    analyze_dataframe,
    classify_lap,
    kappa_interp_fn,
    segment_laps,
    steer_limit_rad,
)


# ---------------------------------------------------------------- fórmula
def test_steer_limit_formula_canonica():
    STEER_MAX = math.radians(45.0)
    STEER_MIN = 0.04
    STEER_V0 = 25.0
    assert steer_limit_rad(0.0) == pytest.approx(STEER_MAX)
    assert steer_limit_rad(25.0) == pytest.approx(STEER_MAX / 2.0)
    for v in np.linspace(0.0, 80.0, 81):
        esperado = max(STEER_MIN, STEER_MAX / (1.0 + (v / STEER_V0) ** 2))
        assert steer_limit_rad(float(v)) == pytest.approx(esperado)
        assert steer_limit_rad(float(v)) == pytest.approx(
            F1MultiContextEnv.steer_limit_rad(float(v)))
    # monótona decrescente e piso
    limits = [steer_limit_rad(float(v)) for v in np.linspace(0.0, 80.0, 81)]
    assert all(b <= a for a, b in zip(limits, limits[1:]))
    assert min(limits) >= STEER_MIN


# ------------------------------------------------------- segmentação laps
def test_segmentacao_laps_por_wrap():
    track_len = 100.0
    s = np.array([0.0, 10, 20, 30, 40, 50, 60, 70, 80, 90,
                  0.0, 10, 20, 30, 40, 50,
                  95.0, 97.0, 99.0, 1.0, 3.0], dtype=float)
    laps = segment_laps(s, track_len)
    assert list(laps[:10]) == [0] * 10
    # 50 -> 95 é incremento (sem wrap): continua na lap 1 até o wrap 99 -> 1
    assert list(laps[10:19]) == [1] * 9
    # wrap 99 -> 1 (queda de 98 > track_len/2) abre a 3ª lap
    assert list(laps[19:]) == [2] * 2


# ------------------------------------------------- janela e classificação
def _rows(s, v, steer, lat):
    n = len(s)
    return pd.DataFrame({
        "tick": np.arange(n),
        "t_s": np.arange(n) * 0.2,
        "speed": v,
        "s": s,
        "lat": lat,
        "steer_rad": steer,
    })


def test_classificacao_A_saturacao_mecanica():
    # aproximação com esterço no teto (ratio 1.0) antes da saída
    v = [20.0] * 6
    lim = steer_limit_rad(20.0)
    steer = [0.2 * lim, 0.5 * lim, 0.8 * lim, lim, lim, lim]
    s = [5.0, 15, 25, 35, 45, 55]
    lat = [0.5, 1.0, 2.0, 3.5, 5.0, 6.5]
    res = classify_lap(_rows(s, v, steer, lat), kappa_interp_fn(
        _circle_track()))
    assert "ratio_no_instante" in res["saidas"]  # saída detectada
    assert res["verdict"] == "A-SATURACAO-MECANICA"
    assert res["ratio_max_pre_saida"] == pytest.approx(1.0)
    assert res["n_ticks_ratio_ge_98pct"] >= 1


def test_classificacao_B_subesterco_controle():
    # folga grande: esterço a 50% do teto e mesmo assim saída
    v = [20.0] * 6
    lim = steer_limit_rad(20.0)
    steer = [0.1 * lim, 0.2 * lim, 0.3 * lim, 0.4 * lim, 0.45 * lim, 0.5 * lim]
    s = [5.0, 15, 25, 35, 45, 55]
    lat = [0.5, 1.5, 3.0, 4.5, 5.5, 6.5]
    res = classify_lap(_rows(s, v, steer, lat), kappa_interp_fn(
        _circle_track()))
    assert res["verdict"] == "B-SUBESTERCO-CONTROLE"
    assert res["ratio_max_pre_saida"] < RATIO_B


def test_classificacao_zona_cinza():
    lim = steer_limit_rad(20.0)
    r = 0.94  # entre RATIO_B (0.90) e RATIO_A (0.98)
    v = [20.0] * 4
    steer = [0.6 * lim, 0.8 * lim, r * lim, r * lim]
    s = [5.0, 15, 25, 35]
    lat = [1.0, 3.0, 5.0, 6.5]
    res = classify_lap(_rows(s, v, steer, lat), kappa_interp_fn(
        _circle_track()))
    assert RATIO_B <= res["ratio_max_pre_saida"] < RATIO_A
    assert res["verdict"] == "CINZA"


def test_janela_recorta_s_0_a_80():
    lim = steer_limit_rad(20.0)
    s = [0.0, 40.0, 79.0, 80.0, 81.0, 120.0, 200.0, 79.5]
    v = [20.0] * len(s)
    steer = [0.1 * lim] * len(s)
    lat = [1.0] * len(s)
    res = classify_lap(_rows(s, v, steer, lat), kappa_interp_fn(
        _circle_track()))
    assert res["n_ticks_janela"] == 5  # 0, 40, 79, 80, 79,5
    assert all(x <= 80.0 for x in res["ticks"]["s_m"])
    assert res["verdict"] == "SEM-SAIDA"  # |lat| nunca passa de 6,0


def test_analyze_dataframe_agregado():
    track_len = 400.0
    lim = steer_limit_rad(20.0)
    # 2 laps: primeira com saturação (A), segunda com folga (B) -> MISTO
    s1 = list(range(0, 300, 10))
    s2 = list(range(0, 300, 10))
    s = s1 + s2
    n1, n2 = len(s1), len(s2)
    v = [20.0] * (n1 + n2)
    steer = ([lim] * 4 + [0.5 * lim] * (n1 - 4)
             + [0.3 * lim] * n2)
    lat = ([1.0] + [2.0] * 2 + [6.5] + [7.0] * (n1 - 4)
           + [1.0] + [2.0] * 2 + [6.5] + [7.0] * (n2 - 4))
    df = _rows(s, v, steer, lat)
    kappa_fn = lambda sv: 0.0  # noqa: E731  (a_lat irrelevante p/ o veredito)
    res = analyze_dataframe(df, kappa_fn, track_len, window=(0.0, 80.0))
    assert res["n_laps"] == 2
    assert res["veredito_agregado"] == "MISTO:A-SATURACAO-MECANICA,B-SUBESTERCO-CONTROLE"
    assert res["laps"][0]["verdict"] == "A-SATURACAO-MECANICA"
    assert res["laps"][1]["verdict"] == "B-SUBESTERCO-CONTROLE"
    # janela: cada lap só tem ticks com s <= 80
    for lap in res["laps"]:
        assert all(x <= 80.0 for x in lap["ticks"]["s_m"])


def _circle_track() -> np.ndarray:
    """Pista sintética circular fechada (κ constante ≈ 1/100 m) para κ(s)."""
    th = np.linspace(0.0, 2.0 * np.pi, 200, endpoint=False)
    return np.stack([100.0 * np.cos(th), 100.0 * np.sin(th)], axis=1)


def test_kappa_interp_circulo():
    wps = _circle_track()
    k = kappa_interp_fn(wps)
    assert k(0.0) == pytest.approx(1.0 / 100.0, rel=0.05)
    assert k(55.0) == pytest.approx(1.0 / 100.0, rel=0.05)
