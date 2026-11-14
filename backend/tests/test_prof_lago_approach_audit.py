"""PROF-CONTROL-1 — testes da auditoria de aproximação/entrada da C01.

Sintético com resposta conhecida: zona de aproximação (vmax, início de
frenagem com brk > 0.05), correlação tyre_grip ↔ lat_max e margem de pista
com capacidade μ_eff·g.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.experiments.controller.prof_lago_approach_audit import (  # noqa: E402
    APPROACH_ZONE_M,
    BRAKE_THRESHOLD,
    GRAVITY,
    HALF_WIDTH_M,
    analyze_dataframe,
    approach_summary,
    corner_summary,
    pearson,
)


def _rows(n: int, s, v, lat, brk, th=None, grip=0.842, life=100.0,
          steer=0.0, t0=0.0):
    return pd.DataFrame({
        "tick": np.arange(n) * 2 + 100,
        "t_s": t0 + np.arange(n) * 0.2,
        "speed": v,
        "s": s,
        "lat": lat,
        "brk": brk,
        "th": th if th is not None else [0.3] * n,
        "steer_rad": steer if not np.isscalar(steer) else [steer] * n,
        "tyre_grip": [grip] * n,
        "tyre_life": [life] * n,
    })


TRACK_LEN = 4160.437


# ------------------------------------------------- zona de aproximação
def test_zona_aproximacao_vmax_e_frenagem():
    # janela de 150 m: s de 4010.437 a 4160.437, frenagem a 80 m da linha
    s = [TRACK_LEN - 150.0 + 4.0 * i for i in range(37)]
    v = [80.0 - 0.5 * i for i in range(37)]          # desacelerando
    brk = [0.0] * 10 + [0.6] * 27                    # freia no 11º tick
    lat = [0.1] * 37
    rows = _rows(len(s), s, v, lat, brk)
    a = approach_summary(rows, TRACK_LEN)
    assert a["presente"] is True
    assert a["v_max_kmh"] == pytest.approx(80.0 * 3.6)
    assert a["v_max_em_s"] == pytest.approx(s[0], abs=1e-6)
    assert a["brake_start_s_m"] == pytest.approx(s[10], abs=1e-6)
    assert a["v_no_inicio_frenagem_kmh"] == pytest.approx(v[10] * 3.6)
    assert a["dist_frenagem_linha_m"] == pytest.approx(TRACK_LEN - s[10], abs=1e-6)
    assert a["lat_final_m"] == pytest.approx(0.1)


def test_deteccao_inicio_frenagem_limiar_exato():
    s = [TRACK_LEN - 20.0, TRACK_LEN - 10.0, TRACK_LEN - 5.0]
    brk = [0.05, 0.0500001, 0.0]                     # 0.05 exato NÃO detecta
    rows = _rows(3, s, [80.0, 78.0, 76.0], [0.1] * 3, brk)
    a = approach_summary(rows, TRACK_LEN)
    assert a["brake_start_s_m"] == pytest.approx(TRACK_LEN - 10.0, abs=1e-6)
    assert a["brake_start_t_s"] == pytest.approx(0.2)


# ------------------------------------------- correlação pneu ↔ espalhamento
def test_correlacao_grip_vs_lat_max_negativa_forte():
    grips = [0.842, 0.833, 0.825, 0.816, 0.807]
    lats = [5.940, 6.050, 6.069, 6.243, 6.261]
    r = pearson(grips, lats)
    assert r is not None and r < -0.95
    assert pearson(grips, [1.0] * 5) is None          # variância zero → None
    assert pearson([0.842], [5.94]) is None           # n=1 → None


def test_analyze_dataframe_correlacao_e_contagem():
    # 3 laps (3 wraps) sobre track_len curto; lat_max cresce com grip caindo
    track_len = 400.0
    rows = []
    grips = [0.842, 0.807, 0.790]
    latmax = [5.94, 6.24, 6.30]
    for lap, (g, lm) in enumerate(zip(grips, latmax)):
        base = lap * track_len
        s_lap = list(np.arange(0.0, track_len, 10.0))
        for i, s_rel in enumerate(s_lap):
            s_abs = (base + s_rel) % track_len
            if lap >= 1 and s_rel == 0.0:
                s_abs = 0.0  # wrap no primeiro tick do lap seguinte
            # janela C01 (s<=80): lat cresce até latmax; resto: 0.1
            lat = (lm if s_rel <= 80.0 and i >= 4 else 0.1)
            v = 20.0
            rows.append((s_abs, v, lat, 0.0, 0.3, g, 100.0 - lap * 7.0))
    df = pd.DataFrame(rows, columns=["s", "speed", "lat", "brk", "th",
                                     "tyre_grip", "tyre_life"])
    df["tick"] = np.arange(len(df)) * 2
    df["t_s"] = np.arange(len(df)) * 0.2
    df["steer_rad"] = 0.0

    kappa_fn = lambda s: 0.0  # noqa: E731  (demanda irrelevante aqui)

    res = analyze_dataframe(df, kappa_fn, track_len)
    assert res["n_passes"] == 2
    r = res["correlacao_tyre_grip_vs_lat_max"]["pearson_r"]
    assert r is not None and r < 0.0  # menos grip → mais lat_max
    assert res["passes_com_saida"] == 2  # laps 2 e 3 cruzam 6,0 m


# ------------------------------------------------------ margem e capacidade
def test_margem_pista_e_capacidade():
    rows = _rows(5, [10.0, 20.0, 30.0, 40.0, 50.0],
                 [21.0] * 5, [1.0, 3.0, 5.0, 5.9, 6.24],
                 [0.0] * 5, grip=0.816, life=79.2)
    kappa_fn = lambda s: 0.02  # noqa: E731  (a_lat = 441*0.02 = 8.82 m/s²)
    c = corner_summary(rows, kappa_fn)
    assert c["lat_max_m"] == pytest.approx(6.24)
    assert c["margem_pista_m"] == pytest.approx(HALF_WIDTH_M - 6.24)
    assert c["saiu"] is True                          # margem negativa
    assert c["tyre_life_pct_no_latmax"] == pytest.approx(79.2)
    assert c["a_lat_demanda_ms2"] == pytest.approx(21.0 ** 2 * 0.02, rel=1e-6)
    # o instrumento reporta a capacidade com 3 decimais
    assert c["a_lat_capacidade_ms2"] == pytest.approx(0.816 * GRAVITY, abs=1e-2)
    # o instrumento reporta razões com 3 decimais
    assert c["demanda_sobre_capacidade"] == pytest.approx(
        (21.0 ** 2 * 0.02) / (0.816 * GRAVITY), abs=1e-3)
    assert c["demanda_sobre_capacidade"] > 1.0        # deslizando largo


def test_margem_positiva_nao_sai():
    rows = _rows(3, [10.0, 20.0, 30.0], [20.0] * 3, [1.0, 2.0, 5.94],
                 [0.0] * 3, grip=0.842, life=100.0)
    c = corner_summary(rows, lambda s: 0.0)
    assert c["saiu"] is False                         # 5.94 < 6.0 (limpo por 6 cm)
    assert c["margem_pista_m"] == pytest.approx(0.06)
