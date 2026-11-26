"""CICLO ALAVANCA — PASSO 3: veredito MECÂNICO do gate (commitado com o prereg).

Regra do PREREG_ALAVANCA_GATE.md §5 (âncoras históricas do braço B R13 10-19):
  PASS-P: mediana(taxa) ≤ 0,307 (p25 histórico)
  PASS-R: nenhuma run com taxa > 0,323 (mediana histórica)
  GUARD-V: 10/10 carros com ≥1 volta completa (cruzamentos de SF − 1 ≥ 1)
  GUARD-P: paradas ≥3 s (v<0,5) = 0 por run
  GUARD-W: wanderers (>60 s) = 0 por run
  GUARD-L: rolante mediana ≤ 141 s (136 histórico + 5)
  GUARD-F: fora% por run ≤ 33,6% (range histórico + 2 pp)
Report-only: excursões/run, tempo de hold, eventos T_max.

    .venv/bin/python scripts/experiments/overtaking/lever_gate_verdict.py race_diag_alv_gap_s20.csv ... s29
"""

# Resolve common imports from the scripts root after topic-based reorganization.
import os as _scripts_os
import sys as _scripts_sys
_scripts_root = _scripts_os.path.dirname(_scripts_os.path.dirname(_scripts_os.path.abspath(__file__)))
_backend_root = _scripts_os.path.dirname(_scripts_root)
_project_root = _scripts_os.path.dirname(_backend_root)
for _script_path in (_scripts_root, _backend_root, _project_root):
    if _script_path not in _scripts_sys.path:
        _scripts_sys.path.insert(0, _script_path)

import sys
from pathlib import Path
import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent.parent
SF_S = 2655.0; SUB = 24
HIST = dict(taxa_p25=0.307, taxa_med=0.323, rol=136.0, off_max=33.6)

def stats(f):
    df = pd.read_csv(f, comment='#')
    ev = pd.read_csv(str(f).replace('.csv', '_events.csv'), comment='#')
    ev['tick'] = ev['sub'] // SUB
    ct = {}
    for r in ev.itertuples():
        ct.setdefault(r.drv_a, set()).add(r.tick)
        ct.setdefault(r.drv_b, set()).add(r.tick)
    n_re = n_dg = n_exc = par = wand = n_comp = 0
    hold_ticks = fb_events = 0
    times = []
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s').reset_index(drop=True)
        s, t = g.s.values, g.t_s.values
        ds = np.diff(s)
        idx = np.where((s[:-1] < SF_S) & (s[1:] >= SF_S) & (ds > 0) & (ds < 100))[0]
        if len(idx) >= 2:
            times.extend(np.diff(t[idx + 1]))
        if len(idx) >= 2: n_comp += 1
        v, tt, off = g.speed.values, g.t_s.values, g.offtrack.values
        i = 0
        while i < len(off):
            if off[i]:
                j = i
                while j < len(off) and off[j]: j += 1
                n_exc += 1
                if j < len(off):
                    n_re += 1
                    tk0 = int(g.tick.values[j])
                    if any(tk0 < tk <= tk0 + 300 for tk in ct.get(drv, set())):
                        n_dg += 1
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
        i = 0
        while i < len(off):
            if off[i]:
                j = i
                while j < len(off) and off[j]: j += 1
                if (j-i)*0.2 > 60: wand += 1
                i = j
            else: i += 1
    if 'rejoin_gap_hold' in df.columns:
        hold_ticks = int(df.rejoin_gap_hold.sum())
    if 'rejoin_gap_fb' in df.columns:
        fb_events = int(df.rejoin_gap_fb.sum())
    return dict(reent=n_re, perigosas=n_dg, taxa=round(n_dg/max(n_re,1), 3),
                exc=n_exc, par=par, wand=wand, n_comp=n_comp,
                rol=round(float(np.median(times)), 0) if times else None,
                off=round(100*df.offtrack.mean(), 1),
                hold_s=round(hold_ticks*0.2, 1), fb=fb_events)

def main(paths):
    rows = []
    seen = set()
    for f in paths:
        f = f.replace('_events.csv', '.csv')  # args podem incluir os events
        if f in seen:
            continue
        seen.add(f)
        st = stats(f)
        st.update(seed=int(Path(f).stem.split('_s')[-1]))
        rows.append(st)
    T = pd.DataFrame(rows)[['seed','reent','perigosas','taxa','exc','par','wand','n_comp','rol','off','hold_s','fb']]
    print("=== CICLO ALAVANCA — tabela por seed (tratamento, --rejoin-gap 20) ===")
    print(T.to_string(index=False))
    med = T.taxa.median()
    print(f"\nmediana taxa: {med:.3f} (PASS-P ≤ {HIST['taxa_p25']}) | pior run: {T.taxa.max():.3f} (PASS-R ≤ {HIST['taxa_med']})")
    checks = {
        'PASS-P taxa mediana ≤ 0,307': med <= HIST['taxa_p25'],
        'PASS-R nenhuma > 0,323': T.taxa.max() <= HIST['taxa_med'],
        'GUARD-V 10/10 voltas': (T.n_comp == 10).all(),
        'GUARD-P paradas 0': (T.par == 0).all(),
        'GUARD-W wanderers 0': (T.wand == 0).all(),
        'GUARD-L rolante ≤ 141s': T.rol.median() <= HIST['rol'] + 5,
        'GUARD-F fora ≤ 33,6%': (T.off <= HIST['off_max']).all(),
    }
    print("\n=== VEREDITO MECÂNICO ===")
    allp = True
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
        allp &= v
    print(f"\nGATE ALAVANCA: {'TODOS PASS — alavanca VIVA no seco (adversos = sessão própria; adoção = revisão)' if allp else 'FAIL — PARE com diagnóstico por seed'}")

if __name__ == '__main__':
    main(sys.argv[1:])
