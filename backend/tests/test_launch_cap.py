"""CICLO LARGADA L-1a — testes unitários do launch-cap (prereg a3b8ff0).

Contratos:
- janela s/t: cap ATIVO dentro (t<T_max E s<s_cut E speed>k×v_plan);
  INATIVO fora por t (expiração) OU por s (liberação no s_cut);
- telemetria por carro (chave drivers[i], lição stale-drv do REPARO);
- default OFF (no-op; regime canônico bit-idêntico);
- constantes PINADAS: k=0,8 | s_cut=2950 | T_max=30 s.

Harness real (padrão test_deep_rejoin/test_rejoin_gap): pista frozen +
engine pybullet + pesos v10; v_plan real do runner (grip 0,788/sf 0,80);
velocidade semeada via pb.resetBaseVelocity.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scripts.run_race_10_cars import NeuralRaceController as N


def _build(launch_cap=True, n_cars=3):
    from backend.model_train.f1_env import load_track_frozen
    from backend.scripts.run_race_10_cars import (NeuralRaceController,
                                                  build_grid_drivers,
                                                  DEFAULT_MAPPINGS_PATH,
                                                  MODEL_DIR)
    from backend.engine import SimulationConfig, SimulationEngine
    from backend.domain import WeatherModel, WeatherKind, BASE_CONDITIONS
    from backend.model_train.velocity_profile import VelocityProfile
    track = load_track_frozen("interlagos")
    drivers = build_grid_drivers()[:n_cars]
    sim_config = SimulationConfig(race_id="launch-cap-test", num_laps=99,
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
        launch_cap=launch_cap)
    # v_plan EXATAMENTE como o runner constrói com --gov vplan
    ctrl._v_plan_cap = VelocityProfile(
        np.array(track.waypoints, dtype=np.float64), grip_mult=0.788,
        sf=0.80, ds_target=4.0, smooth_window_m=20.0)
    return track, drivers, engine, ctrl


def _place(engine, track, drv, s, v=0.0):
    wps = np.asarray(track.waypoints, dtype=np.float64)
    AB = np.roll(wps, -1, axis=0) - wps
    seg = np.hypot(AB[:, 0], AB[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(seg)])[:-1]
    s = s % float(seg.sum())
    j = int(np.searchsorted(cum, s, side="right") - 1) % len(wps)
    t = (s - cum[j]) / (seg[j] + 1e-9)
    x = wps[j, 0] + t * AB[j, 0]
    y = wps[j, 1] + t * AB[j, 1]
    yaw = math.atan2(AB[j, 1], AB[j, 0])
    engine.physics.set_position(engine.handles[drv.driver_id],
                                pos=(x, y, 0.5), yaw_rad=yaw, reset_vel=True)
    if v > 0:
        import pybullet as pb
        pb.resetBaseVelocity(engine.handles[drv.driver_id].chassis_id,
                             linearVelocity=[v * math.cos(yaw), v * math.sin(yaw), 0.0],
                             physicsClientId=engine.physics._client_id)


def test_t1_window_inside_active():
    """Dentro da janela (t=0 < 30, s=2700 < 2950) com v=50 > 0,8×v_plan(57,1):
    cap ATIVO (freio>0, th=0, authority launch_cap)."""
    track, drivers, engine, ctrl = _build()
    A = drivers[0]
    _place(engine, track, A, 2700.0, v=50.0)
    actions = ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl._cap_active.get(A.driver_id) == 1, "cap deveria estar ATIVO"
    assert ctrl.last_authority.get(A.driver_id) == "launch_cap"
    th, brk, _ = actions[0]
    assert th == 0.0 and brk > 0.0, "cap freia (lei do governor)"


def test_t2_tmax_expiry():
    """t >= T_max (30 s): cap INATIVO mesmo com speed alta dentro da região."""
    track, drivers, engine, ctrl = _build()
    A = drivers[0]
    _place(engine, track, A, 2700.0, v=50.0)
    engine.sim_ts = 31.0   # expiração (monkeypatch de teste)
    ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl._cap_active.get(A.driver_id) == 0, "cap expirou em t=31s"


def test_t3_scut_release():
    """s >= s_cut (2950): cap INATIVO mesmo com speed alta e t dentro."""
    track, drivers, engine, ctrl = _build()
    A = drivers[0]
    _place(engine, track, A, 3000.0, v=50.0)   # além do Senna S
    ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl._cap_active.get(A.driver_id) == 0, "cap libera em s>=2950"


def test_t4_telemetry_per_car():
    """3 carros: só o RÁPIDO capped — flag NA chave dele (lição stale-drv),
    zeros nos outros; nada em chave alheia."""
    track, drivers, engine, ctrl = _build()
    fast, s1, s2 = drivers[0], drivers[1], drivers[2]
    _place(engine, track, fast, 2700.0, v=50.0)
    _place(engine, track, s1, 2690.0, v=30.0)
    _place(engine, track, s2, 2680.0, v=30.0)
    ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl._cap_active.get(fast.driver_id) == 1, "flag na chave do holder"
    assert ctrl._cap_active.get(s1.driver_id) == 0
    assert ctrl._cap_active.get(s2.driver_id) == 0


def test_t5_flag_off_default_and_constants():
    """Default OFF = no-op; constantes PINADAS do prereg."""
    track, drivers, engine, ctrl = _build(launch_cap=False)
    A = drivers[0]
    _place(engine, track, A, 2700.0, v=50.0)
    actions = ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl.LAUNCH_CAP_ENABLED is False
    assert all(v == 0 for v in ctrl._cap_active.values()), "sem flag sem cap"
    assert ctrl.last_authority.get(A.driver_id) != "launch_cap"
    assert N.LAUNCH_CAP_K == 0.8 and N.LAUNCH_CAP_S_CUT == 2950.0 \
        and N.LAUNCH_CAP_TMAX_S == 30.0, "constantes do prereg a3b8ff0"


def test_t6_offtrack_no_phantom_flag():
    """Regressão do smoke (3 violações de fase s0): carro OFF-TRACK na janela
    NÃO aciona o cap — flag fantasma = 0 (o rejoin sobrescreve th/brk; o cap
    não pode rotular). v_plan é plano ON-TRACK."""
    track, drivers, engine, ctrl = _build()
    half = track.width_m / 2.0
    A = drivers[0]
    _place(engine, track, A, 2700.0, v=50.0)
    # joga PARA FORA (lat > meia-largura, lado +lat) mantendo a mesma s
    wps = np.asarray(track.waypoints, dtype=np.float64)
    AB = np.roll(wps, -1, axis=0) - wps
    seg = np.hypot(AB[:, 0], AB[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(seg)])[:-1]
    s0 = 2700.0 % float(seg.sum())
    j = int(np.searchsorted(cum, s0, side="right") - 1) % len(wps)
    t0 = (s0 - cum[j]) / (seg[j] + 1e-9)
    x = wps[j, 0] + t0 * AB[j, 0]
    y = wps[j, 1] + t0 * AB[j, 1]
    yaw = math.atan2(AB[j, 1], AB[j, 0])
    L = seg[j]
    nx, ny = -AB[j, 1] / L, AB[j, 0] / L
    off = half + 3.0
    engine.physics.set_position(engine.handles[A.driver_id],
                                pos=(x + nx * off, y + ny * off, 0.5),
                                yaw_rad=yaw, reset_vel=True)
    import pybullet as pb
    pb.resetBaseVelocity(engine.handles[A.driver_id].chassis_id,
                         linearVelocity=[50 * math.cos(yaw), 50 * math.sin(yaw), 0.0],
                         physicsClientId=engine.physics._client_id)
    ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl._cap_active.get(A.driver_id) == 0, "off-track: sem flag fantasma"
    assert ctrl.last_authority.get(A.driver_id) == "rejoin", "off-track: rejoin rotula"
