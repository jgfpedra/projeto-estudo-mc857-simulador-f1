"""Benchmark diferencial de políticas — Fase B da investigação v2 vs v4.

Avalia N modelos em condições ESTRITAMENTE idênticas:
  - mesma física/ambiente (uma única instância por rodada, mesma versão de código)
  - mesma pista e start/finish
  - allow_respawn=False (prova real)
  - aderência realista (grip_override=None)
  - inferência determinística: a = tanh(mean)
  - mesmas sementes por episódio

Para cada modelo x episódio registra:
  - primeiro ponto de falha (s na falha) e motivo
  - progresso físico contínuo (m)
  - velocidade na aproximação da curva crítica (janela de 200 m antes)
  - velocidade mínima da seção (distingue desaceleração controlada de imobilização)
  - acelerador/freio efetivos médios e finais
  - esterço médio/final
  - erro lateral máximo
  - voltas válidas e tempo de volta
  - contagem de steps com v < 2 m/s (imobilização)

Uso:
  .venv/bin/python model_train/benchmark_policies.py \
      --models model_train/v2/multi_context_rl_actor_best.keras \
               model_train/v3/multi_context_rl_actor_best.keras \
               model_train/v4/multi_context_rl_actor_best.keras \
               model_train/multi_context_bc_v2b.keras \
      --episodes 3 --out-prefix bench
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
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import pandas as pd


def run_model(actor, env, episodes, dump_trace=None, label=""):
    import tensorflow as tf
    recs, traces = [], []
    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        done, steps = False, 0
        info, ret = {}, 0.0
        rows = []
        while not done:
            mean = actor({k: v[None] for k, v in obs.items()}, training=False).numpy()[0]
            a = np.tanh(mean)
            if dump_trace is not None:
                phys = env.engine.physics.get_state(env.engine.handles[env.driver_id])
                _, s_now, wp_now, lat_s = env._project_on_path(phys['x'], phys['y'])
                th, br, sr = env.action_to_controls(a, phys['speed_mps'])
                v_allow = env._v_allow_at(s_now, phys['speed_mps'])
                rows.append(dict(
                    model=label, ep=ep, step=steps, s=s_now,
                    progress=info.get('progress_m', 0.0),
                    speed=phys['speed_mps'], lat=lat_s, wp=wp_now,
                    mean_steer=float(mean[0]), mean_long=float(mean[1]),
                    a_steer=float(a[0]), a_long=float(a[1]),
                    throttle=th, brake=br, steer_rad=sr,
                    g_long=phys['g_long'], g_lat=phys['g_lat'],
                    v_allow=v_allow, resp_left=info.get('respawns_left', -1),
                    completed=info.get('completed_lap', False)))
            obs, r, term, trunc, info = env.step(a)
            ret += r
            steps += 1
            done = term or trunc
        if dump_trace is not None:
            traces.extend(rows)
        # métricas resumidas do episódio a partir dos rows (ou recomputa do info)
        recs.append(dict(
            model=label, ep=ep, reason=("VOLTA" if info.get('completed_lap') else
                                         ("saiu" if term else "timeout")),
            steps=steps, progress=info.get('progress_m', 0.0),
            s_end=env._last_s, ret=ret,
            v_end=info.get('speed', 0.0), lat_end=info.get('lat', 0.0),
            completed=bool(info.get('completed_lap', False))))
    df_tr = pd.DataFrame(traces) if traces else None
    return recs, df_tr


def main():
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
    import tensorflow as tf
    from backend.model_train.f1_env import F1MultiContextEnv

    ap = argparse.ArgumentParser()
    ap.add_argument('--models', nargs='+', required=True)
    ap.add_argument('--episodes', type=int, default=3)
    ap.add_argument('--track', default='interlagos')
    ap.add_argument('--year', type=int, default=2024)
    ap.add_argument('--grip-override', type=float, default=None)
    ap.add_argument('--out-prefix', default='bench')
    args = ap.parse_args()

    # UMA instância de ambiente, reutilizada por todos os modelos: mesma pista,
    # mesmo start/finish, mesma física.
    env = F1MultiContextEnv(track=args.track, f1_year=args.year,
                            allow_respawn=False, grip_override=args.grip_override)
    print(f"[bench] pista {env._track_len_s:.0f} m | start wp {env.track.start_finish_waypoint} "
          f"| grip={'real' if args.grip_override is None else args.grip_override} | respawn=OFF")

    all_recs, all_traces = [], []
    for mp in args.models:
        actor = tf.keras.models.load_model(mp, compile=False)
        label = Path(mp).parent.name + "/" + Path(mp).stem.replace('multi_context_rl_', '').replace('multi_context_', '')
        recs, tr = run_model(actor, env, args.episodes, dump_trace=True, label=label)
        all_recs.extend(recs)
        if tr is not None:
            all_traces.append(tr)
        for r in recs:
            print(f"  {label:28s} ep{r['ep']} {r['reason']:7s} prog={r['progress']:7.0f}m "
                  f"s_end={r['s_end']:6.0f} v_end={r['v_end']*3.6:5.0f}kmh ret={r['ret']:8.1f}")

    df = pd.DataFrame(all_recs)
    print("\n===== RESUMO POR MODELO (media por episodio) =====")
    print(df.groupby('model').agg(
        voltas=('completed', 'sum'),
        prog_medio=('progress', 'mean'), prog_max=('progress', 'max'),
        s_falha_medio=('s_end', 'mean'), v_fim_kmh=('v_end', lambda v: np.mean(v)*3.6),
        ret=('ret', 'mean')).round(1).to_string())

    if all_traces:
        tr = pd.concat(all_traces, ignore_index=True)
        tr.to_csv(f"{args.out_prefix}_trace.csv", index=False)
        print(f"\n[trace] {len(tr)} linhas -> {args.out_prefix}_trace.csv")
        # métricas de imobilização / frenagem por modelo
        print("\n===== DIAGNOSTICO 0 km/h (por modelo) =====")
        for lbl, g in tr.groupby('model'):
            slow = (g.speed < 2.0)
            braking = (g.brake > 0.3)
            both = slow & braking
            a_long = g.a_long
            print(f"{lbl}: steps v<2m/s={slow.sum()} | steps brake>0.3={braking.sum()} | "
                  f"v<2 E brake>0.3={both.sum()} | a_long medio={a_long.mean():+.3f} "
                  f"| a_long final(ep0)={g[g.ep==0].a_long.iloc[-1] if len(g[g.ep==0]) else float('nan'):+.3f}")
    df.to_csv(f"{args.out_prefix}_summary.csv", index=False)
    env.close()


if __name__ == '__main__':
    main()
