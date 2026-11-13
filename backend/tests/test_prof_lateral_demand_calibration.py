"""Testes da calibração da razão de demanda lateral (PROF-GRIP-1 seq.).

Fórmula canônica PhysicsParams.a_lat (v=0 → μ·g; v>0 → acréscimo de
downforce), κ_path a partir de heading (círculo sintético com resposta
exata) e classificação/separação LIMPA vs SAÍDA.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from model_train.velocity_profile import PhysicsParams
from scripts.prof_lateral_demand_calibration import (
    kappa_path_from_heading,
    pass_summary,
    separation_stats,
    yaw_rate_series,
)


# --------------------------------------------- PhysicsParams.a_lat canônica
def test_a_lat_v_zero_eh_mu_vezes_g():
    # a_lat(0, grip) = mu·grip·g = 1.8·0.8·9.81
    esperado = PhysicsParams.mu * 0.8 * PhysicsParams.g
    assert PhysicsParams.a_lat(0.0, 0.8) == pytest.approx(esperado, rel=1e-9)
    # com grip 1.0: 1.8·9.81
    assert PhysicsParams.a_lat(0.0, 1.0) == pytest.approx(PhysicsParams.mu * GRAVITY
                                                          if (GRAVITY := PhysicsParams.g)
                                                          else 0.0, rel=1e-9)


def test_a_lat_downforce_acrescenta_com_v():
    base = PhysicsParams.a_lat(0.0, 0.8)
    a20 = PhysicsParams.a_lat(20.0, 0.8)
    a30 = PhysicsParams.a_lat(30.0, 0.842)
    assert a20 > base                       # downforce acrescenta
    assert a30 > a20                        # monótona em v
    # fórmula manual: mu_eff·(m·g + c_df·v²)/m
    manual = (PhysicsParams.mu * 0.842
              * (PhysicsParams.mass * PhysicsParams.g
                 + PhysicsParams.c_downforce() * 30.0 ** 2) / PhysicsParams.mass)
    assert a30 == pytest.approx(manual, rel=1e-9)
    # v=20 (0.8): faixa 14-16 do contexto; v=30 (0.842): downforce empurra ~20
    assert 13.0 < a20 < 17.0
    assert 17.0 < a30 < 23.0


# --------------------------------------- κ_path por heading (círculo exato)
def test_yaw_rate_e_kappa_path_circulo_sintetico():
    # círculo R=25 m percorrido a v=20 m/s: yaw_rate = 0.8 rad/s exato
    R, v, dt, n = 25.0, 20.0, 0.2, 100
    omega = v / R
    t = np.arange(n) * dt
    theta = omega * t + 0.3                 # offset de fase arbitrário
    x = R * np.cos(theta)
    y = R * np.sin(theta)
    yaw = yaw_rate_series(x, y, t)
    # 2 ticks de borda corrompidos pelo gradiente aninhado (documentado);
    # o interior é EXATO (cabeça-chord → θm+π/2, diferenças cancelam)
    assert np.allclose(yaw[2:-2], omega, atol=1e-9)
    kp = kappa_path_from_heading(v, float(yaw[5]))
    assert kp == pytest.approx(1.0 / R, rel=1e-9)
    # a_lat_path = v·yaw_rate = v²/R = 16.0
    assert v * float(yaw[5]) == pytest.approx(v * v / R, rel=1e-9)


def test_kappa_path_guard_v_zero():
    assert kappa_path_from_heading(0.0, 1.0) is None


# ------------------------------------- razão, desfecho e separação
def _pass_rows(v_apex, grip, lat_max, kappa=0.04, n=10):
    """Janela sintética de passagem: s 0→36, v≈v_apex, lat rampa até lat_max."""
    s = np.linspace(0.0, 36.0, n)
    v = np.full(n, v_apex)
    lat = np.linspace(0.5, lat_max, n)
    # corpo em círculo de raio 1/κ: yaw_rate = v·κ (demanda consistente)
    R = 1.0 / kappa
    omega = v_apex * kappa
    t = np.arange(n) * 0.2
    theta = omega * t
    x = R * np.cos(theta + 0.7)
    y = R * np.sin(theta + 0.7)
    return pd.DataFrame({
        "tick": np.arange(n) * 2, "t_s": t, "speed": v, "s": s, "lat": lat,
        "tyre_grip": np.full(n, grip), "body_x": x, "body_y": y,
    })


def test_pass_summary_razao_e_desfecho():
    rows = _pass_rows(v_apex=20.0, grip=0.842, lat_max=4.5, kappa=0.04)
    ps = pass_summary(rows, lambda s: 0.04, lambda s: 0.04)
    assert ps["desfecho"] == "LIMPA"
    assert ps["margem_m"] == pytest.approx(1.5, abs=1e-6)
    # payload com 3 decimais
    assert ps["a_lat_capacidade_ms2"] == pytest.approx(
        PhysicsParams.a_lat(20.0, 0.842), abs=1e-2)
    # demanda center = v²·κ com κ fixo → idêntica nas duas convenções
    assert ps["a_lat_center_suav_ms2"] == pytest.approx(20.0 ** 2 * 0.04, abs=1e-2)
    assert ps["a_lat_center_inst_ms2"] == pytest.approx(20.0 ** 2 * 0.04, abs=1e-2)
    # trajetória circular sintética: κ_path ≈ κ (0.04) — o MÁX de janela é
    # robusto aos 2 ticks de borda do gradiente aninhado
    assert ps["a_lat_path_max_ms2"] == pytest.approx(20.0 ** 2 * 0.04, abs=1e-2)
    assert ps["razao_path_max"] == pytest.approx(ps["razao_center_suav"], rel=5e-3)


def test_desfecho_saida_acima_de_6m():
    rows = _pass_rows(v_apex=20.0, grip=0.842, lat_max=6.24, kappa=0.04)
    ps = pass_summary(rows, lambda s: 0.04, lambda s: 0.04)
    assert ps["desfecho"] == "SAÍDA"
    assert ps["margem_m"] < 0.0


def test_separation_stats_separavel_e_overlap():
    limpa = [0.5, 0.6, 0.7]
    saida = [0.9, 1.0]
    s = separation_stats(limpa, saida)
    assert s["separavel"] is True
    assert s["limiar_separador"] == pytest.approx((0.7 + 0.9) / 2.0)
    overlap = separation_stats([0.5, 1.2], [0.9, 1.0])
    assert overlap["separavel"] is False
    assert overlap["overlap"] == pytest.approx(1.2 - 0.9)
    assert separation_stats([], [1.0])["separavel"] is None
