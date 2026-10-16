"""Fase 0 — Medição dos limites reais da física (H1-H4).

Skidpad (a_lat máxima sustentada), frenagem (decel máxima), e aceleração
disponível, em v = {15, 25, 40, 55, 70} m/s, grip nominal e realista.
Compara com as constantes A_LAT_MAX=14 e A_BRAKE_REF=10 do f1_env.py.

Também verifica:
  H3: mapeamento long->decel (saturação do freio)
  H4: grip_override pula o fator de superfície?

Uso: .venv/bin/python model_train/measure_limits.py
"""
import os, sys, math
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
from pathlib import Path
MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
for p in (str(PROJECT_ROOT), str(MODEL_DIR)):
    sys.path.insert(0, p)
import numpy as np
from backend.model_train.f1_env import F1MultiContextEnv


def skidpad_a_lat(env, target_v, grip, steer_deg=30.0, ticks=200):
    """a_lat máxima sustentada num círculo — mede o REAL, não o teórico."""
    env.reset()
    ph = env.engine.physics
    h = env.engine.handles[env.driver_id]
    sr = math.radians(steer_deg)
    g = grip if grip else None
    for _ in range(ticks):
        v = ph.get_state(h)['speed_mps']
        env.engine.set_driver_input(env.driver_id, target_speed_mps=target_v,
                                    throttle=1.0 if v < target_v else 0.0,
                                    brake=0.5 if v > target_v + 2 else 0.0,
                                    steering_yaw_rad=sr, grip_override=g)
        env.engine._step_tick(env.logic_dt, env.sub_steps)
    # média dos últimos 50 ticks
    vs, gls, yws = [], [], []
    for _ in range(50):
        env.engine.set_driver_input(env.driver_id, target_speed_mps=target_v,
                                    throttle=0.0, brake=0.0,
                                    steering_yaw_rad=sr, grip_override=g)
        env.engine._step_tick(env.logic_dt, env.sub_steps)
        st = ph.get_state(h)
        vs.append(st['speed_mps']); gls.append(abs(st['g_lat'])); yws.append(abs(st['yaw_rate']))
    v = np.mean(vs); gl = np.mean(gls)
    # a_lat do caminho (não a força) = v * yaw_rate
    a_path = v * np.mean(yws)
    return v, gl, a_path


def brake_decel(env, v_start, grip, ticks=80):
    """Decel máxima: solta o acelerador e freia com long=-1, mede -dv/dt."""
    env.reset()
    ph = env.engine.physics
    h = env.engine.handles[env.driver_id]
    g = grip if grip else None
    # acelera até v_start
    for _ in range(300):
        v = ph.get_state(h)['speed_mps']
        if v >= v_start: break
        env.engine.set_driver_input(env.driver_id, target_speed_mps=v_start,
                                    throttle=1.0, brake=0.0,
                                    steering_yaw_rad=0.0, grip_override=g)
        env.engine._step_tick(env.logic_dt, env.sub_steps)
    # freia
    v0 = ph.get_state(h)['speed_mps']
    for _ in range(ticks):
        env.engine.set_driver_input(env.driver_id, target_speed_mps=0,
                                    throttle=0.0, brake=1.0,
                                    steering_yaw_rad=0.0, grip_override=g)
        env.engine._step_tick(env.logic_dt, env.sub_steps)
        if ph.get_state(h)['speed_mps'] < 2.0: break
    v1 = ph.get_state(h)['speed_mps']
    dt = ticks * env.logic_dt
    # decel média nos primeiros ticks (antes de ficar lento demais)
    return (v0 - v1) / dt if dt > 0 else 0


def brake_vs_long(env, v_start, grip, long_cmd, ticks=30):
    """Decel para um comando long específico (H3: mapeamento)."""
    env.reset()
    ph = env.engine.physics
    h = env.engine.handles[env.driver_id]
    g = grip if grip else None
    for _ in range(300):
        v = ph.get_state(h)['speed_mps']
        if v >= v_start: break
        env.engine.set_driver_input(env.driver_id, target_speed_mps=v_start,
                                    throttle=1.0, brake=0.0,
                                    steering_yaw_rad=0.0, grip_override=g)
        env.engine._step_tick(env.logic_dt, env.sub_steps)
    v0 = ph.get_state(h)['speed_mps']
    for _ in range(ticks):
        th, br = max(long_cmd, 0), max(-long_cmd, 0)
        env.engine.set_driver_input(env.driver_id, target_speed_mps=0,
                                    throttle=th, brake=br,
                                    steering_yaw_rad=0.0, grip_override=g)
        env.engine._step_tick(env.logic_dt, env.sub_steps)
        if ph.get_state(h)['speed_mps'] < 1.0: break
    v1 = ph.get_state(h)['speed_mps']
    dt = ticks * env.logic_dt
    return (v0 - v1) / dt


