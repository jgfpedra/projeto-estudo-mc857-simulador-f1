"""R5a PASSO 2 — análise das re-medidas com o instrumento autoritativo.

Tabelas do enunciado R5a:
  (i)   cc-verdadeiro vs cc-5Hz por run (+fator, por par, por regime de dv)
  (ii)  decomposição raiz/eco ATUALIZADA com impulso do solver
        (ambiguidade brk>0,3 resolvida: empurrão vs frenagem própria)
  (iii) rejoin-gerador atualizado (pós-60s, re-entrado <10 s)
  (iv)  tempo FORA decomposto: ECOS / RAÍZES / PRESO(>60 s)
  (v)   sensibilidade do limiar de eco: 5/10/20 s
  (vi)  classificação de ENTRADA dos wanderers (só análise p/ R5c)

    python scripts/r5a_analysis.py <run.csv> [<run.csv> ...]
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

L = 4160.4
SF_S = 2655.0
SUB = 24

def signed_ds(a, b):
    d = (a - b) % L
    return d - L if d > L / 2 else d

def load(run_csv):
    df = pd.read_csv(run_csv, comment='#')
    ev = pd.read_csv(run_csv.replace('.csv', '_events.csv'), comment='#')
    ev['tick'] = ev['sub'] // SUB
    ev['pair'] = [tuple(sorted([a, b])) for a, b in zip(ev.drv_a, ev.drv_b)]
    return df, ev

def cc_tables(df, ev):
    """(i) cc-verdadeiro (pares-tick únicos c/ impulso) vs cc-5Hz (flag)."""
    flag_car_ticks = int((df.car_car > 0).sum())
    flag_pair_ticks = df[df.car_car > 0].groupby('tick').apply(
        lambda g: len({tuple(sorted(p)) for p in zip(
            g.drv, [None]*len(g))})) if False else None  # flag não tem par — só carro-tick
    pair_ticks_true = len(ev[['tick', 'pair']].drop_duplicates())
    car_ticks_true = int(pd.concat([ev[['tick', 'drv_a']].rename(columns={'drv_a': 'drv'}),
                                    ev[['tick', 'drv_b']].rename(columns={'drv_b': 'drv'})])
                         .drop_duplicates().pipe(len))
    # cobertura: flag ⊆ eventos (±1 tick)
    ft = set(zip(df[df.car_car > 0].tick, df[df.car_car > 0].drv))
    et = set(zip(ev.tick, ev.drv_a)) | set(zip(ev.tick, ev.drv_b))
    cov = sum(1 for t, d in ft if any((t + k, d) in et for k in (-1, 0, 1)))
    # falsos positivos do flag: flag sem evento na janela
    fp = len(ft) - cov
    # por par (top) e regime de dv
    by_pair = ev.groupby('pair').agg(n_pt=('tick', lambda x: len(set(zip(x, ev.loc[x.index, 'pair'])))),
                                     dv_max=('j_n', 'max')).sort_values('n_pt', ascending=False).head(5)
    dv_regimes = pd.cut(ev.groupby(['tick','pair']).j_n.sum() / 800.0,
                        [0, 1, 3, 10, 100], labels=['<1', '1-3', '3-10', '>10'])
    return dict(flag=flag_car_ticks, true_pairs=pair_ticks_true,
                true_cars=car_ticks_true, cov=cov, fp=fp, total_ft=len(ft),
                factor=pair_ticks_true / max(flag_car_ticks, 1))

def excursions_with_solver(df, ev, echo_gap_s=10.0):
    """(ii) excursões com classificação por impulso do solver no início."""
    et = {}
    for t in sorted(set(ev.tick)):
        et[t] = (set(ev[ev.tick == t].drv_a) | set(ev[ev.tick == t].drv_b))
    out = []
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s').reset_index(drop=True)
        off = g.offtrack.values
        i = 0
        prev_end = None
        while i < len(off):
            if off[i]:
                j = i
                while j < len(off) and off[j]:
                    j += 1
                t0 = g.t_s.values[i]
                tick0 = g.tick.values[i]
                has_imp = any((tick0 + k) in et and drv in et[tick0 + k] for k in (-1, 0, 1))
                r0 = g.iloc[i]
                root = prev_end is None or (t0 - prev_end) > echo_gap_s
                out.append(dict(drv=drv, t0=t0, tick0=tick0, dur=(j - i) * 0.2,
                                lat_max=g.lat.abs().values[i:j].max(),
                                imp=has_imp, root=root,
                                g0=r0.g_gate, gr=r0.g_gate * r0.r_norm,
                                v0=r0.speed, brk0=r0.brk))
                prev_end = t0 + (j - i) * 0.2
                i = j
            else:
                i += 1
    return pd.DataFrame(out)

def main(paths):
    for path in paths:
        df, ev = load(path)
        print(f"\n{'='*72}\n=== {Path(path).name} ===")
        c = cc_tables(df, ev)
        print(f"(i) cc-5Hz flag: {c['flag']} carro-ticks | VERDADE: "
              f"{c['true_pairs']} pares-tick / {c['true_cars']} carro-ticks | "
              f"fator pares/flag = {c['factor']:.2f}×")
        print(f"    cobertura flag⊆eventos(±1): {c['cov']}/{c['total_ft']} | "
              f"falsos positivos do flag: {c['fp']}")
        E = excursions_with_solver(df, ev)
        R = E[E.root]
        print(f"\n(ii) excursões: {len(E)} | raízes: {len(R)} | ecos: {len(E)-len(R)}")
        n_imp = int(R.imp.sum())
        print(f"    raízes COM impulso do solver no início: {n_imp} ({100*n_imp/max(len(R),1):.0f}%)")
        P = R[~R.imp]
        res_m = (P.g0 > 0) & (P.gr > 0.3); solo = P.g0 < 0.05
        print(f"    raízes SEM impulso (pilots): {len(P)} | residual manda: "
              f"{int(res_m.sum())} | solo puro: {int(solo.sum())} | intermediário: "
              f"{len(P)-int(res_m.sum())-int(solo.sum())}")
        brk_hi = P[P.brk0 > 0.3]
        print(f"    (ambiguidade R4 brk>0,3: {len(brk_hi)} pilots c/ freio forte "
              f"— agora SEM impulso = frenagem própria confirmada)")
        # (iii) rejoin-gerador
        reenter = {}
        for drv, g in df.groupby('drv'):
            g = g.sort_values('t_s')
            off = g.offtrack.values; t = g.t_s.values
            reenter[drv] = [t[k] for k in range(1, len(off)) if off[k-1] == 1 and off[k] == 0]
        pos_ev = ev[ev.tick > 600]
        gen = 0
        for r in pos_ev[['tick', 'drv_a', 'drv_b']].drop_duplicates().itertuples():
            t_now = r.tick * 0.1
            for d in (r.drv_a, r.drv_b):
                if any(0 <= t_now - tr <= 10 for tr in reenter.get(d, [])):
                    gen += 1
                    break
        n_pos = len(pos_ev[['tick', 'drv_a', 'drv_b']].drop_duplicates())
        print(f"\n(iii) rejoin-gerador: {gen}/{n_pos} pares-tick pós-60s envolvem "
              f"re-entrante <10 s ({100*gen/max(n_pos,1):.0f}%)")
        # (iv) tempo fora decomposto
        dur_root = E[E.root].dur.sum(); dur_echo = E[~E.root].dur.sum()
        dur_preso = E[E.dur > 60].dur.sum()
        tot_off = df.offtrack.sum() * 0.2
        print(f"\n(iv) tempo fora: {tot_off:.0f}s | raízes {dur_root:.0f}s "
              f"({100*dur_root/max(tot_off,1):.0f}%) | ecos {dur_echo:.0f}s "
              f"({100*dur_echo/max(tot_off,1):.0f}%) | preso>60s {dur_preso:.0f}s "
              f"({100*dur_preso/max(tot_off,1):.0f}%)")
        # (v) sensibilidade do eco
        line = []
        for gap in (5.0, 10.0, 20.0):
            E2 = excursions_with_solver(df, ev, echo_gap_s=gap)
            line.append(f"gap {gap:.0f}s: {int(E2.root.sum())} raízes/{len(E2)-int(E2.root.sum())} ecos")
        print(f"(v) sensibilidade: " + " | ".join(line))
        # (vi) wanderers: entrada
        W = E[E.dur > 60]
        print(f"\n(vi) wanderers (>60s): {len(W)}")
        for r in W.itertuples():
            drv = r.drv; t0 = r.t0
            ev_win = ev[(ev.tick >= (t0 - 10) * 10) & (ev.tick <= t0 * 10)
                        & ((ev.drv_a == drv) | (ev.drv_b == drv))]
            imp10 = len(ev_win) > 0
            g = df[(df.drv == drv)].sort_values('t_s')
            pre = g[(g.t_s >= t0 - 2) & (g.t_s < t0)]
            spin = pre.obs5.diff().abs().max() > 0.35 if len(pre) > 2 else False
            post = g[(g.t_s >= t0) & (g.t_s < t0 + 30)]
            jump = (post.s.diff().abs().max() > 50) if len(post) > 2 else False
            print(f"    {drv} t={t0:.0f}s: impulso 10s antes={'SIM' if imp10 else 'não'} | "
                  f"spin(sinΔ>0,35)={'SIM' if spin else 'não'} | salto proj >50m={'SIM' if jump else 'não'}")

if __name__ == '__main__':
    main(sys.argv[1:])
