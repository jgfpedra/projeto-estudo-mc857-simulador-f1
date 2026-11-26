"""CICLO ALAVANCA — SESSÃO ADVERSA 0-c: CHECK DE NÃO-VAZAMENTO (commitado junto ao 0-a).

O hold do rejoin-gap só pode atuar DENTRO do estado rejoin: antes da 1ª
reentrada o tratamento é bit-idêntico ao braço sem a flag. PREREG §4.

Modos:
  pair BASE GAP        smoke: wiring (authority rejoin_gap>0, hold>0) E
                       1º tick divergente (colunas físicas comuns, exato)
                       >= 1ª reentrada; bônus report-only: == 1º tick de hold.
  self CSV [CSV...]    10 secos 20-29 + tratamentos: por carro com hold,
                       1º hold >= 1ª reentrada DO MESMO carro.
  exc TRAT HIST [...]  bônus largada: 1ª excursão (drv,t_s,s) bit-idêntica
                       à histórica do mesmo seed.
  phase GAP            REPARO: hold EM FASE — authority 'rejoin_gap' ⟺
                       rejoin_gap_hold=1 linha a linha (0 violações) e
                       fb = transições 0->1 (eventos de fallback).
  drift A B            report-only: linhas divergentes nas colunas comuns +
                       1º tick divergente (código atual vs era histórica).

FAIL em pair/self → vazamento de wiring → PARE (instrumento antes de
interpretação).

    .venv/bin/python scripts/experiments/overtaking/lever_leak_check.py pair BASE GAP
    .venv/bin/python scripts/experiments/overtaking/lever_leak_check.py self experiments/diag-alv-seco/race_diag_alv_gap_s2[0-9].csv
    .venv/bin/python scripts/experiments/overtaking/lever_leak_check.py exc TRAT HIST [TRAT HIST ...]
    .venv/bin/python scripts/experiments/overtaking/lever_leak_check.py drift BASE HIST
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

GAP_COLS = {'rejoin_gap_hold', 'rejoin_gap_fb'}


def load(f):
    return pd.read_csv(f, comment='#')


def first_reentry_per_car(df):
    out = {}
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s').reset_index(drop=True)
        off, tick = g.offtrack.values, g.tick.values
        for i in range(1, len(off)):
            if off[i - 1] == 1 and off[i] == 0:
                out[drv] = int(tick[i])
                break
    return out


def first_hold_per_car(df):
    if 'rejoin_gap_hold' not in df.columns:
        return {}
    h = df[df.rejoin_gap_hold == 1]
    return {drv: int(g.tick.min()) for drv, g in h.groupby('drv')}


def first_excursion(df):
    o = df[df.offtrack == 1]
    if not len(o):
        return None
    r = o.sort_values('t_s').iloc[0]
    return (r.drv, round(float(r.t_s), 3), round(float(r.s), 3))


def shared_phys(a, b):
    return [c for c in a.columns if c in b.columns and c not in GAP_COLS]


def diff_rows(a, b):
    cols = shared_phys(a, b)
    if len(a) != len(b):
        raise SystemExit(f"ERRO: linhas diferentes ({len(a)} vs {len(b)}) — runs não comparáveis")
    m = np.zeros(len(a), dtype=bool)
    for c in cols:
        va, vb = a[c].to_numpy(), b[c].to_numpy()
        if a[c].dtype.kind == 'f' or b[c].dtype.kind == 'f':
            eq = (va == vb) | (np.isnan(va) & np.isnan(vb))
        else:
            eq = va == vb
        m |= ~eq
    return m, cols


def mode_pair(base_f, gap_f):
    b, g = load(base_f), load(gap_f)
    hold = int(g.rejoin_gap_hold.sum()) if 'rejoin_gap_hold' in g.columns else 0
    auth = int((g.authority == 'rejoin_gap').sum()) if 'authority' in g.columns else 0
    fb = int(g.rejoin_gap_fb.sum()) if 'rejoin_gap_fb' in g.columns else 0
    print(f"[pair] {Path(gap_f).name}: wiring rejoin_gap: authority ticks={auth} | hold ticks={hold} | fb ticks={fb}")
    if hold == 0 or auth == 0:
        print("[pair] WIRING MORTO no ramo adverso (authority/hold zerados) -> PARE")
        return 1
    m, _ = diff_rows(b, g)
    idx = np.where(m)[0]
    if not len(idx):
        print("[pair] CSVs idênticos nas colunas físicas -> wiring morto -> PARE")
        return 1
    t_div = int(g.tick.values[idx[0]])
    re_b = first_reentry_per_car(b)
    t_re = min(re_b.values()) if re_b else None
    h = first_hold_per_car(g)
    t_hold = min(h.values()) if h else None
    ok = t_re is not None and t_div >= t_re
    print(f"[pair] 1ª reentrada (base): tick {t_re} | 1ª divergência: tick {t_div} (linha {idx[0]}) | 1º hold: tick {t_hold}")
    print(f"[pair] bônus diverg==1º hold: {'OK' if t_hold == t_div else f'DIFERENTE ({t_hold} vs {t_div}) — report'}")
    print(f"[pair] LEAK CHECK: {'PASS — divergência só a partir da reentrada' if ok else 'FAIL — VAZAMENTO: divergência ANTES da 1ª reentrada -> PARE'}")
    return 0 if ok else 1


def mode_self(files):
    rc = 0
    for f in files:
        df = load(f)
        holds = first_hold_per_car(df)
        name = Path(f).name
        if not holds:
            print(f"[self] {name}: sem holds — N/A")
            continue
        re_ = first_reentry_per_car(df)
        bad = [(drv, th, re_.get(drv)) for drv, th in holds.items()
               if re_.get(drv) is None or th < re_.get(drv)]
        print(f"[self] {name}: 1º hold global tick {min(holds.values())} | carros c/ hold: {len(holds)} | "
              f"{'PASS' if not bad else 'FAIL — hold antes da reentrada'}")
        for drv, th, tre in bad:
            print(f"       {drv}: hold@{th} vs reentrada@{tre}")
        rc |= bool(bad)
    return rc


def mode_exc(pairs):
    rc = 0
    for i in range(0, len(pairs), 2):
        tf, hf = pairs[i], pairs[i + 1]
        e1, e2 = first_excursion(load(tf)), first_excursion(load(hf))
        ok = e1 is not None and e1 == e2
        print(f"[exc] {Path(tf).name}: trat {e1} vs hist {e2} -> {'BIT-IDÊNTICA' if ok else 'DIFERE -> investigar (vazamento ou drift)'}")
        rc |= 0 if ok else 1
    return rc


def mode_phase(gap_f):
    """REPARO (amenda A.1-ii): telemetria em fase — cada linha com
    authority 'rejoin_gap' deve ter rejoin_gap_hold=1 e vice-versa (o hold
    é o único gerador da authority); fb conta como transições 0->1."""
    df = load(gap_f)
    if 'rejoin_gap_hold' not in df.columns or 'authority' not in df.columns:
        print(f"[phase] {Path(gap_f).name}: sem colunas de telemetria (flag off?)")
        return 1
    mism = int((df.authority.eq('rejoin_gap') != df.rejoin_gap_hold.eq(1)).sum())
    fb = int(df.rejoin_gap_fb.sum())
    holds = int(df.rejoin_gap_hold.sum())
    per_drv = int(df[df.rejoin_gap_hold == 1].groupby('drv').size().count())
    print(f"[phase] {Path(gap_f).name}: hold ticks={holds} em {per_drv} carros | "
          f"fb eventos={fb} | violações authority⟷hold: {mism} (esperado 0)")
    ok = mism == 0
    print(f"[phase] {'PASS — hold em fase, keyed por carro' if ok else 'FAIL — telemetria fora de fase -> PARE'}")
    return 0 if ok else 1


def mode_drift(a_f, b_f):
    a, b = load(a_f), load(b_f)
    m, cols = diff_rows(a, b)
    n = int(m.sum())
    idx = np.where(m)[0]
    tick = int(a.tick.values[idx[0]]) if len(idx) else None
    print(f"[drift] {Path(a_f).name} vs {Path(b_f).name}: linhas divergentes={n}/{len(a)} em {len(cols)} colunas comuns"
          + (f" | 1º tick divergente={tick}" if tick is not None else " | BIT-IDÊNTICO nas colunas físicas")
          + " (report-only)")


def main(argv):
    mode, args = argv[0], argv[1:]
    if mode == 'pair':
        return mode_pair(args[0], args[1])
    if mode == 'self':
        return mode_self(args)
    if mode == 'exc':
        if len(args) % 2:
            raise SystemExit("exc: pares TRAT HIST")
        return mode_exc(args)
    if mode == 'phase':
        return mode_phase(args[0])
    if mode == 'drift':
        return mode_drift(args[0], args[1])
    raise SystemExit(__doc__)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
