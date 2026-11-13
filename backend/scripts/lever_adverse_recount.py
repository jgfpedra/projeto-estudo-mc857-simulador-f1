"""CICLO ALAVANCA — SESSÃO ADVERSA 0-a: recontagem adversa HISTÓRICA.

Lê o corpus braço CEGO seeds 0-9 (race_diag_r10_blind_s{0..9}, era R10, mesmo
comando do tratamento menos a flag) com o MESMO instrumento do gate seco
(lever_gate_verdict.stats — zero reimplementação) e emite POR SEED: excursões,
reentradas, perigosas, taxa, fora%, rolante, voltas (líder), carros
completando, paradas, wanderers + rótulo de clima do cabeçalho do CSV.

Saída (commitada — fonte única das âncoras pareadas do 0-d):
  experiments/diag-alv-adverso/recontagem_cego_s0_9.csv

    .venv/bin/python scripts/lever_adverse_recount.py
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND / "scripts"))
from lever_gate_verdict import stats, SF_S  # instrumento canônico do gate seco

CORPUS = BACKEND / "experiments" / "diag-r2-r13"
OUT_DIR = BACKEND / "experiments" / "diag-alv-adverso"


def weather_label(f):
    head = open(f).readline()
    m = re.search(r"weather_transitions=\[(.*?)\]", head)
    if not m or not m.group(1).strip():
        return "sem transicoes"
    steps = re.findall(
        r"\((\d+),\s*<WeatherKind\.(\w+)[^>]*>,\s*<WeatherKind\.(\w+)[^>]*>\)",
        m.group(1))
    return "; ".join(f"v{a}:{b}->{c}" for a, b, c in steps) if steps else m.group(1)[:60]


def voltas_lider(f):
    df = pd.read_csv(f, comment='#', usecols=['drv', 's', 't_s'])
    best = 0
    for _, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        s = g.s.values
        ds = np.diff(s)
        idx = np.where((s[:-1] < SF_S) & (s[1:] >= SF_S) & (ds > 0) & (ds < 100))[0]
        best = max(best, len(idx) - 1)
    return best


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for s in range(10):
        f = CORPUS / f"race_diag_r10_blind_s{s}.csv"
        st = stats(f)
        st.update(seed=s, clima=weather_label(f), voltas_lider=voltas_lider(f))
        rows.append(st)
    cols = ['seed', 'clima', 'exc', 'reent', 'perigosas', 'taxa', 'off', 'rol',
            'voltas_lider', 'n_comp', 'par', 'wand']
    T = pd.DataFrame(rows)[cols]
    out = OUT_DIR / "recontagem_cego_s0_9.csv"
    T.to_csv(out, index=False)
    print("=== 0-a RECONTAGEM ADVERSA HISTORICA (braco cego, seeds 0-9, instrumento stats() do gate seco) ===")
    print(T.to_string(index=False))
    print(f"\n-> {out}")
    print("\n=== seeds do gate {2,8,9} (ancoras pareadas) ===")
    print(T[T.seed.isin([2, 8, 9])].to_string(index=False))


if __name__ == '__main__':
    main()
