"""PASSO 3 (FASE 4 v14) — eval COM tráfego: aluno vs professor (n=5).

Mesmo instrumento para ambos (env idêntico, seeds idênticos, grip real,
sem respawn). Métricas: voltas válidas, tempo mediano, contatos/lap,
% steps em follow (ESTADO: existe carro à frente com 0 < dist_s < 25 m).

SCRUTÍNIO anti-super-aditividade (histórico: 88s, empurrões): para QUALQUER
pista em que o aluno for mais rápido que o professor, o rollout já coleta
as provas — odômetro por volta (progress_m vs 0,98·L do completed_lap),
impulso de contato INTEGRADO por ep (soma de |força normal| ego-fantasma),
offtrack steps e lat máximo. Declaração "aluno ≥ professor" só com estas
provas limpas.

Uso:
  .venv/bin/python model_train/eval_traffic_compare.py \
      --actor model_train/v14_traffic/dagger_actor_best_s2_n8.keras \
      --n-traffic 5 --out v14_traffic_compare.json
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

TRACKS = ['interlagos', 'Monza', 'Hungaroring', 'Mexico', 'procedural:301']
PROCEDURAL_PARAMS = {301: dict(n_hairpins=2, n_esses=2)}


def _resolve(name):
    if name.startswith('procedural:'):
        from backend.model_train.procedural_track import generate_track
        seed = int(name.split(':')[1])
        return generate_track(seed=seed, **PROCEDURAL_PARAMS[seed])
    return name


def _contact_impulse(env):
    """Soma |força normal| dos pontos de contato ego-fantasma neste step
    (proxy de impulso integrado — instrumento do escrutínio)."""
    import pybullet as pb
    try:
        me = env.engine.handles[env.driver_id].chassis_id
        ghosts = {env.engine.handles[g].chassis_id for g in env._ghost_ids}
        imp = 0.0
        for c in pb.getContactPoints(me, physicsClientId=env.engine.physics._client_id):
            if len(c) >= 10 and (c[1] in ghosts or c[2] in ghosts):
                imp += abs(float(c[9]))
        return imp
    except Exception:
        return 0.0


def rollout_metrics(env, act_fn, episodes=3, max_steps=1600):
    """Rollout instrumentado (mesmo instrumento p/ aluno e professor)."""
    import numpy as np
    from backend.model_train.reference_controller import signed_dist_s
    from backend.model_train.train_dagger import _ego_ghost_contacts

    m = dict(laps=0, episodes=episodes, times=[], contacts=0, impulse=0.0,
             follow_steps=0, steps=0, offtrack=0, lat_max=0.0, progress=[])
    L = env._track_len_s
    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        done, steps, info = False, 0, {}
        while not done and steps < max_steps:
            a = act_fn(obs)
            obs, r, term, trunc, info = env.step(a)
            steps += 1
            m['steps'] += 1
            m['contacts'] += _ego_ghost_contacts(env)
            m['impulse'] += _contact_impulse(env)
            lat = abs(float(info.get('lat', 0.0)))
            m['lat_max'] = max(m['lat_max'], lat)
            if lat > env._half_width:
                m['offtrack'] += 1
            # estado de follow: carro à frente dentro de D_FOLLOW (25 m)
            snap = env._all_cars_snapshot()
            s_ego = next(s for (d, s, _, _) in snap if d == env.driver_id)
            ahead = min((signed_dist_s(s, s_ego, L)
                         for (d, s, _, _) in snap if d != env.driver_id), default=0.0)
            if 0.0 < ahead < 25.0:
                m['follow_steps'] += 1
            done = term or trunc
        ok = bool(info.get('completed_lap', False))
        if ok:
            m['laps'] += 1
            m['times'].append(steps * 0.1)
        m['progress'].append(round(float(info.get('progress_m', 0.0)), 1))
    n_laps = m['laps']
    m['time_med'] = float(np.median(m['times'])) if m['times'] else None
    m['contacts_per_lap'] = (m['contacts'] / n_laps) if n_laps else None
    m['follow_pct'] = 100.0 * m['follow_steps'] / max(m['steps'], 1)
    m['impulse_per_lap'] = (m['impulse'] / n_laps) if n_laps else None
    return m


def main():
    import numpy as np
    import tensorflow as tf
    from backend.model_train.f1_env import F1MultiContextEnv
    from backend.model_train.train_dagger import build_teacher

    ap = argparse.ArgumentParser()
    ap.add_argument('--actor', required=True)
    ap.add_argument('--n-traffic', type=int, default=5)
    ap.add_argument('--episodes', type=int, default=3)
    ap.add_argument('--out', default='v14_traffic_compare.json')
    args = ap.parse_args()

    actor = tf.keras.models.load_model(args.actor, compile=False)

    def act_student(obs):
        m = actor({k: np.asarray(v)[None] for k, v in obs.items()},
                  training=False).numpy()[0]
        return np.tanh(m)

    out = {}
    print(f"[compare n={args.n_traffic}] aluno: {Path(args.actor).name} vs professor "
          f"(mesmo instrumento, grip real, sem respawn)\n")
    print(f"{'pista':18s} {'quem':>9s} {'voltas':>7s} {'tempo':>6s} {'cont/lap':>9s} "
          f"{'follow%':>8s} {'imp/lap':>8s} {'offtrk':>6s} {'lat_max':>8s}")
    print('-' * 86)
    scrutiny = []
    for tr in TRACKS:
        row = {}
        for quem, use_teacher in (('aluno', False), ('professor', True)):
            env = F1MultiContextEnv(track=_resolve(tr), allow_respawn=False,
                                    grip_override=None, obs_mode='traffic',
                                    n_traffic=args.n_traffic)
            try:
                if use_teacher:
                    teacher = build_teacher(env)
                    def act_fn(obs, _t=teacher):
                        return _t.action(traffic=env.traffic_for(env.driver_id))
                else:
                    act_fn = act_student
                m = rollout_metrics(env, act_fn, episodes=args.episodes)
            finally:
                env.close()
            row[quem] = m
            print(f"{tr:18s} {quem:>9s} {m['laps']:>3d}/{m['episodes']:<3d} "
                  f"{(m['time_med'] and round(m['time_med'], 1)) or '—':>5}s "
                  f"{(m['contacts_per_lap'] and round(m['contacts_per_lap'], 1)) or m['contacts']:>9} "
                  f"{m['follow_pct']:>7.1f}% "
                  f"{(m['impulse_per_lap'] and round(m['impulse_per_lap'])) or 0:>8.0f} "
                  f"{m['offtrack']:>6d} {m['lat_max']:>8.1f}", flush=True)
        a, p = row['aluno'], row['professor']
        if (a['time_med'] is not None and p['time_med'] is not None
                and a['time_med'] < p['time_med']):
            # veredito PRELIMINAR: o tempo extra do aluno precisa ser explicável
            # por pilotagem, não por empurrão (impulso) nem atalho (offtrack).
            # O odômetro já é garantido pelo env: completed_lap exige
            # progresso >= 0,98·L ao longo da linha (respawns não contam).
            ok_imp = (a['impulse_per_lap'] or 0) <= (p['impulse_per_lap'] or 0) + 1.0
            ok_line = a['offtrack'] <= p['offtrack'] + 3
            verdict = ('LIMPO' if ok_imp and ok_line else 'ESCUTINAR')
            scrutiny.append(dict(track=tr, aluno=a['time_med'], professor=p['time_med'],
                                 impulse_aluno=a['impulse_per_lap'],
                                 impulse_prof=p['impulse_per_lap'],
                                 lat_max_aluno=a['lat_max'], lat_max_prof=p['lat_max'],
                                 progress_aluno=a['progress'], progress_prof=p['progress'],
                                 contacts_aluno=a['contacts_per_lap'],
                                 contacts_prof=p['contacts_per_lap'],
                                 offtrack_aluno=a['offtrack'], offtrack_prof=p['offtrack'],
                                 veredito_preliminar=verdict))
        out[tr] = row

    if scrutiny:
        print('\n===== ESCUTÍNIO (aluno mais rápido que o professor) =====')
        for s in scrutiny:
            print(f"  {s['track']}: aluno {s['aluno']:.1f}s vs professor {s['professor']:.1f}s | "
                  f"impulso/lap aluno={s['impulse_aluno'] and round(s['impulse_aluno'])} "
                  f"prof={s['impulse_prof'] and round(s['impulse_prof'])} | "
                  f"lat_max aluno={s['lat_max_aluno']:.1f} prof={s['lat_max_prof']:.1f} | "
                  f"progresso aluno={s['progress_aluno']} prof={s['progress_prof']}")
            print(f"    >> {s['veredito_preliminar']}")
    json.dump(out, open(args.out, 'w'), indent=1, default=str)
    print(f"\n-> {args.out}")


if __name__ == '__main__':
    main()
