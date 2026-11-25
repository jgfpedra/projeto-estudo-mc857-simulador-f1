"""Avaliação determinística da política treinada (modo "prova": sem respawn).

Uso:
    backend/.venv/bin/python -m backend.model_train.evaluate_policy \
        [--actor backend/model_train/multi_context_rl_actor_best.keras] \
        [--episodes 10] [--track interlagos] [--year 2024]

Métrica principal: TAXA DE VOLTA VÁLIDA (completed_lap) — sem respawn para
mascarar falhas. Também reporta progresso médio/máximo, retorno, velocidade
média e passos por episódio.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_actor(path):
    import tensorflow as tf
    return tf.keras.models.load_model(str(path), compile=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--actor", type=str,
                    default=str(MODEL_DIR / "multi_context_rl_actor_best.keras"))
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--track", type=str, default="interlagos")
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--session", type=str, default="R")
    ap.add_argument("--max-steps", type=int, default=3000)
    args = ap.parse_args()

    from backend.model_train.f1_env import F1MultiContextEnv
    import tensorflow as tf

    actor = load_actor(args.actor)
    env = F1MultiContextEnv(track=args.track, f1_year=args.year, f1_session=args.session,
                            allow_respawn=False,   # AVALIAÇÃO SEM RESPAWN
                            grip_override=None,    # grip realista na prova
                            max_steps=args.max_steps)

    laps, progs, rets, lens, speeds = [], [], [], [], []
    parts_acc = {}
    for ep in range(args.episodes):
        obs, _ = env.reset()
        done, ret, steps = False, 0.0, 0
        info = {}
        spd = []
        while not done:
            t = {k: np.asarray(v)[None] for k, v in obs.items()}
            mean = actor({k: tf.convert_to_tensor(v) for k, v in t.items()}, training=False).numpy()[0]
            a = np.tanh(mean)   # política squashed: ação determinística = tanh(média)
            obs, r, term, trunc, info = env.step(a)
            done = term or trunc
            ret += r
            steps += 1
            spd.append(info.get("speed", 0.0))
            for k, v in (info.get("reward_parts") or {}).items():
                parts_acc[k] = parts_acc.get(k, 0.0) + float(v)
        laps.append(bool(info.get("completed_lap", False)))
        progs.append(float(info.get("progress_m", 0.0)))
        rets.append(ret)
        lens.append(steps)
        speeds.append(float(np.mean(spd)) if spd else 0.0)
        print(f"  ep {ep + 1}/{args.episodes}: lap={laps[-1]} prog={progs[-1]:.0f}m "
              f"ret={ret:.1f} len={steps} v_med={speeds[-1]:.1f}m/s", flush=True)

    print("\n===== RESULTADO =====")
    print(f"volta válida: {sum(laps)}/{len(laps)} ({100 * np.mean(laps):.0f}%)")
    print(f"progresso: média {np.mean(progs):.0f} m | máx {np.max(progs):.0f} m "
          f"(pista ~{env._track_len_s:.0f} m)")
    print(f"retorno médio: {np.mean(rets):.1f} | len médio: {np.mean(lens):.0f} "
          f"| vel média: {np.mean(speeds):.1f} m/s")
    if parts_acc:
        n = max(1, len(laps))
        print("componentes médios/ep: " + ", ".join(f"{k}={v / n:+.2f}"
                                                    for k, v in sorted(parts_acc.items())))
    env.close()
    sys.exit(0 if all(laps) else (0 if any(laps) else 1))


if __name__ == "__main__":
    main()
