"""CICLO LARGADA L-1b — veredito MECÂNICO do gate (prereg cd3ca5e; commitado ANTES
de ler qualquer resultado; glob filtra _events DESDE O 1º COMMIT — NIT R4.1).

Critérios (âncoras 82b12c6; instrumento idêntico ao L-1a):
  PRIMÁRIO-1 (vinculante): pares_W mediana <= 8 E máx <= 14
  PRIMÁRIO-2 (emendado): >= 7/10 com taxonomia != CONTATO-ADJ ou run sem excursão
    (ramo t>12,4s RETIRADO — o mecanismo desloca t por construção)
  NÃO-REGRESSÃO: rolante (EXCLUI volta 1) SECAS <= 141 | s60 <= base+5;
    GUARD-V 10/10; paradas (EXCLUEM janela de hold por authority) SECAS 0 |
    s60 <= base; wanderers SECAS 0 | s60 <= base; fora% <= 28,3;
    cc SECA <= 3.197 | DAMP <= 3.850
  EXPECTATIVA report-only: med <= 8 -> densidade VALIDADA; ~âncora (12-23) ->
    densidade NÃO é o mecanismo -> grid-era falharia a fortiori
  SELF: identity launch_stagger=True 10/10 (logs) + fase authority<->held
    0 violações + release EXATO por carro (held == tick < (slot-1)*10)
  REPORT-ONLY: pares_W estratificado por PAR DE COMPOSTOS (insumo grid-era)

    .venv/bin/python scripts/experiments/launch/largada_lg1b_verdict.py \
      experiments/diag-alv-seco/weather_scan_s60_s69.csv \
      experiments/diag-largada/race_diag_lg1b_base_s60.csv \
      experiments/diag-largada/race_diag_lg1b_s6*.csv
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

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.experiments.overtaking.lever_gate_verdict import stats, SF_S
from scripts.experiments.launch.largada_anatomy import events_of, first_excursion, W

HIST = dict(pares_med_max=8, pares_max=14, rol_seca=141.0, off_max=28.3,
            cc_seca=3197, cc_damp=3850)


def count_stops_excl_hold(df):
    """Paradas >=3 s APÓS o release: episódio = trecho contíguo v<0,5 em
    ticks NÃO-held do carro (a janela de hold NÃO conta — prereg cd3ca5e)."""
    par = 0
    for _, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        if 'stagger_held' in g.columns:
            m = g.stagger_held.values == 0
            v, tt = g.speed.values[m], g.t_s.values[m]
        else:
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
    return par


def rolante_excl_volta1(df):
    """Mediana de tempo de volta EXCLUINDO a volta 1 de cada carro (custo
    declarado do stagger: +9xΔt na volta 1 — prereg)."""
    times = []
    for _, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        s, t = g.s.values, g.t_s.values
        ds = np.diff(s)
        idx = np.where((s[:-1] < SF_S) & (s[1:] >= SF_S) & (ds > 0) & (ds < 100))[0]
        laps = np.diff(t[idx + 1])
        if len(laps) >= 2:
            times.extend(laps[1:])          # exclui a volta 1 de cada carro
    return round(float(np.median(times)), 0) if times else None


def pares_w_compounds(path):
    """Pares distintos em W + estratificação por PAR DE COMPOSTOS (header)."""
    ev = events_of(path)
    head = open(path).readline()
    comp = dict(re.findall(r"'(\w+)':\s*'(\w+)'", head)) if 'compounds' in head else {}
    pairs, strat = set(), {}
    if ev is not None:
        for r in ev[ev.t <= W].itertuples():
            key = tuple(sorted((r.drv_a, r.drv_b)))
            if key in pairs:
                continue
            pairs.add(key)
            cp = "/".join(sorted((comp.get(key[0], '?'), comp.get(key[1], '?'))))
            strat[cp] = strat.get(cp, 0) + 1
    return len(pairs), strat


def taxonomia(path, fx):
    ev = events_of(path)
    if ev is None or fx is None:
        return "SEM-EXCURSAO" if fx is None else "?"
    evd = ev[(ev.drv_a == fx[0]) | (ev.drv_b == fx[0])]
    if not len(evd):
        return "PILOTAGEM"
    return "CONTATO-ADJ" if (evd.t - fx[1]).abs().min() <= 2.0 else "OUTRO"


def self_checks(f, weather_seeds):
    """(identity, fase, release-exato) por run. Divergência -> PARE."""
    name = Path(f)
    log = name.with_suffix('.log')
    ident = 'launch_stagger=True' in open(log).read() if log.exists() else False
    df = pd.read_csv(f, comment='#')
    if 'stagger_held' not in df.columns:
        return False, ['sem coluna stagger_held (flag off?)']
    bad = []
    mism = int((df.authority.eq('stagger') != df.stagger_held.eq(1)).sum())
    if mism:
        bad.append(f"fase {mism} violações")
    head = open(f).readline()
    order = re.findall(r"grid_order=\[(.*?)\]", head)
    slots = {}
    if order:
        slots = {d: i + 1 for i, d in enumerate(re.findall(r"'(\w+)'", order[0]))}
    for drv, g in df.groupby('drv'):
        slot = slots.get(drv)
        if slot is None:
            bad.append(f"{drv}: slot ausente no header")
            continue
        expect = (g.tick.values < (slot - 1) * 10).astype(int)
        if not (g.sort_values('t_s').stagger_held.values == expect).all():
            bad.append(f"{drv}: release não exato")
    return ident and not bad, bad


def main(argv):
    weather = pd.read_csv(argv[0]).set_index('seed')['clima'].to_dict()
    bases = {}
    for f in [x for x in argv[1:] if '_base_s' in Path(x).stem and '_events' not in x]:
        s = int(Path(f).stem.split('_s')[-1])
        df = pd.read_csv(f, comment='#')
        bases[s] = dict(par=count_stops_excl_hold(df), rol=rolante_excl_volta1(df),
                        wand=stats(f)['wand'])
    trats = [x for x in argv[1:]
             if '_base_s' not in Path(x).stem and '_events' not in Path(x).name]
    rows, self_bad, strat_pool = [], [], {}
    for f in sorted(trats):
        s = int(Path(f).stem.split('_s')[-1])
        df = pd.read_csv(f, comment='#')
        st = stats(f)
        npairs, strat = pares_w_compounds(f)
        for k, v in strat.items():
            strat_pool[k] = strat_pool.get(k, 0) + v
        fx = first_excursion(df)
        ok, bad = self_checks(f, weather)
        if not ok:
            self_bad.append((Path(f).name, bad))
        rows.append(dict(seed=s, clima=weather.get(s, '?'), pares_W=npairs,
                         exc_t=fx[1] if fx else None,
                         taxonomia=taxonomia(f, fx),
                         par_excl=count_stops_excl_hold(df), wand=st['wand'],
                         rol_v1ex=rolante_excl_volta1(df), off=st['off'],
                         cc=int(df.car_car.sum()), n_comp=st['n_comp']))
    T = pd.DataFrame(rows)
    print("=== GATE L-1b launch-stagger (seeds 60-69; prereg cd3ca5e) ===")
    print(T.to_string(index=False))
    per = {}
    for r in rows:
        cls = r['clima']
        base = bases.get(60)
        rol_ok = (r['rol_v1ex'] <= base['rol'] + 5) if cls == 'DAMP' \
            else (r['rol_v1ex'] is not None and r['rol_v1ex'] <= HIST['rol_seca'])
        pw_ok = (r['par_excl'] <= base['par'] and r['wand'] <= base['wand']) if cls == 'DAMP' \
            else (r['par_excl'] == 0 and r['wand'] == 0)
        cc_ok = (r['cc'] <= HIST['cc_damp']) if cls == 'DAMP' else (r['cc'] <= HIST['cc_seca'])
        per[r['seed']] = {'PRIM-2': bool(r['exc_t'] is None or r['taxonomia'] != 'CONTATO-ADJ'),
                          'ROL': bool(rol_ok), 'PW': bool(pw_ok),
                          'OFF': bool(r['off'] <= HIST['off_max']), 'CC': bool(cc_ok),
                          'V': bool(r['n_comp'] == 10), 'clima': cls}
    med, mx = T.pares_W.median(), T.pares_W.max()
    n_prim2 = sum(v['PRIM-2'] for v in per.values())
    checks = {
        f'PRIMÁRIO-1 pares_W mediana {med:.0f} <= 8 E máx {mx} <= 14':
            (med <= HIST['pares_med_max']) and (mx <= HIST['pares_max']),
        f'PRIMÁRIO-2 {n_prim2}/10 taxonomia != CONTATO-ADJ ou sem excursão': n_prim2 >= 7,
        'NÃO-REG rolante v1-excl (seca<=141 / damp<=base+5)': all(v['ROL'] for v in per.values()),
        'NÃO-REG GUARD-V 10/10': all(v['V'] for v in per.values()),
        'NÃO-REG paradas-excl-hold/wand (seca 0/0 / damp<=base)': all(v['PW'] for v in per.values()),
        'NÃO-REG fora% <= 28,3': all(v['OFF'] for v in per.values()),
        'NÃO-REG contatos <= hist+10%': all(v['CC'] for v in per.values()),
        'SELF identity+fase+release-exato': not self_bad,
    }
    print("\n=== VEREDITO MECÂNICO ===")
    allp = True
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
        allp &= bool(v)
    print(f"\nEXPECTATIVA (report-only): pares_W med {med:.0f} -> "
          f"{'DENSIDADE VALIDADA (adoção opt-in + grid-era opcional ao dono)' if med <= HIST['pares_med_max'] else '≈ âncora (12-23) -> densidade NÃO é o mecanismo -> grid-era falharia a fortiori -> fechar CICLO com (b)'}")
    print(f"REPORT-ONLY pares_W por PAR DE COMPOSTOS (pooled): {strat_pool}")
    for s in sorted(per):
        fails = [k for k in ('PRIM-2', 'ROL', 'PW', 'OFF', 'CC', 'V') if not per[s][k]]
        print(f"  seed {s} [{per[s]['clima']}]: {'PASS' if not fails else 'FAIL em ' + ','.join(fails)}")
    if self_bad:
        print(f"  SELF VIOLADO: {self_bad}")
    print(f"\nGATE L-1b: {'TODOS PASS — stagger VIVO: densidade é o mecanismo (PARE p/ revisão)' if allp else 'FAIL — PARE por seed com diagnóstico; SEM re-pin, SEM re-run'}")
    return 0 if allp else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
