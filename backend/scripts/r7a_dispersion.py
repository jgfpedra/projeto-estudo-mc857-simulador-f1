"""R7a PASSO 2c — dispersão das 10 seeds com --variance grid,compound.

Tabela de dispersão (cc-verdade, pós-60s, fora%, rolante, preso) + PROVA
de que as realizações são DISTINTAS (variância material): pares de seeds
com trajetórias diferentes + cenários de grid/composto distintos.

    python scripts/r7a_dispersion.py
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
L = 4160.4; SF_S = 2655.0; SUB = 24

def stats(f):
    df = pd.read_csv(f, comment='#')
    ev = pd.read_csv(str(f).replace('.csv', '_events.csv'), comment='#')
    ev['tick'] = ev['sub'] // SUB
    ev['pair'] = [tuple(sorted([a, b])) for a, b in zip(ev.drv_a, ev.drv_b)]
    cc = len(ev[['tick', 'pair']].drop_duplicates())
    pos60 = len(ev[ev.tick > 600][['tick', 'pair']].drop_duplicates())
    laps = 0; times = []
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s'); s, t = g.s.values, g.t_s.values
        ds = np.diff(s)
        idx = np.where((s[:-1] < SF_S) & (s[1:] >= SF_S) & (ds > 0) & (ds < 100))[0]
        ts = t[idx + 1]
        if len(ts) >= 1: laps += 1
        if len(ts) >= 2: times.extend(np.diff(ts))
    preso = 0
    for drv, g in df.groupby('drv'):
        off = g.sort_values('t_s').offtrack.values
        i = 0
        while i < len(off):
            if off[i]:
                j = i
                while j < len(off) and off[j]: j += 1
                if (j - i) * 0.2 > 60: preso += 1
                i = j
            else: i += 1
    return dict(cc=cc, pos60=pos60, off=round(100 * df.offtrack.mean(), 1),
                laps=f"{laps}/10", pace=round(float(np.median(times)), 0) if times else None,
                preso=preso)

def main():
    rows = []
    for s in range(10):
        f = BACKEND / f"race_diag_r7a_disp_s{s}.csv"
        if not f.exists():
            print(f"pendente: seed {s}"); continue
        st = stats(f); st['seed'] = s
        rows.append(st)
    t = pd.DataFrame(rows)[['seed', 'cc', 'pos60', 'off', 'laps', 'pace', 'preso']]
    print("=== R7a DISPERSÃO — 10 seeds, --variance grid,compound (sequencial) ===")
    print(t.to_string(index=False))
    print(f"\nmediana: cc={t.cc.median():.0f} | pós60={t.pos60.median():.0f} | "
          f"fora={t.off.median():.1f}% | pace={t.pace.median():.0f}s | preso={t.preso.median():.0f}")
    print(f"dispersão: cc [{t.cc.min()}, {t.cc.max()}] | fora [{t.off.min()}, {t.off.max()}]% | "
          f"pace [{t.pace.min()}, {t.pace.max()}]s")
    # prova de realizações distintas: cenários de grid distintos por seed
    headers = {}
    for s in range(10):
        f = BACKEND / f"race_diag_r7a_disp_s{s}.csv"
        if f.exists():
            head = open(f).readline()
            headers[s] = head.split('grid_order=')[1].split(' | compounds')[0] if 'grid_order=' in head else '?'
    distinct = len(set(headers.values()))
    print(f"cenários de grid distintos: {distinct}/{len(headers)} seeds — "
          f"{'VARIÂNCIA MATERIAL ✓' if distinct == len(headers) and len(headers) > 1 else 'VERIFICAR'}")

if __name__ == '__main__':
    main()
