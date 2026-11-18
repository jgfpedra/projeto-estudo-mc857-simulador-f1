"""SANIDADE-0 — PASSO 1 diagnóstico READ-ONLY (D1/D2/D3; ZERO corridas novas).

Fonte: CSVs JÁ commitados da FASE-4-v15 (experiments/f4v15-wiring/) — o
CONTROLE v10-cego (1_controle; 3674 cc / 2482 pós-largada) e o
ALL-COMPOSITE sem guard (2_allcomposite; 752/292). Regra da casa: probe
commitado ANTES de cada uso (nunca inline).

D0 VALIDADE (lição R2): a coluna lat do CSV tem convenção de sinal
  suspeita — verificar contra obs4 (canal SINALADO da obs, signed/half_width)
  usando o grid físico (place_grid: colunas ±1,9 m por paridade do slot).
  D1/D3 usam lat SINALizado = obs4 × half_width (hw derivado do próprio grid).
D1 LARGADA: os 2482 contatos pós-largada (t>20 s) por PAR e por t;
  |Δlat| na entrada da T1 (Senna S, s>=2700 — sítio da F0); saídas de
  pista por EMPURRÃO (contato do próprio carro <=5 s antes) vs PILOTAGEM;
  efeito do corredor do professor (LAT_CORRIDOR_M=3,5 — "ele me bloqueia"):
  swerve lateral dos carros na largada (t<=15 s) e sua ligação com contatos.
D2 GRAMA: durações de excursão (off->retorno) por carro; wanders >60 s;
  FATOS ESTÁTICOS da lei de rejoin ativa (código: bearing R3 alvo projeção
  +10 m, ganho 2,0 clip 0,79; teto 8 m/s; throttle 0,35; rejoin_gap OFF)
  + re-derivação ao vivo da latência R13 (v na reentrada; tempo até 15 m/s;
  contato <=30 s pós-reentrada).
D3 COLADOS: pares |Δlat|<2,0 m E adjacentes (Δs wrap <5,5 m — carro tem
  ~5 m) por >2 s contíguos (rows de 0,2 s); esterço/v/freio por carro na
  janela; ACOPLAMENTO FÍSICO (esterço divergente — cada um tenta separar —
  mas o par não separa) vs DECISÃO (esterço convergente/nulo — ninguém
  cede); deadlocks >10 s; fração do tempo colado na largada (t<20 s) —
  "colados seguem reto como na largada".

  .venv/bin/python scripts/analysis/sanidade_diag.py
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
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

F4 = Path('experiments/f4v15-wiring')
T1_S = 2700.0          # entrada da T1 (Senna S; sítio F0: s 2699,7-2814)
L_TRACK = 4160.4       # comprimento do polígono frozen Interlagos (auditoria)
ROW_S = 0.2            # linhas do CSV principal = 0,2 s (ticks lógicos pares)
SHOVE_W_S = 5.0        # janela de empurrão antes da saída
GLUE_LAT = 2.0         # |Δlat| < 2 m (pin do dono)
GLUE_DS = 5.5          # adjacência longitudinal (comprimento do carro ~5 m)
GLUE_MIN_S = 2.0       # janela contígua > 2 s
DEADLOCK_S = 10.0


def by_driver(df):
    """{drv: (frame ordenado por t, {round(t,2): idx})} — lookup O(1)."""
    out = {}
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s').reset_index(drop=True)
        out[drv] = (g, {round(float(t), 2): i for i, t in enumerate(g.t_s)})
    return out


def at(by, drv, t):
    m = by[drv][1]
    return m.get(round(float(t), 2))


def load_events(path):
    ev = pd.read_csv(path, comment='#')
    ev['t01'] = (ev['sub'] // 24) * 0.1     # sub->tick: sub//24; tick 0,1 s
    return ev


def pair_key(a, b):
    return tuple(sorted((a, b)))


def grid_order_of(path):
    """grid_order=[...] do cabeçalho (ordem EFETIVA pós-variance)."""
    with open(path) as f:
        head = f.readline()
    m = re.search(r"grid_order=\[(.*?)\]", head)
    if not m:
        return None
    return re.findall(r"'(\w+)'", m.group(1))


def slat_frames(path):
    """{drv: (frame c/ slat=obs4*hw, {round(t,2): idx})}; hw derivado do grid
    (t=0: |slat| deve = 1,9 m por paridade de slot). Imprime o cheque D0."""
    df = pd.read_csv(path, comment='#')
    order = grid_order_of(path)
    t0 = df[df.t_s <= 0.0]
    hw = 6.0
    if order is not None and len(t0) >= 10:
        m0 = {r.drv: abs(float(r.obs4)) for r in t0.itertuples(index=False)}
        vals = [m0.get(d, 0.0) for d in order]
        hw = 1.9 / (sum(vals) / len(vals))
    df['slat'] = df.obs4 * hw
    print(f"  [D0] {path.name}: hw derivado do grid = {hw:.2f} m "
          f"(esperado ~6,0 = width/2 do frozen)")
    if order is not None:
        for i, drv in enumerate(order):
            exp = 1.9 if i % 2 == 0 else -1.9
            r0 = t0[t0.drv == drv]
            if len(r0):
                rr = r0.iloc[0]
                print(f"    [D0] slot {i} {drv:4s}: esperado {exp:+.1f} | "
                      f"obs4×hw {float(rr.obs4) * hw:+.2f} | coluna lat "
                      f"{float(rr.lat):+.2f}")
    out = {}
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s').reset_index(drop=True)
        out[drv] = (g, {round(float(t), 2): i for i, t in enumerate(g.t_s)})
    return out




def wrap_ds(s1, s2):
    d = abs(s1 - s2)
    return min(d, L_TRACK - d)


def d1(ctl_path, ev_path):
    ev = load_events(ev_path)
    by = slat_frames(ctl_path)
    df = pd.read_csv(ctl_path, comment='#')
    print("=== D1 LARGADA (CONTROLE v10-cego; F4v15; lat SINALADO obs4×hw) ===")
    pos = df[df.t_s > 20]
    tot = int(pos.car_car.sum())
    print(f"pós-largada (t>20s): car_car={tot} (veredito: 2482)")
    for lo, hi in [(20, 30), (30, 60), (60, 999)]:
        s = int(pos[(pos.t_s >= lo) & (pos.t_s < hi)].car_car.sum())
        print(f"  t {lo}-{hi}s: {s} ({100.0 * s / max(tot, 1):.1f}%)")
    c60 = int(pos[pos.t_s < 60].car_car.sum())
    print(f"  âncora PRIM-1 (contatos 20<t<60s): {c60}")
    # --- por par (events, t>20) ---
    evo = ev[(ev.t01 > 20) & (ev.drv_a != ev.drv_b)]
    pairs = defaultdict(set)
    for a, b, t in zip(evo.drv_a, evo.drv_b, evo.t01):
        pairs[pair_key(a, b)].add(round(float(t), 1))
    print(f"  pares distintos em contato pós-largada: {len(pairs)}")
    top = sorted(pairs.items(), key=lambda kv: -len(kv[1]))
    for (a, b), ts in top[:8]:
        print(f"    {a:4s}×{b:4s}: {len(ts)} ticks-0,1s em contato "
              f"(t {min(ts):.0f}-{max(ts):.0f}s)")
    alln = sum(len(ts) for _, ts in pairs.items())
    top5 = sum(len(ts) for _, ts in top[:5])
    print(f"  top-5 pares detêm {100.0 * top5 / max(alln, 1):.0f}% dos ticks de contato")
    # --- |Δlat| na entrada da T1 ---
    print("  entrada da T1 (1º s>=2700): carro | t | lat | v | |Δlat| do vizinho <20m")
    t1lats = []
    for drv, (g, _) in by.items():
        idx = np.where(g.s.values >= T1_S)[0]
        if len(idx) == 0:
            continue
        k = int(idx[0])
        t, lat, v = float(g.at[k, 't_s']), float(g.at[k, 'slat']), float(g.at[k, 'speed'])
        dmin = float('nan')
        for o, (go, _) in by.items():
            if o == drv:
                continue
            ko = at(by, o, t)
            if ko is None:
                continue
            if wrap_ds(float(go.at[ko, 's']), float(g.at[k, 's'])) < 20.0:
                dl = abs(float(go.at[ko, 'slat']) - lat)
                if np.isnan(dmin) or dl < dmin:
                    dmin = dl
        t1lats.append(dmin)
        print(f"    {drv:4s} | {t:5.1f}s | {lat:+5.1f} | {v:5.1f} | {dmin}")
    arr = np.array([x for x in t1lats if x == x])
    print(f"  |Δlat| do vizinho<20m na T1: mediana {np.median(arr):.1f} m | "
          f"min {arr.min():.1f} | máx {arr.max():.1f} | "
          f"n<2m: {int((arr < 2).sum())}/{len(arr)}")
    # --- EMPURRÃO vs PILOTAGEM ---
    starts = []
    for drv, (g, _) in by.items():
        off = g.offtrack.values
        for i in np.where((off[1:] == 1) & (off[:-1] == 0))[0]:
            starts.append((drv, float(g.at[i + 1, 't_s'])))
    shove = 0
    for drv, t0 in starts:
        m = ((ev.drv_a == drv) | (ev.drv_b == drv)) & \
            (ev.t01 >= t0 - SHOVE_W_S) & (ev.t01 < t0)
        if int(m.sum()) > 0:
            shove += 1
    print(f"  saídas de pista (inícios de excursão): {len(starts)} | "
          f"com contato <=5s antes (EMPURRÃO): {shove} "
          f"({100.0 * shove / max(len(starts), 1):.0f}%) | "
          f"sem contato (PILOTAGEM): {len(starts) - shove}")
    # --- corredor LAT_CORRIDOR_M: swerve lateral na largada ---
    print("  largada t<=15s por carro (corredor do professor: 3,5 m): "
          "lat@0 | range | máx|Δlat|/1s | flips | cc_ev")
    for drv, (g, _) in by.items():
        w = g[g.t_s <= 15.0]
        if len(w) < 6:
            continue
        lat = w.slat.values
        rng = float(lat.max() - lat.min())
        rate = float(max(abs(lat[i + 5] - lat[i]) for i in range(len(lat) - 5)))
        flips = int(np.sum(np.diff(np.sign(lat)) != 0))
        m = ((ev.drv_a == drv) | (ev.drv_b == drv)) & (ev.t01 <= 15.0)
        print(f"    {drv:4s} | {lat[0]:+5.1f} | {rng:5.1f} | {rate:5.1f} | "
              f"{flips:2d} | {int(m.sum())}")
    print()


def d2(path, label):
    df = pd.read_csv(path, comment='#')
    by = by_driver(df)
    print(f"=== D2 GRAMA ({label}) ===")
    durs, wand, v_end, to15 = [], [], [], []
    for drv, (g, _) in by.items():
        off = g.offtrack.values
        i = 0
        while i < len(off):
            if off[i] == 1:
                j = i
                while j < len(off) and off[j] == 1:
                    j += 1
                d = (j - i) * ROW_S
                durs.append(d)
                if d > 60.0:
                    wand.append(f"{drv} {d:.0f}s @t={float(g.at[i, 't_s']):.0f}s")
                if j < len(off):
                    v_end.append(float(g.at[j, 'speed']))
                    k = j
                    while k < len(off) and float(g.at[k, 'speed']) < 15.0:
                        k += 1
                    to15.append((k - j) * ROW_S if k < len(off) else float('nan'))
                i = j
            else:
                i += 1
    durs = np.array(durs) if durs else np.array([0.0])
    print(f"  excursões: {len(durs)} | duração mediana {np.median(durs):.1f}s | "
          f"p75 {np.percentile(durs, 75):.1f} | máx {durs.max():.1f} | "
          f"wanders >60s: {len(wand)}")
    for w in wand:
        print(f"    wander {w}")
    print(f"  reentrada: v mediana {np.median(v_end) if v_end else float('nan'):.1f} m/s | "
          f"tempo até 15 m/s: mediana {np.nanmedian(to15) if to15 else float('nan'):.1f}s "
          f"(R13 dossiê: ~8 m/s; ~1,2s)")
    print()


def d2_contato_pos_reentrada(ctl_path, ev_path):
    """Contato <=30s pós-reentrada (re-derivação da latência R13 no CONTROLE)."""
    df = pd.read_csv(ctl_path, comment='#')
    ev = load_events(ev_path)
    by = by_driver(df)
    hits, gaps = 0, []
    tot = 0
    for drv, (g, _) in by.items():
        off = g.offtrack.values
        for i in np.where((off[1:] == 0) & (off[:-1] == 1))[0]:
            t_end = float(g.at[i + 1, 't_s'])
            m = ((ev.drv_a == drv) | (ev.drv_b == drv)) & \
                (ev.t01 >= t_end) & (ev.t01 < t_end + 30.0)
            tot += 1
            if int(m.sum()) > 0:
                hits += 1
                gaps.append(float(ev.t01[m].min() - t_end))
    print(f"  reentradas do CONTROLE c/ contato <=30s depois: {hits}/{tot} "
          f"({100.0 * hits / max(tot, 1):.0f}%) | "
          f"gap mediana {np.median(gaps) if gaps else float('nan'):.1f}s "
          f"(R13: mediana 8,7s; 35% <=5s)")
    print()


def d3(path, ev_path, label):
    ev = load_events(ev_path)
    by = slat_frames(path)
    df = pd.read_csv(path, comment='#')
    ticks = sorted(round(float(t), 2) for t in df.t_s.unique())
    print(f"=== D3 COLADOS ({label}; |Δlat|<{GLUE_LAT}m ∧ Δs wrap<{GLUE_DS}m) ===")
    glue = defaultdict(list)
    for t in ticks:
        snap = {}
        for drv, (g, _) in by.items():
            k = at(by, drv, t)
            if k is not None:
                snap[drv] = (float(g.at[k, 'slat']), float(g.at[k, 's']))
        drvs = sorted(snap)
        for x in range(len(drvs)):
            for y in range(x + 1, len(drvs)):
                a, b = drvs[x], drvs[y]
                if (abs(snap[a][0] - snap[b][0]) < GLUE_LAT
                        and wrap_ds(snap[a][1], snap[b][1]) < GLUE_DS):
                    glue[pair_key(a, b)].append(t)
    wins = []
    for pr, ts in glue.items():
        run = [ts[0]]
        for t in ts[1:]:
            if t - run[-1] <= 1.5 * ROW_S:
                run.append(t)
            else:
                if len(run) * ROW_S > GLUE_MIN_S:
                    wins.append((pr, run))
                run = [t]
        if len(run) * ROW_S > GLUE_MIN_S:
            wins.append((pr, run))
    total = sum(len(r) * ROW_S for _, r in wins)
    dead = [(pr, r) for pr, r in wins if len(r) * ROW_S > DEADLOCK_S]
    early = sum(len(r) * ROW_S for _, r in wins if r[0] < 20.0)
    print(f"  janelas >{GLUE_MIN_S}s: {len(wins)} | tempo total colado "
          f"{total:.0f}s | na largada (t<20s): {early:.0f}s "
          f"({100.0 * early / max(total, 1e-9):.0f}%) | "
          f"deadlocks >{DEADLOCK_S}s: {len(dead)}")
    div_pos = div_neg = 0
    for pr, r in wins:
        (ga, _), (gb, _) = by[pr[0]], by[pr[1]]
        sa, sb, va, vb, ba, bb = [], [], [], [], [], []
        for t in r:
            ka, kb = at(by, pr[0], t), at(by, pr[1], t)
            if ka is not None:
                sa.append(float(ga.at[ka, 'steer_rad']))
                va.append(float(ga.at[ka, 'speed']))
                ba.append(float(ga.at[ka, 'brk']))
            if kb is not None:
                sb.append(float(gb.at[kb, 'steer_rad']))
                vb.append(float(gb.at[kb, 'speed']))
                bb.append(float(gb.at[kb, 'brk']))
        if not sa or not sb:
            continue
        sign = np.sign(float(gb.at[at(by, pr[1], r[0]), 'slat'])
                       - float(ga.at[at(by, pr[0], r[0]), 'slat'])) or 1.0
        div = sign * (np.mean(sb) - np.mean(sa))
        if div > 0:
            div_pos += 1
        else:
            div_neg += 1
        m = (((ev.drv_a == pr[0]) & (ev.drv_b == pr[1])) |
             ((ev.drv_a == pr[1]) & (ev.drv_b == pr[0]))) & \
            (ev.t01 >= r[0]) & (ev.t01 <= r[-1] + 1.0)
        print(f"    {pr[0]:4s}×{pr[1]:4s}: {len(r) * ROW_S:5.1f}s @t={r[0]:6.1f} | "
              f"div={'SEPARANDO' if div > 0 else 'JUNTO/NULO'}({div:+.2f}) | "
              f"v {np.mean(va):4.1f}/{np.mean(vb):4.1f} | "
              f"brk {np.mean(ba):.2f}/{np.mean(bb):.2f} | "
              f"|steer| médio {(abs(np.mean(sa)) + abs(np.mean(sb))) / 2:.2f} | "
              f"cc_ev {int(m.sum())}")
    print(f"  leitura: janelas c/ esterço DIVERGENTE (cada um tenta separar — "
          f"o par não separa => FÍSICA): {div_pos} | "
          f"convergente/nulo (ninguém cede => DECISÃO): {div_neg}")
    print()


def main(argv):
    ctl = F4 / '1_controle.csv'
    comp = F4 / '2_allcomposite.csv'
    print("FATOS ESTÁTICOS da lei de rejoin ATIVA no runner (código lido): "
          "bearing R3 — alvo = projeção +10 m na linha central; "
          "steer = clip(2,0·berr, ±0,79); teto 8 m/s off-track; "
          "throttle 0,35; rejoin_gap (gap-check) DEFAULT OFF.\n")
    d1(ctl, F4 / '1_controle_events.csv')
    d2(ctl, 'CONTROLE v10-cego')
    d2_contato_pos_reentrada(ctl, F4 / '1_controle_events.csv')
    d2(comp, 'ALL-COMPOSITE (sem guard — F4v15)')
    d3(ctl, F4 / '1_controle_events.csv', 'CONTROLE v10-cego')
    d3(comp, F4 / '2_allcomposite_events.csv', 'ALL-COMPOSITE (sem guard)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
