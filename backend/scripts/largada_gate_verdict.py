"""CICLO LARGADA L-1a — veredito MECÂNICO do gate (prereg a3b8ff0 §3; commitado ANTES dos números).

Critérios (âncoras citadas no prereg; instrumentos idênticos ao 0-c/anatomia):
  PRIMÁRIO-1  pares_W mediana <= 8 E máx <= 14 (âncora 12-23, med 17,0)
  PRIMÁRIO-2  >= 7/10 runs com t_1ªexc > 12,4 s OU taxonomia != CONTATO-ADJ
              (run sem excursão conta como PASS)
  NÃO-REGRESSÃO:
    rolante: SECAS <= 141 s (hist 136+5) | s50 <= base fresca s50 + 5 s
    GUARD-V 10/10 | par/wand: SECAS 0/0 | s50 <= base fresca (lição C')
    fora% <= 28,3 | contatos (soma car_car): SECA <= 3.197 | DAMP <= 3.850
  EXPECTATIVA report-only (não-gating): fora% < 15 em >= 7/10
  SELF BLOQUEANTE: authority 'launch_cap' <==> launch_cap_active=1 (0 violações)

    .venv/bin/python scripts/largada_gate_verdict.py \
      experiments/diag-alv-seco/weather_scan_s50_s59.csv \
      experiments/diag-largada/race_diag_lg1_base_s50.csv \
      experiments/diag-largada/race_diag_lg1_s5*.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lever_gate_verdict import stats
from largada_anatomy import events_of, first_excursion, W

HIST = dict(pares_med_max=8, pares_max=14, t2x=12.4, rol_seca=141.0,
            off_max=28.3, cc_seca=3197, cc_damp=3850)
EXPECT_CASCATA = 15.0


def pares_w(path):
    ev = events_of(path)
    if ev is None:
        return 0, []
    pairs = set()
    for r in ev[ev.t <= W].itertuples():
        pairs.add(tuple(sorted((r.drv_a, r.drv_b))))
    return len(pairs), sorted(pairs)


def taxonomia(path, fx):
    ev = events_of(path)
    if ev is None or fx is None:
        return "SEM-EXCURSAO" if fx is None else "?"
    evd = ev[(ev.drv_a == fx[0]) | (ev.drv_b == fx[0])]
    if not len(evd):
        return "PILOTAGEM"
    return "CONTATO-ADJ" if (evd.t - fx[1]).abs().min() <= 2.0 else "OUTRO"


def phase_ok(path):
    df = pd.read_csv(path, comment='#')
    if 'launch_cap_active' not in df.columns:
        return False, -1
    return (int((df.authority.eq('launch_cap') != df.launch_cap_active.eq(1)).sum()) == 0), \
        int(df.launch_cap_active.sum())


def main(argv):
    weather = pd.read_csv(argv[0]).set_index('seed')['clima'].to_dict()
    bases = {}
    for f in [x for x in argv[1:] if '_base_s' in Path(x).stem]:
        s = int(Path(f).stem.split('_s')[-1])
        bases[s] = stats(f)
    trats = [x for x in argv[1:]
             if '_base_s' not in Path(x).stem and '_events' not in Path(x).name]
    rows, phase_bad = [], []
    for f in sorted(trats):
        s = int(Path(f).stem.split('_s')[-1])
        st = stats(f)
        npairs, _ = pares_w(f)
        fx = first_excursion(pd.read_csv(f, comment='#'))
        tx = taxonomia(f, fx)
        ok_ph, ncap = phase_ok(f)
        if not ok_ph:
            phase_bad.append(Path(f).name)
        rows.append(dict(seed=s, clima=weather.get(s, '?'),
                         pares_W=npairs, exc_t=fx[1] if fx else None,
                         taxonomia=tx, par=st['par'], wand=st['wand'],
                         rol=st['rol'], off=st['off'], cc=st.get('cc', None),
                         n_comp=st['n_comp'], cap_ticks=ncap))
    for r in rows:
        f = next(x for x in trats if int(Path(x).stem.split('_s')[-1]) == r['seed'])
        r['cc'] = int(pd.read_csv(f, comment='#').car_car.sum())
    T = pd.DataFrame(rows)
    print("=== GATE L-1a launch-cap (seeds 50-59; âncoras do prereg a3b8ff0) ===")
    print(T.to_string(index=False))
    per = {}
    for r in rows:
        cls = r['clima']
        base = bases.get(r['seed'])
        prim2 = (r['exc_t'] is None) or (r['exc_t'] > HIST['t2x']) or (r['taxonomia'] != 'CONTATO-ADJ')
        rol_ok = (r['rol'] <= bases[50]['rol'] + 5) if cls == 'DAMP' else (r['rol'] <= HIST['rol_seca'])
        pw_ok = (r['par'] <= base['par'] and r['wand'] <= base['wand']) if cls == 'DAMP' \
            else (r['par'] == 0 and r['wand'] == 0)
        cc_ok = (r['cc'] <= HIST['cc_damp']) if cls == 'DAMP' else (r['cc'] <= HIST['cc_seca'])
        per[r['seed']] = {'PRIM-2': bool(prim2), 'ROL': bool(rol_ok), 'PW': bool(pw_ok),
                          'OFF': bool(r['off'] <= HIST['off_max']), 'CC': bool(cc_ok),
                          'V': bool(r['n_comp'] == 10), 'clima': cls}
    med = T.pares_W.median()
    mx = T.pares_W.max()
    n_prim2 = sum(v['PRIM-2'] for v in per.values())
    n_cascata = sum(1 for r in rows if r['off'] < EXPECT_CASCATA)
    checks = {
        f'PRIMÁRIO-1 pares_W mediana {med:.0f} <= 8 E máx {mx} <= 14':
            (med <= HIST['pares_med_max']) and (mx <= HIST['pares_max']),
        f'PRIMÁRIO-2 {n_prim2}/10 com t_1ªexc>12,4s ou não-ADJ': n_prim2 >= 7,
        'NÃO-REG rolante (seca<=141 / damp<=base+5)': all(v['ROL'] for v in per.values()),
        'NÃO-REG GUARD-V 10/10': all(v['V'] for v in per.values()),
        'NÃO-REG par/wand (seca 0/0 / damp<=base)': all(v['PW'] for v in per.values()),
        'NÃO-REG fora% <= 28,3': all(v['OFF'] for v in per.values()),
        'NÃO-REG contatos <= hist+10% (classe)': all(v['CC'] for v in per.values()),
        'SELF fase launch_cap (0 violações)': not phase_bad,
    }
    print("\n=== VEREDITO MECÂNICO ===")
    allp = True
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
        allp &= bool(v)
    print(f"\nEXPECTATIVA (report-only): fora% < 15 em {n_cascata}/10 -> "
          f"{'CASCATA do pacing REAL' if n_cascata >= 7 else 'fora% em 17,3-26,3 -> artefato keying da era contaminada (ou misto)'}")
    for s in sorted(per):
        fails = [k for k in ('PRIM-2', 'ROL', 'PW', 'OFF', 'CC', 'V') if not per[s][k]]
        print(f"  seed {s} [{per[s]['clima']}]: {'PASS' if not fails else 'FAIL em ' + ','.join(fails)}")
    if phase_bad:
        print(f"  SELF VIOLADO em: {phase_bad}")
    print(f"\nGATE L-1a: {'TODOS PASS — launch-cap VIVO (adoção = revisão; grid-era ao dono: 112 pares de grid persistem)' if allp else 'FAIL — PARE por seed com diagnóstico; SEM re-pin, SEM re-run'}")
    return 0 if allp else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
