"""PROF-CURVA-1 Task 1 — calibração da fronteira física atual até 25 m/s.

Derivado de archive/scripts/physics_radius_calibration.py. Protocolo idêntico
(esterço fixo atan(L/R_alvo), v constante, fit circular, classificação
LIMPO/MARGINAL/QUEBRA), com a grade de velocidades/raios/grips do programa
PROF-CURVA-1.

Saída ISOLADA: experiments/prof-curva-1/physics_frontier_current.json
NÃO sobrescreve model_train/physics_frontier.json.

Uso (a partir de backend/):
  .venv/bin/python scripts/calibrate_physics_frontier.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
for p in (str(ROOT), str(BACKEND), str(BACKEND / "model_train")):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402

SPEEDS = [4, 6, 8, 10, 13, 16, 18, 20, 22, 25]
RADII = [4, 6, 8, 10, 13, 16, 20, 25, 30, 40, 50]
GRIPS = [(0.788, "real"), (0.842, "soft")]
WHEELBASE_M = 3.4
OUT_PATH = BACKEND / "experiments" / "prof-curva-1" / "physics_frontier_current.json"
LEGACY_FRONTIER = BACKEND / "model_train" / "physics_frontier.json"


def fit_circle(x, y):
    """Fit circular aos pontos (x,y) → (cx, cy, R). Método algébrico (Kasa)."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.size < 3:
        return None, None, None
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x * x + y * y
    try:
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None, None, None
    cx, cy = sol[0] / 2.0, sol[1] / 2.0
    R = math.sqrt(max(sol[2] + cx * cx + cy * cy, 0.0))
    return float(cx), float(cy), float(R)


def classify(r):
    """LIMPO / MARGINAL / QUEBRA (critérios do script de referência)."""
    if r["R_ratio"] <= 1.1 and r["misalign_deg"] < 5.0:
        return "LIMPO"
    if r["R_ratio"] <= 1.3 and r["misalign_deg"] < 15.0:
        return "MARGINAL"
    return "QUEBRA"


def _native(value):
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def run_circle(env, v_target, R_target, grip, wheelbase=WHEELBASE_M,
               n_revolutions=2.0, max_ticks=800):
    """Spawna em (0,0) heading leste, esterça atan(L/R), mede a trajetória."""
    import pybullet as p

    ph = env.engine.physics
    h = env.engine.handles[env.driver_id]
    cid = ph._client_id
    ph.set_position(h, (0.0, 0.0, 0.5), yaw_rad=0.0)
    p.resetBaseVelocity(
        h.chassis_id,
        linearVelocity=(v_target, 0, 0),
        angularVelocity=(0, 0, 0),
        physicsClientId=cid,
    )

    steer_needed = math.atan(wheelbase / R_target)
    T_needed = n_revolutions * 2 * math.pi * R_target / max(v_target, 0.5)
    n_ticks = min(int(T_needed / 0.1) + 20, max_ticks)

    xs, ys, misalign = [], [], []
    steer_lim = env.steer_limit_rad(v_target)
    for _tick in range(n_ticks):
        v_now = ph.get_state(h)["speed_mps"]
        steer_lim = env.steer_limit_rad(v_now)
        steer_cmd = min(steer_needed, steer_lim)
        if v_now > v_target + 0.3:
            th, br = 0.0, 0.6
        elif v_now < v_target - 0.3:
            th, br = 0.4, 0.0
        else:
            th, br = 0.0, 0.0
        env.engine.set_driver_input(
            env.driver_id,
            target_speed_mps=v_target,
            throttle=th,
            brake=br,
            steering_yaw_rad=steer_cmd,
            grip_override=grip,
        )
        env.engine._step_tick(env.logic_dt, env.sub_steps)
        st = ph.get_state(h)
        xs.append(st["x"])
        ys.append(st["y"])
        vx, vy = st.get("vx", 0), st.get("vy", 0)
        v_mag = math.hypot(vx, vy)
        if v_mag > 0.5:
            vel_ang = math.atan2(vy, vx)
            mis = abs((vel_ang - st["heading_rad"] + math.pi) % (2 * math.pi) - math.pi)
            misalign.append(mis)

    n_warm = max(10, int(len(xs) * 0.3))
    cx, cy, R_eff = fit_circle(xs[n_warm:], ys[n_warm:])
    mis_med = float(np.degrees(np.median(misalign))) if misalign else 999.0
    if R_eff and R_eff > 0.1:
        d = np.hypot(np.array(xs[n_warm:]) - cx, np.array(ys[n_warm:]) - cy)
        lat_proxy = float(np.max(np.abs(d - R_eff)))
    else:
        lat_proxy = 999.0
        R_eff = 999.0

    return {
        "v_target": float(v_target),
        "R_target": float(R_target),
        "grip": float(grip),
        "R_eff": float(R_eff),
        "R_ratio": float(R_eff / R_target) if R_target > 0 else 999.0,
        "misalign_deg": float(mis_med),
        "lat_proxy": float(lat_proxy),
        "steer_capped": bool(steer_needed > steer_lim),
    }


