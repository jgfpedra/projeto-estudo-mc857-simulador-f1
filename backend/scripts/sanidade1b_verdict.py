"""SANIDADE-1b — veredito MECÂNICO (commitado ANTES das corridas; PADRÃO-OURO).

Prereg 87214c7 §3-§6:
  PROTEÇÕES primeiro (return 2 = PARE, zero re-pin):
    P1 v10-cego flags-off s0 == F4v15-v0 (cc 3674, pos 2482, rol 136,0,
       hesit 3, off 22,1)  |  P2 comp flags-off s0 == F4v15-comp
       (cc 752, pos 292, rol 140, hesit 13, off 25,2)
  ABSOLUTO: 0 deadlocks (>10 s) em TODOS os 7 runs.
  ATRIBUIÇÃO M2 (run 3, diagnóstico não-gaitado): fora vs 25,2% c/ PREDIÇÃO
    pré-registrada 31,8% (=25,2 + 1,8s×219/(600×10)); gatilho >29,9 -> ESCALA.
  GATES M3-v2 (runs 4-7, --anti-glue ONLY): PRIMÁRIO comp colado <= 16,5 s
    (½×33 F4v15) em CADA corrida comp; NÃO-REG 5/5 por corrida de gate:
    cc < proteção da SESSÃO (v0 < P1.cc; comp < P2.cc), 0 paradas >=3 s,
    10/10 voltas, fora <= 29,9, rol <= 146,0. hesit/colado-v0 = report.
  ÁRVORE: M3-v2 FAIL (primário/absoluto/não-reg) -> ARQUIVADO research-
    negative COM LEADS; PASS -> CANDIDATO A BUNDLE (promoção = dono, ciclo
    próprio). fora(M2-only) > 29,9 -> ESCALA AO DONO. Zero re-pin/re-run.

  .venv/bin/python scripts/sanidade1b_verdict.py --selftest
  .venv/bin/python scripts/sanidade1b_verdict.py <p1.csv> <p2.csv> <m2.csv> \
      <g_v0_s74.csv> <g_comp_s74.csv> <g_v0_s75.csv> <g_comp_s75.csv>
"""
import sys

import numpy as np
import pandas as pd

SF_S = 2655.0
L_TRACK = 4160.4
ROW_S = 0.2
HW = 6.00               # D0: slat = obs4 × half_width
F4V15_C = dict(cc=3674, pos=2482, rol=136.0, hesit=3, off=22.1)
F4V15_X = dict(cc=752, pos=292, rol=140.0, hesit=13, off=25.2)
PRIM_TETO = 16.5        # ½ × 33 s (comp s0 F4v15) — RE-ANCORADO
NREG_ROL = 146.0        # ctrl s0 136 + 10 s — RE-ANCORADO
NREG_OFF = 29.9         # p75 seco R12 — RE-ANCORADO
M2_PREV_FORA = 31.8     # predição pré-registrada (25,2 + 6,57 pp)
M2_BASE_FORA = 25.2
GLUE_LAT, GLUE_DS = 2.0, 5.5
GLUE_MIN_S, DEADLOCK_S = 2.0, 10.0


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
    par = hesit = 0
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        v, tt, off = g.speed.values, g.t_s.values, g.offtrack.values
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
    c60 = int(df[df.t_s < 60].car_car.sum())
    durs, wand = [], 0
    for drv, g in df.groupby('drv'):
        o = g.sort_values('t_s').offtrack.values
        i = 0
        while i < len(o):
            if o[i] == 1:
                j = i
                while j < len(o) and o[j] == 1:
                    j += 1
                d = (j - i) * ROW_S
                durs.append(d)
                wand += int(d > 60.0)
                i = j
            else:
                i += 1
    med_exc = float(np.median(durs)) if durs else 0.0
    df['slat'] = df.obs4 * HW
    by = {drv: g.sort_values('t_s').reset_index(drop=True)
          for drv, g in df.groupby('drv')}
    idx_of = {drv: {round(float(t), 2): i for i, t in enumerate(g.t_s)}
              for drv, g in by.items()}
    glue = {}
    for t in sorted(round(float(x), 2) for x in df.t_s.unique()):
        snap = {}
        for drv, g in by.items():
            k = idx_of[drv].get(t)
            if k is not None:
                snap[drv] = (float(g.at[k, 'slat']), float(g.at[k, 's']))
        drvs = sorted(snap)
        for a in range(len(drvs)):
            for b in range(a + 1, len(drvs)):
                da, db = drvs[a], drvs[b]
                ds = abs(snap[da][1] - snap[db][1])
                ds = min(ds, L_TRACK - ds)
                if abs(snap[da][0] - snap[db][0]) < GLUE_LAT and ds < GLUE_DS:
                    glue.setdefault(tuple(sorted((da, db))), []).append(t)
    total, dead = 0.0, 0
    for pr, ts in glue.items():
        run = [ts[0]]
        for t in ts[1:]:
            if t - run[-1] <= 1.5 * ROW_S:
                run.append(t)
            else:
                total += len(run) * ROW_S if len(run) * ROW_S > GLUE_MIN_S else 0.0
                dead += int(len(run) * ROW_S > DEADLOCK_S)
                run = [t]
        total += len(run) * ROW_S if len(run) * ROW_S > GLUE_MIN_S else 0.0
        dead += int(len(run) * ROW_S > DEADLOCK_S)
    return dict(off=round(100 * df.offtrack.mean(), 1), par=par, hesit=hesit,
                n_comp=n_comp,
                rol=round(float(np.median(times)), 0) if times else None,
                cc=int(df.car_car.sum()), pos=int(df[df.t_s > 20].car_car.sum()),
                c60=c60, med_exc=med_exc, wand=wand,
                glue=round(total, 1), dead=dead)


