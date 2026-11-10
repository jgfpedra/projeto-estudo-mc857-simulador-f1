"""CICLO LARGADA L-1b — testes unitários do launch-stagger (prereg cd3ca5e).

Contratos:
- t1: schedule exato — release(slot) = (pos−1)×Δt (P1 nunca held; Pk held
  até t < (k−1)×1,0 s; 1º tick pós-release == (pos−1)×10);
- t2: hold de pose — th=0/brk=1 mantém v=0 e s constante (zero creep);
- t3: exclusão de paradas na janela de hold (helper do veredito: held NÃO
  conta; parada pós-release conta);
- t4: telemetria per-carro (chave própria, lição stale-drv);
- t5: flag-off default no-op + REJEIÇÃO cap×stagger (argparse error).

Harness real (pista frozen + engine pybullet + pesos v10; sem v_plan — o
stagger não o consome). Slots setados manualmente (o runner os wiring na
ordem efetiva de largada).
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scripts.run_race_10_cars import NeuralRaceController as N

BACKEND = Path(__file__).resolve().parent.parent


def _build(launch_stagger=True, n_cars=3):
    from backend.model_train.f1_env import load_track_frozen
    from backend.scripts.run_race_10_cars import (NeuralRaceController,
                                                  build_grid_drivers,
                                                  DEFAULT_MAPPINGS_PATH,
                                                  MODEL_DIR)
    from backend.engine import SimulationConfig, SimulationEngine
    from backend.domain import WeatherModel, WeatherKind, BASE_CONDITIONS
    track = load_track_frozen("interlagos")
    drivers = build_grid_drivers()[:n_cars]
    sim_config = SimulationConfig(race_id="stagger-test", num_laps=99,
                                  logic_step_hz=10.0, physics_sub_steps=24,
                                  gui=False, camera_mode="overview",
                                  draw_track=False, realtime=False,
                                  input_stale_after_s=300.0)
    engine = SimulationEngine(config=sim_config, track=track, drivers=drivers,
                              weather_model=WeatherModel(
                                  initial=BASE_CONDITIONS[WeatherKind.DRY]))
    engine.setup()
    engine.race_started = True
    ctrl = NeuralRaceController(
        weights_path=MODEL_DIR / "v10_dagger" / "dagger_actor_best_weights.npz",
        mappings_path=DEFAULT_MAPPINGS_PATH, track=track, obs_mode="edge",
        launch_stagger=launch_stagger)
    ctrl._launch_grid_slots = {d.driver_id: i + 1 for i, d in enumerate(drivers)}
    return track, drivers, engine, ctrl


def _pose_at(track, s):
    wps = np.asarray(track.waypoints, dtype=np.float64)
    AB = np.roll(wps, -1, axis=0) - wps
    seg = np.hypot(AB[:, 0], AB[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(seg)])[:-1]
    s = s % float(seg.sum())
    j = int(np.searchsorted(cum, s, side="right") - 1) % len(wps)
    t = (s - cum[j]) / (seg[j] + 1e-9)
    return (wps[j, 0] + t * AB[j, 0], wps[j, 1] + t * AB[j, 1],
            math.atan2(AB[j, 1], AB[j, 0]))


def test_t1_schedule_exato():
    """P1 nunca held; Pk held enquanto t < (k−1)×1,0 s; release no tick exato."""
    track, drivers, engine, ctrl = _build()
    A, B, C = drivers                       # slots 1, 2, 3 (release 0 / 1,0 / 2,0 s)
    for t_s, held_b, held_c in [(0.0, 1, 1), (0.9, 1, 1), (1.0, 0, 1), (1.9, 0, 1), (2.0, 0, 0)]:
        engine.sim_ts = t_s
        ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
        assert ctrl._stagger_held.get(A.driver_id) == 0, f"P1 nunca held (t={t_s})"
        assert ctrl._stagger_held.get(B.driver_id) == held_b, f"P2 @t={t_s}"
        assert ctrl._stagger_held.get(C.driver_id) == held_c, f"P3 @t={t_s}"
    # release exato: 1º tick pós-release == (slot−1)×10 ticks
    assert N.LAUNCH_STAGGER_DT == 1.0
    # P2: held em t<1,0 s (ticks 0-9), livre de t=1,0 (tick 10) — P1: tick 0


def test_t2_hold_de_pose():
    """th=0/brk=1 mantém o carro parado: v=0 e s constante (zero creep)."""
    track, drivers, engine, ctrl = _build()
    A = drivers[0]
    ctrl._launch_grid_slots = {A.driver_id: 10}      # P10: held até 9 s
    x, y, yaw = _pose_at(track, 2600.0)
    engine.physics.set_position(engine.handles[A.driver_id],
                                pos=(x, y, 0.5), yaw_rad=yaw, reset_vel=True)
    s0 = None
    for _ in range(5):                               # 5 ticks held (t=0..0,5 s)
        actions = ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
        th, brk, _ = actions[0]
        assert th == 0.0 and brk == 1.0, "hold força th=0/brk=1"
        assert ctrl._stagger_held.get(A.driver_id) == 1
        # predict_batch retorna os comandos; neste teste isolado não há
        # controller ligado ao engine, então publique o input como o runner faz.
        engine.set_driver_input(
            A.driver_id, target_speed_mps=0.0,
            steering_yaw_rad=actions[0][2], brake=brk, throttle=th,
        )
        engine._step_tick(0.1, 24)
        st = engine.physics.get_state(engine.handles[A.driver_id])
        s0 = st if s0 is None else s0
        assert abs(st["speed_mps"]) < 0.05, f"creep no hold: {st['speed_mps']}"
        assert abs(st["x"] - s0["x"]) < 0.05, "pose (x) mudou no hold"


def test_t3_exclusao_de_paradas_no_hold():
    """Helper do veredito: episódio held NÃO conta; pós-release conta."""
    from backend.scripts.largada_lg1b_verdict import count_stops_excl_hold
    held = np.ones(90, dtype=int)                    # 9 s de hold (v=0) — NÃO conta
    free_stop = np.zeros(25, dtype=int)               # 5 s pós-release (v=0) — conta
    df = pd.DataFrame(dict(
        drv=["X"] * 115, t_s=np.round(np.arange(115) * 0.2, 1),
        speed=np.concatenate([np.zeros(90), np.zeros(25)]),
        stagger_held=np.concatenate([held, free_stop])))
    assert count_stops_excl_hold(df) == 1, "só a parada pós-release conta"
    df2 = df.copy()
    df2["stagger_held"] = 1                           # tudo held -> 0 paradas
    assert count_stops_excl_hold(df2) == 0


def test_t4_telemetria_per_carro():
    """Slots 1/2/3 em t=0: flags nas chaves CERTAS (lição stale-drv)."""
    track, drivers, engine, ctrl = _build()
    A, B, C = drivers
    ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl._stagger_held.get(A.driver_id) == 0
    assert ctrl._stagger_held.get(B.driver_id) == 1
    assert ctrl._stagger_held.get(C.driver_id) == 1
    assert ctrl.last_authority.get(B.driver_id) == "stagger"
    assert ctrl.last_authority.get(A.driver_id) != "stagger"


def test_t6_release_tick_exato_com_float_acumulado():
    """Regressão do smoke (release não exato 6/10): sim_ts acumulado por +=0.1
    deixa 0,99999… < 1,0 — o release TEM que ser tick-exato (round no tick)."""
    track, drivers, engine, ctrl = _build()
    A, B, _ = drivers                       # slots 1, 2, 3
    engine.sim_ts = 9 * 0.1                  # 0,9 acumulado (tick 9) -> P2 held
    ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl._stagger_held.get(B.driver_id) == 1
    engine.sim_ts = 0.0
    for _ in range(10):
        engine.sim_ts += 0.1                 # acumula até ~1,0 (float < 1,0)
    assert engine.sim_ts < 1.0 or abs(engine.sim_ts - 1.0) < 1e-9
    ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl._stagger_held.get(B.driver_id) == 0, \
        "release no tick exato mesmo com sim_ts acumulado (round)"


def test_t5_flag_off_default_e_exclusao_mutua():
    """Default OFF = no-op; cap×stagger = erro do argparse."""
    track, drivers, engine, ctrl = _build(launch_stagger=False)
    A = drivers[0]
    ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl.LAUNCH_STAGGER_ENABLED is False
    assert all(v == 0 for v in ctrl._stagger_held.values()), "sem flag sem hold"
    assert ctrl.last_authority.get(A.driver_id) != "stagger"
    r = subprocess.run(
        [sys.executable, "model_train/race_diagnostic.py",
         "--launch-cap", "--launch-stagger", "--ticks", "1", "--track", "interlagos"],
        cwd=str(BACKEND), capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and "mutuamente exclusivos" in (r.stderr + r.stdout), \
        f"cap×stagger deveria ser rejeitado: rc={r.returncode}"
