"""CICLO ALAVANCA — REVALIDAÇÃO PASSO 2: veredito MECÂNICO do RE-GATE C' (seeds 40-49).

Clima DECLARADO pelo scan offline (PREREG_ALAVANCA_REVALIDA P0; convenção: o
in-race é um PREFIXO do scan). Critérios:
  PASS-P  mediana(taxa) <= 0,307 | PASS-R máx <= 0,323 (âncoras 1883d6d §5)
  GUARD-V 10/10 carros >=1 volta | GUARD-L rolante mediana <= 141 s
  GUARD-F fora% <= 33,6% em todas
  GUARD-P/W EMENDADOS: seed SECA -> par=0 E wand=0 absolutos (espelho do
    histórico 9/9); seed DAMP -> par_trat <= par_base FRESCA da mesma seed e
    wand_trat <= wand_base (base obrigatória para toda seed damp do scan)
  FALLBACK: report-only (limiar >10 REVOGADO como bloqueio; >10/run =
    diagnóstico obrigatório no relatório)
  SELF leak-check BLOQUEANTE: por carro, 1º hold >= 1ª reentrada (violação =
    instrumento regrediu -> PARE)

    .venv/bin/python scripts/experiments/overtaking/lever_regate_c_verdict.py \
      experiments/diag-alv-seco/weather_scan_s40_s49.csv \
      experiments/diag-alv-seco/race_diag_alv2_base_s42.csv \
      experiments/diag-alv-seco/race_diag_alv2_s40.csv ... s49.csv
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

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.experiments.overtaking.lever_gate_verdict import stats  # instrumento canônico
from scripts.experiments.overtaking.lever_leak_check import first_hold_per_car, first_reentry_per_car

HIST = dict(taxa_p25=0.307, taxa_med=0.323, rol=141.0, off_max=33.6)


def self_ok(f):
    df = pd.read_csv(f, comment='#')
    holds = first_hold_per_car(df)
    if not holds:
        return True, 0
    re_ = first_reentry_per_car(df)
    bad = [d for d, th in holds.items()
           if re_.get(d) is None or th < re_.get(d)]
    return not bad, len(holds)


def main(argv):
    scan_f = argv[0]
    weather = pd.read_csv(scan_f).set_index('seed')['clima'].to_dict()
    bases, trats, seen = {}, [], set()
    for f in argv[1:]:
        f = f.replace('_events.csv', '.csv')
        if f in seen:
            continue
        seen.add(f)
        st = stats(f)
        seed = int(Path(f).stem.split('_s')[-1])
        if '_base_s' in Path(f).stem:
            bases[seed] = st
        else:
            st.update(seed=seed, fb_ev=int(st['fb']))
            trats.append(st)
    T = pd.DataFrame(trats).set_index('seed')
    print(f"=== RE-GATE C' (seeds {int(T.index.min())}-{int(T.index.max())}, tratamento --rejoin-gap 20) ===")
    print(f"clima declarado (scan): { {int(s): weather.get(int(s), '?') for s in T.index} }")
    G = pd.DataFrame(dict(
        seed=T.index, clima=[weather.get(int(s), '?') for s in T.index],
        reent=T.reent.values, perigosas=T.perigosas.values, taxa=T.taxa.values,
        par=T.par.values, wand=T.wand.values, rol=T.rol.values, off=T.off.values,
        hold_s=T.hold_s.values, fb=T.fb_ev.values))
    print(G.to_string(index=False))
    per = {}
    for s in T.index:
        cls = weather.get(int(s), '?')
        if cls == 'SECA':
            okp, okw = T.loc[s, 'par'] == 0, T.loc[s, 'wand'] == 0
            rule = '0 absoluto'
        else:
            if int(s) not in bases:
                print(f"ERRO: seed damp {s} sem base fresca — PARE (pareamento impossível)")
                return 2
            okp = T.loc[s, 'par'] <= bases[int(s)]['par']
            okw = T.loc[s, 'wand'] <= bases[int(s)]['wand']
            rule = (f"<= base fresca (par {bases[int(s)]['par']}, wand {bases[int(s)]['wand']})")
        per[int(s)] = {'clima': cls, 'GUARD-P': bool(okp), 'GUARD-W': bool(okw), 'regra': rule}
    # SELF leak-check bloqueante (por arquivo de tratamento)
    self_bad = []
    for f in [x for x in seen if '_base_s' not in Path(x).stem]:
        ok, n = self_ok(f)
        if not ok:
            self_bad.append(Path(f).name)
    checks = {
        'PASS-P taxa mediana <= 0,307': T.taxa.median() <= HIST['taxa_p25'],
        'PASS-R nenhuma taxa > 0,323': T.taxa.max() <= HIST['taxa_med'],
        'GUARD-V 10/10 voltas': bool((T.n_comp == 10).all()),
        'GUARD-L rolante mediana <= 141s': T.rol.median() <= HIST['rol'],
        'GUARD-F fora <= 33,6%': bool((T.off <= HIST['off_max']).all()),
        'GUARD-P paradas (seca=0 / damp<=base)': all(v['GUARD-P'] for v in per.values()),
        'GUARD-W wanderers (seca=0 / damp<=base)': all(v['GUARD-W'] for v in per.values()),
        'SELF leak-check (hold >= reentrada por carro)': not self_bad,
    }
    print("\n=== VEREDITO MECÂNICO ===")
    allp = True
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
        allp &= bool(v)
    fb_hi = {int(s): int(T.loc[s, 'fb_ev']) for s in T.index if T.loc[s, 'fb_ev'] > 10}
    print(f"\nfallback T_max (report-only): { {int(s): int(T.loc[s, 'fb_ev']) for s in T.index} }"
          + (f" | >10/run em {fb_hi} -> diagnóstico obrigatório" if fb_hi else ""))
    for s in sorted(per):
        fails = [k for k in ('GUARD-P', 'GUARD-W') if not per[s][k]]
        print(f"  seed {s} [{per[s]['clima']}]: {'PASS' if not fails else 'FAIL em ' + ','.join(fails)}"
              f" ({per[s]['regra']})")
    if self_bad:
        print(f"  SELF VIOLADO em: {self_bad}")
    print(f"\nRE-GATE C': {'TODOS PASS — alavanca VIVA no seco com instrumento reparado (adverso = PASSO D)' if allp else 'FAIL — PARE: research-grade FINAL (opt-in documentado); dossiê LARGADA vira o próximo ciclo; SEM re-pin, SEM re-run'}")
    return 0 if allp else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
