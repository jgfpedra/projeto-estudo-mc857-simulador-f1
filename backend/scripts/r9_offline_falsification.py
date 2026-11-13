"""R9 PASSO 0 — falsificação OFFLINE dos candidatos de camada (zero runs).

Motor de contrafactual calibrado contra os CSVs R8 ON (0.1) e aplicado aos
candidatos A (slip-cap) e B (rate-limiter) no corpus R7a OFF, sob os
limiares do PREREG_R9_OFFLINE.md (commitado antes desta análise).

    .venv/bin/python scripts/r9_offline_falsification.py
"""
import os, sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND)); sys.path.insert(0, str(BACKEND.parent))

import numpy as np
import pandas as pd

L_WB = 3.4
SUB = 24
V_MIN_SLIP = 3.0     # ticks com v<3 m/s: slip não confiável (prereg)
PREWIN = 30          # janela pré-saída (ticks, 3 s)


def slip_series(g, track_heading_fn):
    """Slip por tick de um carro (5 Hz), via (s,lat) + obs5/6."""
    g = g.sort_values('t_s').reset_index(drop=True)
    s = g.s.values; lat = g.lat.values; v = g.speed.values
    dt = 0.2
    slip = np.full(len(g), np.nan)
    for k in range(2, len(g)):
        if v[k] < V_MIN_SLIP:
            continue
        ds = (s[k] - s[k-2]) / (2*dt)
        if abs(ds) < 0.3:
            continue
        vel_dir = np.arctan2((lat[k] - lat[k-2]) / (2*dt), ds)
        herr = np.arctan2(g.obs5.values[k], g.obs6.values[k])
        head = track_heading_fn(s[k]) + herr
        slip[k] = np.degrees(abs(np.arctan2(np.sin(head - vel_dir),
                                            np.cos(head - vel_dir))))
    return slip


def exit_ticks(g, imp_by_tick):
    """Inícios de saída-raiz (gap>10 s, sem impulso 10 s antes)."""
    off = g.offtrack.values; prev_end = None; i = 0; out = []
    while i < len(off):
        if off[i]:
            j = i
            while j < len(off) and off[j]: j += 1
            t0 = g.t_s.values[i]; tick0 = int(g.tick.values[i])
            if prev_end is None or (t0 - prev_end) > 10.0:
                drv = g.drv.values[0]
                imp10 = any((k in imp_by_tick) and (drv in imp_by_tick[k])
                            for k in range(max(0, tick0-100), tick0+2))
                if not imp10:
                    out.append(tick0)
            prev_end = t0 + (j-i)*0.2
            i = j
        else:
            i += 1
    return out


