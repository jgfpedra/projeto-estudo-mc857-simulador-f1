"""ANTI-D3-1 — veredito MECÂNICO (commitado ANTES das corridas; PADRÃO-OURO).

Prereg 57a9342 §Critérios (2 corridas seed 0 DRY; controle PRIMEIRO):
  PRIMÁRIO: hesit composite <= hesit controle da MESMA sessão (re-ancorado)
  Não-reg: cc < cc controle | par=0 | 10/10 voltas | fora<=29,9 | rol<=ctrl+10
  Proteção: controle re-run BIT-IDÊNTICO à FASE-4-v15 (cc 3674, pos 2482,
  rol 136, hesit 3, off 22,1) — se divergir -> PARE imediato.
  Mistas: DROP (fora do escopo).

    .venv/bin/python scripts/anti_d3_verdict.py experiments/anti-d3-1/1_controle.csv experiments/anti-d3-1/2_allcomposite.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SF_S = 2655.0
F4V15 = dict(cc=3674, pos=2482, rol=136.0, hesit=3, off=22.1)


def stats(f):
    df = pd.read_csv(f, comment='#')
    times, n_comp = [], 0
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        s, t = g.s.values, g.t_s.values
        ds = np.diff(s)
        idx = np.where((s[:-1] < SF_S) & (s[1:] >= SF_S) & (ds > 0) & (ds < 100))[0]
        if len(idx) >= 2:
            n_comp += 1
            times.extend(np.diff(t[idx + 1]))
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
                if (tt[min(j, len(tt) - 1)] - tt[i]) >= 3.0:
                    par += 1
                i = j
            else:
                i += 1
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
                d = (tt[min(j, len(tt) - 1)] - tt[i]) if j > i else 0
                if 0.3 <= d <= 3.0:
                    hesit += 1
                i = max(j, i + 1)
            else:
                i += 1
    return dict(off=round(100 * df.offtrack.mean(), 1), par=par, hesit=hesit,
                n_comp=n_comp, rol=round(float(np.median(times)), 0) if times else None,
                cc=int(df.car_car.sum()), pos=int(df[df.t_s > 20].car_car.sum()))


def main(argv):
    c, a = stats(argv[0]), stats(argv[1])
    print("=== ANTI-D3-1 (seed 0 DRY 600s; regime canônico) ===")
    print(f"  CONTROLE       : fora={c['off']}% | par={c['par']} | hesit={c['hesit']} | "
          f"comp={c['n_comp']}/10 | rol={c['rol']} | cc={c['cc']} (pos={c['pos']})")
    print(f"  ALL-COMPOSITE  : fora={a['off']}% | par={a['par']} | hesit={a['hesit']} | "
          f"comp={a['n_comp']}/10 | rol={a['rol']} | cc={a['cc']} (pos={a['pos']})")
    # Proteção: controle bit-idêntico à FASE-4-v15
    prot = (c['cc'] == F4V15['cc'] and c['pos'] == F4V15['pos']
            and c['rol'] == F4V15['rol'] and c['hesit'] == F4V15['hesit']
            and c['off'] == F4V15['off'] and c['par'] == 0)
    print(f"\nPROTEÇÃO controle re-run == FASE-4-v15 ({F4V15}): "
          f"{'BIT-IDÊNTICO' if prot else 'DIVERGIU -> PARE IMEDIATO'}")
    if not prot:
        return 2
    checks = {
        f"PRIMÁRIO hesit composite ({a['hesit']}) <= controle ({c['hesit']})": a['hesit'] <= c['hesit'],
        f"Não-reg cc ({a['cc']}) < controle ({c['cc']})": a['cc'] < c['cc'],
        "Não-reg paradas = 0": a['par'] == 0,
        "Não-reg 10/10 voltas": a['n_comp'] == 10,
        "Não-reg fora <= 29,9%": a['off'] <= 29.9,
        f"Não-reg rol ({a['rol']}) <= controle+10 ({(c['rol'] or 0) + 10})":
            a['rol'] is not None and a['rol'] <= (c['rol'] or 0) + 10,
    }
    print("\n=== VEREDITO MECÂNICO ===")
    allp = True
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
        allp &= bool(v)
    print(f"\nANTI-D3-1: {'TODOS PASS — D3 atacado com sucesso pela camada; fila = re-decisão de promoção (dono)' if allp else 'FAIL — PARE; sem re-pin/re-run'}")
    return 0 if allp else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