def _prot_ok(s, ref):
    return (s['cc'] == ref['cc'] and s['pos'] == ref['pos']
            and s['rol'] == ref['rol'] and s['hesit'] == ref['hesit']
            and s['off'] == ref['off'] and s['par'] == 0)


def _line(nm, s):
    return (f"  {nm}: cc={s['cc']} (pós-larg {s['pos']}) | par={s['par']} | "
            f"hesit={s['hesit']} | {s['n_comp']}/10 | rol={s['rol']} | "
            f"off={s['off']}% | exc med {s['med_exc']:.1f}s wand={s['wand']} | "
            f"colado {s['glue']}s dead={s['dead']}")


def selftest():
    """PADRÃO-OURO (review SANIDADE-0): reproduz F4v15 e SANIDADE-0 dos CSVs."""
    f4 = 'experiments/f4v15-wiring'
    s0 = 'experiments/sanidade-0'
    ctl = stats(f'{f4}/1_controle.csv')
    cmp_ = stats(f'{f4}/2_allcomposite.csv')
    assert ctl['cc'] == 3674 and ctl['pos'] == 2482 and ctl['rol'] == 136.0
    assert ctl['hesit'] == 3 and ctl['off'] == 22.1
    assert ctl['c60'] == 1624 and abs(ctl['med_exc'] - 4.2) < 0.05
    assert ctl['wand'] == 0 and ctl['glue'] == 246.8 and ctl['dead'] == 6
    assert cmp_['cc'] == 752 and cmp_['pos'] == 292 and cmp_['rol'] == 140.0
    assert cmp_['hesit'] == 13 and cmp_['off'] == 25.2
    assert abs(cmp_['med_exc'] - 4.2) < 0.05 and cmp_['glue'] == 33.2
    assert cmp_['wand'] == 0 and cmp_['dead'] == 0
    g = [stats(f'{s0}/3_gate_v0_s70.csv'), stats(f'{s0}/4_gate_comp_s71.csv'),
         stats(f'{s0}/5_gate_v0_s72.csv'), stats(f'{s0}/6_gate_comp_s73.csv')]
    assert [x['cc'] for x in g] == [1380, 274, 1854, 416]
    assert [x['c60'] for x in g] == [942, 222, 1352, 340]
    assert [x['glue'] for x in g] == [66.6, 2.4, 99.2, 17.8]
    assert [x['dead'] for x in g] == [0, 0, 1, 0]
    assert [round(x['med_exc'], 1) for x in g] == [5.1, 6.0, 4.0, 4.5]
    assert [x['off'] for x in g] == [25.7, 30.0, 25.6, 30.3]
    print("SELFTEST OK: F4v15 (3674/2482/136/3/22,1 | 752/292/140/13/25,2; "
          "c60 1624; exc 4,2s; colado 246,8/33,2; dead 6/0) e SANIDADE-0 gates "
          "(cc 1380/274/1854/416; c60 942/222/1352/340; colado "
          "66,6/2,4/99,2/17,8; dead 0/0/1/0; exc 5,1/6,0/4,0/4,5) reproduzidos.")
    return 0


