"""SANIDADE-1b — PASSO 1 diagnóstico READ-ONLY (D4/D5; ZERO corridas novas).

Fonte: CSVs JÁ commitados do SANIDADE-0 (experiments/sanidade-0/ gates s70-73)
+ F4v15 (fricção 0,05 de referência). Regra: probe commitado ANTES de cada uso.

D4 — decompor o custo do M3 v1: o Δfora/Δrol vem da FRICÇÃO (0,05→0,01)
  ou do ESTERÇO (preventivo +0,25 rad / breaker +0,4 rad)? Presente da
  estrutura: os gates v0 (G1/G3) rodaram M3 SEM preventivo (escopo
  composite) — fricção+breaker isolados; os comp (G2/G4) com tudo.
  (a) episódios do BREAKER (authority='anti_glue'): nº, duração, e
      excursões do PRÓPRIO carro <=2 s depois (o breaker empurra pra fora?);
  (b) PREVENTIVO indireto (sem telemetria própria): ticks c/ parceiro
      lateral (|Δlat|<2,5 ∧ Δs wrap<10 m) — janelas de exposição — e
      excursões <=2 s depois de tick de exposição;
  (c) SHOVE: excursões c/ contato <=1 s antes (events) — gates (fricção
      0,01) × F4v15 (0,05);
  (d) tempo car·s em episódio/exposição vs custo (fora/rol) por corrida.
D5 — anatomia do deadlock s72 (5_gate_v0_s72): qual par, |Δlat|, v,
  offtrack de alguém, authority por tick, e POR QUE o breaker de 3 s não
  resolveu (nunca engajou? engajou e não separou?).

  .venv/bin/python scripts/analysis/sanidade1b_diag.py
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
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

S0 = Path('experiments/sanidade-0')
F4 = Path('experiments/f4v15-wiring')
HW = 6.00               # D0 (patrimônio): slat = obs4 × half_width
L_TRACK = 4160.4        # polígono frozen Interlagos
ROW_S = 0.2             # linhas do CSV = 0,2 s
GLUE_LAT, GLUE_DS = 2.0, 5.5
PREV_LAT, PREV_DS = 2.5, 10.0   # corredor do preventivo v1 (pin §1)
DEADLOCK_S = 10.0
POST_S = 2.0            # janela de atribuição pós-episódio/exposição
SHOVE_S = 1.0


def load(path):
    df = pd.read_csv(path, comment='#')
    df['slat'] = df.obs4 * HW
    return df


def by_driver(df):
    out = {}
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s').reset_index(drop=True)
        out[drv] = (g, {round(float(t), 2): i for i, t in enumerate(g.t_s)})
    return out


def wrap_ds(s1, s2):
    d = abs(s1 - s2)
    return min(d, L_TRACK - d)


def runs(mask):
    """Índices [ini, fim) de runs True contíguas."""
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def glue_windows(df):
    """Fórmula D3 exata (slat; |Δlat|<2 ∧ Δs<5,5; >2 s) -> [(par, t_ini, dur_s)]."""
    by = by_driver(df)
    ticks = sorted(round(float(t), 2) for t in df.t_s.unique())
    glue = defaultdict(list)
    for t in ticks:
        snap = {}
        for drv, (g, m) in by.items():
            k = m.get(t)
            if k is not None:
                snap[drv] = (float(g.at[k, 'slat']), float(g.at[k, 's']))
        drvs = sorted(snap)
        for a in range(len(drvs)):
            for b in range(a + 1, len(drvs)):
                if (abs(snap[drvs[a]][0] - snap[drvs[b]][0]) < GLUE_LAT
                        and wrap_ds(snap[drvs[a]][1], snap[drvs[b]][1]) < GLUE_DS):
                    glue[tuple(sorted((drvs[a], drvs[b])))].append(t)
    wins = []
    for pr, ts in glue.items():
        run = [ts[0]]
        for t in ts[1:]:
            if t - run[-1] <= 1.5 * ROW_S:
                run.append(t)
            else:
                if len(run) * ROW_S > 2.0:
                    wins.append((pr, run))
                run = [t]
        if len(run) * ROW_S > 2.0:
            wins.append((pr, run))
    return wins, by


def exc_starts(df):
    out = {}
    for drv, g in df.groupby('drv'):
        o = g.sort_values('t_s').offtrack.values
        tt = g.sort_values('t_s').t_s.values
        out[drv] = [float(tt[i + 1]) for i in np.where((o[1:] == 1) & (o[:-1] == 0))[0]]
    return out


def d4(path, label, ev_path=None):
    df = load(path)
    by = by_driver(df)
    exc = exc_starts(df)
    # (a) breaker: runs de authority=='anti_glue' por carro
    brk = {}
    for drv, (g, _) in by.items():
        m = (g.authority.values == 'anti_glue')
        brk[drv] = [(float(g.at[i, 't_s']), float(g.at[j - 1, 't_s']))
                    for i, j in runs(m)]
    n_brk = sum(len(v) for v in brk.values())
    t_brk = sum((b - a) for v in brk.values() for a, b in v) + \
        0.2 * n_brk
    # (b) exposição ao preventivo: ticks c/ parceiro no corredor 2,5/10
    ticks = sorted(round(float(t), 2) for t in df.t_s.unique())
    expo = defaultdict(list)   # drv -> [t]
    for t in ticks:
        snap = {}
        for drv, (g, m) in by.items():
            k = m.get(t)
            if k is not None:
                snap[drv] = (float(g.at[k, 'slat']), float(g.at[k, 's']))
        drvs = sorted(snap)
        for a in range(len(drvs)):
            for b in range(a + 1, len(drvs)):
                da, db = drvs[a], drvs[b]
                if (abs(snap[da][0] - snap[db][0]) < PREV_LAT
                        and wrap_ds(snap[da][1], snap[db][1]) < PREV_DS):
                    expo[da].append(t)
                    expo[db].append(t)
    t_expo = sum(len(v) for v in expo.values()) * ROW_S
    # atribuição de excursões
    ev = None
    if ev_path:
        ev = pd.read_csv(ev_path, comment='#')
        ev['t01'] = (ev['sub'] // 24) * 0.1   # ev['sub']: coluna (ev.sub = método!)
    n_exc = n_pos_brk = n_pos_expo = n_shove = 0
    for drv, ts0 in exc.items():
        for t0 in ts0:
            n_exc += 1
            if any(a - POST_S <= t0 <= b + POST_S for a, b in brk.get(drv, [])):
                n_pos_brk += 1
            elif any(-POST_S <= t0 - x <= POST_S + ROW_S for x in expo.get(drv, [])):
                n_pos_expo += 1
            elif ev is not None:
                m = (((ev.drv_a == drv) | (ev.drv_b == drv))
                     & (ev.t01 >= t0 - SHOVE_S) & (ev.t01 < t0))
                if int(m.sum()) > 0:
                    n_shove += 1
    # (d) fora/rol da corrida p/ custo
    off = round(100 * df.offtrack.mean(), 1)
    rols = []
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        s, t = g.s.values, g.t_s.values
        ds = np.diff(s)
        idx = np.where((s[:-1] < 2655.0) & (s[1:] >= 2655.0) & (ds > 0) & (ds < 100))[0]
        if len(idx) >= 2:
            rols.extend(np.diff(t[idx + 1]))
    print(f"[D4] {label}")
    print(f"  fora={off}% | rol med={np.median(rols) if rols else float('nan'):.0f}s | "
          f"excursões={n_exc}")
    print(f"  breaker: {n_brk} episódios ({t_brk:.1f} car·s) | "
          f"excursões <=2s pós-breaker: {n_pos_brk}")
    print(f"  preventivo (exposição 2,5m/10m): {t_expo:.1f} car·s | "
          f"excursões <=2s pós-exposição: {n_pos_expo}")
    print(f"  excursões c/ contato <=1s antes (shove): {n_shove} | "
          f"sem gatilho próximo: {n_exc - n_pos_brk - n_pos_expo - n_shove}")
    return dict(n_exc=n_exc, n_pos_brk=n_pos_brk, n_pos_expo=n_pos_expo,
                n_shove=n_shove, off=off, t_brk=t_brk, t_expo=t_expo)


def d5(path):
    df = load(path)
    wins, by = glue_windows(df)
    print("[D5] anatomia dos deadlocks (>10 s) do 5_gate_v0_s72.csv:")
    for pr, run in wins:
        dur = len(run) * ROW_S
        if dur <= DEADLOCK_S:
            continue
        print(f"\n  DEADLOCK {pr[0]}×{pr[1]}: {dur:.1f}s @t={run[0]:.1f}..{run[-1]:.1f}")
        ga, gb = by[pr[0]][0], by[pr[1]][0]
        ma, mb = by[pr[0]][1], by[pr[1]][1]
        engaged = False
        for t in run[:: 5]:   # amostra a cada 1 s
            ka, kb = ma.get(round(t, 2)), mb.get(round(t, 2))
            if ka is None or kb is None:
                continue
            la, lb = ga.at[ka, 'slat'], gb.at[kb, 'slat']
            sa, sb = ga.at[ka, 's'], gb.at[kb, 's']
            d = (sb - sa) % L_TRACK
            if d > L_TRACK / 2:
                d -= L_TRACK
            print(f"    t={t:6.1f} Δlat={abs(la - lb):4.2f} Δs={d:+6.2f} | "
                  f"{pr[0]}: v={ga.at[ka, 'speed']:5.1f} slat={la:+5.2f} "
                  f"off={int(ga.at[ka, 'offtrack'])} "
                  f"auth={ga.at[ka, 'authority']:<10} st={ga.at[ka, 'steer_rad']:+.2f} | "
                  f"{pr[1]}: v={gb.at[kb, 'speed']:5.1f} slat={lb:+5.2f} "
                  f"off={int(gb.at[kb, 'offtrack'])} "
                  f"auth={gb.at[kb, 'authority']:<10} st={gb.at[kb, 'steer_rad']:+.2f}")
            if 'anti_glue' in (ga.at[ka, 'authority'], gb.at[kb, 'authority']):
                engaged = True
        na = int((ga.authority.values == 'anti_glue').sum())
        nb = int((gb.authority.values == 'anti_glue').sum())
        print(f"    authority=anti_glue na corrida INTEIRA: {pr[0]}={na} ticks, "
              f"{pr[1]}={nb} ticks | engajou dentro da janela (amostra): "
              f"{'SIM' if engaged else 'NÃO'}")


def main(argv):
    print("=== SANIDADE-1b D4/D5 (read-only; slat=obs4×hw, hw=6,00) ===\n")
    d4(S0 / '3_gate_v0_s70.csv', 'G1 v0 s70 (fricção+breaker; SEM preventivo)',
       S0 / '3_gate_v0_s70_events.csv')
    d4(S0 / '5_gate_v0_s72.csv', 'G3 v0 s72 (fricção+breaker; SEM preventivo)',
       S0 / '5_gate_v0_s72_events.csv')
    d4(S0 / '4_gate_comp_s71.csv', 'G2 comp s71 (M3 completo)',
       S0 / '4_gate_comp_s71_events.csv')
    d4(S0 / '6_gate_comp_s73.csv', 'G4 comp s73 (M3 completo)',
       S0 / '6_gate_comp_s73_events.csv')
    print()
    d4(F4 / '1_controle.csv', 'REF v0 s0 F4v15 (fricção 0,05; SEM M3)',
       F4 / '1_controle_events.csv')
    d4(F4 / '2_allcomposite.csv', 'REF comp s0 F4v15 (fricção 0,05; SEM M3)',
       F4 / '2_allcomposite_events.csv')
    print()
    d5(S0 / '5_gate_v0_s72.csv')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
