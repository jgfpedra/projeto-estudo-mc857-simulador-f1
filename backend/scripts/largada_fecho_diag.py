"""LARGADA-FECHO — PASSO 1: diagnósticos REPORT-ONLY (ZERO simulação; leitura
dos CSVs JÁ existentes; commitado ANTES de executar).

N1: linha GUARD-V (10/10 carros >= 1 volta) do veredito L-1b, recomputada.
N2: driver_id + composto dos carros da 1ª excursão (t~32,8 s, s~31-35 m) nos
    10 tratamentos; padrão SOFT vs os 19/20 pares residuais — AMBOS os
    desfechos são dossiê-válidos; nenhum ciclo novo abre a partir disto.
N3: mapeamento runs->arquivos do L-1b (14 runs -> 13 arquivos; o re-smoke
    sobrescreveu race_diag_lg1b_stg_s0.csv).

    .venv/bin/python scripts/largada_fecho_diag.py
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
LG = BACKEND / "experiments" / "diag-largada"
SF_S = 2655.0


def n1_guardv():
    print("=== N1: GUARD-V do veredito L-1b (recomputado dos CSVs) ===")
    ok = 0
    for s in range(60, 70):
        df = pd.read_csv(LG / f"race_diag_lg1b_s{s}.csv", comment='#')
        comp = 0
        for _, g in df.groupby('drv'):
            g = g.sort_values('t_s')
            sv = g.s.values
            ds = np.diff(sv)
            idx = np.where((sv[:-1] < SF_S) & (sv[1:] >= SF_S) & (ds > 0) & (ds < 100))[0]
            if len(idx) >= 2:
                comp += 1
        ok += comp == 10
    print(f"  GUARD-V 10/10 voltas: {'PASS' if ok == 10 else f'FAIL ({ok}/10)'}")


def n2_primeira_excursao_compostos():
    print("\n=== N2: 1ª excursão dos 10 tratamentos (driver + composto) ===")
    soft = 0
    for s in range(60, 70):
        f = LG / f"race_diag_lg1b_s{s}.csv"
        df = pd.read_csv(f, comment='#')
        head = open(f).readline()
        comp = dict(re.findall(r"'(\w+)':\s*'(\w+)'", head))
        o = df[df.offtrack == 1]
        r = o.sort_values('t_s').iloc[0]
        c = comp.get(r.drv, '?')
        soft += c == 'SOFT'
        print(f"  s{s}: drv={r.drv:3s} composto={c:7s} t={r.t_s:.1f}s s={r.s:.0f}m")
    print(f"  SOFT entre as 1ªs excursões: {soft}/10 "
          f"({'PADRÃO SOFT consistente c/ 19/20 pares residuais' if soft >= 8 else 'SEM padrão dominante — anotar a ausência (AMBOS desfechos dossiê-válidos)'})")


def n3_runs_arquivos():
    print("\n=== N3: mapeamento runs->arquivos L-1b (14 runs -> 13 arquivos) ===")
    mapa = [
        ("run 1", "race_diag_lg1b_base_s0.csv", "smoke base s0 (flag-off)"),
        ("run 2", "race_diag_lg1b_stg_s0.csv", "smoke stagger v1 (release não-exato 6/10) — SOBRESCRITO"),
        ("run 3", "race_diag_lg1b_stg_s0.csv", "RE-SMOKE pós-fix ea1194a (arquivo re-usado; SELF 3/3)"),
        ("run 4", "race_diag_lg1b_base_s60.csv", "base fresca s60 (pareio damp)"),
        ("runs 5-14", "race_diag_lg1b_s60..s69.csv", "10 tratamentos (identity 10/10)"),
    ]
    for r, f, note in mapa:
        print(f"  {r:9s} -> {f:34s} {note}")
    n = len(list(LG.glob('race_diag_lg1b_s6*.csv'))) + \
        len(list(LG.glob('race_diag_lg1b_base_*.csv'))) + \
        len(list(LG.glob('race_diag_lg1b_stg_*.csv')))
    print(f"  arquivos distintos no disco: {n} | runs executadas: 14 (runs != arquivos)")


def main():
    n1_guardv()
    n2_primeira_excursao_compostos()
    n3_runs_arquivos()
    return 0


if __name__ == '__main__':
    sys.exit(main())
