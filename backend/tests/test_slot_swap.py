"""Testes mínimos da análise de slot-swap (FASE 5 A1)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(PROJECT_ROOT), str(PROJECT_ROOT / 'backend')):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.model_train.slot_swap_analysis import (slot_swaps_from_trace,
                                                    summarize_swaps)


def _trace(cars, ticks_s, contacts=()):
    """cars: {drv: [s por tick]}"""
    rows = []
    for t, _ in enumerate(ticks_s):
        for d, ss in cars.items():
            rows.append(dict(tick=t, drv=d, s=ss[t], car_car=0))
    for (d, t) in contacts:
        for r in rows:
            if r['tick'] == t and r['drv'] == d:
                r['car_car'] = 1
    return pd.DataFrame(rows)


class TestSlotSwaps:
    def test_stable_field_zero_swaps(self):
        # 4 carros com gaps constantes: ranking NUNCA permuta
        df = _trace({'A': [100]*6, 'B': [130]*6, 'C': [160]*6, 'D': [200]*6},
                    list(range(6)))
        sw = slot_swaps_from_trace(df, track_len=1000.0)
        assert sw.n_swaps.sum() == 0

    def test_catch_up_swaps_slots(self):
        # B (à frente, +50→+2) e C (atrás recuando, -40→-65): os |dist| se
        # cruzam ~t1 -> a ordem dos slots de A permuta [C,B,D]->[B,C,D]
        sB = [150, 140, 130, 120, 110, 102]
        sC = [60, 55, 50, 45, 40, 35]
        df = _trace({'A': [100]*6, 'B': sB, 'C': sC, 'D': [200]*6},
                    list(range(6)))
        sw = slot_swaps_from_trace(df, track_len=300.0)
        a = sw[sw.drv == 'A'].sort_values('tick')
        assert a.n_swaps.sum() >= 1, "a ultrapassagem em |dist| deve permutar slots"
        assert sw.n_swaps.max() <= 3   # no máx. 1 por slot

    def test_summarize_window_vs_baseline(self):
        # Y aproxima-se por trás e cruza o |dist| de Z no t~7; contato de X
        # no t=10 (janela ±5) -> o swap cai DENTRO da janela, não fora
        n = 21
        cars = {'X': [100.0] * n,
                'Y': [5.0 * i for i in range(n)],
                'Z': [170.0] * n,
                'W': [250.0] * n}
        df = _trace(cars, list(range(n)), contacts=[('X', 10)])
        sw = slot_swaps_from_trace(df, track_len=300.0)
        assert sw.n_swaps.sum() >= 1
        res = summarize_swaps(sw, window_ticks=5)
        assert res['n_near'] > 0 and res['n_base'] > 0
        assert res['rate_near_contact_per_s'] >= res['rate_base_per_s'], (
            "swaps dentro da janela de contato devem ser >= ao baseline")
        assert -1.0 <= res['point_bisserial'] <= 1.0

    def test_wrap_distance_correct(self):
        # carro 5m atrás deve ser |−5| (não +295) num circuito de 300m
        from backend.model_train.slot_swap_analysis import signed_dist
        assert signed_dist([95.0], 100.0, 300.0)[0] == pytest.approx(-5.0)
        assert signed_dist([105.0], 100.0, 300.0)[0] == pytest.approx(5.0)
        assert signed_dist([10.0], 295.0, 300.0)[0] == pytest.approx(15.0)
