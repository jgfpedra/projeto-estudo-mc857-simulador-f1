"""FASE 4 v15 (wiring) — veredito MECÂNICO do B3' (commitado ANTES de ler os CSVs).

Prereg d54bfe: 6 corridas 600s, seed 0, DRY, regime canônico R13.
  CONTROLE: fora 21-32% (senão PARE — instrumento).
  B3.1' all-composite: 10/10 >=1 volta | 0 paradas >=3s (v<0,5) | hesit <=3
    | fora <= 29,9% (p75 seco braço A, R12 0.6) | rolante <= controle+10s
    | contatos < controle da MESMA sessão (GATE PRIMÁRIO).
  B3.3' mistas: pós-largada (t>20s) com grupo composite ~= 0; hesit grupo v10 = 0;
    pace grupo v10 ~ controle; comparação vs CTRL-EMBARALHADO.
  B3.2' hold-at: REPORT-ONLY.

    .venv/bin/python scripts/f4v15_b3_verdict.py experiments/f4v15-wiring
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SF_S = 2655.0
SUB = 24
D = Path(sys.argv[1])


def stats(f):
    df = pd.read_csv(f, comment='#')
    ev = pd.read_csv(str(f).replace('.csv', '_events.csv'), comment='#')
    ev['t'] = (ev['sub'] // SUB) * 0.1
    ct = {}  # contato por driver (ticks) — reuso futuro; não gateia aqui
    for r in ev.itertuples(index=False):
        tick = getattr(r, 't')
        ct.setdefault(r.drv_a, set()).add(tick)
        ct.setdefault(r.drv_b, set()).add(tick)
    # voltas / rolante por carro (SF crossings-1)
    laps_all, times = [], []
    n_comp = 0
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        s, t = g.s.values, g.t_s.values
        ds = np.diff(s)
        idx = np.where((s[:-1] < SF_S) & (s[1:] >= SF_S) & (ds > 0) & (ds < 100))[0]
        laps_all.append(len(idx))
        if len(idx) >= 2:
            times.extend(np.diff(t[idx + 1]))
        if len(idx) >= 2:
            n_comp += 1
    # paradas >=3s v<0,5 (contiguas)
    par = 0
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        v, tt = g.speed.values, g.t_s.values
        i = 0
        while i < len(v):
            if v[i] < 0.5:
                j = i
                while j < len(v) and v[j] < 0.5:
                    j += 1
                dur = (tt[min(j, len(tt) - 1)] - tt[i]) if j > i else 0
                if dur >= 3.0:
                    par += 1
                i = j
            else:
                i += 1
    # hesitacoes: v<0,5 por 0,3-3s, t>20, ON-track
    hesit = 0
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        v, tt, off = g.speed.values, g.t_s.values, g.offtrack.values
        i = 0
        while i < len(v):
            if v[i] < 0.5 and tt[i] > 20 and off[i] == 0:
                j = i
                while j < len(v) and v[j] < 0.5 and off[j] == 0:
                    j += 1
                dur = (tt[min(j, len(tt) - 1)] - tt[i]) if j > i else 0
                if 0.3 <= dur <= 3.0:
                    hesit += 1
                i = max(j, i + 1)
            else:
                i += 1
    return dict(df=df, off=round(100 * df.offtrack.mean(), 1),
                par=par, hesit=hesit, n_comp=n_comp,
                rol=round(float(np.median(times)), 0) if times else None,
                cc=int(df.car_car.sum()),
                cc_pos=int(df[(df.t_s > 20)].car_car.sum()))


def group_stats(f, group):
    df = pd.read_csv(f, comment='#')
    d = df[df.grupo == group]
    return dict(off=round(100 * d.offtrack.mean(), 1) if len(d) else None,
                cc_pos=int(d[d.t_s > 20].car_car.sum()),
                cc=int(d.car_car.sum()),
                n=len(d.drv.unique()))


def main():
    c = stats(D / '1_controle.csv')
    a = stats(D / '2_allcomposite.csv')
    m2 = stats(D / '3_mista_2comp.csv')
    m4 = stats(D / '4_mista_4comp.csv')
    ce = stats(D / '5_ctrl_embaralhado.csv')
    h = stats(D / '6_holdat.csv')
    print("=== B3' (regime canônico R13; seed 0 DRY; 600s) ===")
    for name, s in [('1 CONTROLE', c), ('2 ALL-COMPOSITE', a), ('3 MISTA 2comp', m2),
                    ('4 MISTA 4comp', m4), ('5 CTRL-EMBARALHADO', ce), ('6 HOLD-AT (report)', h)]:
        print(f"  {name}: fora={s['off']}% | par={s['par']} | hesit={s['hesit']} | "
              f"comp={s['n_comp']}/10 | rol={s['rol']}s | cc={s['cc']} (pós-largada={s['cc_pos']})")
    # por grupo nas mistas
    for name, f in [('3 MISTA', D / '3_mista_2comp.csv'), ('4 MISTA', D / '4_mista_4comp.csv')]:
        for grp in ('composite', 'edge'):
            gs = group_stats(f, grp)
            print(f"  {name} grupo {grp}: n={gs['n']} | fora={gs['off']}% | cc={gs['cc']} (pós-larg={gs['cc_pos']})")
    print("\n=== VEREDITO MECÂNICO ===")
    checks = {
        'CONTROLE no regime canônico (fora 21-32%)': 21.0 <= c['off'] <= 32.0,
        'B3.1 GUARD-V 10/10 >=1 volta': a['n_comp'] == 10,
        'B3.1 GUARD-P paradas=0': a['par'] == 0,
        'B3.1 HESIT <=3': a['hesit'] <= 3,
        'B3.1 fora <= 29,9% (p75 seco A)': a['off'] <= 29.9,
        'B3.1 rolante <= controle+10s': a['rol'] is not None and c['rol'] is not None and a['rol'] <= c['rol'] + 10,
        'B3.1 CONTATOS < controle (PRIMÁRIO)': a['cc'] < c['cc'],
        'B3.3 mistas: pós-largada composite ~0 (<=2)': group_stats(D / '3_mista_2comp.csv', 'composite')['cc_pos'] <= 2
        and group_stats(D / '4_mista_4comp.csv', 'composite')['cc_pos'] <= 2,
    }
    allp = True
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
        allp &= bool(v)
    print(f"\nB3': {'TODOS PASS — evidência para o dono decidir PROMOÇÃO (a fase NÃO promove)' if allp else 'FAIL — PARE com diagnóstico; sem re-pin/re-run'}")
    return 0 if allp else 1


if __name__ == '__main__':
    sys.exit(main())
