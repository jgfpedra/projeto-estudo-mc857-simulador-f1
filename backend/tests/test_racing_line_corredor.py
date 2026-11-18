"""RACING-LINE-1 Task 3 — testes unitários dos gates geométricos do candidato.

Sintético com resposta conhecida: quina de 90° à direita com pernas longas.
O fillet de raio R tem pontos de tangência a R·tan(45°) do ápice em cada perna
e desvio máximo R·(1−cos 45°) em relação à polilinha:
- R=18,0 m → desvio máximo 5,273 m ≤ 6,0 m (corredor PASS);
- R=30,0 m → desvio máximo 8,787 m > 6,0 m (corredor FAIL).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.experiments.racing_line.racing_line_1_corredor import (  # noqa: E402
    build_virtual_line,
    c1_deviation_deg,
    evaluate_gates,
    segments_self_intersect,
    vertex_geometry,
)

# Pernas: +x em y=0, quina à direita em (100,0), −y em x=100, retorno longe.
# Subdividido a ~3,75 m (resolução da pista frozen) — o campo de tangente
# centrado interpolado exige resolução fina para ser bem-comportado.
_p1 = np.linspace(np.array([-50.0, 0.0]), np.array([100.0, 0.0]), 41)
_p2 = np.linspace(np.array([100.0, -3.75]), np.array([100.0, -150.0]), 40)
WPS_SYN = np.vstack([_p1, _p2, [
    [150.0, -150.0],
    [150.0, -200.0],
    [-50.0, -200.0],
]])
CUM_SYN, TOTAL_SYN = vertex_geometry(WPS_SYN)  # quina: s=150; tangências 150±R


def _fillet_limits(R: float) -> tuple:
    d = R * np.tan(np.radians(45.0))
    return 150.0 - d, 150.0 + d


def test_corredor_contem_raio_18():
    s_a, s_b = _fillet_limits(18.0)
    virt, info = build_virtual_line(WPS_SYN, CUM_SYN, s_a, s_b, 18.0, 1.0)
    gates = evaluate_gates(virt, WPS_SYN, CUM_SYN, info, s_a, s_b)
    assert info["ds_arc_m"] <= 1.0
    # desvio máximo teórico R(1-cos45°) = 5,273 m (sonda 0,05 m ⇒ cota 0,025)
    assert gates["corredor"]["desvio_max_m"] == pytest.approx(18.0 * (1 - np.cos(np.pi / 4)), abs=0.03)
    assert gates["corredor"]["desvio_max_m"] + gates["corredor"]["cota_erro_m"] <= 6.0
    assert gates["corredor"]["ok"] is True


def test_corredor_estoura_com_raio_30():
    s_a, s_b = _fillet_limits(30.0)
    virt, info = build_virtual_line(WPS_SYN, CUM_SYN, s_a, s_b, 30.0, 1.0)
    gates = evaluate_gates(virt, WPS_SYN, CUM_SYN, info, s_a, s_b)
    assert gates["corredor"]["desvio_max_m"] > 6.0
    assert gates["corredor"]["ok"] is False


def test_c1_emendas_quase_zero_no_sintetico():
    s_a, s_b = _fillet_limits(18.0)
    virt, info = build_virtual_line(WPS_SYN, CUM_SYN, s_a, s_b, 18.0, 1.0)
    gates = evaluate_gates(virt, WPS_SYN, CUM_SYN, info, s_a, s_b)
    assert gates["c1_emendas"]["emenda_a_deg"] < 1e-9
    assert gates["c1_emendas"]["emenda_b_deg"] < 1e-9
    assert gates["c1_emendas"]["ok"] is True


def test_fechamento_e_topologia_no_sintetico():
    s_a, s_b = _fillet_limits(18.0)
    virt, info = build_virtual_line(WPS_SYN, CUM_SYN, s_a, s_b, 18.0, 1.0)
    gates = evaluate_gates(virt, WPS_SYN, CUM_SYN, info, s_a, s_b)
    assert gates["fechamento"]["ok"] is True
    assert gates["fechamento"]["erro_tangencia_a_m"] < 1e-12
    assert gates["fechamento"]["erro_tangencia_b_m"] < 1e-12
    assert gates["topologia"]["auto_intersecao"] is False
    assert gates["topologia"]["ok"] is True


def test_externo_invariante_byte_identico():
    s_a, s_b = _fillet_limits(18.0)
    virt, info = build_virtual_line(WPS_SYN, CUM_SYN, s_a, s_b, 18.0, 1.0)
    gates = evaluate_gates(virt, WPS_SYN, CUM_SYN, info, s_a, s_b)
    assert gates["externo_invariante"]["ok"] is True
    assert gates["externo_invariante"]["vertices_externos_ausentes"] == []
    assert gates["externo_invariante"]["vertices_internos_remanescentes"] == []
    # vértices externos preservados com igualdade exata de floats
    virt_set = {tuple(p) for p in map(tuple, virt)}
    for i in info["keep_lo"] + info["keep_hi"]:
        assert tuple(WPS_SYN[i]) in virt_set


def test_arco_nao_altera_vertices_frozen_em_interlagos():
    """Invariância do trecho externo na pista real (limites da Emenda nº 1)."""
    import json
    from scripts.experiments.racing_line.racing_line_1_corredor import S_A_M, S_B_M, TRACK_FILE, TRACK_SHA_PIN
    with TRACK_FILE.open("r", encoding="utf-8") as f:
        track = json.load(f)
    assert track["sha256"] == TRACK_SHA_PIN
    wps = np.array(track["waypoints"], dtype=np.float64)
    cum, _ = vertex_geometry(wps)
    virt, info = build_virtual_line(wps, cum, S_A_M, S_B_M, 18.0, 1.0)
    virt_set = {tuple(p) for p in map(tuple, virt)}
    for i in info["keep_lo"] + info["keep_hi"]:
        assert tuple(wps[i]) in virt_set
    for i in range(len(wps)):
        if S_A_M < cum[i] < S_B_M:
            assert tuple(wps[i]) not in virt_set


def test_c1_deviation_graduacoes():
    t0 = np.array([1.0, 0.0])
    assert c1_deviation_deg(t0, t0) == pytest.approx(0.0)
    assert c1_deviation_deg(t0, np.array([0.0, 1.0])) == pytest.approx(90.0)
    assert c1_deviation_deg(t0, -t0) == pytest.approx(180.0)


def test_auto_intersecao_detector():
    quadrado = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    inter, _ = segments_self_intersect(quadrado)
    assert inter is False
    gravata = np.array([[0.0, 0.0], [10.0, 10.0], [10.0, 0.0], [0.0, 10.0]])
    inter, par = segments_self_intersect(gravata)
    assert inter is True and par is not None