def main(argv):
    if argv and argv[0] == '--selftest':
        return selftest()
    if len(argv) < 7:
        print(__doc__)
        return 3
    p1, p2, m2 = stats(argv[0]), stats(argv[1]), stats(argv[2])
    gates = [(stats(argv[3]), 'v0', 'G1 v0 s74'), (stats(argv[4]), 'comp', 'G2 comp s74'),
             (stats(argv[5]), 'v0', 'G3 v0 s75'), (stats(argv[6]), 'comp', 'G4 comp s75')]
    print("=== SANIDADE-1b (regime canônico; prereg 87214c7) ===")
    print(_line('P1 v0 flags-off s0 ', p1))
    print(_line('P2 comp flags-off s0', p2))
    ok1 = _prot_ok(p1, F4V15_C)
    ok2 = _prot_ok(p2, F4V15_X)
    print(f"\nPROTEÇÃO P1 == F4v15-v0 {F4V15_C}: "
          f"{'BIT-IDÊNTICO' if ok1 else 'DIVERGIU -> PARE IMEDIATO'}")
    print(f"PROTEÇÃO P2 == F4v15-comp {F4V15_X}: "
          f"{'BIT-IDÊNTICO' if ok2 else 'DIVERGIU -> PARE IMEDIATO'}")
    if not (ok1 and ok2):
        return 2
    # ---- ABSOLUTO: 0 deadlocks em TODOS os 7 runs ----
    print(f"\nABSOLUTO deadlocks=0 (todos os 7 runs): "
          f"P1={p1['dead']} P2={p2['dead']} M2={m2['dead']} "
          f"gates={[g[0]['dead'] for g in gates]}")
    abs_ok = all(s['dead'] == 0 for s in (p1, p2, m2, *[g[0] for g in gates]))
    # ---- ATRIBUIÇÃO M2 (diagnóstico; não-gate) ----
    print(f"\nATRIBUIÇÃO M2 (comp M2-only s0 — diagnóstico, não-gate):")
    print(_line('M2-only comp s0    ', m2))
    delta = round(m2['off'] - M2_BASE_FORA, 1)
    escala = m2['off'] > NREG_OFF
    print(f"  fora={m2['off']}% vs base 25,2% (Δ{delta:+.1f}pp) | "
          f"predição pré-registrada {M2_PREV_FORA}% "
          f"(25,2 + 1,8s×219 excursões/6000 car·s) | "
          f"{'FORA > 29,9 -> ESCALA AO DONO (M2 pode sair do bundle)' if escala else 'fora dentro do teto'}")
    # ---- GATES M3-v2 ----
    print("\n=== GATES M3-v2 (--anti-glue ONLY; isolamento) ===")
    m3_ok = True
    nreg_fail = []
    for s, arm, nm in gates:
        print(_line(nm, s))
        cc_teto = p1['cc'] if arm == 'v0' else p2['cc']   # proteção da SESSÃO
        checks = [
            (f"PRIMÁRIO comp colado ({s['glue']}s) <= {PRIM_TETO}", arm == 'comp',
             s['glue'] <= PRIM_TETO),
            (f"Não-reg cc ({s['cc']}) < proteção sessão ({cc_teto})", True,
             s['cc'] < cc_teto),
            ('Não-reg paradas = 0', True, s['par'] == 0),
            ('Não-reg 10/10 voltas', True, s['n_comp'] == 10),
            (f"Não-reg off ({s['off']}%) <= 29,9", True, s['off'] <= NREG_OFF),
            (f"Não-reg rol ({s['rol']}) <= 146,0", True,
             s['rol'] is not None and s['rol'] <= NREG_ROL),
            (f"ABSOLUTO deadlocks = 0 (há {s['dead']})", True, s['dead'] == 0),
        ]
        for txt, applies, val in checks:
            if not applies:
                continue
            print(f"      {txt}: {'PASS' if val else 'FAIL'}")
            if txt.startswith('PRIMÁRIO') or txt.startswith('ABSOLUTO') \
                    or txt.startswith('Não-reg'):
                if txt.startswith('PRIMÁRIO'):
                    m3_ok &= bool(val)
                elif txt.startswith('Não-reg'):
                    nreg_fail.append((nm, txt)) if not val else None
                else:
                    m3_ok &= bool(val)
    nreg_ok = not nreg_fail
    # SECUNDÁRIO (disclosure; caveat cross-seed)
    print(f"\nSECUNDÁRIO (disclosure; caveat CROSS-SEED — s74/s75 são novas "
          f"realizações): v0 s74/s75 {gates[0][0]['cc']}/{gates[2][0]['cc']} "
          f"vs ref {p1['cc']}; comp s74/s75 "
          f"{gates[1][0]['cc']}/{gates[3][0]['cc']} vs ref {p2['cc']}")
    print()
    if m3_ok and nreg_ok and abs_ok:
        print("M3-v2: PASS — documentado como CANDIDATO A BUNDLE "
              "(promoção = decisão do dono em ciclo próprio)")
    else:
        print(f"M3-v2: FAIL — ARQUIVADO research-negative COM LEADS "
              f"(D4 preventivo-custo; D5 interação M2×M3; ativo v1 colado "
              f"−73/−60% v0){'' if nreg_ok else '; não-reg FAIL ' + str(nreg_fail)}"
              f"{'' if abs_ok else '; ABSOLUTO deadlocks FAIL'}")
    if escala:
        print("M2: fora(M2-only) > 29,9% — ESCALA AO DONO "
              "(M2 pode sair do bundle; decisão do dono)")
    else:
        print("M2: atribuição limpa registrada (fora dentro do teto); memo no fechamento")
    all_ok = m3_ok and nreg_ok and abs_ok and not escala
    print(f"\nSANIDADE-1b: {'TODOS PASS' if all_ok else 'VEREDITO ACIMA — seguir a árvore do prereg §6'}")
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
