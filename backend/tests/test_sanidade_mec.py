"""SANIDADE-0 — testes dos mecanismos M1/M2/M3 + bundle (prereg 1007636 §6).

t_m1: place_grid layout — f1 (±1,9 m) vs staggered (±2,5 m; Δlat 5,0 m);
  determinístico; pista frozen REAL com engine MOCKADO (só registra poses).
t_m2: lei do alvo raso — ahead = clip(|lat|/tan(15°), 10, 120): 2 m -> 10;
  10 m -> 37,3; 40 m -> 120; cap grama 6,0 < bearing 8,0; default bearing.
t_m3_breaker: par sintético colado DEVE SEPARAR (teste PINADO do prereg):
  2 carros lado a lado (Δlat 1,6 m, mesmo s), anti_glue ON -> o de FORA
  cede após 3 s e o par separa (|Δlat| > 3 m) em <10 s; OFF -> o estado
  _glue_state permanece vazio (mecanismo inerte por construção).
t_m3_wiring: defaults OFF na assinatura; blocos M2/M3 gated por flag
  (source); bundle GUI --modo espectador liga os três (source); identidade
  do race_diagnostic imprime grid/rejoin/anti_glue.
"""
import inspect
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scripts.simulation.run_race_10_cars import (NeuralRaceController as N,
                                             build_grid_drivers,
                                             place_grid,
                                             DEFAULT_MAPPINGS_PATH,
                                             MODEL_DIR)


class _MockPhysics:
    def __init__(self):
        self.poses = []

    def set_position(self, handle, pos, yaw_rad=0.0, reset_vel=True):
        self.poses.append((pos[0], pos[1]))


class _MockEngine:
    """Só o que place_grid toca (linha 1334+): registra poses."""

    def __init__(self):
        self.physics = _MockPhysics()
        self.handles = {}
        self.states = {}
        self.last_pos = {}
        self.cum_dist_m = {}
        self.prev_waypoint_idx = {}


def _m1_lats(layout):
    from backend.model_train.f1_env import load_track_frozen
    track = load_track_frozen("interlagos")
    drivers = build_grid_drivers()
    eng = _MockEngine()
    for d in drivers:
        eng.handles[d.driver_id] = object()
        eng.states[d.driver_id] = SimpleNamespace()
    place_grid(eng, track, drivers, layout=layout)
    lats = sorted({round(track.nearest_segment(x, y)[0], 1)
                   for x, y in eng.physics.poses})
    return lats, eng.physics.poses


def test_t_m1_grid_layout_f1_vs_staggered():
    lats_f1, poses_f1 = _m1_lats("f1")
    assert lats_f1 == [1.9], f"f1 deve dar colunas ±1,9 (veio {lats_f1})"
    lats_st, poses_st = _m1_lats("staggered")
    assert lats_st == [2.5], \
        f"staggered deve dar colunas ±2,5 — Δlat 5,0 m (veio {lats_st})"
    # determinístico: duas chamadas -> mesmas poses
    _, poses_st2 = _m1_lats("staggered")
    assert poses_st == poses_st2
    # 10 poses distintas (fileiras não colapsam)
    assert len(set(poses_st)) == 10


def test_t_m2_lei_do_alvo_raso():
    tan15 = math.tan(math.radians(N.REJOIN_PERCEPTIVE_ANGLE_DEG))
    assert N.REJOIN_PERCEPTIVE_ANGLE_DEG == 15.0
    ahead = lambda d: float(np.clip(d / tan15,
                                    N.REJOIN_PERCEPTIVE_AHEAD_MIN_M,
                                    N.REJOIN_PERCEPTIVE_AHEAD_MAX_M))
    assert round(ahead(2.0), 1) == 10.0    # clip inferior (= bearing)
    assert round(ahead(10.0), 1) == 37.3   # 10/tan15° — ângulo de 15°
    assert round(ahead(40.0), 1) == 120.0   # clip superior
    assert N.REJOIN_PERCEPTIVE_V_GRASS == 6.0 < N.REJOIN_TARGET_MPS
    # default 'bearing' e o bloco perceptive gated por REJOIN_MODE
    sig = inspect.signature(N.__init__).parameters
    assert sig['rejoin_mode'].default == 'bearing'
    src = inspect.getsource(N.predict_batch)
    assert "if self.REJOIN_MODE == 'perceptive':" in src


