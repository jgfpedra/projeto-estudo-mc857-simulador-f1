"""Testes da validação fora da amostra (PROF-GRIP-1 seq.).

Forma fechada exata com downforce (verificação pela EQUAÇÃO DEFINIDORA),
classificação cega pelo limiar 0,615, matriz de confusão sintética e
monotonia do t_lap no grip.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from model_train.velocity_profile import PhysicsParams
from scripts.prof_demand_out_of_sample import (
    classify,
    closed_form_vsafe,
    confusion,
)


GRAVITY = 9.81


# ------------------------------------------------- forma fechada exata
def test_closed_form_resolve_equacao_definidora():
    """v_safe deve SATISFAZER η·a_lat(v_safe, grip) = v_safe²·κ — a equação
    que define o teto com downforce (não é aproximação)."""
    for kappa in (0.02, 0.04, 0.0741, 0.1261):
        for grip in (0.807, 0.842):
            for eta in (0.60, 0.615):
                v = closed_form_vsafe(kappa, grip, eta)
                assert v is not None and v > 0.0
                a_lat = PhysicsParams.a_lat(v, grip)
                assert eta * a_lat == pytest.approx(v ** 2 * kappa, rel=1e-9)


def test_closed_form_denom_nao_positivo_retorna_none():
    c_m = PhysicsParams.c_downforce() / PhysicsParams.mass
    # κ ≤ η·(1,8·grip)·c_m → sem solução real (a curva não limita: o teto é
    # o próprio v_plan) → None e o chamador mantém v_plan
    kappa_baixa = 0.6 * (1.8 * 0.842) * c_m * 0.5
    assert closed_form_vsafe(kappa_baixa, 0.842, 0.60, c_m) is None


def test_closed_form_monotonia():
    # κ maior → v_safe menor (monótona decrescente)
    seq = [closed_form_vsafe(k, 0.842, 0.60) for k in (0.02, 0.04, 0.08, 0.1261)]
    assert all(b < a for a, b in zip(seq, seq[1:]))
    # grip menor → v_safe menor (a_lat menor)
    assert closed_form_vsafe(0.04, 0.807, 0.60) < closed_form_vsafe(0.04, 0.842, 0.60)


# ------------------------------------------------- classificação cega
def test_classify_limiar_0615():
    assert classify(0.615) == "LIMPA"      # ≤ limiar (fronteira inclusa)
    assert classify(0.6106) == "LIMPA"     # máx LIMPA da calibração
    assert classify(0.6205) == "SAÍDA"     # min SAÍDA da calibração
    assert classify(0.0) == "LIMPA"
    assert classify(1.0) == "SAÍDA"


# ------------------------------------------------ matriz de confusão
def test_confusion_matrix_sintetica():
    preds = ["SAÍDA", "SAÍDA", "LIMPA", "LIMPA", "SAÍDA", "LIMPA"]
    actuals = ["SAÍDA", "LIMPA", "LIMPA", "SAÍDA", "SAÍDA", "LIMPA"]
    cm = confusion(preds, actuals)
    assert cm["TP_saida_prev_e_real"] == 2
    assert cm["FP_saida_prev_limpa_real"] == 1
    assert cm["TN_limpa_prev_e_real"] == 2
    assert cm["FN_limpa_prev_saida_real"] == 1
    assert cm["acuracia"] == pytest.approx(4 / 6, abs=1e-3)
    assert confusion([], [])["acuracia"] is None


def test_confusion_perfeita_e_pessima():
    perfeita = confusion(["SAÍDA", "LIMPA"], ["SAÍDA", "LIMPA"])
    assert perfeita["acuracia"] == pytest.approx(1.0)
    pessima = confusion(["LIMPA", "SAÍDA"], ["SAÍDA", "LIMPA"])
    assert pessima["acuracia"] == pytest.approx(0.0)


# ------------------------------------------------------ guarda interna
def test_kamm_unused_guard_nao_existe():
    # o módulo não exporta nada de Kamm (a autoridade aqui é a forma fechada)
    import scripts.prof_demand_out_of_sample as mod
    assert not hasattr(mod, "kamm_brake_rem")


def test_gravity_constante():
    from scripts.prof_demand_out_of_sample import GRAVITY_MPS
    assert GRAVITY_MPS == pytest.approx(9.81)
