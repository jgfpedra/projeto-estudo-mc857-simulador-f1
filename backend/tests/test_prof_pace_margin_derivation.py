"""Testes da derivação v2 (escada fixa de η + perfil longitudinal completo).

Cobre o mandato: forma fechada + identidade física, denom ≤ 0 passthrough,
monotonicidade em η, fator 0,93 explícito, passada backward, passada
forward, limites de aceleração/frenagem, integração do perfil completo,
binding no ápice, extensão engajada, regra fixa η1/η2, ausência de
regressão para o preregistro e determinismo estrutural.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from model_train.velocity_profile import PhysicsParams
from scripts.prof_pace_margin_derivation import (
    ETA1,
    ETA2,
    ESCADA_ETA,
    MARGIN_CONTROLLER,
    SF_PERFIL,
    build_v_target_cap,
    descriptive_diagnosis,
    engagement_for_stage,
    propagate_longitudinal,
    vsafe_grip,
)

GRAVITY = 9.81
C_M = PhysicsParams.c_downforce() / PhysicsParams.mass


# ---------------------------------------------- forma fechada + identidade
def test_vsafe_formula_e_identidade_fisica():
    # v_safe satisfaz a EQUAÇÃO DEFINIDORA: η·a_lat(v_safe, grip) = v_safe²·κ_inst
    for kappa in (0.02, 0.04, 0.0741, 0.1261):
        for grip in (0.807, 0.842):
            for eta in (ETA1, ETA2):
                v = vsafe_grip(kappa, grip, eta)
                assert v is not None and v > 0.0
                a_lat = PhysicsParams.a_lat(v, grip)
                assert eta * a_lat == pytest.approx(v ** 2 * kappa, rel=1e-9)


def test_vsafe_denom_nao_positivo_passthrough():
    # κ ≤ η·(1,8·grip)·c_m → denom ≤ 0 → None (o chamador mantém v_plan)
    c_m = PhysicsParams.c_downforce() / PhysicsParams.mass
    grip, eta = 0.842, ETA2
    kappa_baixa = eta * (PhysicsParams.mu * grip) * c_m * 0.5
    assert vsafe_grip(kappa_baixa, grip, eta) is None


def test_vsafe_monotonia_em_eta_e_grip():
    seq = [vsafe_grip(0.04, 0.842, e) for e in (0.30, 0.40, 0.48848, 0.60)]
    assert all(b >= a for a, b in zip(seq, seq[1:]))   # η maior → v_safe maior
    assert vsafe_grip(0.04, 0.807, 0.40) <= vsafe_grip(0.04, 0.842, 0.40)


# --------------------------------- fator 0,93 explícito + passadas
def _kappa_flat(value):
    return lambda s: value


def test_margem_093_explicita_no_seed():
    # fora das janelas: v_seed = 0,93·v_base EXATAMENTE (fator explícito)
    n = 200
    v_base = np.full(n, 30.0)
    s = np.arange(n) * 4.0
    seed, _ = build_v_target_cap(v_base, np.zeros(n), s, {}, _kappa_flat(0.005),
                                 ETA1, 0.842)
    assert np.all(seed == MARGIN_CONTROLLER * v_base)
    # dentro da janela com κ baixa: v_safe > 0,93·v_plan → seed intacto
    seed2, _ = build_v_target_cap(v_base, np.zeros(n), s,
                                  {"C01": (0.0, 100.0)}, _kappa_flat(0.005),
                                  ETA1, 0.842)
    assert np.all(seed2 == MARGIN_CONTROLLER * v_base)


def test_passada_backward_frena_a_montante():
    # degrau: seed alto (30) → baixo (10) em κ=0 (reta): a passada backward
    # limita o ponto ANTERIOR pela frenagem disponível
    n = 6
    v_seed = np.array([30.0, 30.0, 30.0, 10.0, 10.0, 10.0])
    k_flat = np.zeros(n)
    cap = propagate_longitudinal(v_seed, k_flat, 4.0, grip=0.842)
    # o ponto imediatamente antes do degrau não pode exceder a frenagem
    v_next = 10.0
    a_max = PhysicsParams.a_lat(0.5 * (v_next + 30.0), 0.842) * SF_PERFIL
    a_drag = PhysicsParams.c_drag() * v_next * v_next / PhysicsParams.mass
    v_brake = math.sqrt(v_next ** 2 + 2.0 * max(a_max + a_drag, 0.3) * 4.0)
    assert cap[2] <= v_brake + 1e-9
    assert cap[4] == pytest.approx(10.0)                # dentro do vale: intacto
    assert np.all(cap >= 10.0)                          # nunca abaixo do seed


def test_passada_forward_limita_aceleracao():
    # degrau: seed baixo (10) → alto (30): a passada forward limita a subida
    n = 6
    v_seed = np.array([10.0, 10.0, 10.0, 30.0, 30.0, 30.0])
    k_flat = np.zeros(n)
    cap = propagate_longitudinal(v_seed, k_flat, 4.0, grip=0.842)
    a_acc = PhysicsParams.a_accel(10.0, 0.842) * SF_PERFIL
    v_accel = math.sqrt(10.0 ** 2 + 2.0 * a_acc * 4.0)
    assert cap[3] <= v_accel + 1e-9                     # pós-degrau limitado
    assert cap[0] == pytest.approx(10.0)
    assert np.all(cap <= 30.0)


def test_limites_longitudinais_canonicos():
    # a passada usa EXATAMENTE os limites canônicos do PhysicsParams
    v_seed = np.array([5.0, 5.0, 5.0, 5.0])
    k_flat = np.zeros(4)
    cap = propagate_longitudinal(v_seed, k_flat, 4.0, grip=0.842)
    # em κ=0 e seed plano, nada muda (sem frenagem/aceleração necessária)
    assert np.allclose(cap, 5.0)
    # a_accel disponível é positiva e finita (canônico)
    assert 0.0 < PhysicsParams.a_accel(10.0, 0.842) < 50.0
    # a_brake ≥ a_lat(10, 0.842) (o drag SOMA na frenagem)
    assert PhysicsParams.a_brake(10.0, 0.842) >= PhysicsParams.a_lat(10.0, 0.842)


def test_integracao_perfil_completo_fecha_o_laco():
    n = 300
    v_base = np.full(n, 30.0)
    s = np.arange(n) * 4.0
    seed, cap = build_v_target_cap(v_base, np.zeros(n), s,
                                   {"C01": (0.0, 100.0)},
                                   _kappa_flat(0.005), ETA1, 0.842)
    ds = 4.0
    t = float(np.sum(ds / np.maximum(cap, 0.5)))
    assert t == pytest.approx(n * ds / (MARGIN_CONTROLLER * 30.0), rel=1e-9)


# --------------------------------------- binding no ápice e extensão
def _synthetic_window_rows(lat_max=6.5):
    n = 40
    t = np.arange(n) * 0.2
    s = np.linspace(0.0, 76.0, n)
    lat = 0.5 + (lat_max - 0.5) * (np.linspace(0.0, 1.0, n) ** 2)
    v = np.linspace(21.0, 19.0, n)
    return pd.DataFrame({"tick": np.arange(n) * 2, "t_s": t, "speed": v,
                         "s": s, "lat": lat,
                         "tyre_grip": np.full(n, 0.807)})


CORNERS_FAKE = [{"id": "C01", "name": "quina A", "s0": 0.0, "s1": 80.0,
                 "kmax": 0.04}]
WINDOWS_FAKE = {"C01": (0.0, 80.0)}


def test_binding_no_apice_e_extensao():
    df = _synthetic_window_rows(lat_max=6.5)
    # v_base: perfil histórico ~28 m/s na janela; κ_inst 0.04 → v_safe(η1) ≪
    # → o cap binda na janela inteira
    n = len(df)
    v_base = np.full(n, 30.0)
    s_arr = df["s"].to_numpy(float)
    v_ctrl = MARGIN_CONTROLLER * v_base
    seed, cap = build_v_target_cap(v_base, np.zeros(n), s_arr, WINDOWS_FAKE,
                                   lambda s: 0.04, ETA1, 0.842)
    # v_safe no ápice da janela (κ=0.04, grip 0.842, η1):
    vs = vsafe_grip(0.04, 0.842, ETA1)
    assert vs < MARGIN_CONTROLLER * 30.0                # o cap binda
    exits = [{"i_exit": int(np.argmax(df["lat"].to_numpy() > 6.0)),
              "s_exit_m": float(s_arr[int(np.argmax(df["lat"].to_numpy() > 6.0))]),
              "t_exit_s": 0.0, "lat_max_m": 6.5}]
    e = engagement_for_stage(cap, v_ctrl, s_arr, WINDOWS_FAKE["C01"], exits,
                             4.0, "eta1|grip 0.842")
    assert e["cap_engajou_algum_ponto"] is True
    assert e["extensao_engajada_m"] > 0.0
    assert e["pct_da_janela"] > 0.0
    assert e["maior_trecho_continuo_m"] > 0.0
    assert e["v_capada_min_kmh"] <= e["v_historica_min_kmh"]


def test_regra_fixa_eta1_eta2():
    # escada pré-declarada: constantes de engenharia, NÃO derivadas de dados
    assert ETA1 == pytest.approx(0.8 * 0.6106, rel=1e-12)
    assert ETA1 == pytest.approx(0.48848, abs=1e-12)
    assert ETA2 == pytest.approx(0.40000, abs=1e-12)
    assert [(nome, valor) for nome, valor in ESCADA_ETA] == [
        ("eta1", ETA1), ("eta2", ETA2)]
    assert ETA2 < ETA1                                  # escalada aumenta corte


def test_ausencia_de_regressao_para_preregistro():
    # a escada é constante de módulo — nenhum campo de derivacao/regressão
    # alimenta os valores de η (estrutura: η vem só de ESCADA_ETA)
    import scripts.prof_pace_margin_derivation as mod
    assert mod.ETA1 == 0.8 * mod.MAX_RAZAO_LIMPA_CALIBRACAO
    assert mod.ETA2 == 0.40000
    # a escada é literal no módulo (não função de dados)
    assert isinstance(mod.ESCADA_ETA, list)


def test_diagnostico_rotulo_obrigatorio():
    # o rótulo obrigatório existe no módulo (ajuste C01 = diagnóstico
    # indicativo, SEM poder de derivar ou validar η)
    import scripts.prof_pace_margin_derivation as mod
    assert "sem poder de derivar ou validar η" in mod.DIAG_LABEL
    assert mod.DIAG_LABEL.startswith("diagnóstico indicativo")


# --------------------------------------------------- determinismo
def test_determinismo_estrutural():
    n = 200
    v_base = np.full(n, 30.0)
    s = np.arange(n) * 4.0
    args = (v_base, np.zeros(n), s, {"C01": (0.0, 100.0)},
            _kappa_flat(0.04), ETA1, 0.842)
    a = build_v_target_cap(*args)
    b = build_v_target_cap(*args)
    assert np.array_equal(a[0], b[0])                   # v_seed idêntico
    assert np.array_equal(a[1], b[1])                   # perfil idêntico
