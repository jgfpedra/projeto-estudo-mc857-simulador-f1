"""
Sanity check do F1MultiContextEnv — rode ANTES de treinar RL.

Se um controlador manual (PD simples) não consegue dar a volta no ambiente, o RL
também não vai conseguir: o problema está no ambiente/física/recompensa, não no PPO.

    python backend/model_train/sanity_check_env.py
    python backend/model_train/sanity_check_env.py --track interlagos --max-steps 2500

Cenários:
  1. controlador PD        -> deve completar a volta, retorno POSITIVO alto, sem crash
  2. esterço travado (+1)  -> deve "andar em círculos" e terminar por crash (retorno negativo)
  3. parado (sem pedais)   -> deve ser encerrado por "sem progresso" (não 2000 steps de lixo)
  4. sinal do erro lateral -> empurra o carro p/ a esquerda e confere que lateral_err > 0
"""
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
from backend.model_train.f1_env import F1MultiContextEnv, OBS_SPEED


def run(env, policy, max_steps=3000, verbose=False):
    obs, _ = env.reset(seed=0)
    total, n, reason, lat_max = 0.0, 0, "max_steps", 0.0
    while n < max_steps:
        action = policy(env, obs, n)
        obs, r, term, trunc, info = env.step(action)
        total += r; n += 1; lat_max = max(lat_max, info["lat"])
        if term or trunc:
            lap = env.engine.states[env.driver_id].lap >= 1
            reason = "VOLTA COMPLETA" if lap else ("crash/stuck" if term else "timeout")
            break
    return dict(ret=total, steps=n, reason=reason, progress=info["progress_m"],
                lat_max=lat_max, v_end=info["speed"])


def pd_policy(env, obs, n):
    tel = obs["telemetry"]
    v = tel[0] * OBS_SPEED
    lat = tel[6] * env._half_width            # + = esquerda da linha
    hd = tel[7] * math.pi                     # + = carro apontando p/ esquerda da tangente
    prev = np.abs(tel[10:13]) * math.pi       # giro da pista nos próximos 30/60/120 m
    # velocidade-alvo pela curvatura à frente (~2.5 g laterais, conservador)
    kappa = max(prev[0] / 30.0, prev[1] / 60.0, prev[2] / 120.0, 1e-4)
    v_tgt = float(np.clip(math.sqrt(25.0 / kappa), 15.0, 70.0))
    throttle = float(np.clip(0.25 * (v_tgt - v), 0.0, 1.0))
    brake = float(np.clip(0.25 * (v - v_tgt), 0.0, 1.0))
    # esterço: corrige erro de direção e erro lateral (sinais: + esquerda => esterça p/ direita)
    steer_rad = -(1.2 * hd + math.atan2(0.6 * lat, v + 3.0)) + 0.0
    steer = steer_rad / env.steer_limit_rad(v)
    return np.array([throttle, brake, np.clip(steer, -1, 1)], dtype=np.float32)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default="interlagos")
    ap.add_argument("--max-steps", type=int, default=3000)
    args = ap.parse_args()

    env = F1MultiContextEnv(track=args.track, max_steps=args.max_steps)
    print(f"Pista: {env.track.name} | comprimento ≈ {env._track_len_s:.0f} m | largura {env.track.width_m} m")
    print(f"Limite de esterço: {math.degrees(env.steer_limit_rad(0)):.1f}° parado | "
          f"{math.degrees(env.steer_limit_rad(30)):.1f}° a 30 m/s | {math.degrees(env.steer_limit_rad(70)):.1f}° a 70 m/s\n")

    res = run(env, pd_policy, args.max_steps)
    print(f"1) controlador PD      : {res['reason']:<15} ret={res['ret']:8.1f} steps={res['steps']:5d} "
          f"progresso={res['progress']:7.0f} m  lat_max={res['lat_max']:.1f} m")

    res = run(env, lambda e, o, n: np.array([0.6, 0.0, 1.0], dtype=np.float32), args.max_steps)
    print(f"2) esterço travado (+1): {res['reason']:<15} ret={res['ret']:8.1f} steps={res['steps']:5d} "
          f"progresso={res['progress']:7.0f} m")

    res = run(env, lambda e, o, n: np.zeros(3, dtype=np.float32), args.max_steps)
    print(f"3) parado              : {res['reason']:<15} ret={res['ret']:8.1f} steps={res['steps']:5d}")

    # 4) sinal do erro lateral
    obs, _ = env.reset(seed=0)
    ph = env.engine.physics.get_state(env.engine.handles[env.driver_id])
    yaw = ph["heading_rad"]
    lx, ly = -math.sin(yaw), math.cos(yaw)    # vetor "esquerda" do carro parado na largada
    env.engine.physics.set_position(env.engine.handles[env.driver_id],
                                    (ph["x"] + 3 * lx, ph["y"] + 3 * ly, 0.5), yaw_rad=yaw)
    lat = env._get_obs()["telemetry"][6] * env._half_width
    print(f"4) deslocado 3 m p/ esquerda -> lateral_err = {lat:+.2f} m "
          f"({'OK (positivo = esquerda)' if lat > 2 else 'SINAL INVERTIDO! confira a convenção do seu Track'})")
    env.close()


if __name__ == "__main__":
    main()