def main():
    from backend.model_train.f1_env import load_track_frozen
    track = load_track_frozen('interlagos')
    wps = np.asarray(track.waypoints)
    closed = np.vstack([wps, wps[:1]])
    seg = np.hypot(np.diff(closed[:, 0]), np.diff(closed[:, 1]))
    seg_cum = np.concatenate([[0], np.cumsum(seg)])[:-1]
    seg_head = np.arctan2(np.diff(closed[:, 1]), np.diff(closed[:, 0]))
    L = float(seg.sum())

    def track_heading(s):
        s %= L
        j = int(np.searchsorted(seg_cum, s, side='right') - 1) % len(wps)
        return seg_head[j]

    # ---------------- 0.1 — calibração do motor nos CSVs R8 ON -----------
    print("=== 0.1 — CALIBRAÇÃO do motor (reproduzir steer_gov_active, R8 ON) ===")
    for seed in range(10):
        df = pd.read_csv(BACKEND / f'race_diag_r8_on_s{seed}.csv', comment='#')
        k = df.obs10.abs() / 25.0
        cap = 2.0 * np.arctan(L_WB * k)
        pred = (df.steer_rad.abs() >= cap - 1e-6).astype(int)
        conc = (pred == df.steer_gov_active).mean()
        flag = 'OK' if conc >= 0.99 else 'FAIL'
        print(f"  s{seed}: concordância {100*conc:.2f}% [{flag}] "
              f"(ativo: log={df.steer_gov_active.sum()}, pred={pred.sum()})")

    # ---------------- corpus OFF: slip, saídas, ticks normais ------------
    print("\n=== construindo corpus OFF (slip por tick, saídas, normal) ===")
    norm_rows, pre_rows = [], []
    for seed in range(10):
        f = BACKEND / f'race_diag_r7a_disp_s{seed}.csv'
        df = pd.read_csv(f, comment='#')
        ev = pd.read_csv(str(f).replace('.csv', '_events.csv'), comment='#')
        ev['tick'] = ev['sub'] // SUB
        imp_by_tick = {}
        for r in ev.itertuples():
            imp_by_tick.setdefault(r.tick, set()).update([r.drv_a, r.drv_b])
        for drv, g in df.groupby('drv'):
            g = g.sort_values('t_s').reset_index(drop=True)
            slip = slip_series(g, track_heading)
            g['slip'] = slip
            exits = set()
            for tick0 in exit_ticks(g, imp_by_tick):
                exits.update(range(max(0, tick0 - PREWIN), tick0 + 1))
            for k in range(2, len(g)):
                if np.isnan(slip[k]) or g.offtrack.values[k] == 1:
                    continue
                row = dict(seed=seed, drv=drv, tick=int(g.tick.values[k]),
                           delta=abs(g.steer_rad.values[k]),
                           k10=abs(g.obs10.values[k]) / 25.0,
                           slip=slip[k], v=g.speed.values[k],
                           ddot=np.nan)
                if int(g.tick.values[k]) in exits:
                    pre_rows.append(row)
                else:
                    norm_rows.append(row)
            # δ̇ por carro (uma passada)
            dd = np.abs(np.diff(g.steer_rad.values)) / 0.2
            for i, d in enumerate(dd):
                pass  # δ̇ anexado abaixo no dataframe por tick
    N = pd.DataFrame(norm_rows)
    P = pd.DataFrame(pre_rows)
    # δ̇ precisa do contexto por carro — recompute por dataframe de saída
    ddot_by = {}
    for seed in range(10):
        df = pd.read_csv(BACKEND / f'race_diag_r7a_disp_s{seed}.csv', comment='#')
        for drv, g in df.groupby('drv'):
            g = g.sort_values('t_s').reset_index(drop=True)
            dd = np.abs(np.diff(g.steer_rad.values)) / 0.2
            for k in range(1, len(g)):
                ddot_by[(seed, drv, int(g.tick.values[k]))] = dd[k-1] if k-1 < len(dd) else np.nan
    N['ddot'] = [ddot_by.get((r.seed, r.drv, r.tick), np.nan) for r in N.itertuples()]
    P['ddot'] = [ddot_by.get((r.seed, r.drv, r.tick), np.nan) for r in P.itertuples()]
    N.to_csv(BACKEND / 'r9_norm_ticks.csv', index=False)
    P.to_csv(BACKEND / 'r9_preexit_ticks.csv', index=False)
    print(f"ticks normais: {len(N)} | ticks pré-saída: {len(P)}")

    # ---------------- 0.2 — candidato A: slip-cap ------------------------
    print("\n=== 0.2 — CANDIDATO A: slip-cap (k_A=3,0) ===")
    capA = 3.0 * np.arctan(L_WB * N.k10.values)
    for theta in (5.0, 10.0, 15.0):
        condN = (N.slip.values > theta) & (N.delta.values > capA)
        disc = condN.mean()
        print(f"  θ={theta:4.0f}°: disciplina (clip de normais) {100*disc:.2f}% "
              f"[limiar 0,5%] | slip>θ em normais: {100*(N.slip.values>theta).mean():.1f}%")
    # lead/cobertura com o θ do sintoma (10°)
    for theta in (10.0,):
        capP = 3.0 * np.arctan(L_WB * P.k10.values)
        act = (P.slip.values > theta) & (P.delta.values > capP)
        print(f"  θ={theta:.0f}°: janela pré-saída com condição ativa: "
              f"{100*act.mean():.1f}% dos ticks pré-saída")

    # ---------------- 0.3 — candidato B: rate-limiter ---------------------
    print("\n=== 0.3 — CANDIDATO B: rate-limiter ===")
    D = N.ddot.dropna()
    for q in (0.995, 0.999):
        rho = D.quantile(q)
        print(f"  ρ(p{100*q:.1f}) = {rho:.3f} rad/s → disciplina inerente {100*(1-q):.2f}%")
        sep = (P.ddot.dropna() > rho).mean()
        print(f"    rate-spike pré-cruzamento: {100*sep:.1f}% das saídas "
              f"[morte se <30%]")
    # lead do B com ρ p99,9
    rho = D.quantile(0.999)
    print(f"  (lead mediano do B: computado no CSV de pré-saída por saída — "
          f"ver relatório)")


if __name__ == '__main__':
    main()