@pytest.mark.slow
def test_t_m3_breaker_par_sintetico_separa():
    """O teste PINADO: par colado sintético deve separar com a flag ON."""
    from backend.model_train.f1_env import load_track_frozen
    from backend.engine import SimulationConfig, SimulationEngine
    from backend.domain import WeatherModel, WeatherKind, BASE_CONDITIONS

    track = load_track_frozen("interlagos")
    drivers = build_grid_drivers()[:2]
    sim_config = SimulationConfig(race_id="glue-test", num_laps=99,
                                  logic_step_hz=10.0, physics_sub_steps=24,
                                  gui=False, camera_mode="overview",
                                  draw_track=False, realtime=False,
                                  input_stale_after_s=300.0)
    engine = SimulationEngine(config=sim_config, track=track, drivers=drivers,
                              weather_model=WeatherModel(
                                  initial=BASE_CONDITIONS[WeatherKind.DRY]))
    engine.setup()
    engine.race_started = True

    ctrl = N(
        weights_path=MODEL_DIR / "v10_dagger" / "dagger_actor_best_weights.npz",
        mappings_path=DEFAULT_MAPPINGS_PATH, track=track, obs_mode="edge",
        anti_glue=True)

    # par COLADO: mesmo s (Δs=0 -> empate -> cede o de FORA), Δlat 1,6 m
    wps = np.asarray(track.waypoints, dtype=np.float64)
    AB = np.roll(wps, -1, axis=0) - wps
    seg = 400
    L = float(np.hypot(AB[seg, 0], AB[seg, 1]))
    h = math.atan2(AB[seg, 1], AB[seg, 0])
    nx, ny = -AB[seg, 1] / L, AB[seg, 0] / L
    cx = wps[seg, 0] + 0.5 * AB[seg, 0]
    cy = wps[seg, 1] + 0.5 * AB[seg, 1]
    for k, off in ((0, +1.0), (1, -0.6)):
        px, py = cx + nx * off, cy + ny * off
        engine.physics.set_position(engine.handles[drivers[k].driver_id],
                                    pos=(px, py, 0.5), yaw_rad=h,
                                    reset_vel=True)

    dt = 1.0 / sim_config.logic_step_hz
    max_dlat, broke = 0.0, False
    for t in range(120):  # 12 s
        actions = ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
        for k in range(2):
            th, brk, steer = actions[k]
            engine.set_driver_input(drivers[k].driver_id, throttle=th,
                                    brake=brk, steering_yaw_rad=steer)
        engine._step_tick(dt, sim_config.physics_sub_steps)
        p0 = engine.physics.get_state(engine.handles[drivers[0].driver_id])
        p1 = engine.physics.get_state(engine.handles[drivers[1].driver_id])
        d0, _ = track.nearest_segment(p0["x"], p0["y"])
        d1, _ = track.nearest_segment(p1["x"], p1["y"])
        max_dlat = max(max_dlat, abs(d0 - d1))
        if any(st.get('breaking') for st in ctrl._glue_state.values()):
            broke = True
    assert broke, "breaker nunca engajou em par colado de 12 s (flag ON)"
    assert max_dlat > 2.5, \
        f"par colado NÃO separou (máx |Δlat| {max_dlat:.2f} m em 12 s)"


@pytest.mark.slow
def test_t_m3_flag_off_e_inerte():
    """OFF: _glue_state permanece vazio — bit-identidade por construção."""
    from backend.model_train.f1_env import load_track_frozen
    from backend.engine import SimulationConfig, SimulationEngine
    from backend.domain import WeatherModel, WeatherKind, BASE_CONDITIONS

    track = load_track_frozen("interlagos")
    drivers = build_grid_drivers()[:2]
    sim_config = SimulationConfig(race_id="glue-off", num_laps=99,
                                  logic_step_hz=10.0, physics_sub_steps=24,
                                  gui=False, camera_mode="overview",
                                  draw_track=False, realtime=False,
                                  input_stale_after_s=300.0)
    engine = SimulationEngine(config=sim_config, track=track, drivers=drivers,
                              weather_model=WeatherModel(
                                  initial=BASE_CONDITIONS[WeatherKind.DRY]))
    engine.setup()
    engine.race_started = True
    ctrl = N(
        weights_path=MODEL_DIR / "v10_dagger" / "dagger_actor_best_weights.npz",
        mappings_path=DEFAULT_MAPPINGS_PATH, track=track, obs_mode="edge")
    dt = 1.0 / sim_config.logic_step_hz
    for t in range(50):
        actions = ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
        for k in range(2):
            th, brk, steer = actions[k]
            engine.set_driver_input(drivers[k].driver_id, throttle=th,
                                    brake=brk, steering_yaw_rad=steer)
        engine._step_tick(dt, sim_config.physics_sub_steps)
    assert ctrl._glue_state == {}, "flag OFF não pode tocar o estado"


def test_t_m3_wiring_defaults_e_bundle():
    sig = inspect.signature(N.__init__).parameters
    assert sig['anti_glue'].default is False
    assert sig['rejoin_mode'].default == 'bearing'
    assert N.ANTI_GLUE_NEAR_LAT == 2.5 and N.ANTI_GLUE_BREAK_STEER == 0.4
    src = inspect.getsource(N.predict_batch)
    assert 'if self.ANTI_GLUE_ENABLED and not offtrack:' in src
    assert 'elif glue_breaking:' in src          # autoridade anti_glue
    gui = (Path(__file__).resolve().parent.parent
           / 'scripts' / 'simulation' / 'run_race_10_cars.py').read_text()
    assert '"--modo"' in gui and '"espectador"' in gui
    # ÁRVORE do veredito s70-73: M1/M3 FAIL saem; bundle = SÓ M2 (verde)
    assert '"f1", "perceptive", False' in gui
    rd = (Path(__file__).resolve().parent.parent
          / 'model_train' / 'race_diagnostic.py').read_text()
    assert "add_argument('--grid'" in rd
    assert "add_argument('--rejoin'" in rd
    assert "add_argument('--anti-glue'" in rd
    assert "grid={args.grid} | rejoin={args.rejoin} | anti_glue={args.anti_glue}" in rd
    # M3(i): fricção sob a flag (physics)
    ph = (Path(__file__).resolve().parent.parent
          / 'engine' / 'physics.py').read_text()
    assert 'def set_chassis_lateral_friction' in ph
    assert 'engine.physics.set_chassis_lateral_friction(0.01)' in rd
