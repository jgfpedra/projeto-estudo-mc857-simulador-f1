"""PASSO 3 (FASE 3 v14) — gate manual de um checkpoint específico.

Uso:
  .venv/bin/python model_train/gate_checkpoint.py \
      --actor model_train/v14_traffic/dagger_actor_best_s2_n8.keras \
      --g1-tracks "interlagos,Suzuka" --g2-traffic 8 --episodes 3
"""
from __future__ import annotations

import argparse
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


def main():
    import numpy as np
    import tensorflow as tf
    from backend.model_train.train_dagger import eval_gate
    from backend.model_train.procedural_track import generate_track

    PROCEDURAL_PARAMS = {301: dict(n_hairpins=2, n_esses=2)}

    def _resolve(name):
        if name.startswith('procedural:'):
            seed = int(name.split(':')[1])
            return generate_track(seed=seed, **PROCEDURAL_PARAMS.get(seed, dict(n_hairpins=2, n_esses=1)))
        return name

    ap = argparse.ArgumentParser()
    ap.add_argument('--actor', required=True)
    ap.add_argument('--g1-tracks', default='interlagos,Suzuka')
    ap.add_argument('--g2-traffic', type=int, default=None,
                    help='n_traffic do gate COM tráfego (omite G2 se None)')
    ap.add_argument('--episodes', type=int, default=3)
    args = ap.parse_args()

    actor = tf.keras.models.load_model(args.actor, compile=False)
    print(f"[gate] ator: {args.actor}")

    ok = True
    for tr in [t.strip() for t in args.g1_tracks.split(',')]:
        g = eval_gate(actor, _resolve, tr, n_traffic=0, obs_mode='traffic',
                      episodes=args.episodes)
        passed = g['laps'] == g['episodes']
        ok = ok and passed
        print(f"  G1 sem tráfego {tr:12s}: {g['laps']}/{g['episodes']} voltas "
              f"| tempo={g['time_med'] and round(g['time_med'], 1)}s "
              f"{'OK' if passed else '<< FALHOU'}", flush=True)
    if args.g2_traffic is not None:
        g = eval_gate(actor, _resolve, 'interlagos', n_traffic=args.g2_traffic,
                      obs_mode='traffic', episodes=args.episodes, count_contacts=True)
        print(f"  G2 com tráfego n={args.g2_traffic}: {g['laps']}/{g['episodes']} voltas "
              f"| tempo={g['time_med'] and round(g['time_med'], 1)}s "
              f"| contatos/lap={g['contacts_per_lap'] and round(g['contacts_per_lap'], 1)}",
              flush=True)
    print(f"[gate] {'PASSOU' if ok else 'FALHOU'}")


if __name__ == '__main__':
    main()
