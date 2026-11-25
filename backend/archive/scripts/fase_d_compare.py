"""Fase D — comparar v2, v3, v4 e BC v2b no MESMO estado (deadlock da curva-monstro).

Reconstrói no env de treino o estado em que os carros da corrida ficam presos
(s ~ 25-31, v ~ 0, lat do trace) e consulta cada política sobre a observação
idêntica. Varia também a velocidade (0, 5, 10, 15 m/s) para mapear a reação de
cada política à curva-monstro em função da velocidade.
"""
import os, sys, math
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
from pathlib import Path
MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
for p in (str(PROJECT_ROOT), str(MODEL_DIR)):
    sys.path.insert(0, p)
import numpy as np
import tensorflow as tf
from backend.model_train.f1_env import F1MultiContextEnv

MODELS = {
    'v2': "model_train/v2/multi_context_rl_actor_best.keras",
    'v3': "model_train/v3/multi_context_rl_actor_best.keras",
    'v4': "model_train/v4/multi_context_rl_actor_best.keras",
    'BC_v2b': "model_train/multi_context_bc_v2b.keras",
}

env = F1MultiContextEnv(track='interlagos', allow_respawn=False)
actors = {k: tf.keras.models.load_model(str(MODEL_DIR.parent / v), compile=False)
          for k, v in MODELS.items()}

def obs_at(s, lat, v, prev_steer=0.0, prev_long=0.0):
    """Teleporta o carro, seta velocidade e devolve a observação v2 (23 dims)."""
    x, y, yaw = env._point_at(s)
    nx, ny = -math.sin(yaw), math.cos(yaw)
    env.engine.physics.set_position(env.engine.handles[env.driver_id],
                                    (x + nx * lat, y + ny * lat, 0.5), yaw_rad=yaw)
    env._set_forward_speed(yaw, v)
    env._prev_steer, env._prev_long = prev_steer, prev_long
    obs, _, _, _ = env._get_obs(), None, None, None
    return obs

print("=== Acoes por politica no estado do deadlock (s=28, lat=+4.1) ===")
print(f"{'v(m/s)':>7} | " + " | ".join(f"{k:>18}" for k in MODELS))
for v in (0.0, 2.0, 5.0, 10.0, 15.0):
    obs = obs_at(28.0, +4.1, v, prev_steer=0.4, prev_long=-0.95)
    row = []
    for k, actor in actors.items():
        mean = actor({kk: np.asarray(vv)[None] for kk, vv in obs.items()}, training=False).numpy()[0]
        a = np.tanh(mean)
        row.append(f"st={a[0]:+.2f} lg={a[1]:+.2f}")
    print(f"{v:7.1f} | " + " | ".join(f"{r:>18}" for r in row))

print("\n=== Mesmo sweep na RETA (s=450, lat=0) — controle ===")
for v in (0.0, 5.0, 15.0, 40.0):
    obs = obs_at(450.0, 0.0, v)
    row = []
    for k, actor in actors.items():
        mean = actor({kk: np.asarray(vv)[None] for kk, vv in obs.items()}, training=False).numpy()[0]
        a = np.tanh(mean)
        row.append(f"st={a[0]:+.2f} lg={a[1]:+.2f}")
    print(f"{v:7.1f} | " + " | ".join(f"{r:>18}" for r in row))

print("\n=== Observacao do deadlock (s=28, v=0, lat=4.1) — os 23 valores ===")
obs = obs_at(28.0, +4.1, 0.0, prev_steer=0.4, prev_long=-0.95)
names = ['speed','yaw_rate','g_lat','g_long','lat_err','sin_h','cos_h','p_steer','p_long']
for i, n in enumerate(names):
    print(f"  obs[{i:2d}] {n:9s} = {obs['telemetry'][i]:+.4f}")
for j, d in enumerate((10.,20.,35.,50.,75.,100.,150.)):
    dh, kp = obs['telemetry'][9+2*j], obs['telemetry'][10+2*j]
    print(f"  preview {d:5.0f}m: dh={dh:+.3f} kappa_obs={kp:+.3f} (kappa={kp/25:+.4f} rad/m)")
env.close()
