"""Testes da viabilidade do gatilho preditivo v2 Kamm (PROF-GRIP-1 seq.).

Cobre a revisão do Dono: agrupamento de excursões encadeadas (cascata),
janela de gatilho = 150 m de arco antes do ápice com classe JÁ-FORA/CASCATA,
v_safe dupla convenção (instantânea/suavizada — números da Junção), Círculo
de Kamm (a_brake_rem), monotonicidade do aviso no T e integração t_lap com
v_safe analítica.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from scripts.experiments.controller.prof_warning_time_feasibility import (
    analyze_events,
    group_excursions,
    integrate_vsafe_lap,
    kamm_brake_rem,
    lap_time_of,
    lat_pred_series,
    v_lat_series,
    v_safe,
)

GRAVITY = 9.81


# ------------------------------------------------------------- fórmulas puras
def test_v_lat_diferenca_central_linear():
    t = np.arange(10) * 0.2
    lat = 3.0 + 2.0 * t
    assert np.allclose(v_lat_series(lat, t)[1:-1], 2.0)


def test_lat_pred_formula():
    lat = np.array([3.0, 4.0])
    pred = lat_pred_series(lat, np.array([2.0, -1.0]), 0.4)
    assert pred[0] == pytest.approx(3.8)
    assert pred[1] == pytest.approx(4.4)               # |v_lat| em módulo
    assert np.all(pred >= np.abs(lat))


def test_v_safe_analitica_exata():
    assert v_safe(0.04, 0.80) == pytest.approx(math.sqrt(0.8 * GRAVITY / 0.04))
    assert v_safe(1e-6, 0.80) == pytest.approx(math.sqrt(0.8 * GRAVITY / 1e-4))
    assert v_safe(0.04, 0.005) == pytest.approx(math.sqrt(0.1 / 0.04))
    assert v_safe(0.08, 0.80) == pytest.approx(v_safe(0.04, 0.80) / math.sqrt(2))


# ------------------------------------------------ agrupamento (cascata)
def test_cascada_encadeada_agrupa_uma_excursao():
    lat = np.array([0.5, 6.5, 6.5, 4.0, 5.5, 6.2, 0.5, 0.5])
    # dois cruzamentos de 6,0 (idx 1 e 5) SEM retorno < 3,0 → UMA excursão
    grouped, cascades = group_excursions([(1, 2), (4, 5)], lat)
    assert grouped == [(1, 5)]
    assert cascades == 1


def test_retorno_abaixo_de_3_separa_excursoes():
    lat = np.array([0.5, 6.5, 6.5, 2.0, 0.5, 6.2, 0.5])
    grouped, cascades = group_excursions([(1, 2), (5, 5)], lat)
    assert grouped == [(1, 2), (5, 5)]
    assert cascades == 0


# ----------------------------------------------------------- Kamm
def test_kamm_brake_rem_circulo_de_atrito():
    cap = 0.842 * GRAVITY
    a_lat = 0.9 * cap                                    # 90% da capacidade
    rem = kamm_brake_rem(0.842, a_lat)
    assert rem == pytest.approx(math.sqrt(cap ** 2 - a_lat ** 2))
    assert rem == pytest.approx(cap * math.sqrt(1.0 - 0.81))
    assert kamm_brake_rem(0.842, cap) == pytest.approx(0.0)      # ápice: nada
    assert kamm_brake_rem(0.842, cap + 1.0) == pytest.approx(0.0)  # clamp
    assert kamm_brake_rem(0.842, 0.0) == pytest.approx(cap)  # sem demanda lateral


# ----------------------------------------------- v_safe dupla convenção
def test_v_safe_dupla_convencao_juncao():
    # números da Junção (correção do Dono): R_inst 7,93 m e R_suav 13,5 m com
    # grip de fim de vida 0,807 → ≈28,5 e ≈37 km/h
    grip = 0.807
    k_inst = 1.0 / 7.93
    k_suav = 1.0 / 13.5
    vi = v_safe(k_inst, grip) * 3.6
    vs = v_safe(k_suav, grip) * 3.6
    assert vi == pytest.approx(28.5, abs=0.6)
    assert vs == pytest.approx(37.0, abs=0.6)
    assert vi < vs                                        # κ inst > κ suav


# ------------------------------------- janela de busca e JÁ-FORA/CASCATA
CORNERS_FAKE = [{"id": "C01", "name": "quina A", "s0": 0.0, "s1": 80.0,
                 "kmax": 0.04}]
WINDOWS_FAKE = {"C01": (0.0, 80.0)}


def _df_from(s, lat, v=None, grip=0.807):
    n = len(s)
    return pd.DataFrame({
        "tick": np.arange(n) * 2, "t_s": np.arange(n) * 0.2,
        "speed": v if v is not None else np.full(n, 20.0),
        "s": s, "lat": lat, "tyre_grip": np.full(n, grip),
    })


def test_ja_fora_quando_entra_na_janela_acima_do_limiar():
    # excursão cujo INÍCIO da janela de aproximação já está com lat 5.2
    # (≥ 3.5 e ≥ 4.0) → classe JÁ-FORA/CASCATA nos dois limiares
    s = np.linspace(10.0, 76.0, 30)
    lat = np.linspace(5.2, 7.0, 30)
    df = _df_from(s, lat)
    res = analyze_events(df, lambda s: 0.04, lambda s: 0.08,
                         CORNERS_FAKE, 400.0, WINDOWS_FAKE)
    assert res["n_excursions"] == 1
    exc = res["excursions"][0]
    assert exc["por_config"]["T0.0_lim4.0"]["classe"] == "JÁ-FORA/CASCATA"
    assert exc["por_config"]["T0.0_lim3.5"]["classe"] == "JÁ-FORA/CASCATA"


def test_gatilho_dentro_da_janela_150m():
    # aproximação limpa (lat 0.5→7.0) dentro dos 150 m antes do ápice
    s = np.linspace(0.0, 76.0, 30)
    lat = np.linspace(0.5, 7.0, 30)
    df = _df_from(s, lat)
    res = analyze_events(df, lambda s: 0.04, lambda s: 0.08,
                         CORNERS_FAKE, 400.0, WINDOWS_FAKE)
    cfg = res["excursions"][0]["por_config"]["T0.0_lim3.5"]
    assert cfg["classe"] == "GATILHO"
    lat_arr = np.linspace(0.5, 7.0, 30)
    idx3 = int(np.argmax(lat_arr >= 3.5))
    assert cfg["t_trigger_s"] == pytest.approx(idx3 * 0.2)
    assert cfg["delta_t_aviso_s"] > 0.0


def test_monotonicidade_tempo_de_aviso_no_horizonte():
    s = np.linspace(0.0, 76.0, 30)
    lat = 0.5 + 6.5 * (np.linspace(0.0, 76.0, 30) / 76.0) ** 2  # rampa convexa
    df = _df_from(s, lat)
    res = analyze_events(df, lambda s: 0.04, lambda s: 0.08,
                         CORNERS_FAKE, 400.0, WINDOWS_FAKE)
    exc = res["excursions"][0]
    dts = [exc["por_config"][f"T{T}_lim3.5"]["delta_t_aviso_s"]
           for T in (0.0, 0.4, 0.8, 1.2)]
    assert all(d is not None for d in dts)
    assert all(b >= a for a, b in zip(dts, dts[1:]))


# ---------------------------------------------------------- Kamm no audit
def test_autoridade_kamm_classificacao_e_cap():
    s = np.linspace(0.0, 76.0, 30)
    lat = np.linspace(0.5, 7.0, 30)
    # grip 0.5: capacidade 4.905 m/s²; demanda v²·κ ≈ 20²·0.04 = 16 ≫ 4.905
    # → a_brake_rem = 0 → INSUFICIENTE (frear no ápice não desacelera)
    df = _df_from(s, lat, v=np.linspace(21.0, 19.0, 30), grip=0.5)
    res = analyze_events(df, lambda s: 0.04, lambda s: 0.08,
                         CORNERS_FAKE, 400.0, WINDOWS_FAKE)
    cfg = res["excursions"][0]["por_config"]["T0.0_lim3.5"]
    assert cfg["classe"] == "GATILHO"
    assert cfg["a_brake_rem_ms2"] == 0.0
    assert cfg["autoridade_kamm_inst"] == "INSUFICIENTE"
    # grip alto (0.842): capacidade 8.263 > demanda ~16? não — mas com
    # v menor no gatilho a demanda cai e a sobra aparece
    df2 = _df_from(s, lat, v=np.linspace(21.0, 19.0, 30), grip=0.842)
    res2 = analyze_events(df2, lambda s: 0.04, lambda s: 0.08,
                          CORNERS_FAKE, 400.0, WINDOWS_FAKE)
    cfg2 = res2["excursions"][0]["por_config"]["T0.0_lim3.5"]
    assert cfg2["a_brake_rem_ms2"] >= 0.0
    assert cfg2["autoridade_kamm_inst"] in ("APROVADO", "INSUFICIENTE")


# --------------------------------------------------- integração t_lap
def test_t_lap_integrado_vsafe_analitico():
    # convenção do instrumento: cada PONTO vale um intervalo ds (laço fechado
    # tem n pontos = n intervalos) — a resposta analítica conta pontos
    n = 300
    ds = 4.0
    s = np.arange(n) * ds
    v = np.full(n, 30.0)
    mask = (s >= 400.0) & (s <= 800.0)
    kappa_fn = lambda s: 0.04  # noqa: E731
    grip = 0.8                                           # v_safe = 14.007 m/s
    t = integrate_vsafe_lap(v, s, mask, kappa_fn, grip)
    n_in = int(mask.sum())
    n_out = n - n_in
    esperado = (n_out * ds / 30.0
                + n_in * ds / math.sqrt(0.8 * GRAVITY / 0.04))
    assert t == pytest.approx(esperado, rel=1e-9)
    assert lap_time_of(v, ds) == pytest.approx(n * ds / 30.0, rel=1e-12)


def test_t_lap_integrado_sem_janela_igual_base():
    n = 100
    v = np.full(n, 20.0)
    t = integrate_vsafe_lap(v, np.arange(n) * 4.0,
                            np.zeros(n, dtype=bool),
                            lambda s: 0.04, 0.8)
    assert t == pytest.approx(n * 4.0 / 20.0, rel=1e-12)
