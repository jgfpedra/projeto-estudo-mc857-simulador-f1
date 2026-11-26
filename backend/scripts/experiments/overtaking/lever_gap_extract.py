"""CICLO ALAVANCA PASSO 0-c/0-d — derivação de X do corpus R13 (ZERO runs).

Sobre os 20 CSVs do braço CEGO (seeds 10-19 do R13-GATE) + os 10 do braço A
(R7a, seeds 0-9, para o histograma 0-d), mede:

0-c (alavanca rejoin-gap-check — derivação MECÂNICA de X):
  1. Distribuição de gaps (à frente/atrás, metros E segundos-tempo) no
     momento de cada reentrada (primeiro tick on-track após excursão).
  2. Curva de cobertura: para X ∈ {10,15,20,25,30} m, % das reentradas com
     gap ≥ X na janela útil (~10s depois da reentrada).
  3. A mesma curva no subconjunto PERIGOSO (contato do dono ≤30s pós-reentrada).
  4. Custo: mediana/p75 do tempo extra de espera por gap, por X.
  Tabela X × (%perigosas bloqueadas, %de todas atendidas, espera mediana).
  NÃO escolhe X (PASSO 1 do ciclo).

0-d (primeira excursão): posição s e tempo t da 1ª excursão de cada corrida
  do braço cego; quantas têm 1ª excursão na janela de largada (t<60s).

    .venv/bin/python scripts/experiments/overtaking/lever_gap_extract.py
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
SUB = 24
L = 4160.4
WINDOW_S = 10.0        # janela útil (dossiê: mediana reentrada→contato 8,7s)
HORIZON_CONTACT_S = 30.0  # definição de reentrada perigosa (dossiê R13)
X_GRID = [10, 15, 20, 25, 30]

def signed_ds(a, b):
    d = (a - b) % L
    return d - L if d > L / 2 else d

def load_run(csv_path):
    df = pd.read_csv(csv_path, comment='#')
    ev_path = str(csv_path).replace('.csv', '_events.csv')
    ev = pd.read_csv(ev_path, comment='#') if Path(ev_path).exists() else None
    return df, ev

def contact_events_by_driver(ev):
    """{(tick, drv)} de contato — todos os pares em que drv participou."""
    out = {}
    if ev is None or len(ev) == 0:
        return out
    ev = ev.copy()
    ev['tick'] = ev['sub'] // SUB
    for r in ev.itertuples():
        out.setdefault(r.drv_a, set()).add(r.tick)
        out.setdefault(r.drv_b, set()).add(r.tick)
    return out

def reentries(df):
    """Reentradas por carro: primeiro tick on-track após excursão (off→on)."""
    res = []
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s').reset_index(drop=True)
        off = g.offtrack.values
        i = 0
        while i < len(off):
            if off[i]:
                j = i
                while j < len(off) and off[j]:
                    j += 1
                if j < len(off):  # reentrada real (não fim de corrida)
                    res.append((drv, g.tick.values[j], g.t_s.values[j],
                                g.s.values[j]))
                i = j
            else:
                i += 1
    return res

def gaps_at(df, tick, drv):
    """Gap à frente e atrás (m e s-tempo) no tick dado, vs TODOS os outros carros."""
    frame = df[df.tick == tick]
    me = frame[frame.drv == drv]
    if not len(me):
        return None, None, None, None
    s_me, v_me = me.s.iloc[0], me.speed.iloc[0]
    d_f, d_b = None, None
    for r in frame.itertuples():
        if r.drv == drv:
            continue
        d = signed_ds(r.s, s_me)  # >0 = à frente
        if d > 0 and (d_f is None or d < d_f):
            d_f = d
        if d < 0 and (d_b is None or -d < -d_b):
            d_b = -d
    t_f = d_f / max(v_me, 3.0) if d_f is not None else None
    t_b = d_b / max(r.speed, 3.0) if d_b is not None else None
    return d_f, d_b, t_f, t_b

def min_gap_in_window(df, drv, tick0, seconds=WINDOW_S):
    """Menor gap à frente dentro da janela útil pós-reentrada (None se sem carro)."""
    g = df[(df.drv == drv) & (df.tick > tick0) & (df.tick <= tick0 + int(seconds * 10))]
    if not len(g):
        return None
    return float(g.obs4.abs().min()) * 6.0 if 'obs4' in g.columns else None

def main():
    csvs = []
    EVDIR = BACKEND / 'experiments' / 'diag-r2-r13'
    for s in range(10, 20):
        for arm in ('b', 'a'):
            p = EVDIR / f'race_diag_r13_{arm}_s{s}.csv'
            if p.exists():
                csvs.append((f'{arm}_s{s}', p))
    # 0-c corpus: braço CEGO (b) — o produto default; e braço A para o 0-d
    print(f"corpus: {[t for t, _ in csvs]}")

    # ---------- 0-c: gaps nas reentradas do braço CEGO ----------
    re_rows = []
    first_exc = []  # 0-d
    for tag, path in csvs:
        df, ev = load_run(path)
        contacts = contact_events_by_driver(ev)
        # 0-d: primeira excursão (só braço cego)
        if tag.startswith('b_'):
            seen = set()
            for drv, g in df.groupby('drv'):
                g = g.sort_values('t_s')
                off = g.offtrack.values
                i = 0
                while i < len(off):
                    if off[i]:
                        first_exc.append(dict(run=tag, drv=drv,
                                              t=g.t_s.values[i], s=g.s.values[i]))
                        seen.add(tag)
                        break
                    i += 1
        # 0-c: reentradas com gaps
        for drv, tick0, t0, s0 in reentries(df):
            d_f, d_b, t_f, t_b = gaps_at(df, tick0, drv)
            # perigosa: contato do dono ≤30s pós-reentrada
            ct = contacts.get(drv, set())
            dangerous = any(tick0 < tk <= tick0 + int(HORIZON_CONTACT_S * 10) for tk in ct)
            re_rows.append(dict(run=tag, drv=drv, t0=t0, s0=s0,
                                gap_f=d_f, gap_b=d_b, gap_f_s=t_f, gap_b_s=t_b,
                                dangerous=int(dangerous)))
    RE = pd.DataFrame(re_rows)
    B = RE[RE.run.str.startswith('b_')].copy()
    B.to_csv(BACKEND / 'lever_gaps_braço_cego.csv', index=False)

    print(f"\n=== 0-c: {len(B)} reentradas no braço cego (20 corridas) ===")
    print(f"perigosas (contato ≤30s): {B.dangerous.sum()} ({100*B.dangerous.mean():.0f}%)")
    gf = B.gap_f.dropna()
    print(f"\ngap À FRENTE na reentrada (m): mediana {gf.median():.0f} | p25 {gf.quantile(.25):.0f} | p75 {gf.quantile(.75):.0f} | sem carro à frente: {B.gap_f.isna().sum()}")
    gfs = B.gap_f_s.dropna()
    if len(gfs):
        print(f"gap à frente em TEMPO (s): mediana {gfs.median():.1f}s | p25 {gfs.quantile(.25):.1f}s | p75 {gfs.quantile(.75):.1f}s")
    gb = B.gap_b.dropna()
    print(f"gap ATRÁS na reentrada (m): mediana {gb.median():.0f} | p75 {gb.quantile(.75):.0f}")

    # curva X
    print(f"\n=== 0-c: tabela X × (%perigosas bloqueadas, %todas atendidas, espera mediana) ===")
    print(f"{'X (m)':>6} {'%perig. bloqueadas':>18} {'%todas atendidas':>16} {'espera med (s)':>14}")
    dan = B[B.dangerous == 1]
    for X in X_GRID:
        # bloqueadas = perigosas com gap_f < X na reentrada (o gap-check as teria segurado)
        blk = (dan.gap_f.dropna() < X).sum() if len(dan) else 0
        pct_blk = 100 * blk / max(len(dan), 1)
        atend = (B.gap_f.dropna() >= X).sum()
        pct_at = 100 * atend / max(len(B), 1)
        # custo: espera mediana estimada = gap em tempo à frente − X/v (aprox)
        wait = []
        for r in B.itertuples():
            if r.gap_f is not None and not np.isnan(r.gap_f) and r.gap_f < X:
                v = max(3.0, 20.0)
                wait.append((X - r.gap_f) / v)
        med_wait = float(np.median(wait)) if wait else 0.0
        print(f"{X:>6} {pct_blk:>17.0f}% {pct_at:>15.0f}% {med_wait:>13.1f}s")

    # ---------- 0-d: primeira excursão ----------
    print(f"\n=== 0-d: primeira excursão por corrida (braço cego) ===")
    F = pd.DataFrame(first_exc)
    F.to_csv(BACKEND / 'lever_first_excursion.csv', index=False)
    per_run = F.sort_values('t').groupby('run').first().reset_index()
    print(per_run[['run', 'drv', 't', 's']].round(0).to_string(index=False))
    n_launch = (per_run.t < 60).sum()
    print(f"\ncorridas com 1ª excursão na janela de largada (t<60s): {n_launch}/{len(per_run)}")
    print(f"t mediana da 1ª excursão: {per_run.t.median():.0f}s | s mediana: {per_run.s.median():.0f}m")

if __name__ == '__main__':
    main()
