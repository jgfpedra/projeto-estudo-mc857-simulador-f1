"""PASSO 1 (FASE 6) — diagnóstico do near-miss de Suzuka no v14b best_s1_n4.

1) Reprodução com trace: n_traffic=4, seeds 0-4 — onde o episódio falho morre
   (s, v, lat, motivo), o que a obs mostrava (bloco de tráfego + kappa).
2) ABLATION: o MESMO checkpoint com n_traffic=0 (dims de tráfego zeradas =
   comportamento edge puro). Suzuka 3/3 com n=0 + 2/3 com n=4 → LINHAS DE
   TRÁFEGO culpadas; 2/3 também com n=0 → DESVIO DO BC.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
BACKEND = MODEL_DIR.parent
for p in (str(PROJECT_ROOT), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')

import numpy as np


def run_config(actor, n_traffic, seeds, label):
    from backend.model_train.f1_env import F1MultiContextEnv
    env = F1MultiContextEnv(track='Suzuka', allow_respawn=False,
                             grip_override=None, obs_mode='traffic',
                             n_traffic=n_traffic)
    laps, detail = [], []
    for ep in seeds:
        obs, _ = env.reset(seed=ep)
        done, steps, info, tail = False, 0, {}, []
        while not done and steps < 1600:
            m = actor({k: np.asarray(v)[None] for k, v in obs.items()},
                      training=False).numpy()[0]
            obs, r, term, trunc, info = env.step(np.tanh(m))
            steps += 1
            tail.append((info.get('lat', 0.0), info.get('speed', 0.0),
                         env._last_s, obs['telemetry'][34:46].copy(),
                         obs['telemetry'][9:11].copy()))
            done = term or trunc
        ok = bool(info.get('completed_lap', False))
        laps.append(ok)
        rp = info.get('reward_parts', {})
        motivo = ('VOLTA' if ok else
                  ('saiu da pista' if abs(float(rp.get('terminal', 0))) <= 15
                   else 'sem progresso'))
        d = dict(ep=ep, ok=ok, motivo=motivo, steps=steps,
                 s=round(env._last_s, 0), prog=round(info.get('progress_m', 0)))
        if not ok:
            last = tail[-1]
            d['v_fim'] = round(last[1], 1)
            d['lat_fim'] = round(last[0], 1)
            # tráfego no fim: 3 mais próximos [(|d|/100, dv, lat, ahead)]
            d['traffic_fim'] = np.round(last[3], 2).tolist()
            d['kappa10'] = round(float(last[4][1]), 2)   # kappa@10m normalizado
        detail.append(d)
    env.close()
    print(f"\n===== {label} (n_traffic={n_traffic}) — Suzuka =====")
    for d in detail:
        extra = (f" | s={d['s']:.0f} v={d['v_fim']} lat={d['lat_fim']} "
                 f"κ@10m={d['kappa10']} traffic={d['traffic_fim']}"
                 if not d['ok'] else "")
        print(f"  ep{d['ep']}: {'✓ VOLTA' if d['ok'] else '✗ ' + d['motivo']} "
              f"({d['steps']} steps, prog={d['prog']}m){extra}")
    print(f"  ==> {sum(laps)}/{len(laps)} voltas")
    return sum(laps)


def main():
    import argparse
    import tensorflow as tf
    ap = argparse.ArgumentParser()
    ap.add_argument('--actor', required=True)
    args = ap.parse_args()
    actor = tf.keras.models.load_model(args.actor, compile=False)
    seeds = [0, 1, 2, 3, 4]
    n0 = run_config(actor, 0, seeds, 'ABLATION (dims de tráfego ZERADAS)')
    n4 = run_config(actor, 4, seeds, 'REPRODUÇÃO (com 4 fantasmas)')
    print(f"\n===== VEREDITO ABLATION =====")
    if n0 == len(seeds) and n4 < len(seeds):
        print("LINHAS DE TRÁFEGO culpadas: solo limpa, falha só com fantasma à "
              "frente — interação tráfego×esses; o treino precisa de esses com "
              "tráfego + fantasmas parados/atrás.")
    elif n0 < len(seeds) and n4 < len(seeds):
        print("DESVIO DO BC: falha mesmo com dims zeradas — o dataset do estágio "
              "corrompeu a pilotagem; âncora de replay é o remédio direto.")
    else:
        print("SEM FALHA nestas seeds — near-miss era marginal/ruído; considerar "
              "critério com evidência ampliada (10 eps).")


if __name__ == '__main__':
    main()
