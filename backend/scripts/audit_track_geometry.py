#!/usr/bin/env python
"""FASE G (v15 Trilha B): auditoria de instrumento geométrico — LEITURA-ONLY.

Mede por pista: clearance mínimo centro↔centro entre segmentos não adjacentes
(gap de arco > 40 m), raio mínimo, comprimento, posição da SF, desvio da SF.
Nada de runtime muda. Gera CSV + relatório textual.
"""
from __future__ import annotations
import argparse, math, sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
for p in (str(BACKEND.parent), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np

# Comprimentos oficiais (m) — F1 2024
OFFICIAL_LENGTHS = {
    'São Paulo': 4309, 'Monaco': 3337, 'Monza': 5793, 'Hungaroring': 4381,
    'Silverstone': 5891, 'Montreal': 4361, 'Bahrain': 5412, 'Mexico': 4304,
    'Suzuka': 5807, 'Spa': 7004, 'Zandvoort': 4259,
}

MIN_ARC_GAP_M = 40.0  # segmentos "não adjacentes" = gap de arco > 40 m
KDTree_RADIUS_M = 15.0

def audit_track(track):
    """Retorna dict de métricas geométricas da pista."""
    wps = np.array(track.waypoints, dtype=np.float64)
    n = len(wps)
    A = wps
    B = np.roll(A, -1, axis=0)
    AB = B - A
    L = np.hypot(AB[:, 0], AB[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(L)])[:-1]
    total = float(L.sum())
    heading = np.arctan2(AB[:, 1], AB[:, 0])

    # SF
    sf = track.start_finish_waypoint
    sf_s = float(cum[sf])
    sf_frac = sf_s / total

    # raio mínimo (κ máxima via _kappa_signed do F1MultiContextEnv)
    from backend.model_train.f1_env import F1MultiContextEnv

    class _H:
        pass
    h = _H()
    h._wps_arr = A
    h._seg_AB = AB
    h._seg_len = L
    h._seg_cum = cum
    h._seg_heading = heading
    h._track_len_s = total
    h._kappa_signed = F1MultiContextEnv._kappa_signed.__get__(h)
    h._heading_at = F1MultiContextEnv._heading_at.__get__(h)
    h._wrap = F1MultiContextEnv._wrap
    kappas = [abs(h._kappa_signed(float(cum[i]))) for i in range(0, n, 5)]
    kmax = max(kappas)
    r_min = 1.0 / max(kmax, 1e-6)

    # clearance mínimo: centro↔centro entre segmentos não adjacentes
    # (usa amostragem de pontos e cKDTree para eficiência)
    from scipy.spatial import cKDTree
    # amostra pontos da polilinha com seus s (arco)
    pts = []
    s_vals = []
    for i in range(n):
        n_sub = max(1, int(L[i] / 4.0))
        for j in range(n_sub):
            t = j / max(n_sub, 1)
            px = A[i, 0] + t * AB[i, 0]
            py = A[i, 1] + t * AB[i, 1]
            pts.append((px, py))
            s_vals.append(cum[i] + t * L[i])
    pts = np.array(pts)
    s_vals = np.array(s_vals)
    tree = cKDTree(pts)
    pairs = tree.query_pairs(r=KDTree_RADIUS_M, output_type='ndarray')

    min_clearance = 1e9
    min_gap_arc = 0
    min_pair_s = (0, 0)
    critical_pairs = []
    for i, j in pairs:
        si, sj = s_vals[i], s_vals[j]
        gap = abs(sj - si)
        gap = min(gap, total - gap)
        if gap < MIN_ARC_GAP_M:
            continue
        d = float(np.hypot(pts[i, 0] - pts[j, 0], pts[i, 1] - pts[j, 1]))
        if d < min_clearance:
            min_clearance = d
            min_gap_arc = gap
            min_pair_s = (si, sj)
        if d < 8.0:
            critical_pairs.append((d, gap, si, sj))

    # SF real (fallback: só marca como desconhecido — o circuit_info exige
    # a sessão carregada que pode falhar por rede; ver G4)
    name_match = None
    for k, v in OFFICIAL_LENGTHS.items():
        if k.lower() in track.name.lower():
            name_match = k
            break
    official_len = OFFICIAL_LENGTHS.get(name_match, None)
    len_dev = (total - official_len) / official_len * 100 if official_len else None

    return dict(
        name=track.name, n_wp=n, length_m=total, official_len=official_len,
        len_dev_pct=round(len_dev, 2) if len_dev is not None else None,
        width_m=getattr(track, 'width_m', 12.0),
        sf_idx=sf, sf_s=round(sf_s, 1), sf_frac=round(sf_frac, 3),
        r_min=round(r_min, 2), kappa_max=round(kmax, 5),
        min_clearance=round(min_clearance, 2),
        min_clearance_gap_arc=round(min_gap_arc, 1),
        min_clearance_s=round(min_pair_s[0], 1),
        n_critical_pairs_lt8m=len(critical_pairs),
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tracks', type=str,
                    default='interlagos,Monza,Suzuka,Monaco,Hungaroring,Silverstone,'
                            'Montreal,Bahrain,Mexico,Zandvoort,Spa')
    ap.add_argument('--out', type=str, default='experiments/track_geometry_audit.csv')
    args = ap.parse_args()

    from backend.model_train.f1_env import resolve_track
    import pandas as pd
    rows = []
    for name in args.tracks.split(','):
        name = name.strip()
        try:
            t = resolve_track(track=name, year=2024)
            r = audit_track(t)
            rows.append(r)
            print(f"  {r['name']:30s} wp={r['n_wp']:4d} L={r['length_m']:6.0f}m "
                  f"(of {r['official_len'] or '?'} dev={r['len_dev_pct']}%) "
                  f"R_min={r['r_min']:6.2f} clearance_min={r['min_clearance']:6.2f}m "
                  f"(gap {r['min_clearance_gap_arc']:5.0f}m @ s={r['min_clearance_s']:.0f}) "
                  f"SF={r['sf_frac']:.1%} crit<8m={r['n_critical_pairs_lt8m']}")
        except Exception as e:
            print(f"  {name:30s} ERRO: {e}")
    if rows:
        pd.DataFrame(rows).to_csv(args.out, index=False)
        print(f"\n-> {args.out}")

if __name__ == '__main__':
    main()
