"""
Avalia uma política treinada no F1MultiContextEnv e mostra ONDE ela falha.

    python backend/model_train/eval_policy.py                         # usa *_best.keras
    python backend/model_train/eval_policy.py --actor multi_context_rl_actor.keras --episodes 20
    python backend/model_train/eval_policy.py --noise 0.2             # com ruído gaussiano na ação
    python backend/model_train/eval_policy.py --respawn               # permite respawn (diagnóstico)
    python backend/model_train/eval_policy.py --dump-csv falha.csv    # trace completo do episódio 0

Compatível com a política v2: aplica tanh(média) — ação determinística da
política squashed (modelos v1 de 3 ações já saem saturados de fábrica e seguem
o mapeamento legado do ambiente).

Avaliação padrão é PROVA REAL: sem respawn (use --respawn para ligar) e com
aderência física realista (sem grip override; use --grip-override 1.0 p/
comparar com as condições de treino).

Definições (ver f1_env.py):
- progress_m : progresso REAL percorrido, acumulando apenas avanços ao longo da
  linha; respawns e wrap de pista NÃO somam progresso.
- s_fim      : posição absoluta final na pista. Pode ser maior que progress_m
  (o carro larga de um start/finish no meio da pista e progresso conta a partir
  dali) ou MENOR (após respawn para trás). Não são a mesma métrica.

Motivo do término: VOLTA (completed_lap do env), sem progresso (stuck),
saiu da pista (terminal), ou timeout (trunc).
"""
import os
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
for p in (str(PROJECT_ROOT), str(MODEL_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import tensorflow as tf
from backend.model_train.f1_env import F1MultiContextEnv


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--actor", default=str(MODEL_DIR / "multi_context_rl_actor_best.keras"))
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--noise", type=float, default=0.0, help="desvio do ruído gaussiano na ação (pré-tanh)")
    ap.add_argument("--track", default="interlagos")
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--session", default="R")
    ap.add_argument("--max-steps", type=int, default=3000)
    ap.add_argument("--respawn", action="store_true", help="permite respawn (padrão: NÃO — prova real)")
    ap.add_argument("--grip-override", type=float, default=None,
                    help="força grip (1.0 = grip do treino); padrão: física realista")
    ap.add_argument("--dump-csv", type=str, default=None,
                    help="grava trace completo por passo do episódio 0 (diagnóstico da falha)")
    ap.add_argument("--noise-sigma", type=float, default=0.0,
                    help="σ do ruído GAUSSIANO somado à ação tanh(mu) pós-clip "
                         "(0 = determinístico puro; 0.1 = exploração leve)")
    ap.add_argument("--obs-mode", type=str, default='legacy',
                    choices=['legacy', 'edge', 'traffic'],
                    help="esquema de observação do MODELO: legacy=23d | edge=34d | traffic=46d (v14)")
    args = ap.parse_args()

    actor = tf.keras.models.load_model(args.actor, compile=False)
    act_dim = int(actor.outputs[0].shape[-1])
    env = F1MultiContextEnv(track=args.track, f1_year=args.year, f1_session=args.session,
                            max_steps=args.max_steps, random_start_prob=0.0,
                            allow_respawn=args.respawn,
                            grip_override=args.grip_override,
                            obs_mode=args.obs_mode)
    L = env._track_len_s
    rng = np.random.default_rng(0)
    ends, laps = [], []

    # VALIDAÇÃO de compatibilidade obs_mode ↔ modelo
    obs_dim = int(actor.inputs[0].shape[1])
    env_dim = env._n_obs
    if obs_dim != env_dim:
        raise ValueError(
            f"INCOMPATÍVEL: o ator espera telemetry={obs_dim} dims mas o env "
            f"produz {env_dim} (obs_mode={args.obs_mode}). "
            f"Use --obs-mode {'edge' if obs_dim > 23 else 'legacy'} "
            f"ou treine o modelo com o esquema correto.")
    print(f"Pista {L:.0f} m | ator: {Path(args.actor).name} ({act_dim} ações, obs {obs_dim}d) "
          f"| ruído={args.noise} "
          f"| respawn={args.respawn} | grip={'real' if args.grip_override is None else args.grip_override}\n")
    print(f"{'ep':>3} {'motivo':<16} {'steps':>5} {'prog(m)':>8} {'s_fim(m)':>9} "
          f"{'v_fim(km/h)':>12} {'lat(m)':>7} {'ret':>8} {'gates':>6}")

    trace = []
    for ep in range(args.episodes):
        obs, _ = env.reset(seed=ep)
        tot, n = 0.0, 0
        info = {}
        reason = "timeout"
        while True:
            mean = actor({k: v[None] for k, v in obs.items()}, training=False).numpy()[0]
            a = np.tanh(mean) if act_dim == 2 else mean   # v2: ação det. = tanh(média)
            if args.noise > 0:
                a = np.clip(a + rng.normal(0, args.noise, size=a.shape), -1.0, 1.0)
            if args.noise_sigma > 0:
                a = np.clip(a + rng.normal(0, args.noise_sigma, size=a.shape), -1.0, 1.0)
            if args.dump_csv is not None and ep == 0:
                phys = env.engine.physics.get_state(env.engine.handles[env.driver_id])
                _, s_now, wp_now, lat_s = env._project_on_path(phys['x'], phys['y'])
                th, br, sr = env.action_to_controls(a, phys['speed_mps'])
                row = dict(step=n, s=s_now, progress_m=info.get('progress_m', 0.0),
                           x=phys['x'], y=phys['y'], heading=phys['heading_rad'],
                           speed=phys['speed_mps'], yaw_rate=phys['yaw_rate'],
                           g_lat=phys['g_lat'], g_long=phys['g_long'],
                           lat=lat_s, wp=wp_now,
                           a_steer=float(a[0]),
                           a_long=float(a[1]) if act_dim == 2 else float(a[0] - a[1]),
                           mean0=float(mean[0]), mean1=float(mean[-1]),
                           steer_rad=sr, throttle=th, brake=br)
                for j, v in enumerate(obs['telemetry']):
                    row[f'obs{j}'] = float(v)
                trace.append(row)
            obs, r, term, trunc, info = env.step(a)
            tot += r; n += 1
            if term or trunc:
                lap = bool(info.get('completed_lap', False))
                laps.append(lap)
                if lap:
                    reason = "VOLTA"
                elif term:
                    rp = info.get('reward_parts', {})
                    reason = "saiu da pista" if abs(float(rp.get('terminal', 0))) <= 15 \
                        else "sem progresso"
                else:
                    reason = "timeout"
                break
        s_end = env._last_s
        ends.append(s_end)
        print(f"{ep:3d} {reason:<16} {n:5d} {info.get('progress_m', 0.0):8.0f} {s_end:9.0f} "
              f"{info.get('speed', 0.0)*3.6:12.0f} {info.get('lat', 0.0):7.1f} {tot:8.1f} "
              f"{info.get('gate', 0):3d}/{info.get('n_gates', 0):<3d}", flush=True)

    print(f"\nVoltas válidas: {sum(laps)}/{len(laps)}")
    print("\nOnde os episódios terminam (faixas de 200 m ao longo da pista):")
    bins = np.arange(0, L + 200, 200)
    hist, _ = np.histogram(ends, bins=bins)
    for lo, hi, c in zip(bins[:-1], bins[1:], hist):
        if c:
            print(f"  {lo:5.0f}-{hi:5.0f} m | {'#' * c} {c}")

    if args.dump_csv and trace:
        import pandas as pd
        pd.DataFrame(trace).to_csv(args.dump_csv, index=False)
        print(f"\n[trace] {len(trace)} passos do episódio 0 salvos em {args.dump_csv}")
    env.close()


if __name__ == "__main__":
    main()
