"""FASE H-0 — H3: DETECTOR G3 de saltos de hint (REPORT-ONLY; zero runtime).

Prereg §4 (critério pinado ANTES): sobre TODAS as pistas frozen existentes:
- (a) gaps de espaçamento: |Δs| entre waypoints adjacentes > 12,0 m (3× ds);
- (b) risco de salto de hint: pares de segmentos NÃO-adjacentes (gap de arco
  > 40 m) com distância mútua < 2,0 m — AMBIGUIDADE da projeção
  nearest-segment (o hint pode saltar de braço; caso Suzuka 0,39 m).
Validação esperada (declaração prévia do prereg): Suzuka_v1 DEVE flaggear
(crossover real); Monaco_v1 DEVE flaggear (artifact 1,71 m); Spa_v1 NÃO deve
flaggear gaps (spacing uniforme — o furo dela é comprimento).

    .venv/bin/python scripts/track_g3_detector.py
"""
import json
import sys
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND / "scripts"))
from track_mirror_build import seg_seg_min_dist, DS_M

FROZEN = BACKEND / "model_train" / "tracks_frozen"
GAP_M = 12.0     # 3 x ds (prereg §4a)
RISK_M = 2.0     # ambiguidade de projeção (prereg §4b)


def detect(name):
    d = json.loads((FROZEN / name).read_text())
    wps = np.array(d["waypoints"], dtype=np.float64)
    n = len(wps)
    seg = np.hypot(*np.diff(np.vstack([wps, wps[:1]]), axis=0).T)
    gaps = [(i, float(seg[i])) for i in np.where(seg > GAP_M)[0]]
    cum = np.concatenate([[0.0], np.cumsum(seg)])[:-1]
    pairs = seg_seg_min_dist(wps)
    risks = [((i, j), dst) for i, j, dst in pairs if dst < RISK_M]
    clearance = min((dst for _, _, dst in pairs), default=99.0)
    return dict(arquivo=name, n_wp=n, L_m=round(float(seg.sum()), 1),
                n_gaps=len(gaps), gaps=[(int(i), round(s, 1)) for i, s in gaps[:4]],
                n_riscos=len(risks),
                riscos=[(f"s={cum[i]:.0f}m<->s={cum[j]:.0f}m", round(dst, 2))
                        for (i, j), dst in risks[:4]],
                clearance_min=round(clearance, 2))


def main():
    print("=== H3 — detector G3 (gaps >12 m; riscos de hint = não-adjacentes <2 m) ===")
    files = sorted(p.name for p in FROZEN.glob("*.json"))
    n_flag = 0
    for f in files:
        r = detect(f)
        flag = r["n_gaps"] > 0 or r["n_riscos"] > 0
        n_flag += flag
        print(f"  {f:34s} n_wp={r['n_wp']:5d} L={r['L_m']:7.0f}m | "
              f"gaps={r['n_gaps']}{r['gaps'] if r['n_gaps'] else ''} | "
              f"riscos_hint={r['n_riscos']}{r['riscos'] if r['n_riscos'] else ''} | "
              f"clearance={r['clearance_min']}")
    print(f"\n{n_flag}/{len(files)} pistas FLAGGEADAS (report-only; zero mudança de runtime)")
    print("Validação do prereg: Suzuka_v1 e Monaco_v1 DEVIAM flaggar; Spa_v1 sem gaps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
