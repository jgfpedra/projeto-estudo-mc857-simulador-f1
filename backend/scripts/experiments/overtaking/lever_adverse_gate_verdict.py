"""CICLO ALAVANCA — SESSÃO ADVERSA 0-d: veredito MECÂNICO PAREADO (commitado junto ao 0-a).

Cada seed contra o SEU histórico (recontagem_cego_s0_9.csv = braço cego R10
seeds 0-9, mesmo comando do tratamento menos a flag). PREREG_ALAVANCA_ADVERSA.md §5:
  PASS-A  taxa_trat <= taxa_hist (mesmo seed) em 3/3
  GUARD-V n_comp_trat >= n_comp_hist (mesmo seed) em 3/3
  GUARD-P paradas_trat <= par_hist (mesmo seed) em 3/3   [EMENDA REPARO: exigir
          0 absoluto onde o histórico tem 8-14 confundiria CLIMA com ALAVANCA;
          s2⇒0, s8⇒14, s9⇒8]
  GUARD-W wanderers_trat <= wand_hist (mesmo seed) em 3/3 [EMENDA idem;
          s2⇒0, s8⇒17, s9⇒13]
  GUARD-L rol_trat <= rol_hist + 5 s (mesmo seed) em 3/3
          (NaN: hist NaN + trat c/ voltas -> PASS; hist c/ voltas + trat NaN
           -> FAIL; ambos NaN -> PASS — pinado no prereg)
  GUARD-F off_trat <= off_hist + 2 pp (mesmo seed) em 3/3
  FALLBACK: evento = transição 0->1 de rejoin_gap_fb por carro (REPARO);
  REPORT-ONLY (emenda REVALIDAÇÃO: limiar >10 REVOGADO como bloqueio —
  >10/run = diagnóstico obrigatório no relatório).
  SELF leak-check BLOQUEANTE (emenda REVALIDAÇÃO): por carro, 1º hold >=
  1ª reentrada em cada tratamento (violação = instrumento regrediu -> PARE).

    .venv/bin/python scripts/experiments/overtaking/lever_adverse_gate_verdict.py \
      experiments/diag-alv-adverso/recontagem_cego_s0_9.csv \
      experiments/diag-alv-adverso/race_diag_alv_adv_s2.csv \
      experiments/diag-alv-adverso/race_diag_alv_adv_s8.csv \
      experiments/diag-alv-adverso/race_diag_alv_adv_s9.csv
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
from scripts.experiments.overtaking.lever_gate_verdict import stats
from scripts.experiments.overtaking.lever_leak_check import first_hold_per_car, first_reentry_per_car

GATE_SEEDS = (2, 8, 9)


def self_ok(f):
    """REVALIDAÇÃO: 1º hold por carro >= 1ª reentrada do MESMO carro."""
    df = pd.read_csv(f, comment='#')
    holds = first_hold_per_car(df)
    if not holds:
        return True, 0
    re_ = first_reentry_per_car(df)
    bad = [d for d, th in holds.items()
           if re_.get(d) is None or th < re_.get(d)]
    return not bad, len(holds)


def fb_events(f):
    """Eventos de fallback = transições 0->1 de rejoin_gap_fb por carro."""
    df = pd.read_csv(f, comment='#')
    if 'rejoin_gap_fb' not in df.columns:
        return 0
    n = 0
    for _, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        v = g.rejoin_gap_fb.values
        n += int(((v[1:] == 1) & (v[:-1] == 0)).sum()) + int(v[0] == 1)
    return n


def rol_ok(rt, rh):
    if pd.isna(rh):
        return True   # histórico sem volta nenhuma: tratamento não pode piorar além disso
    if pd.isna(rt):
        return False  # histórico tinha pace, tratamento perdeu
    return rt <= rh + 5


def main(argv):
    hist_f = argv[0]
    trat, seen, trat_files = [], set(), []
    for f in argv[1:]:
        f = f.replace('_events.csv', '.csv')  # args podem incluir os events
        if f in seen:
            continue
        seen.add(f)
        st = stats(f)
        st.update(seed=int(Path(f).stem.split('_s')[-1]), fb_ev=fb_events(f))
        trat.append(st)
        trat_files.append(f)
    T = pd.DataFrame(trat).set_index('seed')
    H = pd.read_csv(hist_f).set_index('seed')
    missing = [s for s in GATE_SEEDS if s not in T.index]
    if missing:
        print(f"ERRO: seeds do gate ausentes nos args: {missing}")
        return 2
    G, HG = T.loc[list(GATE_SEEDS)], H.loc[list(GATE_SEEDS)]
    cmp = pd.DataFrame(dict(
        seed=G.index,
        taxa_hist=HG.taxa.values, taxa_trat=G.taxa.values,
        ncomp_hist=HG.n_comp.values, ncomp_trat=G.n_comp.values,
        rol_hist=HG.rol.values, rol_trat=G.rol.values,
        off_hist=HG.off.values, off_trat=G.off.values,
        reent=G.reent.values, perig=G.perigosas.values,
        par=G.par.values, wand=G.wand.values,
        hold_s=G.hold_s.values, fb_ev=G.fb_ev.values,
    ))
    print("=== SESSAO ADVERSA — GATE PAREADO seeds {2,8,9} (tratamento --rejoin-gap 20 vs historico do mesmo seed) ===")
    print(cmp.to_string(index=False))
    per = {}
    for s in GATE_SEEDS:
        per[s] = {
            'PASS-A': bool(T.loc[s, 'taxa'] <= H.loc[s, 'taxa']),
            'GUARD-V': bool(T.loc[s, 'n_comp'] >= H.loc[s, 'n_comp']),
            'GUARD-P': bool(G.loc[s, 'par'] <= H.loc[s, 'par']),
            'GUARD-W': bool(G.loc[s, 'wand'] <= H.loc[s, 'wand']),
            'GUARD-L': bool(rol_ok(T.loc[s, 'rol'], H.loc[s, 'rol'])),
            'GUARD-F': bool(T.loc[s, 'off'] <= H.loc[s, 'off'] + 2.0),
        }
    # SELF leak-check bloqueante (emenda REVALIDAÇÃO)
    self_bad = [Path(f).name for f in trat_files if not self_ok(f)[0]]
    checks = {
        'PASS-A taxa <= hist por seed (3/3)': all(per[s]['PASS-A'] for s in GATE_SEEDS),
        'GUARD-V completando >= hist por seed (3/3)': all(per[s]['GUARD-V'] for s in GATE_SEEDS),
        'GUARD-P paradas <= hist por seed (3/3)': all(per[s]['GUARD-P'] for s in GATE_SEEDS),
        'GUARD-W wanderers <= hist por seed (3/3)': all(per[s]['GUARD-W'] for s in GATE_SEEDS),
        'GUARD-L rolante <= hist+5s por seed (3/3)': all(per[s]['GUARD-L'] for s in GATE_SEEDS),
        'GUARD-F fora% <= hist+2pp por seed (3/3)': all(per[s]['GUARD-F'] for s in GATE_SEEDS),
        'SELF leak-check (hold >= reentrada por carro)': not self_bad,
    }
    print("\n=== VEREDITO MECANICO ===")
    allp = True
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
        allp &= bool(v)
    fb_hi = {int(s): int(G.loc[s, 'fb_ev']) for s in GATE_SEEDS if G.loc[s, 'fb_ev'] > 10}
    print(f"\nfallback T_max (report-only; evento = transicao 0->1 de rejoin_gap_fb por carro): "
          f"{ {int(s): int(G.loc[s, 'fb_ev']) for s in GATE_SEEDS} }"
          + (f" | >10/run em {fb_hi} -> diagnostico obrigatorio no relatorio" if fb_hi else ""))
    if self_bad:
        print(f"SELF leak-check VIOLADO em: {self_bad} (instrumento regrediu)")
    for s in GATE_SEEDS:
        fails = [k for k, v in per[s].items() if not v]
        print(f"  seed {s}: {'PASS' if not fails else 'FAIL em ' + ','.join(fails)}")
    print(f"\nGATE ADVERSO: {'TODOS PASS — alavanca VIVA no adverso (adoção = revisão)' if allp else 'FAIL — PARE com diagnóstico por seed; SEM re-pin, SEM re-run; alavanca permanece opt-in (viva no seco, adverso reprovado)'}")
    return 0 if allp else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