def theoretical_a_lat(v, grip_mult=1.0):
    """a_lat teórica com downforce: mu_eff * (mg + 0.5*rho*CL*A*v²) / m."""
    m, g, rho, cl, area, mu = 798.0, 9.81, 1.225, 3.2, 1.5, 1.8
    mu_eff = mu * grip_mult
    downforce = 0.5 * rho * cl * area * v * v
    fz = m * g + downforce
    return mu_eff * fz / m


def main():
    env = F1MultiContextEnv(track='interlagos', allow_respawn=False)
    print("=" * 78)
    print("FASE 0 — MEDIÇÃO DOS LIMITES REAIS DA FÍSICA")
    print("=" * 78)

    # ---- H1: a_lat máxima vs A_LAT_MAX=14 ----
    print("\n### H1: a_lat máxima sustentada (skidpad 30°) ###")
    print(f"{'v_alvo':>7s} {'v_real':>7s} {'a_lat força':>11s} {'a_lat path':>10s} "
          f"{'teórica(grip1)':>14s} {'teórica(real)':>13s} {'>14?':>5s}")
    for v_t in (15, 25, 40, 55, 70):
        try:
            v1, gl1, ap1 = skidpad_a_lat(env, v_t, 1.0)
            v2, gl2, ap2 = skidpad_a_lat(env, v_t, None)
            th1 = theoretical_a_lat(v_t, 1.0)
            th2 = theoretical_a_lat(v_t, 0.788)
            print(f"{v_t:6.0f} {v1:7.1f} {gl1*9.81:10.1f} {ap1:10.1f} "
                  f"{th1:13.1f} {th2:13.1f} {'SIM' if ap1 > 14 else 'não':>5s}")
        except Exception as e:
            print(f"{v_t:6.0f} ERRO: {e}")

    # ---- H3: mapeamento long -> decel (saturação) ----
    print(f"\n### H3: decel em função de long (v=50 m/s) ###")
    print(f"{'long':>6s} {'decel':>7s} {'frac_max':>9s}")
    dmax = None
    for long_cmd in (-0.05, -0.10, -0.20, -0.30, -0.50, -0.70, -1.00):
        d = brake_vs_long(env, 50.0, 1.0, long_cmd)
        if dmax is None: dmax = d
        print(f"{long_cmd:6.2f} {d:7.1f} {d/dmax if dmax else 0:8.1%}")

    # ---- frenagem máxima em várias velocidades ----
    print(f"\n### Frenagem máxima vs A_BRAKE_REF=10 ###")
    print(f"{'v':>6s} {'decel(grip1)':>12s} {'decel(real)':>12s} {'>10?':>5s}")
    for v in (20, 40, 60, 80):
        try:
            d1 = brake_decel(env, v, 1.0, ticks=20)
            d2 = brake_decel(env, v, None, ticks=20)
            print(f"{v:5.0f} {d1:11.1f} {d2:11.1f} {'SIM' if d1 > 10 else 'não':>5s}")
        except Exception as e:
            print(f"{v:5.0f} ERRO: {e}")

    # ---- H2: V_TGT_MIN=15 vs curvas fechadas ----
    print(f"\n### H2: velocidade física das curvas mais fechadas ###")
    from backend.model_train.f1_env import A_LAT_MAX
    for tr in ('interlagos', 'Monaco'):
        try:
            e2 = F1MultiContextEnv(track=tr, allow_respawn=False)
            kappas = sorted(((abs(e2._kappa_signed(e2._seg_cum[i])), e2._seg_cum[i])
                             for i in range(0, len(e2._seg_cum), 5)), reverse=True)
            kmax = kappas[0][0]
            v_phys = math.sqrt(A_LAT_MAX / max(kmax, 1e-4))
            v_real = math.sqrt(14.0 / max(kmax, 1e-4))  # com grip real ~0.79: mu_eff=1.42
            print(f"  {tr}: kappa_max={kmax:.4f} (R={1/max(kmax,1e-4):.0f}m) | "
                  f"v_física(A_LAT=14)={v_phys:.1f} m/s | V_TGT_MIN=15 {'✗ EXCESSIVO' if v_phys < 15 else 'OK'}")
            e2.close()
        except Exception as e:
            print(f"  {tr}: ERRO {e}")

    # ---- H4: grip_override pula superfície? ----
    print(f"\n### H4: grip_override vs fator de superfície ###")
    from backend.domain.track import Track
    t = env.track
    # na pista
    on = t.surface_grip_factor_from_distance(3.0)
    off = t.surface_grip_factor_from_distance(9.0)
    print(f"  surface(3m)={on:.2f} (no asfalto) | surface(9m)={off:.2f} (fora)")
    print(f"  _compute_grip com override: retorna o override DIRETO (pula superfície)")
    print(f"  SEM override: grip_tyre × surface — na grama = 0.79×0.35 = {0.788*0.35:.3f}")
    print(f"  IMPACTO: treino nunca vê perda de grip na grama; avaliação sim.")
    print(f"           O professor imita o treino (usa _v_target sem surface).")

    env.close()
    print("\n" + "=" * 78)


if __name__ == '__main__':
    main()
