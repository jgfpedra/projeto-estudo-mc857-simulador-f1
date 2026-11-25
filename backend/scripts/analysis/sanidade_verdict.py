"""SANIDADE-0 — veredito MECÂNICO (commitado ANTES das corridas; PADRÃO-OURO).

Prereg 1007636 §2/§3 (proteções PRIMEIRO; gate s70-73 SECAS pelo weather-scan):

  PROTEÇÃO (ABSOLUTO; PARE=2 se divergir, sem ler mais nada):
    P1 all-v0 seed 0 flags-OFF == F4v15-controle (cc 3674, pos 2482, rol 136,0,
       hesit 3, off 22,1)
    P2 all-composite seed 0 flags-OFF == F4v15-composite (cc 752, pos 292,
       rol 140, hesit 13, off 25,2)
  PRIM-1 (M1; CADA all-v0 do gate): contatos t<60s <= 812 (= 50% de 1624)
  PRIM-2 (M2; CADA corrida): mediana de excursão <= 8,4s (2× a atual —
       tolerância de não-piora do trade-off ângulo-raso; leitura literal
       "2× melhor" REJEITADA no prereg c/ derivação) E wanders>60s = 0
  PRIM-3 (M3; CADA corrida): tempo colado <= 123,5s (v0) / 16,5s (comp)
       E deadlocks>10s = 0
  NÃO-REG (CADA corrida): 10/10 voltas; 0 paradas >=3s; rol <= 146;
       cc <= 3674 (v0) / 752 (comp — o 1520 do prompt era o guard REPROVADO,
       agora flag-off); off <= 29,9
  ÁRVORE: primário FAIL => mecanismo research-negativo e SAI do bundle
  espectador; sem re-pin/re-run/promoção.

    .venv/bin/python scripts/analysis/sanidade_verdict.py <p1.csv> <p2.csv> \
        <g_v0_s70.csv> <g_comp_s71.csv> <g_v0_s72.csv> <g_comp_s73.csv>
    # com apenas <p1.csv> <p2.csv>: checa SOMENTE as proteções (antes do gate)
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

import numpy as np
import pandas as pd

SF_S = 2655.0
L_TRACK = 4160.4       # polígono frozen Interlagos (auditoria)
ROW_S = 0.2            # linhas do CSV = 0,2 s
HW = 6.00              # half-width (D0 do sanidade_diag: grid dá hw=6,00)
F4V15_C = dict(cc=3674, pos=2482, rol=136.0, hesit=3, off=22.1)
F4V15_X = dict(cc=752, pos=292, rol=140.0, hesit=13, off=25.2)
PRIM1_TETO = 812       # 50% de 1624 (t<60s do controle; derivação 3674-2050)
PRIM2_MED_TETO = 8.4   # 2x a mediana atual (4,2s)
PRIM3_TETO = {'v0': 123.5, 'comp': 16.5}   # -50% de 247s / 33s (D3 slat)
NREG_CC = {'v0': 3674, 'comp': 752}
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
    # SANIDADE-0: t<60s (PRIM-1) + grama (PRIM-2) + colados (PRIM-3, slat)
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
                n_comp=n_comp, rol=round(float(np.median(times)), 0) if times else None,
                cc=int(df.car_car.sum()), pos=int(df[df.t_s > 20].car_car.sum()),
                c60=c60, med_exc=med_exc, wand=wand,
                glue=round(total, 1), dead=dead)


def _prot_ok(s, ref):
    return (s['cc'] == ref['cc'] and s['pos'] == ref['pos']
            and s['rol'] == ref['rol'] and s['hesit'] == ref['hesit']
            and s['off'] == ref['off'] and s['par'] == 0)


def main(argv):
    p1 = stats(argv[0])
    p2 = stats(argv[1])
    print("=== SANIDADE-0 (regime canônico; prereg 1007636) ===")
    print(f"  P1 all-v0 flags-off : cc={p1['cc']} pos={p1['pos']} rol={p1['rol']} "
          f"hesit={p1['hesit']} off={p1['off']}%")
    print(f"  P2 all-comp flags-off: cc={p2['cc']} pos={p2['pos']} rol={p2['rol']} "
          f"hesit={p2['hesit']} off={p2['off']}%")
    ok1 = _prot_ok(p1, F4V15_C)
    ok2 = _prot_ok(p2, F4V15_X)
    print(f"\nPROTEÇÃO P1 == F4v15-controle {F4V15_C}: "
          f"{'BIT-IDÊNTICO' if ok1 else 'DIVERGIU -> PARE IMEDIATO'}")
    print(f"PROTEÇÃO P2 == F4v15-composite {F4V15_X}: "
          f"{'BIT-IDÊNTICO' if ok2 else 'DIVERGIU -> PARE IMEDIATO'}")
    if not (ok1 and ok2):
        return 2
    if len(argv) < 6:
        print("\nProteções verdes (modo 2-args). Gate pode rodar.")
        return 0
    arms = [('v0', argv[2]), ('comp', argv[3]), ('v0', argv[4]), ('comp', argv[5])]
    names = ['G1 v0 s70', 'G2 comp s71', 'G3 v0 s72', 'G4 comp s73']
    res = {'M1': True, 'M2': True, 'M3': True}
    print("\n=== VEREDITO MECÂNICO ===")
    for (arm, path), nm in zip(arms, names):
        s = stats(path)
        line = (f"  {nm}: cc={s['cc']} (t<60s {s['c60']}) | par={s['par']} | "
                f"hesit={s['hesit']} | comp={s['n_comp']}/10 | rol={s['rol']} | "
                f"off={s['off']}% | excursão med {s['med_exc']:.1f}s "
                f"wand={s['wand']} | colado {s['glue']}s dead={s['dead']}")
        print(line)
        checks = [
            (f"PRIM-1 c60 ({s['c60']}) <= {PRIM1_TETO}", arm == 'v0',
             s['c60'] <= PRIM1_TETO),
            (f"PRIM-2 excursão med ({s['med_exc']:.1f}s) <= {PRIM2_MED_TETO}",
             True, s['med_exc'] <= PRIM2_MED_TETO),
            (f"PRIM-2 wanders = 0 (há {s['wand']})", True, s['wand'] == 0),
            (f"PRIM-3 colado ({s['glue']}s) <= {PRIM3_TETO[arm]}", True,
             s['glue'] <= PRIM3_TETO[arm]),
            (f"PRIM-3 deadlocks = 0 (há {s['dead']})", True, s['dead'] == 0),
            (f"Não-reg 10/10 voltas", True, s['n_comp'] == 10),
            (f"Não-reg paradas = 0", True, s['par'] == 0),
            (f"Não-reg rol ({s['rol']}) <= 146", True,
             s['rol'] is not None and s['rol'] <= 146),
            (f"Não-reg cc ({s['cc']}) <= {NREG_CC[arm]}", True,
             s['cc'] <= NREG_CC[arm]),
            (f"Não-reg off ({s['off']}%) <= 29,9", True, s['off'] <= 29.9),
        ]
        for txt, applies, val in checks:
            if not applies:
                continue
            print(f"      {txt}: {'PASS' if val else 'FAIL'}")
            if txt.startswith('PRIM-1'):
                res['M1'] &= bool(val)
            elif txt.startswith('PRIM-2'):
                res['M2'] &= bool(val)
            elif txt.startswith('PRIM-3'):
                res['M3'] &= bool(val)
    print()
    for m, ok in res.items():
        print(f"  {m}: {'PASS — embarca no bundle' if ok else 'FAIL — research-negativo, SAI do bundle'}")
    allok = all(res.values())
    print(f"\nSANIDADE-0: {'TODOS OS PRIMÁRIOS PASS' if allok else 'PRIMÁRIO(S) FAIL — mecanismo(s) sai(m) do bundle; sem re-pin/re-run/promoção'}")
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
