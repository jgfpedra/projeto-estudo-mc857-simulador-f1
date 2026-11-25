"""PASSO 2 (FASE 4 v14) — protocolo padrão de 51 eps SEM tráfego.

17 pistas × 3 eps (determinístico, grip real, sem respawn, obs 'traffic'
com bloco zerado). Compara linha a linha com o v10 PINADO (48/51:
treino 39/39, Zandvoort 3/3, Suzuka 3/3, Spa 3/3, Monaco 0/3).

NOTA Suzuka: foi pista de GATE nos estágios A/B/C da FASE 3 — o zero-shot
do v14 nela carrega essa ressalva. Spa é o zero-shot LIMPO restante.

Uso:
  .venv/bin/python model_train/eval_protocol.py \
      --actor model_train/v14_traffic/dagger_actor_best_s2_n8.keras \
      --out v14_protocol.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
BACKEND = MODEL_DIR.parent
for p in (str(PROJECT_ROOT), str(BACKEND), str(MODEL_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')

SPLITS = {
    'TREINO': ['interlagos', 'Monza', 'Hungaroring', 'Silverstone', 'Montreal',
               'Bahrain', 'Mexico', 'procedural:101', 'procedural:103',
               'procedural:107', 'procedural:201', 'procedural:203',
               'procedural:301'],
    'VALIDACAO': ['Zandvoort'],
    'TESTE': ['Monaco', 'Suzuka', 'Spa'],
}

# v10 pinado (PROJECT_STATE.md, Meta B/B') — baseline da comparação
V10_PINADO = {
    'interlagos': 3, 'Monza': 3, 'Hungaroring': 3, 'Silverstone': 3,
    'Montreal': 3, 'Bahrain': 3, 'Mexico': 3, 'procedural:101': 3,
    'procedural:103': 3, 'procedural:107': 3, 'procedural:201': 3,
    'procedural:203': 3, 'procedural:301': 3, 'Zandvoort': 3,
    'Suzuka': 3, 'Spa': 3, 'Monaco': 0,
}

PROCEDURAL_PARAMS = {
    101: dict(n_hairpins=2, n_esses=0), 103: dict(n_hairpins=2, n_esses=0),
    107: dict(n_hairpins=3, n_esses=0), 201: dict(n_hairpins=0, n_esses=3),
    203: dict(n_hairpins=0, n_esses=4), 301: dict(n_hairpins=2, n_esses=2),
}


def _resolve(name):
    if name.startswith('procedural:'):
        from backend.model_train.procedural_track import generate_track
        seed = int(name.split(':')[1])
        t = generate_track(seed=seed, **PROCEDURAL_PARAMS.get(seed, dict(n_hairpins=2, n_esses=1)))
        if t is None:
            raise ValueError(f"procedural:{seed} rejeitada pelo gate de kappa")
        return t
    return name


def main():
    import numpy as np
    import tensorflow as tf
    from backend.model_train.train_dagger import eval_gate

    ap = argparse.ArgumentParser()
    ap.add_argument('--actor', required=True)
    ap.add_argument('--episodes', type=int, default=3)
    ap.add_argument('--out', default='v14_protocol.json')
    args = ap.parse_args()

    actor = tf.keras.models.load_model(args.actor, compile=False)
    print(f"[protocolo 51 eps] ator: {args.actor} | grip real | sem respawn | "
          f"obs traffic (n=0)\n")
    print(f"{'conjunto':10s} {'pista':18s} {'v14':>6s} {'v10':>6s} {'tempo':>7s} {'regressão?':>10s}")
    print('-' * 62)

    results, total_laps, total_eps = {}, 0, 0
    regressions = []
    for split, tracks in SPLITS.items():
        for tr in tracks:
            g = eval_gate(actor, _resolve, tr, n_traffic=0, obs_mode='traffic',
                          episodes=args.episodes)
            results[tr] = g
            total_laps += g['laps']
            total_eps += g['episodes']
            v10 = V10_PINADO[tr]
            reg = g['laps'] < v10
            if reg:
                regressions.append((tr, g['laps'], v10))
            print(f"{split:10s} {tr:18s} {g['laps']:>3d}/{g['episodes']:<2d} "
                  f"{v10:>3d}/3   "
                  f"{(g['time_med'] and round(g['time_med'], 1)) or '—':>5}s "
                  f"{'SIM' if reg else '':>10s}", flush=True)

    print('-' * 62)
    print(f"TOTAL: {total_laps}/{total_eps} (v10 pinado: 48/51)")
    if regressions:
        print(f"REGRESSÕES: {regressions}")
    # FASE 0.8 (v15): MLflow best-effort (nunca bloqueia a avaliação)
    try:
        from backend.model_train import tracking
        with tracking.start_run('dagger-solo',
                                params={'protocol': '51eps', 'actor': args.actor},
                                tags={'status': 'research'}):
            tracking.log_eval('51eps', results)
    except Exception:
        pass
    json.dump(dict(actor=args.actor, results=results,
                   total=f'{total_laps}/{total_eps}',
                   regressions=[[t, l, v] for t, l, v in regressions]),
              open(args.out, 'w'), indent=1, default=str)
    print(f"-> {args.out}")


if __name__ == '__main__':
    main()
