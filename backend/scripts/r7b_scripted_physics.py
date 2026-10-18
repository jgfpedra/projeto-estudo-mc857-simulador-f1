"""R7b PASSO 2 — física SCRIPTED (sem policy, sem tráfego) no hotspot.

Replica o protocolo do physics_radius_calibration (esterço fixo atan(L/R),
v constante, fit circular, desalinhamento vel/heading), nos pontos que as
SAÍDAS realmente acontecem (v0/v_allow ≈ 0,72-0,81 nas bandas quentes):

  hotspot : κ = 0,010 (R = 100 m) — banda com mais saídas com κ real
  controle: κ = 0,005 (R = 200 m) — banda reta com saídas "weave"

Velocidades: v_allow(κ) do perfil, 0,81×v_allow (a mediana observada), e
o alvo efetivo do professor (0,93×v_plan). Falsificação H1:
  física segura → H1 refutada nos estados suaves → doença é entrada do policy;
  física quebra a 0,81×v_allow → H1 confirmada.

Uso:  .venv/bin/python scripts/r7b_scripted_physics.py
"""
import os, sys, math
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
from pathlib import Path
BACKEND = Path(__file__).resolve().parent.parent
for p in (str(BACKEND), str(BACKEND.parent), str(BACKEND / 'model_train')):
    if p not in sys.path:
        sys.path.insert(0, p)
import numpy as np
import pandas as pd


def fit_circle(x, y):
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


def run_circle(env, v_target, R_target, grip='real', wheelbase=3.4,
               n_revolutions=1.2, max_ticks=600):
    ph = env.engine.physics
    h = env.engine.handles[env.driver_id]
    import pybullet as p
    cid = ph._client_id
    ph.set_position(h, (0.0, 0.0, 0.5), yaw_rad=0.0)
    p.resetBaseVelocity(h.chassis_id, linearVelocity=(v_target, 0, 0),
                        angularVelocity=(0, 0, 0), physicsClientId=cid)
    steer_needed = math.atan(wheelbase / R_target)
    T_needed = n_revolutions * 2 * math.pi * R_target / max(v_target, 0.5)
    n_ticks = min(int(T_needed / 0.1) + 20, max_ticks)
    xs, ys, mis = [], [], []
    grip_mult = 1.0 if grip == 'real' else float(grip)
    for tick in range(n_ticks):
        v_now = ph.get_state(h)['speed_mps']
        steer_cmd = steer_needed
        th, br = (0.0, 0.6) if v_now > v_target + 0.3 else \
                 ((0.4, 0.0) if v_now < v_target - 0.3 else (0.0, 0.0))
        env.engine.set_driver_input(env.driver_id, target_speed_mps=v_target,
                                    throttle=th, brake=br, steering_yaw_rad=steer_cmd,
                                    grip_override=grip_mult)
        env.engine._step_tick(env.logic_dt, env.sub_steps)
        st = ph.get_state(h)
        xs.append(st['x']); ys.append(st['y'])
        vx, vy = st.get('vx', 0), st.get('vy', 0)
        if math.hypot(vx, vy) > 0.5:
            va = math.atan2(vy, vx)
            mis.append(abs((va - st['heading_rad'] + math.pi) % (2 * math.pi) - math.pi))
    n_warm = max(10, int(len(xs) * 0.3))
    cx, cy, R_eff = fit_circle(xs[n_warm:], ys[n_warm:])
    mis_med = float(np.degrees(np.median(mis))) if mis else 999.0
    if R_eff and R_eff > 0.1:
        d = np.hypot(np.array(xs[n_warm:]) - cx, np.array(ys[n_warm:]) - cy)
        lat_proxy = float(np.max(np.abs(d - R_eff)))
    else:
        lat_proxy = 999.0
    return dict(R_eff=R_eff or 999.0, R_ratio=(R_eff / R_target) if R_eff else 999.0,
                misalign_deg=mis_med, lat_proxy=lat_proxy, n=len(xs))


def main():
    from backend.model_train.f1_env import F1MultiContextEnv
    from backend.model_train.velocity_profile import VelocityProfile, PhysicsParams
    from backend.model_train.f1_env import load_track_frozen

    track = load_track_frozen('interlagos')
    vp = VelocityProfile(np.array(track.waypoints, dtype=np.float64),
                        grip_mult=0.788, sf=0.80, ds_target=4.0, smooth_window_m=20.0)
    env = F1MultiContextEnv(track='interlagos', allow_respawn=False)
    env.reset()

    tests = []
    for label, k in (('HOTSPOT κ=0,010 (R=100)', 0.010), ('CONTROLE κ=0,005 (R=200)', 0.005)):
        R_m = 1.0 / k
        KAPPA_SF_FLOOR = 0.10
        sf_i = 0.80 * min(1.0, KAPPA_SF_FLOOR / max(k, KAPPA_SF_FLOOR))
        mu_s = PhysicsParams.mu * 0.788 * sf_i
        c_m = PhysicsParams.c_downforce() / PhysicsParams.mass
        denom = k - mu_s * c_m
        v_curve = math.sqrt(mu_s * PhysicsParams.g / denom) if denom > 1e-6 else 200.0
        v_all = min(v_curve, float(vp.v_max))
        for v, tag in ((v_all, 'v_allow'), (0.81 * v_all, '0,81×v_allow'),
                       (0.93 * v_all, 'prof 0,93×'), (0.72 * v_all, '0,72× (saída mediana)')):
            if v < 3:
                continue
            r = run_circle(env, v, R_m)
            r.update(label=label, kappa=k, v=v, tag=tag)
            tests.append(r)
            print(f"{label:26s} v={v:5.1f} ({tag:18s}): R_eff={r['R_eff']:6.1f} "
                  f"(ratio {r['R_ratio']:5.2f}) | desalinh {r['misalign_deg']:5.1f}° "
                  f"| lat_proxy {r['lat_proxy']:5.1f} m")
    env.close()
    pd.DataFrame(tests).to_csv('r7b_scripted_physics.csv', index=False)
    print("\n-> r7b_scripted_physics.csv")


if __name__ == '__main__':
    main()
