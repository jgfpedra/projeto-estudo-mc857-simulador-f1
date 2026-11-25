"""Parte 0 — Calibração da fronteira física de raio.

Para cada (velocidade, raio-alvo, grip): spawna o carro num plano livre
(grip_override elimina o fator de superfície), esterço fixo = atan(L/R_alvo),
mantém velocidade constante, mede ≥2 voltas e classifica:

  LIMPO    — raio efetivo ≤ 1.1×raio_alvo e desalinhamento vel/heading < 5°
  MARGINAL — raio efetivo ≤ 1.3×raio_alvo e desalinhamento < 15°
  QUEBRA   — acima disso (o carro desliza lateralmente)

Saída: model_train/physics_frontier.json com R_min(v) = menor raio LIMPO
àquela velocidade, por nível de grip. Consumido pelo gerador procedural.

Uso:
  .venv/bin/python model_train/physics_radius_calibration.py
"""
import os, sys, math, json
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
from pathlib import Path
MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
for p in (str(PROJECT_ROOT), str(MODEL_DIR)):
    sys.path.insert(0, p)
import numpy as np


def fit_circle(x, y):
    """Fit circular aos pontos (x,y) → (cx, cy, R). Método algebraico (Kasa)."""
    x, y = np.asarray(x), np.asarray(y)
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x * x + y * y
    try:
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None, None, None
    cx, cy = sol[0] / 2, sol[1] / 2
    R = math.sqrt(max(sol[2] + cx * cx + cy * cy, 0.0))
    return cx, cy, R


def run_circle(env, v_target, R_target, grip, wheelbase=3.4,
               n_revolutions=2.0, max_ticks=800):
    """Spawna em (0,0) heading leste, esterça atan(L/R), mede a trajetória.

    Retorna dict com raio_efetivo, desalinhamento, traço XY.
    """
    ph = env.engine.physics
    h = env.engine.handles[env.driver_id]
    # teleporta para posição livre (longe da pista — o grip_override
    # elimina o fator de superfície de qualquer forma)
    ph.set_position(h, (0.0, 0.0, 0.5), yaw_rad=0.0)
    # velocidade inicial
    ph.reset_debug_visualizer_camera if False else None
    # zera velocidades residuais
    import pybullet as p
    cid = env.engine.physics._client_id
    p.resetBaseVelocity(h.chassis_id, linearVelocity=(v_target, 0, 0),
                        angularVelocity=(0, 0, 0), physicsClientId=cid)

    # esterço para o raio alvo
    steer_needed = math.atan(wheelbase / R_target)

    # tempo para ≥n_revolutions: circunferência = 2πR, dist = v·t
    T_needed = n_revolutions * 2 * math.pi * R_target / max(v_target, 0.5)
    n_ticks = min(int(T_needed / 0.1) + 20, max_ticks)

    xs, ys, misalign = [], [], []
    for tick in range(n_ticks):
        v_now = ph.get_state(h)['speed_mps']
        steer_lim = env.steer_limit_rad(v_now)
        steer_cmd = min(steer_needed, steer_lim)  # respeita o teto
        # controle agressivo de velocidade
        if v_now > v_target + 0.3:
            th, br = 0.0, 0.6
        elif v_now < v_target - 0.3:
            th, br = 0.4, 0.0
        else:
            th, br = 0.0, 0.0
        env.engine.set_driver_input(env.driver_id, target_speed_mps=v_target,
                                    throttle=th, brake=br,
                                    steering_yaw_rad=steer_cmd,
                                    grip_override=grip)
        env.engine._step_tick(env.logic_dt, env.sub_steps)
        st = ph.get_state(h)
        xs.append(st['x']); ys.append(st['y'])
        # desalinhamento: ângulo do vetor velocidade vs heading
        vx, vy = st.get('vx', 0), st.get('vy', 0)
        v_mag = math.hypot(vx, vy)
        if v_mag > 0.5:
            vel_ang = math.atan2(vy, vx)
            mis = abs((vel_ang - st['heading_rad'] + math.pi) % (2 * math.pi) - math.pi)
            misalign.append(mis)

    # fit circular nos últimos 70% (descarta transiente)
    n_warm = max(10, int(len(xs) * 0.3))
    cx, cy, R_eff = fit_circle(xs[n_warm:], ys[n_warm:])
    mis_med = float(np.degrees(np.median(misalign))) if misalign else 999.0

    # desvio máximo do círculo ajustado (proxy de "lat" no plano livre)
    if R_eff and R_eff > 0.1:
        d = np.hypot(np.array(xs[n_warm:]) - cx, np.array(ys[n_warm:]) - cy)
        lat_proxy = float(np.max(np.abs(d - R_eff)))
    else:
        lat_proxy = 999.0

    return dict(v_target=v_target, R_target=R_target, grip=grip,
                R_eff=R_eff if R_eff else 999.0,
                R_ratio=(R_eff / R_target) if R_eff and R_target > 0 else 999.0,
                misalign_deg=mis_med, lat_proxy=lat_proxy,
                steer_capped=bool(steer_needed > steer_lim) if 'steer_lim' in dir() else False)


