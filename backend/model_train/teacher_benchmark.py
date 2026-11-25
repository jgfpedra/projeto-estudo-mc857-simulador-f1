"""Fase 0 — benchmark do professor em todas as pistas (treino+val+teste).

Roda o ReferenceController 10× por pista, em grip 1.0 e grip realista.
Reporta: voltas válidas, tempo mediano, local de falha, v_min por curva crítica.
"""
import os, sys, math, json, time
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
from pathlib import Path
MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
for p in (str(PROJECT_ROOT), str(MODEL_DIR)):
    sys.path.insert(0, p)
import numpy as np

TRACKS = {
    'TREINO':    ['interlagos', 'Monza', 'Hungaroring', 'Silverstone'],
    'VALIDACAO': ['Zandvoort'],
    'TESTE':     ['Monaco', 'Suzuka', 'Spa'],
}


def run_teacher(track, grip, a_lat=12.0, episodes=10):
    from backend.model_train.f1_env import F1MultiContextEnv
    from backend.model_train.reference_controller import ReferenceController
    env = F1MultiContextEnv(track=track, allow_respawn=False,
                            grip_override=grip if grip else None)
    ctrl = ReferenceController(env, a_lat_max=a_lat)
    laps, times, fails = [], [], []
    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        done, steps = False, 0
        while not done:
            a = ctrl.action()
            obs, r, term, trunc, info = env.step(a)
            steps += 1
            done = term or trunc
        ok = bool(info.get('completed_lap', False))
        laps.append(ok)
        if ok:
            times.append(steps * 0.1)
        else:
            fails.append(dict(s=env._last_s, prog=info.get('progress_m', 0),
                              lat=info.get('lat', 0), v=info.get('speed', 0)))
    env.close()
    return dict(voltas=sum(laps), total=episodes,
                tempo_med=float(np.median(times)) if times else None,
                tempos=times, falhas=fails)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', type=int, default=10)
    ap.add_argument('--a-lat', type=float, default=10.0)
    args = ap.parse_args()

    results = {}
    print(f"{'conjunto':10s} {'pista':14s} {'grip':>5s} {'voltas':>7s} {'tempo':>8s} "
          f"{'falha':>20s}")
    print("-" * 70)
    for split, tracks in TRACKS.items():
        for tr in tracks:
            for grip, glabel in [(1.0, '1.0'), (None, 'real')]:
                try:
                    r = run_teacher(tr, grip, args.a_lat, args.episodes)
                    key = f"{tr}_{glabel}"
                    results[key] = r
                    fail_s = f"s={r['falhas'][0]['s']:.0f}m" if r['falhas'] and not r['voltas'] else '—'
                    print(f"{split:10s} {tr:14s} {glabel:>5s} {r['voltas']:>3d}/{r['total']:<3d} "
                          f"{str(r['tempo_med'] or '—'):>8s} {fail_s:>20s}", flush=True)
                except Exception as e:
                    print(f"{split:10s} {tr:14s} {glabel:>5s} ERRO: {str(e)[:40]}", flush=True)

    # salva
    out = MODEL_DIR / 'teacher_benchmark.json'
    json.dump(results, open(out, 'w'), indent=1, default=str)
    print(f"\n-> {out}")


if __name__ == '__main__':
    main()
