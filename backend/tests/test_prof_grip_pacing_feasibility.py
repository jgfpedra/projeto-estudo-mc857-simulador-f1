"""Testes da viabilidade do pacing sensível ao grip (PROF-CONTROL-1 seq.).

Sintético com resposta analítica exata: fórmula sqrt(grip/ref/(1+R)),
integração do tempo de volta (perfil constante e linear) e monotonicidade
do t_lap em função do grip.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from scripts.experiments.controller.prof_grip_pacing_feasibility import (
    apply_corner_scaling,
    lap_time,
    scale_factor,
)


# ------------------------------------------------------------ fórmula sqrt
def test_scale_factor_formula():
    assert scale_factor(0.85) == pytest.approx(1.0)          # topo = no-op
    assert scale_factor(0.80) == pytest.approx(math.sqrt(0.80 / 0.85))
    assert scale_factor(0.80, reserve=0.10) == pytest.approx(
        math.sqrt(0.80 / 0.85 / 1.10))
    # reserva de 10% na capacidade → fator menor por 1/sqrt(1.1)
    assert scale_factor(0.80, reserve=0.10) == pytest.approx(
        scale_factor(0.80) / math.sqrt(1.10))
    assert scale_factor(0.75) < scale_factor(0.78) < scale_factor(0.85)
    with pytest.raises(ValueError):
        scale_factor(0.0)
    with pytest.raises(ValueError):
        scale_factor(0.80, reserve=-0.1)


# ------------------------------------------------- integração analítica
def test_lap_time_constante():
    n = 250
    ds = 4.0
    v = np.full(n, 25.0)
    assert lap_time(v, ds) == pytest.approx(n * ds / 25.0, rel=1e-12)


def test_lap_time_linear_analitica():
    # 1/v(s) = a + b·s (recíproco-linear): a soma de Riemann do instrumento
    # (Σ ds/v(s_i), endpoint esquerdo) é EXATA para essa família
    n = 400
    ds = 4.0
    s = np.arange(n) * ds
    a, b = 0.05, -0.00002                    # w(L)=0.018 → v(L)=55.6 m/s
    v = 1.0 / (a + b * s)
    assert np.all(np.isfinite(v)) and v.min() > 0.0
    esperado = ds * (n * a + b * (ds * n * (n - 1) / 2.0))  # Σ ds·w(s_i)
    assert lap_time(v, ds) == pytest.approx(esperado, rel=1e-12)


# ------------------------------------------------ janelas e monotonicidade
def _base_profile(n=300, v_lo=15.0, v_hi=40.0):
    return np.linspace(v_hi, v_lo, n)  # desacelera ao longo "da pista"


def test_apply_scaling_somente_nas_janelas():
    v = _base_profile()
    s = np.arange(len(v)) * 4.0
    windows = [(200.0, 320.0)]
    v_cap = apply_corner_scaling(v, s, windows, 0.9)
    fora = (s < 200.0) | (s > 320.0)
    assert np.array_equal(v_cap[fora], v[fora])       # fora: byte-idêntico
    assert np.allclose(v_cap[~fora], v[~fora] * 0.9)  # dentro: fator exato


def test_apply_scaling_nunca_escala_para_cima():
    v = _base_profile()
    s = np.arange(len(v)) * 4.0
    v_cap = apply_corner_scaling(v, s, [(200.0, 320.0)], 1.0)  # grip = ref
    assert np.array_equal(v_cap, v)
    v_up = apply_corner_scaling(v, s, [(200.0, 320.0)], 1.3)
    assert np.array_equal(v_up, v)


def test_monotonicidade_menor_grip_tempo_maior_ou_igual():
    v = _base_profile()
    s = np.arange(len(v)) * 4.0
    windows = [(200.0, 320.0)]
    tempos = []
    for grip in (0.85, 0.84, 0.82, 0.80, 0.78, 0.75):
        fator = scale_factor(grip)
        tempos.append(lap_time(apply_corner_scaling(v, s, windows, fator), 4.0))
    assert tempos[0] == pytest.approx(lap_time(v, 4.0))  # grip=ref → no-op
    assert all(b >= a for a, b in zip(tempos, tempos[1:]))
    assert tempos[-1] > tempos[0]                        # 0.75 estritamente maior
