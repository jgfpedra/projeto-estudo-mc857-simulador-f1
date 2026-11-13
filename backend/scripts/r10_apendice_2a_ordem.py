"""R10 PASSO 3 (APÊNDICE, zero runs, SEM impacto no gate) — assinatura de 2ª ordem.

Hipótese da fila pós-gate: o padrão TEMPORAL do comando (offset sustentado +
yaw crescente + curvatura de caminho baixa, em janela deslizante) separa
ticks normais da janela pré-saída, sob a metodologia R9 (denominador
completo + lead time). Veredito: separa / não separa.

Método (pinado no PREREG_R10_GATE.md §PASSO 3):
- features por tick (janela ±2 ticks = 1 s): mediana |δ|; yaw_rate =
  |Δheading_cano|/Δt; path_curv = |Δ direção da velocidade|/Δt.
- regra conjuntiva com limiares da distribuição NORMAL: dispara quando
  med|δ| > p95(normal) E yaw_rate > p95(normal) E path_curv < p50(normal).
- disciplina = fração de ticks NORMAIS disparados (limiar 0,5%);
  cobertura = % de saídas com ≥1 disparo na janela pré-saída (limiar 50%);
  lead = mediana do primeiro disparo antes do cruzamento (limiar 5 ticks).
- RAMO: falha técnica → apêndice INCONCLUSIVO (não bloqueia o gate).

    .venv/bin/python scripts/r10_apendice_2a_ordem.py
"""
import os, sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND)); sys.path.insert(0, str(BACKEND.parent))
import numpy as np
import pandas as pd

L_WB = 3.4; SUB = 24; V_MIN = 3.0; PREWIN = 30; WIN = 2

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
            s = g.s.values; lat = g.lat.values; v = g.speed.values
            n = len(g)
            # séries por tick
            head = np.full(n, np.nan); vdir = np.full(n, np.nan)
            for k in range(2, n):
                if v[k] < V_MIN: continue
                ds = (s[k] - s[k-2]) / 0.4
                if abs(ds) < 0.3: continue
                vdir[k] = np.arctan2((lat[k] - lat[k-2]) / 0.4, ds)
                herr = np.arctan2(g.obs5.values[k], g.obs6.values[k])
                head[k] = track_heading(s[k]) + herr
            # features de janela ±2
            med_d = np.full(n, np.nan); yaw_r = np.full(n, np.nan); path_c = np.full(n, np.nan)
            for k in range(WIN, n - WIN):
                w = slice(k - WIN, k + WIN + 1)
                med_d[k] = np.nanmedian(np.abs(g.steer_rad.values[w]))
                hh = head[w]; vv = vdir[w]
                if not np.isnan(hh).all() and not np.isnan(vv).all():
                    yaw_r[k] = abs((hh[-1] - hh[0]) / (2 * WIN * 0.2))
                    path_c[k] = abs((vv[-1] - vv[0]) / (2 * WIN * 0.2))
            # saídas raiz
            exits = set()
            off = g.offtrack.values; prev_end = None; i = 0
            while i < len(off):
                if off[i]:
                    j = i
                    while j < len(off) and off[j]: j += 1
                    t0 = g.t_s.values[i]; tick0 = int(g.tick.values[i])
                    if prev_end is None or (t0 - prev_end) > 10.0:
                        if not any((kk in imp_by_tick) and (drv in imp_by_tick[kk])
                                   for kk in range(max(0, tick0-100), tick0+2)):
                            exits.update(range(max(0, tick0 - PREWIN), tick0))
                            # pré-saída estrita: ANTES do cruzamento
                    prev_end = t0 + (j - i) * 0.2
                    i = j
                else: i += 1
            # percorre ticks: normal vs pré-saída
            for k in range(WIN, n - WIN):
                if v[k] < V_MIN or np.isnan(med_d[k]): continue
                tk = int(g.tick.values[k])
                if g.offtrack.values[k]: continue
                row = dict(seed=seed, drv=drv, tick=tk, med_d=med_d[k],
                           yaw_r=yaw_r[k], path_c=path_c[k])
                if tk in exits:
                    pre_rows.append(row)
                else:
                    norm_rows.append(row)
            # (norm_rows anteriores com exit=0 são duplicatas — limpar)
    N = pd.DataFrame(norm_rows)
    P = pd.DataFrame(pre_rows)
    N = N.drop_duplicates(subset=['seed', 'drv', 'tick'])
    P = P.drop_duplicates(subset=['seed', 'drv', 'tick'])
    print(f"ticks normais: {len(N)} | ticks pré-saída (strict): {len(P)}")
    # limiares da distribuição NORMAL (metodologia R9)
    d95 = N.med_d.quantile(0.95); y95 = N.yaw_r.quantile(0.95); c50 = N.path_c.quantile(0.50)
    print(f"limiares normais: med|δ|>p95={d95:.2f} rad | yaw_rate>p95={y95:.3f} rad/s | "
          f"path_curv<p50={c50:.3f} rad/s")
    fireN = (N.med_d > d95) & (N.yaw_r > y95) & (N.path_c < c50)
    fireP = (P.med_d > d95) & (P.yaw_r > y95) & (P.path_c < c50)
    disc = fireN.mean(); cov = fireP.mean()
    print(f"DISCIPLINA (normais disparados): {100*disc:.2f}% [limiar 0,5%]")
    print(f"COBERTURA (ticks pré-saída disparados): {100*cov:.1f}% [limiar 50%]")
    # lead por saída: primeiro tick disparado antes do cruzamento
    leads = []
    for (seed, drv), g in P.groupby(['seed', 'drv']):
        pass
    # lead computado por saída (reagrupando)
    P2 = P.copy(); P2['fire'] = fireP.values
    for (seed, drv), gg in P2.groupby(['seed', 'drv']):
        gg = gg.sort_values('tick')
        fired = gg[gg.fire]
        if len(fired):
            leads.append(int(gg.tick.max() - fired.tick.iloc[0]))
    if leads:
        print(f"LEAD mediano (ticks antes do último tick pré-saída): {int(np.median(leads))} "
              f"[limiar 5] | saídas com disparo: {len(leads)}/{P2.groupby(['seed','drv']).ngroups}")
    verdict = (disc <= 0.005) and (cov >= 0.50) and (leads and np.median(leads) >= 5)
    print(f"\n=== APÊNDICE 2ª ORDEM — VEREDITO: "
          f"{'SEPARA (assinatura viável p/ fila pós-gate)' if verdict else 'NÃO SEPARA'} ===")

if __name__ == '__main__':
    main()
