"""R10 PASSO 2 — VEREDITO MECÂNICO do gate de produto (script commitado com o prereg).

Regra de decisão lexicográfica do PREREG_R10_GATE.md §0.3 — proibido veredito
à mão. Lê os braços A (race_diag_r7a_disp_s{0..9}) e B (race_diag_r10_blind_s{0..9}),
calcula a tabela POR SEED, deltas pareados, medianas, e aplica D1∧D2∧D3.

    .venv/bin/python scripts/r10_gate_verdict.py
"""
import os, re, sys
from pathlib import Path
import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
L = 4160.4; SF_S = 2655.0; SUB = 24

def metrics(csv_path, log_path=None):
    df = pd.read_csv(csv_path, comment='#')
    ev = pd.read_csv(str(csv_path).replace('.csv', '_events.csv'), comment='#')
    ev['tick'] = ev['sub'] // SUB
    ev['pair'] = [tuple(sorted([a, b])) for a, b in zip(ev.drv_a, ev.drv_b)]
    cc = len(ev[['tick', 'pair']].drop_duplicates())
    pos60 = len(ev[ev.tick > 600][['tick', 'pair']].drop_duplicates())
    off_pct = 100 * df.offtrack.mean()
    laps, times = 0, []
    wand_cars, preso = 0, 0
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        s, t = g.s.values, g.t_s.values
        ds = np.diff(s)
        idx = np.where((s[:-1] < SF_S) & (s[1:] >= SF_S) & (ds > 0) & (ds < 100))[0]
        ts = t[idx + 1]
        if len(ts) >= 1: laps += 1
        if len(ts) >= 2: times.extend(np.diff(ts))
        off = g.offtrack.values
        i, n_eps = 0, 0
        while i < len(off):
            if off[i]:
                j = i
                while j < len(off) and off[j]: j += 1
                if (j - i) * 0.2 > 60:
                    preso += 1; n_eps += 1
                i = j
            else: i += 1
        if n_eps: wand_cars += 1
    hesit = 0
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        m = (g.t_s.values > 20) & (g.offtrack.values == 0)
        v, t = g.speed.values[m], g.t_s.values[m]
        i = 0
        while i < len(v):
            if v[i] < 0.5:
                j = i
                while j < len(v) and v[j] < 0.5: j += 1
                dur = (t[min(j, len(t) - 1)] - t[i]) if j > i else 0.0
                if 0.3 <= dur < 3.0: hesit += 1
                i = j
            else: i += 1
    stops = 0
    if log_path and Path(log_path).exists():
        txt = Path(log_path).read_text()
        m = re.search(r'TOTAL: (\d+) paradas', txt)
        stops = int(m.group(1)) if m else (0 if 'nenhuma parada' in txt else -1)
    return dict(cc=cc, pos60=pos60, stops=stops, off_pct=round(off_pct, 1),
                wand=wand_cars, preso=preso,
                rolante=round(float(np.median(times)), 0) if times else None,
                hesit=hesit)

def main():
    rows = []
    for seed in range(10):
        a = metrics(BACKEND / f'race_diag_r7a_disp_s{seed}.csv',
                    BACKEND / f'race_diag_r7a_disp_s{seed}.log')
        a.update(seed=seed, arm='A(composite)')
        b = metrics(BACKEND / f'race_diag_r10_blind_s{seed}.csv',
                    BACKEND / f'race_diag_r10_blind_s{seed}.log')
        b.update(seed=seed, arm='B(cego)')
        rows += [a, b]
    T = pd.DataFrame(rows)[['seed', 'arm', 'cc', 'pos60', 'stops', 'off_pct',
                            'wand', 'preso', 'rolante', 'hesit']]
    print("=== R10 GATE — tabela POR SEED ===")
    print(T.to_string(index=False))
    A = T[T.arm.str.startswith('A')].reset_index(drop=True)
    B = T[T.arm.str.startswith('B')].reset_index(drop=True)
    print("\n=== medianas ===")
    med = pd.DataFrame({'A': A[['cc','pos60','off_pct','wand','preso','rolante','hesit']].median(),
                        'B': B[['cc','pos60','off_pct','wand','preso','rolante','hesit']].median()})
    print(med.round(1).to_string())
    print(f"paradas A (todas seeds): {A.stops.tolist()} | B: {B.stops.tolist()}")
    # ---- D1 SEGURANÇA ----
    d1 = (med.loc['cc','A'] < med.loc['cc','B']) and \
         (med.loc['pos60','A'] <= med.loc['pos60','B']) and \
         (A.stops == 0).all()
    # ---- D2 PISTA ----
    d2 = (med.loc['off_pct','A'] <= med.loc['off_pct','B'] + 10) and \
         (med.loc['wand','A'] <= med.loc['wand','B']) and \
         (med.loc['preso','A'] <= med.loc['preso','B'] + 5)
    # ---- D3 PACE ----
    d3 = (med.loc['rolante','A'] <= med.loc['rolante','B'] + 15) and \
         (med.loc['hesit','A'] <= med.loc['hesit','B'] + 3)
    print(f"\nD1 SEGURANÇA: {'PASS' if d1 else 'FAIL'} (cc {med.loc['cc','A']:.0f} vs {med.loc['cc','B']:.0f} | "
          f"pós60 {med.loc['pos60','A']:.0f} vs {med.loc['pos60','B']:.0f} | paradas A todas 0: {(A.stops==0).all()})")
    print(f"D2 PISTA: {'PASS' if d2 else 'FAIL'} (fora {med.loc['off_pct','A']} vs {med.loc['off_pct','B']} (+10 pp) | "
          f"wand {med.loc['wand','A']} vs {med.loc['wand','B']} | preso {med.loc['preso','A']} vs {med.loc['preso','B']} (+5))")
    print(f"D3 PACE: {'PASS' if d3 else 'FAIL'} (rolante {med.loc['rolante','A']} vs {med.loc['rolante','B']} (+15 s) | "
          f"hesit {med.loc['hesit','A']} vs {med.loc['hesit','B']} (+3))")
    print(f"\n=== VEREDITO MECÂNICO: "
          f"{'PROMOÇÃO PROPOSTA (D1∧D2∧D3) — executar SÓ após aprovação da revisão' if (d1 and d2 and d3) else 'MANUTENÇÃO DO v10 + composite research-grade'} ===")
    if not (d1 and d2 and d3):
        fails = [n for n, ok in (('D1', d1), ('D2', d2), ('D3', d3)) if not ok]
        print(f"    dimensão(ões) falha: {', '.join(fails)}")

if __name__ == '__main__':
    main()