def build_frontier(results):
    frontier = {}
    for grip, glabel in GRIPS:
        frontier[glabel] = {}
        for v in SPEEDS:
            clean = [
                r for r in results
                if r["grip"] == grip and r["v_target"] == float(v) and r["classe"] == "LIMPO"
            ]
            frontier[glabel][str(v)] = (
                min(r["R_target"] for r in clean) if clean else None
            )
    return frontier


def main():
    from backend.model_train.f1_env import F1MultiContextEnv

    if LEGACY_FRONTIER.exists():
        print(f"[calib] legado intocado: {LEGACY_FRONTIER}", flush=True)

    env = F1MultiContextEnv(track="interlagos", allow_respawn=False)
    env.reset()

    results = []
    print(
        f"{'grip':>6s} {'v':>4s} {'R_alvo':>6s} {'R_eff':>6s} {'ratio':>6s} "
        f"{'misalign':>8s} {'lat_p':>6s} {'classe':>8s}"
    )
    print("-" * 62)
    for grip, glabel in GRIPS:
        for v in SPEEDS:
            for R in RADII:
                steer_needed = math.atan(WHEELBASE_M / R)
                steer_lim = env.steer_limit_rad(v)
                if steer_needed > steer_lim * 1.3:
                    continue
                r = run_circle(env, float(v), float(R), grip)
                r["classe"] = classify(r)
                results.append(r)
                print(
                    f"{glabel:>6s} {v:4d} {R:6.0f} {r['R_eff']:6.1f} "
                    f"{r['R_ratio']:6.2f} {r['misalign_deg']:7.1f}° "
                    f"{r['lat_proxy']:5.1f}m {r['classe']:>8s}",
                    flush=True,
                )

    frontier = build_frontier(results)
    payload = {
        "protocol": {
            "source": "backend/archive/scripts/physics_radius_calibration.py",
            "wheelbase_m": WHEELBASE_M,
            "speeds_mps": SPEEDS,
            "radii_m": RADII,
            "grips": [{"value": g, "label": lab} for g, lab in GRIPS],
            "limpo": {"R_ratio_max": 1.1, "misalign_deg_max": 5.0},
            "marginal": {"R_ratio_max": 1.3, "misalign_deg_max": 15.0},
        },
        "frontier": frontier,
        "measurements": [{k: _native(v) for k, v in row.items()} for row in results],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")
    tmp.replace(OUT_PATH)

    print(f"\n{'=' * 62}")
    print("FRONTEIRA R_min(v) — menor raio LIMPO por velocidade:")
    for _grip, glabel in GRIPS:
        print(f"  grip {glabel}: {frontier[glabel]}")
    print(f"-> {OUT_PATH}")
    print(f"[calib] legado permanece: {LEGACY_FRONTIER}")
    env.close()


if __name__ == "__main__":
    main()
