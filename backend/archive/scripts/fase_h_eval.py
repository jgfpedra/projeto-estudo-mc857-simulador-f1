"""Fase H — avaliação comparativa final: v2, v4, BC v5, v5b.

Determinístico (10 eps, sem respawn, grip real) + corrida 10 carros headless.
Métricas: voltas, prog, v entrada/mínima nos dois pontos, tempo parado,
intervenções de recuperação (autônomo vs assistido).
"""
import os, sys, subprocess
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
from pathlib import Path
MODEL_DIR = Path(__file__).resolve().parent
BACKEND = MODEL_DIR.parent
for p in (str(BACKEND.parent), str(BACKEND)):
    sys.path.insert(0, p)
import numpy as np
import pandas as pd
import tensorflow as tf
from backend.model_train.f1_env import F1MultiContextEnv

MODELS = {
    'v2':      'model_train/v2/multi_context_rl_actor_best.keras',
    'v4':      'model_train/v4/multi_context_rl_actor_best.keras',
    'bc_v5':   'model_train/multi_context_bc_v5.keras',
    'v5':      'model_train/v5/multi_context_rl_actor_best.keras',
    'v5b':     'model_train/v5b/multi_context_rl_actor_best.keras',
}
# pontos criticos (Fase A): curva aberta ~2048, hairpin ~2286-2310, wrap ~4155-40
ZONES = {'aberta': (1950, 2100), 'hairpin': (2250, 2360), 'wrap': (4090, 4160)}


def det_eval(env, actor, episodes=10):
    """Avaliação determinística autônoma: tanh(mean), sem respawn, grip real."""
    laps, progs, vmin, entry = 0, [], {}, {k: [] for k in ZONES}
    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        done, info, prev_v = False, {}, None
        zone_v = {k: [] for k in ZONES}
        while not done:
            m = actor({k: np.asarray(v)[None] for k, v in obs.items()}, training=False).numpy()[0]
            a = np.tanh(m)
            obs, r, term, trunc, info = env.step(a)
            phys = env.engine.physics.get_state(env.engine.handles[env.driver_id])
            _, s, _, _ = env._project_on_path(phys['x'], phys['y'])
            for k, (lo, hi) in ZONES.items():
                if lo <= s <= hi:
                    zone_v[k].append(phys['speed_mps'])
            done = term or trunc
        laps += int(bool(info.get('completed_lap', False)))
        progs.append(info.get('progress_m', 0.0))
        for k in ZONES:
            entry[k].append(min(zone_v[k]) if zone_v[k] else float('nan'))
    return laps, float(np.mean(progs)), {k: float(np.nanmean(v)) for k, v in entry.items()}


def race_metrics(csv):
    df = pd.read_csv(csv)
    race = df[df.t_s >= 15.0]
    hes = []
    for drv, g in race.groupby('drv'):
        g = g.sort_values('tick'); v = g.speed.values; t = g.tick.values; s = g.s.values
        i = 0
        while i < len(v):
            if v[i] < 2.0:
                j = i
                while j < len(v) and v[j] < 2.0:
                    j += 1
                d = (t[min(j, len(t)) - 1] - t[i]) * 0.1
                if d >= 0.3:
                    hes.append((s[i], d))
                i = j
            else:
                i += 1
    ev = pd.DataFrame(hes, columns=['s', 'dur'])
    rec = int((race.authority.isin(['recovery', 'recovery_rejoin'])).sum())
    return dict(n_hes=len(ev), t_parado=ev.dur.sum(), max_parado=ev.dur.max() if len(ev) else 0,
                recovery_ticks=rec, offtrack=int((race.offtrack == 1).sum()),
                hairpin_v=float(race[(race.s > 2250) & (race.s < 2360)].speed.mean()),
                aberta_v=float(race[(race.s > 1950) & (race.s < 2100)].speed.mean()))


if __name__ == '__main__':
    env = F1MultiContextEnv(track='interlagos', allow_respawn=False, grip_override=None)
    print(f"{'modelo':8s} {'voltas':>7s} {'prog_med':>9s} {'v_aberta':>9s} {'v_hairpin':>10s} {'v_wrap':>8s}")
    for name, path in MODELS.items():
        if not (BACKEND / path).exists():
            print(f"{name:8s} (checkpoint ausente)")
            continue
        actor = tf.keras.models.load_model(str(BACKEND / path), compile=False)
        laps, prog, entry = det_eval(env, actor)
        print(f"{name:8s} {laps:>4d}/10 {prog:>8.0f}m "
              f"{entry.get('aberta', float('nan')):>8.1f} {entry.get('hairpin', float('nan')):>9.1f} "
              f"{entry.get('wrap', float('nan')):>7.1f}")
    env.close()

    print("\n=== corrida 10 carros headless (600 s, assistida) ===")
    print(f"{'modelo':8s} {'hesit':>6s} {'t_par':>6s} {'max_par':>8s} {'recov':>6s} {'v_hair':>7s} {'v_abert':>8s}")
    for name, csv in [('v4', 'race_diag_recovery.csv'), ('v5', 'race_diag_v5.csv')]:
        p = BACKEND / csv
        if p.exists():
            m = race_metrics(str(p))
            print(f"{name:8s} {m['n_hes']:>6d} {m['t_parado']:>5.0f}s {m['max_parado']:>7.1f}s "
                  f"{m['recovery_ticks']:>6d} {m['hairpin_v']:>6.1f} {m['aberta_v']:>7.1f}")
