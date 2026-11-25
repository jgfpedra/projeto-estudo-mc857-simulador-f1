"""Fase E — BC v5: demonstrações do professor na GEOMETRIA CORRIGIDA.

Diferenças do BC v2b (que foi treinado na geometria antiga e herdou seus
vícios de distribuição):
  1. Voltas completas do ReferenceController na geometria atual.
  2. EPISÓDIOS DE APROXIMAÇÃO às curvas críticas (s~2048 aberta, s~2309
     hairpin, s~4160 wrap): carro nasce 100-300 m antes com velocidades
     0.5-1.15 × v_segura — o professor demonstra FREAR ATÉ a velocidade da
     curva e acelerar na saída (exatamente o comportamento que a v4 não tem).
  3. Split treino/validação POR EPISÓDIO (sem vazamento de estados quase
     duplicados — o BC v2b usava validation_split aleatório por AMOSTRA).
  4. Perturbações leves de estado lateral/heading nas aproximações.

Uso:
  .venv/bin/python model_train/train_bc_v5.py --laps 10 --approaches 30 \
      --out model_train/multi_context_bc_v5.keras
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
for p in (str(PROJECT_ROOT), str(MODEL_DIR)):
    sys.path.insert(0, p)

import numpy as np


def atanh_np(a):
    a = np.clip(a, -0.98, 0.98)
    return 0.5 * (np.log1p(a) - np.log1p(-a))


# Zonas de aproximação: (nome, s_lo, s_hi) — 100–300 m antes de cada curva
# crítica da geometria atual (kappa 0.054/0.102/0.037; ver AUDITORIA_RL.md)
APPROACH_ZONES = [
    ("aberta_2048", 2048 - 300, 2048 - 100),
    ("hairpin_2309", 2309 - 300, 2309 - 100),
    ("wrap_4160", 4160 - 300, 4160 - 100),
]


def collect_episode(env, ctrl, max_steps=900):
    """Roda um episódio do professor; devolve lista de (obs, acao)."""
    obs, _ = env.reset()
    done, data = False, []
    for _ in range(max_steps):
        a = ctrl.action()
        o = {k: np.asarray(v).copy() for k, v in obs.items()}
        data.append((o, a.astype(np.float32)))
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
        if done:
            break
    return data, bool(info.get('completed_lap', False)), info


def place_before_zone(env, rng, s_lo, s_hi):
    """Teleporta o carro ANTES da curva com velocidade de aproximação."""
    s0 = float(rng.uniform(s_lo, s_hi)) % env._track_len_s
    v_allow = env._v_allow_at(s0, 85.0)
    v0 = float(np.clip(rng.uniform(0.5, 1.15) * v_allow, 0.0, 85.0))
    j = int(np.searchsorted(env._seg_cum, s0, side='right') - 1)
    j = min(max(j, 0), len(env._wps_arr) - 1)
    yaw = float(env._seg_heading[j])
    lat_j = float(rng.uniform(-0.3, 0.3)) * env._half_width
    nx, ny = -math.sin(yaw), math.cos(yaw)
    px = float(env._wps_arr[j, 0]) + nx * lat_j
    py = float(env._wps_arr[j, 1]) + ny * lat_j
    env.engine.physics.set_position(env.engine.handles[env.driver_id],
                                    (px, py, 0.5), yaw_rad=yaw)
    env._set_forward_speed(yaw, v0)
    if hasattr(env.engine, "last_pos"):
        env.engine.last_pos[env.driver_id] = (px, py)
    _, env._last_s, env._last_wp_idx, _ = env._project_on_path(px, py)
    env._next_gate = int(np.searchsorted(env._gates, env._last_s, side='right') % env._n_gates)
    env._respawns_left = 10
    env._prog_hist.clear()
    env._total_wp_progress = 0.0
    env.steps = 0
    env.engine.cum_dist_m[env.driver_id] = 0.0
    return v0


def main():
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
    ap = argparse.ArgumentParser()
    ap.add_argument('--laps', type=int, default=10)
    ap.add_argument('--approaches', type=int, default=30)
    ap.add_argument('--a-lat', type=float, default=12.0)
    ap.add_argument('--epochs', type=int, default=80)
    ap.add_argument('--out', default=str(MODEL_DIR / 'multi_context_bc_v5.keras'))
    args = ap.parse_args()

    from backend.model_train.f1_env import F1MultiContextEnv
    from backend.model_train.reference_controller import ReferenceController

    env = F1MultiContextEnv(track='interlagos', allow_respawn=False, grip_override=1.0)
    ctrl = ReferenceController(env, a_lat_max=args.a_lat)
    rng = np.random.default_rng(5)

    episodes = []      # lista de listas de (obs, a) — split POR EPISÓDIO

    # ---- 1. voltas completas -------------------------------------------------
    laps_done = 0
    tries = 0
    while laps_done < args.laps and tries < args.laps * 3:
        tries += 1
        data, ok, info = collect_episode(env, ctrl, max_steps=1500)
        if ok:
            episodes.append(('lap', data))
            laps_done += 1
        print(f"[BCv5] volta {tries}: completed={ok} prog={info.get('progress_m', 0):.0f} m "
              f"({len(data)} passos)", flush=True)
    if laps_done == 0:
        raise SystemExit("[BCv5] ERRO: o professor não completou nenhuma volta na geometria atual")

    # ---- 2. aproximações às curvas críticas ---------------------------------
    for i in range(args.approaches):
        name, s_lo, s_hi = APPROACH_ZONES[i % len(APPROACH_ZONES)]
        env.reset()                       # estado limpo
        v0 = place_before_zone(env, rng, s_lo, s_hi)
        obs, _, _, _ = env._get_obs(), None, None, None
        # roda ~35 s ou ate saida/termino
        data, done = [], False
        cur_obs = env._get_obs()
        for _ in range(350):
            a = ctrl.action()
            o = {k: np.asarray(v).copy() for k, v in cur_obs.items()}
            data.append((o, a.astype(np.float32)))
            cur_obs, r, term, trunc, info = env.step(a)
            done = term or trunc
            if done:
                break
        # aceita o trecho se o carro andou >= 150 m sem sair da pista
        prog = info.get('progress_m', 0.0) if done else env._total_wp_progress
        ok = (not term) and prog >= 150.0
        if ok:
            episodes.append((f'appr_{name}', data))
        print(f"[BCv5] aprox {i + 1}/{args.approaches} "
              f"({name}) v0={v0:.0f} -> prog={prog:.0f} m ok={ok}", flush=True)

    # ---- 3. split POR EPISÓDIO (sem vazamento de estados consecutivos) -------
    order = rng.permutation(len(episodes))
    n_val = max(2, len(episodes) // 6)
    val_idx = set(order[:n_val].tolist())
    train_eps = [ep for i, ep in enumerate(episodes) if i not in val_idx]
    val_eps = [ep for i, ep in enumerate(episodes) if i in val_idx]
    print(f"[BCv5] episódios: {len(episodes)} | treino {len(train_eps)} | val {len(val_eps)}")

    def stack(eps):
        X = {"telemetry": [], "ctx_numeric": [], "track_id": [], "compound_id": []}
        y = []
        for _, data in eps:
            for o, a in data:
                for k in X:
                    X[k].append(np.asarray(o[k], dtype=np.int32 if k.endswith('_id') else np.float32))
                y.append(a)
        return {k: np.array(v) for k, v in X.items()}, atanh_np(np.array(y, dtype=np.float32))

    Xtr, ytr = stack(train_eps)
    Xva, yva = stack(val_eps)
    print(f"[BCv5] amostras: treino {len(ytr)} | val {len(yva)}")

    # ---- 4. treino ------------------------------------------------------------
    import tensorflow as tf
    from backend.model_train.train_multi_context_ppo import MultiContextPPOAgent
    agent = MultiContextPPOAgent(obs_spaces=env.observation_space, act_dim=2)
    agent.actor.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="mse")
    hist = agent.actor.fit(Xtr, ytr, validation_data=(Xva, yva),
                           epochs=args.epochs, batch_size=256, verbose=2)
    # erro por componente na validação
    pred = agent.actor(Xva, training=False).numpy()
    err_steer = float(np.mean(np.abs(np.tanh(pred[:, 0]) - np.tanh(yva[:, 0]))))
    err_long = float(np.mean(np.abs(np.tanh(pred[:, 1]) - np.tanh(yva[:, 1]))))
    # erro em estados de FRENAGEM do professor (long < -0.3)
    brk = np.tanh(yva[:, 1]) < -0.3
    err_brake = float(np.mean(np.abs(np.tanh(pred[brk, 1]) - np.tanh(yva[brk, 1])))) if brk.any() else 0.0
    print(f"[BCv5] val_loss={hist.history['val_loss'][-1]:.4f} | "
          f"|err steer|={err_steer:.3f} | |err long|={err_long:.3f} | "
          f"|err em frenagem|={err_brake:.3f} (n={int(brk.sum())})")
    agent.actor.save(args.out)
    print(f"[BCv5] ator salvo em {args.out}")
    env.close()


if __name__ == "__main__":
    main()