def classify(r):
    """LIMPO / MARGINAL / QUEBRA."""
    if r['R_ratio'] <= 1.1 and r['misalign_deg'] < 5.0:
        return 'LIMPO'
    if r['R_ratio'] <= 1.3 and r['misalign_deg'] < 15.0:
        return 'MARGINAL'
    return 'QUEBRA'


def main():
    from backend.model_train.f1_env import F1MultiContextEnv
    env = F1MultiContextEnv(track='interlagos', allow_respawn=False)
    env.reset()

    SPEEDS = [4, 6, 8, 10, 13, 16]
    RADII = [4, 6, 8, 10, 13, 16, 20]
    GRIPS = [(1.0, 'treino'), (0.788, 'real')]

    results = []
    print(f"{'grip':>6s} {'v':>4s} {'R_alvo':>6s} {'R_eff':>6s} {'ratio':>6s} "
          f"{'misalign':>8s} {'lat_p':>6s} {'classe':>8s}")
    print("-" * 62)
    for grip, glabel in GRIPS:
        for v in SPEEDS:
            for R in RADII:
                # pula combinaações impossíveis (steer satura MUITO antes)
                steer_needed = math.atan(3.4 / R)
                steer_lim = env.steer_limit_rad(v)
                if steer_needed > steer_lim * 1.3:
                    continue  # esterço necessário muito acima do teto
                r = run_circle(env, float(v), float(R), grip)
                r['classe'] = classify(r)
                results.append(r)
                print(f"{glabel:>6s} {v:4d} {R:6.0f} {r['R_eff']:6.1f} "
                      f"{r['R_ratio']:6.2f} {r['misalign_deg']:7.1f}° "
                      f"{r['lat_proxy']:5.1f}m {r['classe']:>8s}", flush=True)

    # fronteira: para cada (grip, v), menor R com class LIMPO
    frontier = {}
    for grip, glabel in GRIPS:
        frontier[glabel] = {}
        for v in SPEEDS:
            clean = [r for r in results
                     if r['grip'] == grip and r['v_target'] == v and r['classe'] == 'LIMPO']
            if clean:
                frontier[glabel][str(v)] = min(r['R_target'] for r in clean)
            else:
                frontier[glabel][str(v)] = None  # nenhum raio LIMPO nesta velocidade

    out = MODEL_DIR / 'physics_frontier.json'
    json.dump({'frontier': frontier, 'measurements': results},
              open(out, 'w'), indent=1)
    print(f"\n{'='*62}")
    print(f"FRONTEIRA R_min(v) — menor raio LIMPO por velocidade:")
    for glabel in ('treino', 'real'):
        print(f"  grip {glabel}: {frontier[glabel]}")
    print(f"-> {out}")
    env.close()


if __name__ == '__main__':
    main()
