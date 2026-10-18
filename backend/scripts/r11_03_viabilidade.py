"""R11 0.3 — VIABILIDADE OFFLINE do dataset weave/slide (go/no-go PINADO no prereg).

Para cada saída root do corpus R7a: simular δ_prof (pure-pursuit com
parâmetros do reference_controller) nos ticks da janela pré-saída [−30,0)
e medir correção substantiva fora do envelope do aluno.

MÉTRICA PINADA (PREREG_R11 §0.3): fração de saídas com ≥5 ticks em que
|δ_prof − δ_aluno| > 0,15 rad → **≥50% GO; <50% NO-GO**.
RAMO: estado não simulável offline → limite do critério (NO-GO conservador).
"""
import os, sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND)); sys.path.insert(0, str(BACKEND.parent))
import math
import numpy as np
import pandas as pd

SUB = 24; L_WB = 3.4; PREWIN = 30

def main():
    from backend.model_train.f1_env import load_track_frozen
    from backend.model_train.velocity_profile import VelocityProfile
    from backend.model_train.reference_controller import ReferenceController

    track = load_track_frozen('interlagos')
    vp = VelocityProfile(np.array(track.waypoints, dtype=np.float64),
                         grip_mult=0.788, sf=0.80, ds_target=4.0, smooth_window_m=20.0)
    wps = np.asarray(track.waypoints)
    closed = np.vstack([wps, wps[:1]])
    seg = np.hypot(np.diff(closed[:, 0]), np.diff(closed[:, 1]))
    seg_cum = np.concatenate([[0], np.cumsum(seg)])[:-1]
    seg_head = np.arctan2(np.diff(closed[:, 1]), np.diff(closed[:, 0]))
    L = float(seg.sum())

    def pose_at_s(s):
        s %= L
        j = int(np.searchsorted(seg_cum, s, side='right') - 1) % len(wps)
        t = (s - seg_cum[j]) / max(seg[j], 1e-9)
        return (wps[j, 0]*(1-t) + wps[(j+1) % len(wps), 0]*t,
                wps[j, 1]*(1-t) + wps[(j+1) % len(wps), 1]*t), seg_head[j]

    # parâmetros do professor (pure-pursuit; k_ld=0,6, ld 5-45 m — do __init__)
    K_LD, LD_MIN, LD_MAX, MARGIN = 0.6, 5.0, 45.0, 0.93
    n_go = n_nogo = n_total = n_unsim = 0
    rows = []
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
            off = g.offtrack.values; prev_end = None; i = 0
            while i < len(off):
                if off[i]:
                    j = i
                    while j < len(off) and off[j]: j += 1
                    t0 = g.t_s.values[i]; tick0 = int(g.tick.values[i])
                    if prev_end is None or (t0 - prev_end) > 10.0:
                        if not any((k in imp_by_tick) and (drv in imp_by_tick[k])
                                   for k in range(max(0, tick0-100), tick0+2)):
                            n_total += 1
                            subst = 0; unsim = False
                            # janela [−30, 0) ticks antes do cruzamento (por ROW index)
                            for row in range(max(0, i-PREWIN), i):
                                v = g.speed.values[row]; s_now = g.s.values[row]
                                lat_now = g.lat.values[row]
                                if v < 3.0:
                                    continue
                                herr = math.atan2(g.obs5.values[row], g.obs6.values[row])
                                ld = np.clip(K_LD*v, LD_MIN, LD_MAX)
                                s_tg = (s_now + ld) % L
                                (tx, ty), _ = pose_at_s(s_tg)
                                # pose do carro
                                (cx, cy), h_seg = pose_at_s(s_now)
                                # heading do carro = seg heading + herr
                                import numpy as _np
                                head = h_seg + herr
                                # posição do carro = centro + lat_now na normal
                                nx, ny = -math.sin(h_seg), math.cos(h_seg)
                                px, py = cx + nx*lat_now, cy + ny*lat_now
                                alpha = math.atan2(ty-py, tx-px) - head
                                alpha = math.atan2(math.sin(alpha), math.cos(alpha))
                                d_prof = math.atan(2*L_WB*math.sin(alpha)/ld)
                                d_aluno = g.steer_rad.values[row]
                                if abs(d_prof - d_aluno) > 0.15:
                                    subst += 1
                            if subst >= 5:
                                n_go += 1
                                rows.append(dict(seed=seed, drv=drv, t0=t0, subst=subst, verdict='GO'))
                            else:
                                n_nogo += 1
                                rows.append(dict(seed=seed, drv=drv, t0=t0, subst=subst, verdict='NO-GO'))
                    prev_end = t0 + (j-i)*0.2
                    i = j
                else: i += 1
    R = pd.DataFrame(rows)
    R.to_csv(BACKEND / 'r11_03_viabilidade.csv', index=False)
    frac = n_go / max(n_total, 1)
    print(f"saídas avaliadas: {n_total} | GO (≥5 ticks subst): {n_go} ({100*frac:.0f}%) | NO-GO: {n_nogo}")
    print(f"subst ticks por saída: mediana {R.subst.median():.0f} | p90 {R.subst.quantile(0.9):.0f}")
    print(f"\n=== 0.3 VEREDITO ({'≥50% = GO' if frac >= 0.5 else '<50% = NO-GO'}): "
          f"{'GO — retreino weave/slide VIÁVEL (PASSO 1)' if frac >= 0.5 else 'NO-GO — retreino volta para a fila; PASSOS 1-2 NÃO executados'} ===")

if __name__ == '__main__':
    main()
