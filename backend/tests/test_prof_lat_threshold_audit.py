"""Testes da auditoria de limiares de margem lateral (PROF-GRIP-1 seq.).

Sintético com resposta conhecida: detecção de limiar, agrupamento em eventos
contíguos, custo cinemático de desaceleração, monotonicidade de ticks e
mapeamento de setor.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.experiments.controller.prof_lat_threshold_audit import (  # noqa: E402
    contiguous_events,
    decel_cost_s,
    threshold_audit,
)


def _rows(n: int, s, lat, v, t0=0.0):
    return pd.DataFrame({
        "tick": np.arange(n) * 2 + 100,
        "t_s": t0 + np.arange(n) * 0.2,
        "speed": v,
        "s": s,
        "lat": lat,
    })


CORNERS_FAKE = [
    {"id": "C01", "name": "quina A", "s0": 0.0, "s1": 80.0, "kmax": 0.05},
    {"id": "C02", "name": "quina B", "s0": 200.0, "s1": 280.0, "kmax": 0.04},
]
TRACK_LEN_FAKE = 400.0


# --------------------------------------------------- eventos contíguos
def test_contiguous_events_serie_conhecida():
    mask = np.array([0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0], dtype=bool)
    ev = contiguous_events(mask)
    assert ev == [(2, 4), (7, 7), (9, 10)]  # 3 runs contíguos
    durs = [(b - a + 1) * 0.2 for a, b in ev]
    assert durs == pytest.approx([0.6, 0.2, 0.4])


def test_contiguous_events_vazio_e_total():
    assert contiguous_events(np.zeros(5, dtype=bool)) == []
    assert contiguous_events(np.ones(4, dtype=bool)) == [(0, 3)]


# -------------------------------------------- custo cinemático de frenagem
def test_custo_desaceleracao_10_e_20_por_cento():
    assert decel_cost_s(20.0, 0.10) == pytest.approx(2.0 / 15.0)
    assert decel_cost_s(20.0, 0.20) == pytest.approx(4.0 / 15.0)
    assert decel_cost_s(20.0, 0.20) == pytest.approx(2.0 * decel_cost_s(20.0, 0.10))
    with pytest.raises(ValueError):
        decel_cost_s(20.0, 1.5)                # fração fora do contrato
    with pytest.raises(ValueError):
        decel_cost_s(-1.0, 0.10)


# ----------------------------------------------------- limiar e monotonia
def _synthetic_rows():
    n = 20
    lat = np.array([0.5] * 5 + [3.6] * 3 + [0.5] * 4 + [4.2] * 2 +
                   [0.5] * 3 + [5.1] * 3 + [0.5] * 0)  # 20 posições
    lat = lat[:n]
    s = np.linspace(0.0, 76.0, n)                    # dentro da janela C01
    v = np.linspace(30.0, 20.0, n)
    return _rows(n, s, lat, v)


def test_limiar_contagem_e_monotonicidade():
    rows = _synthetic_rows()
    a35 = threshold_audit(rows, 3.5, CORNERS_FAKE, TRACK_LEN_FAKE, n_laps=4)
    a50 = threshold_audit(rows, 5.0, CORNERS_FAKE, TRACK_LEN_FAKE, n_laps=4)
    # lat: 3 ticks ≥3.6, 2 ≥4.2, 3 ≥5.1 → monotonicidade de nesting
    assert a35["ticks_violacao"] == 3 + 2 + 3
    assert a50["ticks_violacao"] == 3
    assert a35["ticks_violacao"] >= a50["ticks_violacao"]
    # eventos: em 3.5 os dois primeiros blocos se fundem? não — são separados
    assert a35["n_eventos"] == 3
    assert a50["n_eventos"] == 1                     # só o bloco de 5.1
    assert a35["duracao_media_s"] == pytest.approx((3 + 2 + 3) / 3 * 0.2, abs=1e-3)
    # payload com 3 decimais
    assert a35["v_max_violacao_mps"] == pytest.approx(  # v decrescente no bloco 1
        float(rows["speed"].to_numpy()[5:8].max()), abs=1e-2)
    assert a35["pct_tempo"] == pytest.approx(100.0 * 8 / 20, abs=1e-3)


def test_mapeamento_setor_cronica_vs_outra():
    # bloco em s<80 → C01; gap fora do limiar; bloco em s∈[200,280] → C02
    n1, n2, ngap = 5, 5, 3
    s = np.concatenate([np.linspace(10.0, 60.0, n1),
                        np.full(ngap, 150.0),
                        np.linspace(210.0, 270.0, n2)])
    lat = np.concatenate([np.full(n1, 5.2), np.full(ngap, 0.2),
                          np.full(n2, 5.2)])
    v = np.full(n1 + ngap + n2, 25.0)
    rows = _rows(n1 + ngap + n2, s, lat, v)
    a = threshold_audit(rows, 5.0, CORNERS_FAKE, TRACK_LEN_FAKE, n_laps=4)
    assert a["setores"]["cronicas_C01_C06_C07_C08"] == 1   # C01
    assert a["setores"]["outras_curvas"] == 1             # C02
    assert a["setores"]["reta"] == 0
    assert a["n_eventos"] == 2


# ----------------------------------------- integração de custo no audit
def test_custo_projetado_no_audit():
    rows = _synthetic_rows()
    a = threshold_audit(rows, 3.5, CORNERS_FAKE, TRACK_LEN_FAKE, n_laps=4)
    custo = a["custo_desaceleracao"]["total_projeta_s_por_corrida"]
    # soma manual sobre os 3 eventos (v média de cada bloco)
    manual = 0.0
    for a_i, b_i in contiguous_events(rows["lat"].to_numpy() >= 3.5):
        v_med = float(rows["speed"].to_numpy()[a_i:b_i + 1].mean())
        manual += decel_cost_s(v_med, 0.10)
    assert custo["0.1"] == pytest.approx(manual, abs=1e-2)
    assert a["custo_desaceleracao"]["total_projeta_s_por_volta"]["0.1"] == \
        pytest.approx(custo["0.1"] / 4, abs=1e-2)  # payload com 3 decimais
