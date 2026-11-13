"""v15 FASE 3 — avaliação do COMPOSITE (solo v10 congelado + residual gated).

Faz a ação a = tanh(m_solo + g·r) com gate calculado por estado (a partir
da obs 'traffic' 46d — o residual consome os 12d de tráfego + 4 auxiliares;
o solo consome os 34d edge). Este módulo é o único ponto de eval do
composite — gate_checkpoint e os gates do treino o chamam.

Uso:
  .venv/bin/python model_train/eval_composite.py \
      --solo model_train/v10_dagger/dagger_actor_best.keras \
      --residual model_train/v15_residual/residual_best.keras \
      --tracks "interlagos,Suzuka" --n-traffic 0 --episodes 3
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
BACKEND = MODEL_DIR.parent
for p in (str(BACKEND.parent), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')


class CompositePolicy:
    """Callable que o eval_gate consome: recebe o obs dict, devolve a ação."""

    def __init__(self, solo_path, residual_path):
        import tensorflow as tf
        from backend.model_train.residual_gated import (CompositeActor, gate_value,
                                                          build_residual_input)
        self.comp = CompositeActor(solo_path, residual_path)
        self._gate_value = gate_value
        self._build_in = build_residual_input
        self._prev = (0.0, 0.0)

    def __call__(self, obs_batch):
        """obs_batch: {telemetry (N,46), ctx_numeric, track_id, compound_id}."""
        import numpy as np
        tels = obs_batch['telemetry']
        n = tels.shape[0]
        o34 = dict(obs_batch)
        o34['telemetry'] = tels[:, :34]
        m_solo = self.comp.solo(o34, training=False).numpy()
        res_inputs = []
        gates = []
        for i in range(n):
            tf_feats = tels[i, 34:46]
            # v_ego: derivado do speed na obs (idx 0 = speed/100)
            v_ego = float(tf_feats[0]) * 0.0  # placeholder — use obs speed
            v_ego = float(tels[i, 0]) * 100.0  # obs idx 0 = speed/OBS_SPEED
            d_min = None
            for k in range(3):
                if tf_feats[4 * k + 3] > 0.5:
                    d = tf_feats[4 * k] * 100.0
                    if d_min is None or d < d_min:
                        d_min = d
            g = self._gate_value(v_ego, d_min)
            kap = float(tels[i, 11]) / 25.0
            ps, pl = self._prev
            res_inputs.append(self._build_in(tf_feats, v_ego, kap, ps, pl))
            gates.append(g)
        res_in = np.asarray(res_inputs, dtype=np.float32)
        gates_arr = np.asarray(gates, dtype=np.float32)
        r = self.comp.residual.predict(res_in, verbose=0)
        a = np.tanh(m_solo + gates_arr[:, None] * r)
        # atualiza prev para o batch de 1 (eval é sempre 1 por chamada)
        self._prev = (float(np.clip(a[-1, 0], -1, 1)),
                      float(np.clip(a[-1, 1], -1, 1)))
        return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo', required=True)
    ap.add_argument('--residual', required=True)
    ap.add_argument('--tracks', type=str, default='interlagos')
    ap.add_argument('--n-traffic', type=int, default=0)
    ap.add_argument('--episodes', type=int, default=3)
    ap.add_argument('--count-contacts', action='store_true')
    args = ap.parse_args()

    import numpy as np
    from backend.model_train.train_dagger import eval_gate, _ego_ghost_contacts
    from backend.model_train.f1_env import F1MultiContextEnv
    policy = CompositePolicy(args.solo, args.residual)
    print(f"[eval-composite] solo={Path(args.solo).name} + residual={Path(args.residual).name}")

    PROCEDURAL_PARAMS = {301: dict(n_hairpins=2, n_esses=2)}

    def _resolve(name):
        if name.startswith('procedural:'):
            from backend.model_train.procedural_track import generate_track
            seed = int(name.split(':')[1])
            return generate_track(seed=seed,
                                  **PROCEDURAL_PARAMS.get(seed, dict(n_hairpins=2, n_esses=1)))
        return name

    for tr in [t.strip() for t in args.tracks.split(',')]:
        env = F1MultiContextEnv(track=_resolve(tr), allow_respawn=False,
                                grip_override=None, obs_mode='traffic',
                                n_traffic=args.n_traffic)
        laps, times, contacts = [], [], 0
        try:
            for ep in range(args.episodes):
                obs, _ = env.reset(seed=ep)
                done, steps, info = False, 0, {}
                while not done and steps < 1600:
                    batch = {k: np.asarray(v)[None] for k, v in obs.items()}
                    a = policy(batch)[0]
                    obs, r, term, trunc, info = env.step(a)
                    steps += 1
                    if args.count_contacts:
                        contacts += _ego_ghost_contacts(env)
                    done = term or trunc
                ok = bool(info.get('completed_lap', False))
                laps.append(ok)
                if ok:
                    times.append(steps * 0.1)
        finally:
            env.close()
        n_ok = sum(laps)
        print(f"  {tr:14s} n={args.n_traffic}: {n_ok}/{args.episodes} voltas"
              + (f" | tempo={np.median(times):.1f}s" if times else "")
              + (f" | contatos={contacts} ({contacts/n_ok:.1f}/lap)" if args.count_contacts and n_ok else ""))


if __name__ == '__main__':
    main()
