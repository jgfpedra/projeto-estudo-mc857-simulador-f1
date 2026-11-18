"""CICLO LARGADA L-1b 0-c — DERIVAÇÃO DO Δt do launch-stagger (zero corridas).

Disciplina da L-1a: derivação ANTES de pinar, com v_plan REAL do runner
(construtor EXATO: grip_mult=0,788, sf=0,80, ds_target=4,0, smooth_window_m=20,0
— kwarg errado proibido) + velocidades medidas na aproximação (âncora cega 0-19).

Modelo: release(slot) = (grid_position − 1) × Δt, frente→trás. Gap entre
carros adjacentes k e k+1 no ponto s, pós-release: g(s, Δt, k) ≈ v(s) × k × Δt
(perfis idênticos; cada par separa-se por v×Δt a cada slot de atraso acumulado).
Comparação contra o gap do GRID = 9 m (fileiras de ~9 m, pares na mesma s).

    .venv/bin/python scripts/experiments/launch/largada_dt_probe.py
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
sys.path.insert(0, str(BACKEND))
from model_train.f1_env import load_track_frozen
from model_train.velocity_profile import VelocityProfile

CORPUS = BACKEND / "experiments" / "diag-r2-r13"
S_BANDS = [(2650, 2750, "reta pós-SF"), (2750, 2950, "entrada do S")]
DELTA_TS = [0.5, 1.0, 1.5]


def main():
    track = load_track_frozen("interlagos")
    # construtor EXATO do race_diagnostic (--gov vplan)
    vp = VelocityProfile(np.array(track.waypoints, dtype=np.float64),
                         grip_mult=0.788, sf=0.80, ds_target=4.0,
                         smooth_window_m=20.0)
    # velocidades medidas na aproximação (âncora cega s0, t<=15s)
    df = pd.read_csv(CORPUS / "race_diag_r10_blind_s0.csv", comment='#')
    print("=== 0-c DERIVAÇÃO DO Δt (launch-stagger) ===")
    print("\nv_plan REAL na janela de largada (construtor exato do runner):")
    for s in [2650, 2700, 2725, 2750, 2800, 2850, 2900, 2950]:
        print(f"  s={s}: v_plan={vp.at(float(s)):5.1f} m/s")
    print("\nvelocidade medida (cegos s0, t<=15 s):")
    for lo, hi, tag in S_BANDS:
        w = df[(df.t_s <= 15) & (df.s > lo) & (df.s <= hi)]
        print(f"  {tag} (s {lo}-{hi}): med {w.speed.median():.1f} | p90 "
              f"{w.speed.quantile(0.9):.1f} | máx {w.speed.max():.1f} m/s")
    print("\nGAP pós-release por Δt (v(s)×Δt do 1º par separado; k×Δt acumula):")
    print("  [gap do GRID = ~9 m entre fileiras; pares na mesma s = 0 m]")
    for dt in DELTA_TS:
        print(f"  Δt={dt} s:")
        for s, label in [(2725, "freada (s2725)"), (2800, "ápice entrada-S (s2800)"),
                         (2850, "saída do S (s2850)"), (2700, "reta pós-SF (s2700)")]:
            v = vp.at(float(s))
            print(f"    {label}: v_plan {v:5.1f} -> gap 1º par {v*dt:5.1f} m "
                  f"| par P9-P10 (9×Δt): {v*9*dt:6.1f} m")
        print(f"    custo máx de atraso (P10): {9*dt:.1f} s")
    print("\n=== LEITURA ===")
    print("Δt=1,0 s: ápice v_plan 20,3 → gap 1º par ≈ 20 m vs 9 m do grid (≥2×);")
    print("  freada 18-35 m; reta 24-38 m — separação em TODA a zona da queixa.")
    print("Δt=0,5 s: 9-17 m — marginal (encosta no gap do grid na freada).")
    print("Δt=1,5 s: +13,5 s de atraso com ganho decrescente (gaps já ≥2× em 1,0).")
    print("→ Δt PINADO = 1,0 s/slot (citar estes números no prereg L-1b).")
    return 0


if __name__ == '__main__':
    sys.exit(main())
