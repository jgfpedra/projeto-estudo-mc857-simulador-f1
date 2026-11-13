"""R13-GATE — análise e veredito MECÂNICO (prereg commitado 2882a37; working tree limpo).

Limiares derivados do braço A seeds 0-9 (CSV; quantis PINADOS no prereg):
  SECO:    fora ≤ 30,4% | rolante ≤ 164s | hesit ≤ 17 | cc ≤ 545 |
           paradas = 0 | wanderers ≤ 2 | floor: 10/10 completam
  ADVERSO: fora ≤ 50,1% | rolante ≤ 184s | hesit ≤ 12 | cc ≤ 430 |
           T-adv = 8 | wanderers ≤ 12 | floor: 10/10
Rótulo de clima MECÂNICO: adverso = (w_trans==1) em qualquer tick do run.
Árvore avaliada SÓ após os 10 runs do braço A (sem early-stop).

    .venv/bin/python scripts/r13_gate_verdict.py
"""
import re, sys
from pathlib import Path
import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
SF_S = 2655.0; SUB = 24
LIM = {
    'seco':    dict(off=30.4, rol=164, hesit=17, cc=545, par=0, wand=2),
    'adverso': dict(off=50.1, rol=184, hesit=12, cc=430, par=8, wand=12),
}

def stats(f, log_path=None):
    df = pd.read_csv(f, comment='#')
    ev = pd.read_csv(str(f).replace('.csv', '_events.csv'), comment='#')
    ev['tick'] = ev['sub'] // SUB
    ev['pair'] = [tuple(sorted([a, b])) for a, b in zip(ev.drv_a, ev.drv_b)]
    cc = len(ev[['tick', 'pair']].drop_duplicates())
    pos60 = len(ev[ev.tick > 600][['tick', 'pair']].drop_duplicates())
    times = []; wand = par = hesit = n_comp = 0
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s'); s, t = g.s.values, g.t_s.values
        ds = np.diff(s)
        idx = np.where((s[:-1] < SF_S) & (s[1:] >= SF_S) & (ds > 0) & (ds < 100))[0]
        if len(idx) > 1: times.extend(np.diff(t[idx + 1]))
        if len(idx) >= 2: n_comp += 1
        offv = g.offtrack.values; v, tt = g.speed.values, g.t_s.values
        i = 0
        while i < len(offv):
            if offv[i]:
                j = i
                while j < len(offv) and offv[j]: j += 1
                if (j - i) * 0.2 > 60: wand += 1
                i = j
            else: i += 1
        i = 0
        while i < len(v):
            if v[i] < 0.5:
                j = i
                while j < len(v) and v[j] < 0.5: j += 1
                dur = (tt[min(j, len(tt)-1)] - tt[i]) if j > i else 0
                if dur >= 3.0: par += 1
                i = j
            else: i += 1
        m = (g.t_s.values > 20) & (g.offtrack.values == 0)
        v2, t2 = g.speed.values[m], g.t_s.values[m]
        i = 0
        while i < len(v2):
            if v2[i] < 0.5:
                j = i
                while j < len(v2) and v2[j] < 0.5: j += 1
                dur = (t2[min(j, len(t2)-1)] - t2[i]) if j > i else 0
                if 0.3 <= dur < 3.0: hesit += 1
                i = j
            else: i += 1
    adv = int((df.w_trans == 1).any()) if 'w_trans' in df.columns else None
    return dict(cc=cc, pos60=pos60, off=round(100 * df.offtrack.mean(), 1),
                rol=round(float(np.median(times)), 0) if times else None,
                hesit=hesit, par=par, wand=wand, n_comp=n_comp, adv=adv)

def apply_gate(st, clima):
    L = LIM[clima]
    checks = {
        'floor 10/10': (st['n_comp'] == 10, f"{st['n_comp']}/10"),
        'fora':  (st['off'] <= L['off'], f"{st['off']} ≤ {L['off']}"),
        'rolante': (st['rol'] is not None and st['rol'] <= L['rol'], f"{st['rol']} ≤ {L['rol']}"),
        'hesit': (st['hesit'] <= L['hesit'], f"{st['hesit']} ≤ {L['hesit']}"),
        'cc': (st['cc'] <= L['cc'], f"{st['cc']} ≤ {L['cc']}"),
        'paradas': (st['par'] <= L['par'], f"{st['par']} ≤ {L['par']}"),
        'wanderers': (st['wand'] <= L['wand'], f"{st['wand']} ≤ {L['wand']}"),
    }
    return checks

def main():
    print("=== R13-GATE — braço A (composite), seeds 10-19 (out-of-sample) ===")
    rows, gate_rows = [], []
    for s in range(10, 20):
        st = stats(BACKEND / f'race_diag_r13_a_s{s}.csv')
        clima = 'adverso' if st['adv'] == 1 else 'seco'
        st.update(seed=s, clima=clima, arm='A')
        rows.append(st)
        checks = apply_gate(st, clima)
        ok = all(v[0] for v in checks.values())
        gate_rows.append((s, clima, checks, ok))
        print(f"s{s} [{clima:7s}]: " + " | ".join(
            f"{k}:{'✓' if v[0] else '✗'}({v[1]})" for k, v in checks.items()) + f" → {'PASS' if ok else 'FAIL'}")
    T = pd.DataFrame(rows)
    print("\n=== tabela A (todas as métricas CSV) ===")
    print(T[['seed', 'clima', 'cc', 'pos60', 'off', 'rol', 'hesit', 'par', 'wand', 'n_comp']].to_string(index=False))
    all_ok = all(g[3] for g in gate_rows)
    by_clima = {}
    for s, clima, checks, ok in gate_rows:
        by_clima.setdefault(clima, []).append(ok)
    print("\n=== braço B (v10-cego) pareado — reporte cru (independente do PASS/FAIL) ===")
    rowsB = []
    for s in range(10, 20):
        stB = stats(BACKEND / f'race_diag_r13_b_s{s}.csv')
        stB.update(seed=s, arm='B')
        rowsB.append(stB)
    B = pd.DataFrame(rowsB).set_index('seed')
    A = T.set_index('seed')
    print(f"{'seed':>4} {'clima':>8} {'Δcc':>7} {'Δpos60':>7} {'Δfora':>7} {'Δrol':>6} {'Δpar':>6} {'Δwand':>6}")
    for s in range(10, 20):
        a, b = A.loc[s], B.loc[s]
        print(f"{s:>4} {a.clima:>8} {a.cc-b.cc:>+7} {a.pos60-b.pos60:>+7} {a.off-b.off:>+7} "
              f"{(a.rol-b.rol):>+6} {a.par-b.par:>+6} {a.wand-b.wand:>+6}")
    print("\n=== VEREDITO MECÂNICO (após TODOS os 10 runs de A — sem early-stop) ===")
    for clima, oks in by_clima.items():
        print(f"  {clima}: {sum(oks)}/{len(oks)} seeds PASS")
    print(f"\nGATE R13: {'PASS — PROPOSTA DE PROMOÇÃO (decisão FINAL da revisão)' if all_ok else 'FAIL — VEREDITO R10 PERMANENTE (manutenção do v10) com confirmação out-of-sample'}")
    if not all_ok:
        for s, clima, checks, ok in gate_rows:
            if not ok:
                fails = [f"{k}({v[1]})" for k, v in checks.items() if not v[0]]
                print(f"  s{s} [{clima}] falhou em: {', '.join(fails)}")

if __name__ == '__main__':
    main()
