"""Behavior Cloning v2: demonstrações do controlador clássico -> ator Keras.

Gera episódios com o ReferenceController (baseline validado — completa a volta
sem respawn) EM exatamente a mesma observação/ação da política v2, e treina a
rede do ator por regressão: mean -> atanh(ação_expert) (a política é
tanh-squashed; regredir no espaço pré-tanh mantém a semântica).

Uso:
    backend/.venv/bin/python model_train/train_bc_v2.py \
        --laps 8 --out model_train/multi_context_bc_v2.keras

Depois, no PPO:
    --init-actor model_train/multi_context_bc_v2.keras
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
for p in (str(PROJECT_ROOT), str(MODEL_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


def atanh_np(a):
    a = np.clip(a, -0.98, 0.98)
    return 0.5 * (np.log1p(a) - np.log1p(-a))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--laps", type=int, default=8)
    ap.add_argument("--track", default="interlagos")
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--a-lat", type=float, default=12.0)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--out", default=str(MODEL_DIR / "multi_context_bc_v2.keras"))
    args = ap.parse_args()

    from backend.model_train.f1_env import F1MultiContextEnv
    from backend.model_train.reference_controller import ReferenceController

    env = F1MultiContextEnv(track=args.track, f1_year=args.year,
                            allow_respawn=False, grip_override=1.0)
    ctrl = ReferenceController(env, a_lat_max=args.a_lat)

    obs_buf, act_buf = {"telemetry": [], "ctx_numeric": [], "track_id": [], "compound_id": []}, []
    laps_done = 0
    ep = 0
    while laps_done < args.laps and ep < args.laps * 3:
        ep += 1
        obs, _ = env.reset(seed=ep)
        done = False
        while not done:
            a = ctrl.action()
            for k in obs_buf:
                obs_buf[k].append(np.asarray(obs[k], dtype=np.int32 if k.endswith("_id") else np.float32))
            act_buf.append(a.astype(np.float32))
            obs, r, term, trunc, info = env.step(a)
            done = term or trunc
        if info.get("completed_lap"):
            laps_done += 1
        print(f"[BC] ep {ep}: completed={info.get('completed_lap')} "
              f"prog={info.get('progress_m', 0):.0f} m | amostras={len(act_buf)}", flush=True)
    env.close()

    if laps_done == 0:
        raise SystemExit("[BC] ERRO: o baseline não completou nenhuma volta — "
                         "corrija a física/controlador antes de gerar demos.")

    X = {k: np.array(v) for k, v in obs_buf.items()}
    y = atanh_np(np.array(act_buf, dtype=np.float32))   # alvo no espaço pré-tanh
    print(f"[BC] dataset: {len(y)} amostras, {laps_done} voltas")

    from backend.model_train.train_multi_context_ppo import MultiContextPPOAgent
    import tensorflow as tf
    agent = MultiContextPPOAgent(obs_spaces=env_obs_spaces(), act_dim=2)
    agent.actor.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="mse")
    agent.actor.fit(X, y, epochs=args.epochs, batch_size=256, validation_split=0.05, verbose=1)
    agent.actor.save(args.out)
    print(f"[BC] ator salvo em {args.out}")


def env_obs_spaces():
    # reconstrói os espaços sem abrir a física de novo
    from gymnasium import spaces
    from backend.model_train.f1_env import N_OBS_TELEMETRY
    return {
        "telemetry": spaces.Box(-5, 5, shape=(N_OBS_TELEMETRY,), dtype=np.float32),
        "ctx_numeric": spaces.Box(-5, 5, shape=(2,), dtype=np.float32),
        "track_id": spaces.Box(0, 20, shape=(1,), dtype=np.int32),
        "compound_id": spaces.Box(0, 5, shape=(1,), dtype=np.int32),
    }


if __name__ == "__main__":
    main()
